# import os
# from flask import Flask, render_template, redirect, url_for, request, session, flash
# import boto3
# from boto3.dynamodb.conditions import Key, Attr
# from werkzeug.security import generate_password_hash, check_password_hash
# from datetime import datetime, timedelta
# from decimal import Decimal
# import uuid
# import random
# import logging
# from functools import wraps

# # Application Configuration
# app = Flask(__name__)
# app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')  # Change this in production

# # Constants
# USERS_TABLE = 'travelgo_users'
# TRAINS_TABLE = 'trains'
# BOOKINGS_TABLE = 'bookings'
# SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN', '')

# # Database Setup
# dynamodb = boto3.resource(
#     'dynamodb',
#     aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
#     aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
#     region_name='ap-south-1'
# )

# users_table = dynamodb.Table(USERS_TABLE)
# trains_table = dynamodb.Table(TRAINS_TABLE)
# bookings_table = dynamodb.Table(BOOKINGS_TABLE)

# # SNS Client for Notifications
# sns_client = boto3.client(
#     'sns',
#     aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
#     aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
#     region_name='ap-south-1'
# )

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Sample Data (Replace with database queries in production)
# available_trains = [
#     {'id': 'TRN001', 'name': 'Express Rail', 'departure_time': '06:00 AM', 
#      'arrival_time': '10:00 AM', 'price': 800, 'class_options': ['Sleeper', 'AC3']},
#     {'id': 'TRN002', 'name': 'City Link', 'departure_time': '09:30 AM', 
#      'arrival_time': '01:30 PM', 'price': 750, 'class_options': ['Sleeper', 'AC2']},
#     {'id': 'TRN003', 'name': 'Night Rider', 'departure_time': '08:00 PM', 
#      'arrival_time': '06:00 AM', 'price': 1200, 'class_options': ['AC1', 'AC2', 'AC3']}
# ]

# available_buses = [
#     {'id': 'bus_001', 'name': 'Luxury Travels', 'time': '08:00 AM', 'price': 500, 'seats_available': 30},
#     {'id': 'bus_002', 'name': 'Speedy Express', 'time': '10:00 AM', 'price': 450, 'seats_available': 25},
#     {'id': 'bus_003', 'name': 'Comfort Bus', 'time': '01:00 PM', 'price': 550, 'seats_available': 20}
# ]

# available_flights = [
#     {'id': 'FLT101', 'name': 'AirConnect', 'departure_time': '07:00 AM', 
#      'arrival_time': '09:00 AM', 'price': 3500, 'class_options': ['Economy', 'Business']},
#     {'id': 'FLT102', 'name': 'SkyHigh', 'departure_time': '11:00 AM', 
#      'arrival_time': '01:00 PM', 'price': 4200, 'class_options': ['Economy', 'Premium Economy']},
#     {'id': 'FLT103', 'name': 'Global Wings', 'departure_time': '03:00 PM', 
#      'arrival_time': '05:00 PM', 'price': 5000, 'class_options': ['Economy', 'Business', 'First Class']}
# ]

# # Helper Functions
# def login_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if 'user' not in session:
#             flash('Please log in to access this page.', 'warning')
#             return redirect(url_for('login', next=request.url))
#         return f(*args, **kwargs)
#     return decorated_function

# def get_user_bookings(user_phone):
#     """Retrieve bookings for a specific user"""
#     try:
#         response = bookings_table.query(
#             IndexName='user_phone-index',
#             KeyConditionExpression=Key('user_phone').eq(user_phone)
#         )
#         return sorted(response['Items'], key=lambda x: x.get('booked_at', ''), reverse=True)
#     except Exception as e:
#         logger.error(f"Error fetching bookings: {str(e)}")
#         return []

# def create_booking(booking_data):
#     """Create a new booking in the database"""
#     try:
#         booking_id = str(uuid.uuid4())
#         booking_data['booking_id'] = booking_id
#         bookings_table.put_item(Item=booking_data)
#         return booking_id
#     except Exception as e:
#         logger.error(f"Failed to create booking: {str(e)}")
#         return None

# # Routes
# @app.before_request
# def make_session_permanent():
#     session.permanent = True
#     app.permanent_session_lifetime = timedelta(minutes=30)

# @app.route('/')
# def index():
#     return redirect(url_for('login'))

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         phone = request.form.get('phone')
#         password = request.form.get('password')
        
#         try:
#             response = users_table.get_item(Key={'phone': phone})
#             if 'Item' in response and check_password_hash(response['Item']['password'], password):
#                 session['user'] = phone
#                 flash('Login successful!', 'success')
#                 return redirect(url_for('home'))
            
#             flash('Invalid phone number or password', 'danger')
#         except Exception as e:
#             logger.error(f"Login error: {str(e)}")
#             flash('An error occurred during login', 'danger')
    
