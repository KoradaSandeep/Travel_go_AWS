from flask import Flask, render_template, redirect, url_for, request, session
from datetime import datetime
import boto3
import uuid # For generating unique booking IDs
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a'

# AWS Configuration (replace with your actual region and SNS Topic ARN)
AWS_REGION = 'us-east-1'  # Example: Mumbai region
USERS_TABLE_NAME = 'travel_app_users'
BOOKINGS_TABLE_NAME = 'travel_app_bookings'
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:682033465674:Travelgo:074030e8-4ca8-4d4e-8717-5deb1bffeef6' # Replace with your SNS Topic ARN

# Initialize DynamoDB and SNS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns_client = boto3.client('sns', region_name=AWS_REGION)

users_table = dynamodb.Table(USERS_TABLE_NAME)
bookings_table = dynamodb.Table(BOOKINGS_TABLE_NAME)

# --- DynamoDB Helper Functions ---

def get_user_by_phone(phone):
    try:
        response = users_table.get_item(Key={'phone': phone})
        return response.get('Item')
    except ClientError as e:
        print(f"Error getting user: {e.response['Error']['Message']}")
        return None

def create_user(phone, password):
    try:
        users_table.put_item(
            Item={
                'phone': phone,
                'password': password
            },
            ConditionExpression='attribute_not_exists(phone)' # Ensure uniqueness
        )
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return False # User with this phone already exists
        print(f"Error creating user: {e.response['Error']['Message']}")
        return False

def get_user_bookings(user_phone):
    try:
        # Assuming a GSI on user_phone for efficient querying
        response = bookings_table.query(
            IndexName='UserPhoneIndex', # You'll need to create this GSI
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_phone').eq(user_phone),
            ScanIndexForward=False # Sort by booked_at in descending order
        )
        return response.get('Items', [])
    except ClientError as e:
        print(f"Error getting bookings for user {user_phone}: {e.response['Error']['Message']}")
        return []

def create_booking(booking_data):
    try:
        booking_id = str(uuid.uuid4())
        booking_data['_id'] = booking_id # DynamoDB doesn't use ObjectId, so we'll use a string UUID
        booking_data['booked_at'] = datetime.utcnow().isoformat() # Store as ISO format string
        bookings_table.put_item(Item=booking_data)
        return booking_id
    except ClientError as e:
        print(f"Error creating booking: {e.response['Error']['Message']}")
        return None

def delete_booking_by_id(booking_id):
    try:
        bookings_table.delete_item(Key={'_id': booking_id})
        return True
    except ClientError as e:
        print(f"Error deleting booking: {e.response['Error']['Message']}")
        return False

def publish_sns_message(subject, message):
    try:
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=subject
        )
        print(f"SNS message published: {response['MessageId']}")
        return True
    except ClientError as e:
        print(f"Error publishing SNS message: {e.response['Error']['Message']}")
        return False

