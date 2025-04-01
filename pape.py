from flask import Flask, render_template, redirect, url_for, request, session, flash
import os, sys
from supabase import create_client, Client
from flask_wtf.csrf import CSRFProtect
from forms import LoginForm, UserForm
from func import is_logged_in

# Supabase credentials
url: str = "https://gnslsajivcvhjomcairx.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imduc2xzYWppdmN2aGpvbWNhaXJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMyNTU5NzMsImV4cCI6MjA1ODgzMTk3M30.nbrw9uWK2Uxmp92RmZCLZCp_aGIXBJJkieJzNewJW7g"
supabase: Client = create_client(url, key)

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = "randomrandom"

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        print('form', file=sys.stderr)
        try:
            # Authenticate with Supabase
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            # Get user details from 'user' table
            user_response = supabase.table("user").select("*").eq("email", email).execute()
            user_data = user_response.data
            print(user_response, file=sys.stderr)

            if not user_data:
                print('usernotfound', file=sys.stderr)
                flash("User not found in database", 'login_error')
                return render_template('login.html', form=form)

            # Store user in session
            session["user"] = user_data[0]

            # Redirect to the user's home page
            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(str(e), 'login_error')

    else:
        print('else', file=sys.stderr)
        for fieldName, errorMessages in form.errors.items():
            for err in errorMessages:
                flash(f"Error in {fieldName}: {err}", 'login_error')

    return render_template('login.html', form=form, category='login_error')



@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = UserForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        username = form.username.data
        
        try:
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"username": username}}
            })
            
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('signup.html', form=form, error=str(e))
    
    return render_template('signup.html', form=form)


@app.route("/dashboard")
def dashboard():
    user = is_logged_in()
    if user is None:
        return redirect(url_for("login"))
     # Fetch all files uploaded by the user
    files_response = supabase.table('uploaded-file').select("*").eq('user_id', user["id"]).execute()
    files = files_response.data if files_response.data else []
    
    return render_template("dashboard.html", user=user, files=files)

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