#     return render_template('login.html')

# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == 'POST':
#         phone = request.form.get('phone')
#         password = request.form.get('password')
        
#         if not phone or not password:
#             flash('Phone number and password are required', 'danger')
#             return redirect(url_for('signup'))
        
#         try:
#             users_table.put_item(
#                 Item={
#                     'phone': phone,
#                     'password': generate_password_hash(password),
#                     'created_at': datetime.utcnow().isoformat()
#                 },
#                 ConditionExpression='attribute_not_exists(phone)'
#             )
#             flash('Account created successfully! Please log in.', 'success')
#             return redirect(url_for('login'))
#         except users_table.meta.client.exceptions.ConditionalCheckFailedException:
#             flash('User with this phone number already exists.', 'danger')
#         except Exception as e:
#             logger.error(f"Signup error: {str(e)}")
#             flash('An error occurred during signup', 'danger')
    
#     return render_template('signup.html')

# @app.route('/home')
# @login_required
# def home():
#     user_bookings = get_user_bookings(session['user'])
#     return render_template('home.html', bookings=user_bookings, datetime=datetime)

# @app.route('/trains_search')
# @login_required
# def trains_search():
#     return render_template('trains_search.html')

# @app.route('/trains_select', methods=['POST'])
# @login_required
# def trains_select():
#     if request.method == 'POST':
#         source = request.form.get('source')
#         destination = request.form.get('destination')
#         travel_date = request.form.get('travel_date')
        
#         session['train_search_criteria'] = {
#             'source': source,
#             'destination': destination,
#             'travel_date': travel_date
#         }
        
#         return render_template('trains_select.html', 
#                             trains=available_trains, 
#                             source=source, 
#                             destination=destination, 
#                             travel_date=travel_date)
    
#     return redirect(url_for('home'))

# @app.route('/trains')
# @login_required
# def trains():
#     train_id = request.args.get('train_id')
#     if not train_id:
#         return redirect(url_for('trains_search'))
    
#     search_criteria = session.get('train_search_criteria', {})
#     return render_template('trains_booking.html',
#                          train_id=train_id,
#                          source=search_criteria.get('source'),
#                          destination=search_criteria.get('destination'),
#                          travel_date=search_criteria.get('travel_date'))

# # Similar structure for buses and flights routes...

# @app.route('/booking', methods=['POST'])
# @login_required
# def booking():
#     booking_type = request.form.get('booking_type')
#     if not booking_type:
#         flash('Invalid booking type', 'danger')
#         return redirect(url_for('home'))
    
#     booking_data = {
#         'user_phone': session['user'],
#         'type': booking_type,
#         'booked_at': datetime.utcnow().isoformat(),
#         'data': request.form.to_dict()
#     }
    
#     # Set type-specific fields
#     if booking_type == 'hotels':
#         booking_data.update({
#             'destination': booking_data['data'].get('location'),
#             'start_date': booking_data['data'].get('check_in'),
#             'end_date': booking_data['data'].get('check_out')
#         })
#     elif booking_type in ['trains', 'buses']:
#         booking_data.update({
#             'destination': booking_data['data'].get('destination'),
#             'start_date': booking_data['data'].get('travel_date')
#         })
#     elif booking_type == 'flights':
#         booking_data.update({
#             'destination': booking_data['data'].get('destination'),
#             'start_date': booking_data['data'].get('departure_date'),
#             'end_date': booking_data['data'].get('return_date')
#         })
    
#     booking_id = create_booking(booking_data)
#     if booking_id:
#         session['booking_details'] = {
#             'type': booking_type,
#             'data': booking_data['data'],
#             'booking_id': booking_id
#         }
#         return render_template('booking.html', booking_data=booking_data)
    
#     flash('Failed to create booking. Please try again.', 'danger')
#     return redirect(url_for('home'))

# @app.route('/confirm_booking', methods=['POST'])
# @login_required
# def confirm_booking():
#     if 'booking_details' not in session:
#         flash('No booking to confirm', 'danger')
#         return redirect(url_for('home'))
    
#     session['payment_method'] = request.form.get('payment_method')
#     return redirect(url_for('payment_success'))

# @app.route('/payment_success')
# @login_required
# def payment_success():
#     if 'booking_details' not in session:
#         flash('No booking found', 'danger')
#         return redirect(url_for('home'))
    
#     try:
#         logger.info(f"Booking confirmed for {session['user']}")
#     except Exception as e:
#         logger.error(f"Failed to send notification: {str(e)}")
    
#     booking_details = session.pop('booking_details', {})
#     return render_template('payment_success.html', booking_details=booking_details)