# --- Flask Routes (largely unchanged, but using DynamoDB helpers) ---

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        user = get_user_by_phone(phone)
        if user and user['password'] == password:
            session['user'] = phone
            return redirect(url_for('home'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        if not create_user(phone, password):
            return "User with this phone number already exists. Please login or use a different phone number."
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    current_user_phone = session['user']
    user_bookings = get_user_bookings(current_user_phone)
    for booking in user_bookings:
        if 'booked_at' in booking:
            try:
                booking['booked_at'] = datetime.fromisoformat(booking['booked_at'])
            except ValueError:
                booking['booked_at'] = None # Handle potential malformed dates
    return render_template('home.html', bookings=user_bookings, datetime=datetime)

@app.route('/hotels')
def hotels():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('hotels.html')

@app.route('/trains_search')
def trains_search():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('trains_search.html')

@app.route('/trains_select', methods=['POST'])
def trains_select():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        travel_date = request.form['travel_date']
        session['train_search_criteria'] = {
            'source': source,
            'destination': destination,
            'travel_date': travel_date
        }
        available_trains = [
            {'id': 'TRN001', 'name': 'Express Rail', 'departure_time': '06:00 AM', 'arrival_time': '10:00 AM', 'price': 800, 'class_options': ['Sleeper', 'AC3']},
            {'id': 'TRN002', 'name': 'City Link', 'departure_time': '09:30 AM', 'arrival_time': '01:30 PM', 'price': 750, 'class_options': ['Sleeper', 'AC2']},
            {'id': 'TRN003', 'name': 'Night Rider', 'departure_time': '08:00 PM', 'arrival_time': '06:00 AM', 'price': 1200, 'class_options': ['AC1', 'AC2', 'AC3']}
        ]
        return render_template('trains_select.html', trains=available_trains, source=source, destination=destination, travel_date=travel_date)
    return redirect(url_for('home'))

@app.route('/trains')
def trains():
    if 'user' not in session:
        return redirect(url_for('login'))
    train_id = request.args.get('train_id')
    if not train_id:
        return redirect(url_for('trains_search'))
    search_criteria = session.get('train_search_criteria', {})
    return render_template('trains_booking.html',
                           train_id=train_id,
                           source=search_criteria.get('source'),
                           destination=search_criteria.get('destination'),
                           travel_date=search_criteria.get('travel_date'))

@app.route('/buses_search')
def buses_search():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('bus_search.html')

@app.route('/buses_select', methods=['POST'])
def buses_select():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        travel_date = request.form['travel_date']
        session['bus_search_criteria'] = {
            'source': source,
            'destination': destination,
            'travel_date': travel_date
        }
        available_buses = [
            {'id': 'bus_001', 'name': 'Luxury Travels', 'time': '08:00 AM', 'price': 500, 'seats_available': 30},
            {'id': 'bus_002', 'name': 'Speedy Express', 'time': '10:00 AM', 'price': 450, 'seats_available': 25},
            {'id': 'bus_003', 'name': 'Comfort Bus', 'time': '01:00 PM', 'price': 550, 'seats_available': 20}
        ]
        return render_template('bus_select.html', buses=available_buses, source=source, destination=destination, travel_date=travel_date)
    return redirect(url_for('home'))

@app.route('/buses')
def buses():
    if 'user' not in session:
        return redirect(url_for('login'))
    bus_id = request.args.get('bus_id')
    if not bus_id:
        return redirect(url_for('buses_search'))
    search_criteria = session.get('bus_search_criteria', {})
    bus_details = {
        'bus_001': {'total_seats': 40, 'occupied_seats': ['A3', 'B1', 'C4', 'D2']},
        'bus_002': {'total_seats': 35, 'occupied_seats': ['A1', 'B2', 'C3']},
        'bus_003': {'total_seats': 30, 'occupied_seats': ['A5', 'B6', 'C7', 'D8', 'E9']}
    }
    current_bus_info = bus_details.get(bus_id, {'total_seats': 30, 'occupied_seats': []})
    return render_template('buses.html',
                           bus_id=bus_id,
                           total_seats=current_bus_info['total_seats'],
                           occupied_seats=current_bus_info['occupied_seats'],
                           source=search_criteria.get('source'),
                           destination=search_criteria.get('destination'),
                           travel_date=search_criteria.get('travel_date'))

@app.route('/flights_search')
def flights_search():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('flights_search.html')

@app.route('/flights_select', methods=['POST'])
def flights_select():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        source = request.form['source']
        destination = request.form['destination']
        departure_date = request.form['departure_date']
        return_date = request.form.get('return_date')
        session['flight_search_criteria'] = {
            'source': source,
            'destination': destination,
            'departure_date': departure_date,
            'return_date': return_date
        }
        available_flights = [
            {'id': 'FLT101', 'name': 'AirConnect', 'departure_time': '07:00 AM', 'arrival_time': '09:00 AM', 'price': 3500, 'class_options': ['Economy', 'Business']},
            {'id': 'FLT102', 'name': 'SkyHigh', 'departure_time': '11:00 AM', 'arrival_time': '01:00 PM', 'price': 4200, 'class_options': ['Economy', 'Premium Economy']},
            {'id': 'FLT103', 'name': 'Global Wings', 'departure_time': '03:00 PM', 'arrival_time': '05:00 PM', 'price': 5000, 'class_options': ['Economy', 'Business', 'First Class']}
        ]
        return render_template('flights_select.html', flights=available_flights, source=source, destination=destination, departure_date=departure_date, return_date=return_date)
    return redirect(url_for('home'))

@app.route('/flights')
def flights():
    if 'user' not in session:
        return redirect(url_for('login'))
    flight_id = request.args.get('flight_id')
    if not flight_id:
        return redirect(url_for('flights_search'))
    search_criteria = session.get('flight_search_criteria', {})
    return render_template('flights_booking.html',
                           flight_id=flight_id,
                           source=search_criteria.get('source'),
                           destination=search_criteria.get('destination'),
                           departure_date=search_criteria.get('departure_date'),
                           return_date=search_criteria.get('return_date'))

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if 'user' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        current_user_phone = session['user']
        booking_type = request.form.get('booking_type')
        booking_data_from_form = request.form.to_dict()

        # Prepare the booking document for DynamoDB
        new_booking_doc = {
            'user_phone': current_user_phone,
            'type': booking_type,
            'data': booking_data_from_form
        }

        # Add specific fields based on booking type for better querying/display
        if booking_type == 'hotels':
            new_booking_doc['destination'] = booking_data_from_form.get('location')
            new_booking_doc['start_date'] = booking_data_from_form.get('check_in')
            new_booking_doc['end_date'] = booking_data_from_form.get('check_out')
        elif booking_type == 'trains':
            new_booking_doc['destination'] = booking_data_from_form.get('destination')
            new_booking_doc['start_date'] = booking_data_from_form.get('travel_date')
        elif booking_type == 'buses':
            new_booking_doc['destination'] = booking_data_from_form.get('destination')
            new_booking_doc['start_date'] = booking_data_from_form.get('travel_date')
        elif booking_type == 'flights':
            new_booking_doc['destination'] = booking_data_from_form.get('destination')
            new_booking_doc['start_date'] = booking_data_from_form.get('departure_date')
            new_booking_doc['end_date'] = booking_data_from_form.get('return_date')

        booking_id = create_booking(new_booking_doc)

        if booking_id:
            session['booking_details'] = {
                'type': booking_type,
                'data': booking_data_from_form,
                'booking_id': booking_id # Store the new booking ID
            }
            # Publish SNS message
            subject = f"New {booking_type.capitalize()} Booking Confirmation for {current_user_phone}"
            message = f"Booking ID: {booking_id}\nType: {booking_type}\nDetails: {booking_data_from_form}"
            publish_sns_message(subject, message)

            return render_template('booking.html')
        else:
            return "Failed to create booking. Please try again."
    return redirect(url_for('home'))

@app.route('/confirm_booking', methods=['POST'])
def confirm_booking():
    # In a real app, this would involve processing payment.
    # For this example, we directly go to payment_success after collecting method.
    if 'booking_details' not in session:
        return redirect(url_for('home'))
    session['payment_method'] = request.form['payment_method']
    return redirect(url_for('payment_success'))

@app.route('/payment_success')
def payment_success():
    if 'booking_details' not in session:
        return redirect(url_for('home'))
    return render_template('payment_success.html')

@app.route('/cancel_booking/<booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    if delete_booking_by_id(booking_id):
        # Optionally publish an SNS message for cancellation
        subject = f"Booking Cancellation for {session['user']}"
        message = f"Booking ID {booking_id} has been cancelled."
        publish_sns_message(subject, message)
        return redirect(url_for('home'))
    return "Failed to cancel booking. Please try again."

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('booking_details', None)
    session.pop('payment_method', None)
    session.pop('bus_search_criteria', None)
    session.pop('train_search_criteria', None)
    session.pop('flight_search_criteria', None)
    return redirect(url_for('login'))

@app.route('/others')
def others():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('others.html')

if __name__ == '__main__':
    app.run(debug=True)
