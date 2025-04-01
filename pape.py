from flask import Flask, render_template, redirect, url_for, request, session, flash
import os
import json
import sys
from supabase import create_client, Client
from flask_wtf.csrf import CSRFProtect
from forms import LoginForm, UserForm, BookForm
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
        try:
            # Authenticate with Supabase
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            user_id = auth_response.user.id
            username = auth_response.user.user_metadata['username']

            text = f"User {username} logged in successfully with ID {user_id}"

            return redirect(url_for('dashboard'))

        except Exception as e:
            print('Error:', e, file=sys.stderr)

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

            response = supabase.table("users").insert({"id": auth_response.user.id, "username": username}).execute()
            
            return redirect(url_for('login'))
        except Exception as e:
            return render_template('signup.html', form=form, error=str(e))
    
    return render_template('signup.html', form=form)

@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    form = BookForm()
    user = supabase.auth.get_user()
    if user is None:
        return redirect(url_for("login"))
    else:
        if form.validate_on_submit():
            title = form.title.data
            pages = form.pages.data

            try:
                response = supabase.table("books").insert({
                    "title": title,
                    "pages": pages,
                }).execute()

                return redirect(url_for("dashboard"))
            except Exception as e:
                return f"Error adding book: {str(e)}"
        
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    form = BookForm()
    user = supabase.auth.get_user()
    
    if user is None:
        return redirect(url_for("login"))
    
    curr_user = supabase.table("users").select("*").eq("id", user.user.id).execute()
    points = curr_user.data[0]["points"]
    books = []
    response = (supabase.table("books").select("*").eq("user_id", user.user.id).execute())
    for book in response.data:
        book_id = book["id"]
        title = book["title"]
        pages = book["pages"]
        read = book["pages_read"]
        books.append({"id": book_id, "title": title, "pages": pages, "read": read})
    
    return render_template("dashboard.html", user=user, form=form, books=books, points=points)

@app.route("/update_pages/<book_id>", methods=["POST"])
def update_pages(book_id):
    user = supabase.auth.get_user()
    if user is None:
        return redirect(url_for("login"))
    
    pages_read = request.form.get("pages_read")

    curr_book = supabase.table("books").select("*").eq("user_id", user.user.id).eq("id", book_id).execute()
    curr_book_data = curr_book.data[0]
    total_pages = curr_book_data["pages"]
    curr_pages_read = curr_book_data["pages_read"]

    old_percent = int((curr_pages_read / total_pages) * 100)
    new_pages_read = curr_pages_read + int(pages_read)
    new_percent = int((new_pages_read / total_pages) * 100)

    old_milestone = old_percent // 10
    new_milestone = new_percent // 10
    milestone_reached = new_milestone - old_milestone

    if milestone_reached > 0:
        user_points = supabase.table("users").select("points").eq("id", user.user.id).execute()
        curr_points = user_points.data[0]["points"]
        points_per_milestone = 10
        new_points = curr_points + (milestone_reached * points_per_milestone)
        supabase.table("users").update({"points": new_points}).eq("id", user.user.id).execute()

    try:
        response = supabase.table("books").update({"pages_read": new_pages_read}).eq("user_id", user.user.id).eq("id", book_id).execute()
        return redirect(url_for("dashboard"))
    except Exception as e:
        return f"Error updating pages: {str(e)}"

@app.route("/remove_book/<int:book_id>")
def remove_book(book_id):
    user = supabase.auth.get_user()
    if user is None:
        return redirect(url_for("login"))
    
    try:
        response = supabase.table("books").delete().eq("user_id", user.user.id).eq("id", book_id).execute()
        return redirect(url_for("dashboard"))
    except Exception as e:
        return f"Error removing book: {str(e)}"

@app.route('/logout')
def logout():
    supabase.auth.sign_out()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
