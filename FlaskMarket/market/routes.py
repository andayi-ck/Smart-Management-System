from market import app, db, bcrypt
from flask import render_template, redirect, url_for, flash, get_flashed_messages, request, jsonify
from market.models import Item, User, Veterinary, Illness
from market.forms import RegisterForm, LoginForm, PurchaseItemForm
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime

import sqlite3

#@app.route('/')
# def hello_world():
#    return '<h1>Home Page</h1>'

@app.route('/')

def welcome_page():
    return render_template('welcome-page.html')


@app.route('/home')
def home_page():
    return render_template('home.html')
    #  we went on to call the home.html file as can be seen above.
    # 'render_template()' basically works by rendering files.


#@login_required
#below list of dictionaries is sent to the market page through the market.html
#       but we are going to look for a way to store information inside an organized
#       DATABASE which can be achieved through configuring a few things in our flask
#       application
# WE ARE THUS GOING TO USE SQLITE3 is a File WHich allows us to store information and we are going to
#   connect it to the Flask APplication.We thus have to install some flask TOOL THAT ENABLES THIS through the terminal


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        user_to_create = User(username=form.username.data,
                            email_address=form.email_address.data,
                            password_hash=form.password1.data)
        db.session.add(user_to_create)
        db.session.commit()
        login_user(user_to_create)
        flash(f"Account created successfully! You are now logged in as {user_to_create.username}", category='success')
        return redirect(url_for('welcome_page'))
    if form.errors != {}: #If there are not errors from the validations
        for err_msg in form.errors.values():
            #print(f'There was an error with creating a user: {err_msg}')
            flash(f'There was an error with creating a user: {err_msg}', category='danger')
            
    
    return render_template('html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(username=form.username.data).first()
        if attempted_user and attempted_user.check_password_correction(
                attempted_password=form.password.data
        ):
            login_user(attempted_user)
            flash(f'Success! You are logged in as: {attempted_user.username}', category='success')
            return redirect(url_for('livestock_dashboard'))
        else:
            flash('Username and password are not match! Please try again', category='danger')

    return render_template('login.html', form=form)

@app.route('/logout')
def logout_page():
    logout_user()
    flash("You have been logged out!", category='info')
    return redirect(url_for("home_page"))

#added this code for the search bar at the navbar in 'base.html'
@app.route('/search', methods=['GET'])
def search_results():
    query = request.args.get('animal', '').strip()

    if not query:
        return render_template('livestock_dashboard.html', error="Please enter an animal name.")

    conn = get_db_connection()
    cur = conn.cursor()

    # Get animal ID
    cur.execute("SELECT id FROM Animals WHERE LOWER(name) = LOWER(?)", (query,))
    animal = cur.fetchone()
    if not animal:
        conn.close()
        return render_template('livestock_dashboard.html', error=f"No data found for {query}.", animal=query)
    animal_id = animal['id']

    # Fetch static data (no age range)
    cur.execute("SELECT name AS species_name FROM Species WHERE animal_id = ?", (animal_id,))
    species = cur.fetchone()

    cur.execute("SELECT preferred_conditions AS habitat, temperature_range FROM Habitat WHERE animal_id = ?", (animal_id,))
    habitat = cur.fetchone()

    cur.execute("SELECT product_type AS produce FROM Produce WHERE animal_id = ?", (animal_id,))
    produce = cur.fetchone()

    # Fetch age-specific data
    cur.execute("SELECT age_range, feed_type, quantity_per_day FROM Feed WHERE animal_id = ?", (animal_id,))
    feeds = cur.fetchall()

    cur.execute("SELECT age_range, vaccine_name FROM VaccinationSchedule WHERE animal_id = ?", (animal_id,))
    vaccines = cur.fetchall()

    cur.execute("SELECT age_range, disease_name FROM Diseases WHERE animal_id = ?", (animal_id,))
    diseases = cur.fetchall()

    cur.execute("SELECT age_range, average_weight FROM WeightTracking WHERE animal_id = ?", (animal_id,))
    weights = cur.fetchall()

    cur.execute("SELECT age_range, supplement_name, dosage FROM AdditivesAndMinerals WHERE animal_id = ?", (animal_id,))
    supplements = cur.fetchall()

    conn.close()

    # Group age-specific data
    grouped_results = {}
    for table_data, key in [
        (feeds, 'feeds'), (vaccines, 'vaccines'), (diseases, 'diseases'),
        (weights, 'weights'), (supplements, 'supplements')
    ]:
        for row in table_data:
            age = row['age_range'] or 'Unknown'
            if age not in grouped_results:
                grouped_results[age] = {
                    'species_name': species['species_name'] if species else 'Not Available',
                    'habitat': habitat['habitat'] if habitat else 'Not Available',
                    'temperature_range': habitat['temperature_range'] if habitat else 'Not Available',
                    'produce': produce['produce'] if produce else 'Not Available',
                    'feeds': [], 'vaccines': [], 'diseases': [], 'weights': [], 'supplements': []
                }
            if key == 'feeds':
                grouped_results[age]['feeds'].append({'feed_type': row['feed_type'], 'quantity_per_day': row['quantity_per_day']})
            elif key == 'vaccines':
                grouped_results[age]['vaccines'].append(row['vaccine_name'])
            elif key == 'diseases':
                grouped_results[age]['diseases'].append(row['disease_name'])
            elif key == 'weights':
                grouped_results[age]['weights'].append(row['average_weight'])
            elif key == 'supplements':
                grouped_results[age]['supplements'].append({'supplement_name': row['supplement_name'], 'dosage': row['dosage']})

    if not grouped_results:
        return render_template('livestock_dashboard.html', error=f"No detailed data found for {query}.", animal=query)

    return render_template('livestock_dashboard.html', grouped_results=grouped_results, animal=query)
# Function to connect to SQLite
def get_db_connection():
    conn = sqlite3.connect('C:/Users/ADMIN/.vscode/.vscode/FlaskMarket/market.db')
    conn.row_factory = sqlite3.Row  # Allows fetching results as dictionaries
    return conn


# Age Calculator Route
@app.route('/livestock_dashboard/age_calculator', methods=['POST'])
def age_calculator():
    try:
        # Get form data
        dob_str = request.form['dob']
        calc_date_str = request.form['calc_date']
        format_choice = request.form['format_choice']

        # Convert strings to datetime objects
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        calc_date = datetime.strptime(calc_date_str, '%Y-%m-%d')

        # Validate dates
        if calc_date < dob:
            return jsonify({"error": "Calculate date must be after date of birth."})

        # Use relativedelta for precise age calculation
        delta = relativedelta(calc_date, dob)

        # Format result based on choice
        if format_choice == 'days':
            total_days = (calc_date - dob).days
            result = f"{total_days} days"
        elif format_choice == 'weeks':
            total_days = (calc_date - dob).days
            weeks = total_days // 7
            result = f"{weeks} weeks"
        elif format_choice == 'months':
            months = delta.years * 12 + delta.months
            result = f"{months} months"
        elif format_choice == 'years':
            years = delta.years
            result = f"{years} years"
        elif format_choice == 'ymd':
            result = f"{delta.years} years, {delta.months} months, {delta.days} days"

        return jsonify({"result": result})

    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYY-MM-DD."})




def get_animal_info(animal_name):
    conn = sqlite3.connect('C:/Users/ADMIN/.vscode/.vscode/FlaskMarket/market.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM animals WHERE LOWER(name) = LOWER(?)", (animal_name,))
    animal = cursor.fetchone()
    conn.close()
    return animal


@app.route('/Privacy_page')
def Privacy_page():
    return render_template('Privacy_page.html')

@app.route('/nearby-vets')
def nearby_vets():
    return render_template('nearby-vets.html')


@app.route('/home2_page')
def home2_page():
    return render_template('home2.html')


@app.route('/livestock_dashboard')
def livestock_dashboard():
    return render_template('livestock_dashboard.html')

@app.route('/near-veterinaries')
def near_veterinaries():
    return render_template('near-veterinaries.html')



@app.route('/symptom-checker', methods=['GET', 'POST'])
def symptom_checker():
    form = SymptomCheckerForm()
    result = None
    recommended_vet = None

    if form.validate_on_submit():
        user_symptoms = [symptom.strip().lower() for symptom in form.symptoms.data.split(',')]
        illnesses = Illness.query.all()
        best_match = None
        max_matches = 0

        for illness in illnesses:
            illness_symptoms = [symptom.strip().lower() for symptom in illness.symptoms.split(',')]
            matches = len(set(user_symptoms) & set(illness_symptoms))
            if matches > max_matches:
                max_matches = matches
                best_match = illness

        if best_match and max_matches > 0:
            result = {
                'illness': best_match.name,
                'matched_symptoms': max_matches,
                'total_symptoms': len(best_match.symptoms.split(',')),
                'required_specialist': best_match.required_specialist
            }
            recommended_vet = Veterinary.query.filter_by(specialty=best_match.required_specialist).first()
            if not recommended_vet:
                flash("No veterinary found for this specialty.", category='warning')
        else:
            flash("No matching illness found for the given symptoms.", category='danger')

    return render_template('symptom_checker.html', form=form, result=result, recommended_vet=recommended_vet)


@app.route('/connect-farmers')
def connect_farmers():
    farmers = Farmer.query.all()
    return render_template('connect-farmers.html', farmers=farmers)




    
@app.route('/search_vets', methods=['POST'])
def search_vets():
    data = request.get_json()
    vet_name = data.get('vetName', '').lower()
    specialty = data.get('specialty', '').lower()
    clinic = data.get('clinic', '').lower()
    animal_type = data.get('animalType', '').lower()

    # Build the query
    query = Vet.query

    # Filter by vet name
    if vet_name:
        query = query.filter(Vet.name.ilike(f'%{vet_name}%'))

    # Filter by specialty (disease expertise)
    if specialty:
        # Remove common suffixes like "expert" or "specialist" for broader matching
        specialty_keywords = [specialty]
        for suffix in ['expert', 'specialist']:
            if specialty.endswith(suffix):
                specialty_keywords.append(specialty.replace(suffix, '').strip())
        # Search for any of the keywords in the specialty field
        specialty_conditions = [Vet.specialty.ilike(f'%{keyword}%') for keyword in specialty_keywords]
        query = query.filter(or_(*specialty_conditions))

    # Filter by clinic (locality)
    if clinic:
        query = query.filter(Vet.clinic.ilike(f'%{clinic}%'))

    # Filter by animal type (specific animal or category)
    if animal_type:
        # Map animals to categories and keywords
        animal_category_map = {
            'dog': ['dog', 'small animals', 'mammal'],
            'cat': ['cat', 'small animals', 'mammal'],
            'cow': ['cow', 'large animals', 'mammal'],
            'horse': ['horse', 'large animals', 'mammal'],
            'pig': ['pig', 'large animals', 'mammal'],
            'goat': ['goat', 'large animals', 'mammal'],
            'sheep': ['sheep', 'large animals', 'mammal'],
            'parrot': ['parrot', 'avian', 'bird'],
            'chicken': ['chicken', 'avian', 'bird'],
            'rabbit': ['rabbit', 'small animals', 'mammal'],
            'hamster': ['hamster', 'small animals', 'mammal']
        }

        # Get the list of keywords to search for in specialty
        search_keywords = animal_category_map.get(animal_type, [animal_type])
        animal_conditions = [Vet.specialty.ilike(f'%{keyword}%') for keyword in search_keywords]
        query = query.filter(or_(*animal_conditions))

    vets = query.all()

    # Convert vets to a JSON-serializable format
    vet_list = [{
        'id': vet.id,
        'name': vet.name,
        'specialty': vet.specialty,
        'clinic': vet.clinic,
        'experience': vet.experience,
        'availability': vet.availability,
        'accepting': vet.accepting,
        'rating': vet.rating,
        'price': vet.price,
        'image_url': vet.image_url
    } for vet in vets]

    return jsonify({'vets': vet_list})



@app.route('/admin/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if current_user.role != 'admin':
        flash('Unauthorized access. Only admins can create events.', 'error')
        return redirect(url_for('home_page'))
    
    form = CreateEventForm()
    if form.validate_on_submit():
        event_date = datetime.combine(form.event_date.data, time(0, 0))
        new_event = Event(
            title=form.title.data,
            content=form.content.data,
            event_date=event_date
        )
        db.session.add(new_event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('home_page'))
    
    return render_template('create_event.html', form=form)




@app.route('/unsubscribe/<email>')
def unsubscribe(email):
    user = User.query.filter_by(email_address=email).first()
    if user and user.role == 'subscriber':
        db.session.delete(user)
        db.session.commit()
        flash('You have been unsubscribed successfully.', 'success')
    else:
        flash('Email not found or not a subscriber.', 'error')
    return redirect(url_for('home_page'))




@app.route('/analytics_dashboard')
def analytics_dashboard():
    return render_template('analytics_dashboard.html')