# @app.route('/cancel_booking/<booking_id>', methods=['POST'])
# @login_required
# def cancel_booking(booking_id):
#     try:
#         bookings_table.delete_item(
#             Key={'booking_id': booking_id},
#             ConditionExpression='user_phone = :user',
#             ExpressionAttributeValues={':user': session['user']}
#         )
#         flash('Booking cancelled successfully', 'success')
#     except Exception as e:
#         logger.error(f"Failed to cancel booking: {str(e)}")
#         flash('Failed to cancel booking', 'danger')
    
#     return redirect(url_for('home'))

# @app.route('/logout')
# def logout():
#     session.clear()
#     flash('You have been logged out', 'info')
#     return redirect(url_for('login'))

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)

###-----------------------------


import os
from flask import Flask, render_template, redirect, url_for, request, session, flash
import boto3
from boto3.dynamodb.conditions import Key
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
import logging
from functools import wraps

# Application Configuration
app = Flask(__name__)

# Constants
USERS_TABLE = 'travelgo_user'
TRAINS_TABLE = 'trains'
BOOKINGS_TABLE = 'bookings'
SNS_TOPIC_ARN = os.getenv('arn:aws:sns:us-east-1:491085421614:Travelgo:f8f735ac-4d75-4125-8525-ef8cac33cf42')

# AWS Services - Using IAM role credentials automatically
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
sns_client = boto3.client('sns', region_name='us-east-1')

# DynamoDB Tables
users_table = dynamodb.Table(USERS_TABLE)
trains_table = dynamodb.Table(TRAINS_TABLE)
bookings_table = dynamodb.Table(BOOKINGS_TABLE)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample Data - In production, replace with actual DynamoDB queries
available_trains = [
    {'id': 'TRN001', 'name': 'Express Rail', 'departure_time': '06:00 AM'}
]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def notify_sns(message, subject):
    """Generic SNS notification function"""
    if not SNS_TOPIC_ARN:
        logger.warning("No SNS topic configured - skipping notification")
        return False
    
    try:
        response = sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=subject
        )
        logger.info(f"Notification sent: {response['MessageId']}")
        return True
    except Exception as e:
        logger.error(f"SNS notification failed: {str(e)}")
        return False

def get_user_bookings(user_phone):
    """Get bookings directly using partition key scan"""
    try:
        response = bookings_table.query(
            KeyConditionExpression=Key('user_phone').eq(user_phone)
        )
        return sorted(response['Items'], key=lambda x: x['booked_at'], reverse=True)
    except Exception as e:
        logger.error(f"Booking query failed: {str(e)}")
        return []

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=30)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        try:
            response = users_table.get_item(Key={'phone': phone})
            if 'Item' in response and check_password_hash(response['Item']['password'], password):
                session['user'] = phone
                notify_sns(f"User {phone} logged in", "Login Notification")
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            
            flash('Invalid credentials', 'danger')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('Login failed. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        if not phone or not password:
            flash('Both fields are required', 'danger')
            return redirect(url_for('signup'))
        
        try:
            users_table.put_item(
                Item={
                    'phone': phone,
                    'password': generate_password_hash(password),
                    'created_at': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_not_exists(phone)'
            )
            notify_sns(f"New user registered: {phone}", "New User Signup")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logger.error(f"Signup failed: {str(e)}")
            flash('Registration failed. Phone number may already exist.', 'danger')
    
    return render_template('signup.html')

@app.route('/home')
@login_required
def home():
    bookings = get_user_bookings(session['user'])
    return render_template('home.html', bookings=bookings)

@app.route('/book', methods=['POST'])
@login_required
def book():
    booking_data = {
        'user_phone': session['user'],
        'booking_id': str(uuid.uuid4()),
        'booked_at': datetime.utcnow().isoformat(),
        'details': request.form.to_dict()
    }
    
    try:
        bookings_table.put_item(Item=booking_data)
        notify_sns(f"New booking created: {booking_data['booking_id']}", "New Booking")
        flash('Booking successful!', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Booking failed: {str(e)}")
        flash('Booking failed. Please try again.', 'danger')
        return redirect(url_for('home'))

@app.route('/cancel/<booking_id>', methods=['POST'])
@login_required
def cancel(booking_id):
    try:
        response = bookings_table.delete_item(
            Key={'user_phone': session['user'], 'booking_id': booking_id},
            ReturnValues='ALL_OLD'
        )
        
        if 'Attributes' in response:
            notify_sns(f"Booking canceled: {booking_id}", "Booking Canceled")
            flash('Booking canceled', 'success')
        else:
            flash('Booking not found', 'warning')
    except Exception as e:
        logger.error(f"Cancel failed: {str(e)}")
        flash('Cancellation failed', 'danger')
    
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
