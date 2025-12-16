from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv 

# Indlæs miljøvariabler fra .env filen
load_dotenv() 

app = Flask(__name__)

# --- DATABASE KONFIGURATION VIA MILJØVARIABLER ---
DB_USER = os.environ.get("DATABASE_USER")
DB_PASSWORD = os.environ.get("DATABASE_PASSWORD")
DB_HOST = os.environ.get("DATABASE_HOST")
DB_PORT = os.environ.get("DATABASE_PORT")
DB_NAME = os.environ.get("DATABASE_NAME")
# -------------------------------------------------

# VIGTIGT: Vi bruger 'postgresql+psycopg2' for at specificere driveren (bedst praksis)
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

db = SQLAlchemy(app)


# --- HJÆLPEFUNKTION FOR TIMESTAMP KONSISTENS ---
def now_in_utc_to_second():
    """
    Returnerer den aktuelle tid i UTC, afrundet til nærmeste sekund.
    Dette matcher formatet 'YYYY-MM-DD HH:MM:SS' for konsistens.
    """
    now = datetime.utcnow()
    # Fjerner mikrosekunder
    return now - timedelta(microseconds=now.microsecond)


# --- DEFINITION AF DATABASENS MODEL (KundeData) ---
class KundeData(db.Model):
    __tablename__ = 'kunde_data' 
    id = db.Column(db.Integer, primary_key=True)
    
    # Kolonner matchende create_table.sql
    kunde_id = db.Column(db.Integer, nullable=False, default=42)
    # BRUG AF HJÆLPEFUNKTIONEN for at afrunde til sekunder:
    dato_tid = db.Column(db.DateTime, nullable=False, default=now_in_utc_to_second) 
    forbrug_kwh = db.Column(db.Numeric(10, 3), nullable=False, default=0.0)
    pris_pr_kwh = db.Column(db.Numeric(10, 4), nullable=False, default=0.0)
    donationsstatus = db.Column(db.String(10), nullable=False)


# --- FLASK ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/impact')
def impact_dashboard():
    return render_template('impact_dashboard.html')

@app.route('/start-onboarding')
def start_onboarding():
    return redirect(url_for('onboarding_step', step_number=1))

@app.route('/onboarding/<int:step_number>')
def onboarding_step(step_number):
    if step_number == 1:
        return render_template('onboarding_step1.html')
    elif step_number == 2:
        return render_template('onboarding_step2.html')
    elif step_number == 3:
        return render_template('onboarding_step3.html')
    elif step_number == 4:
        return render_template('onboarding_step4.html')
    elif step_number == 5:
        return render_template('onboarding_step5.html')
    else:
        return redirect(url_for('start_onboarding')) 

# NY RUTE TIL BEKRÆFTELSESSIDEN
@app.route('/complete')
def onboarding_complete():
    """Viser siden, der bekræfter, at opsætningen er færdig."""
    return render_template('onboarding_complete.html')


@app.route('/complete-onboarding', methods=['POST'])
def complete_onboarding():
    """
    Håndterer POST request fra Trin 5 og gemmer data i PostgreSQL.
    """
    income_choice = request.form.get('income_choice')
    
    # 1. Map valget til den ønskede status
    if income_choice == 'donation':
        db_status = 'aktiv' # Donér = aktiv donationsstatus
    elif income_choice == 'deferred_donation': 
        db_status = 'udsat' # Status: Passiv i 6 måneder, derefter aktiv.
    else:
        db_status = 'passiv' # Passiv indkomst = passiv donationsstatus

    # 2. Opret en ny række (objekt) til databasen
    new_entry = KundeData(
        # Vi hardkoder de nødvendige værdier for at opfylde skemaet i MVP'en
        kunde_id=43, 
        forbrug_kwh=0.0,
        pris_pr_kwh=0.0,
        donationsstatus=db_status # Bruger nu 'aktiv', 'passiv' eller 'udsat'
    )
    
    # 3. Gem objektet i databasen og commit transaktionen
    try:
        db.session.add(new_entry)
        db.session.commit()
        print(f"SUCCESS: Donationsstatus '{db_status}' gemt i bodil_energi_beam.")
    except Exception as e:
        db.session.rollback()
        print(f"FEJL ved gemning til DB: {e}")

    # 4. Redirect til den nye færdiggørelsesside
    return redirect(url_for('onboarding_complete')) # <--- PEGER NU PÅ DEN NYE SIDE

if __name__ == '__main__':
    app.run(debug=True)