from flask import Flask, render_template, redirect, url_for, request, session, flash
import os
import json
import sys
from supabase import create_client, Client
from flask_wtf.csrf import CSRFProtect
from forms import LoginForm, UserForm, BookForm
import logging

# Supabase credentials
url: str = "https://gnslsajivcvhjomcairx.supabase.co"
key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imduc2xzYWppdmN2aGpvbWNhaXJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMyNTU5NzMsImV4cCI6MjA1ODgzMTk3M30.nbrw9uWK2Uxmp92RmZCLZCp_aGIXBJJkieJzNewJW7g"
supabase: Client = create_client(url, key)

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = "randomrandom"

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

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

@app.route('/logout')
def logout():
    supabase.auth.sign_out()
    return redirect(url_for('login'))

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

    top_reward_resp = supabase.table("rewards").select("reward_name, points").eq("user_id", user.user.id).order("priority", desc=False).limit(1).execute()
    if len(top_reward_resp.data) != 0:
        top_reward = top_reward_resp.data[0]
    else:
        top_reward = None
        
    return render_template("dashboard.html", user=user, form=form, books=books, points=points, top_reward=top_reward)

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

@app.route("/rewards")
def rewards():
    user = supabase.auth.get_user()
    if user is None:
        return redirect(url_for("login"))
    
    form = BookForm()
    curr_user = supabase.table("users").select("*").eq("id", user.user.id).execute()
    points = curr_user.data[0]["points"]

    try:
        curr_rewards = supabase.table("rewards").select("*").eq("user_id", user.user.id).order('priority', desc=False).execute()
        rewards_data = curr_rewards.data

        rewards_claim = []
        for reward in rewards_data:
            if points < reward['points']:
                break
            rewards_claim.append(reward['id'])
        
    except Exception as e:
        return f"Error fetching rewards: {str(e)}"
    
    top_reward_resp = supabase.table("rewards").select("reward_name, points").eq("user_id", user.user.id).order("priority", desc=False).limit(1).execute()
    if len(top_reward_resp.data) != 0:
        top_reward = top_reward_resp.data[0]
    else:
        top_reward = None
        
    return render_template("rewards.html", user=user, rewards=rewards_data, points=points, form=form, top_reward=top_reward, rewards_claim=rewards_claim)

@app.route("/rewards/add", methods=["POST"])
def add_reward():
    user = supabase.auth.get_user()
    if user is None:
        return redirect(url_for("login"))
    
    reward_name = request.form.get("reward_name")
    points_required = request.form.get("points_required")

    try:
        priority_res = supabase.table("rewards").select("priority").eq("user_id", user.user.id).order('priority', desc=True).limit(1).execute()
        max_priority = 1

        if priority_res.data:
            max_priority = priority_res.data[0]["priority"] + 1

    except Exception as e:
        return f"Error fetching priority: {str(e)}"
    try:
        response = supabase.table("rewards").insert({
            "reward_name": reward_name,
            "points": points_required,
            "priority": max_priority,
            "user_id": user.user.id
        }).execute()
        return redirect(url_for("rewards"))
    except Exception as e:
        return f"Error adding reward: {str(e)}"
    
@app.route("/rewards/prioritise/<int:reward_id>", methods=["POST"])
def prioritise_reward(reward_id):
    user = supabase.auth.get_user()
    if user is None:
        return redirect(url_for("login"))
    
    try:
        priority_res = supabase.table("rewards").select("id, priority").eq("user_id", user.user.id).eq("id", reward_id).maybe_single().execute()
        target_reward = priority_res.data

        old_priority = target_reward["priority"]

        if old_priority == 1:
            return redirect(url_for("rewards"))
        
        reward_shift = supabase.table("rewards").select("id, priority").eq("user_id", user.user.id).lt("priority", old_priority).execute()
        rewards_to_shift = reward_shift.data

        for reward in sorted(rewards_to_shift, key=lambda x: x["priority"], reverse=True):
            updated_res = supabase.table("rewards").update({"priority": reward["priority"] + 1}).eq("id", reward["id"]).execute()

            updated_target = supabase.table("rewards").update({"priority": 1}).eq("id", reward_id).execute()

        return redirect(url_for("rewards"))
    
    except Exception as e:
        return f"Error fetching reward: {str(e)}"
    
@app.route('/rewards/remove/<int:reward_id>', methods=['POST'])
def remove_reward(reward_id):
    """Removes a reward and shifts subsequent priorities up."""
    if not supabase:
        flash("Database connection failed.", "error")
        return redirect(url_for('rewards'))

    user = supabase.auth.get_user()
    user_id = user.user.id
    if not user_id:
        flash("User not logged in.", "error")
        return redirect(url_for('login'))

    try:
        # --- Transactional Logic (Simulated) ---
        # Again, a stored procedure is recommended for atomicity.

        # 1. Get the reward to be removed to find its priority
        target_reward_resp = supabase.table('rewards') \
                                     .select('id, priority, reward_name') \
                                     .eq('user_id', user_id) \
                                     .eq('id', reward_id) \
                                     .maybe_single() \
                                     .execute()
        target_reward = target_reward_resp.data

        if not target_reward:
            flash("Reward not found or you don't have permission.", "error")
            return redirect(url_for('rewards'))

        removed_priority = target_reward['priority']
        removed_name = target_reward['reward_name']

        delete_resp = supabase.table('rewards') \
                              .delete() \
                              .eq('id', reward_id) \
                              .execute()

        if not delete_resp or ('error' in delete_resp and delete_resp['error'] is not None):
            error_details = delete_resp.get('error')
            flash(f"Failed to remove reward. Error: {error_details}", "error")
            logging.error(f"Failed to delete reward {reward_id} for user {user_id}. Response: {delete_resp}")
            return redirect(url_for('rewards'))


        logging.info(f"Deleted reward {reward_id} ('{removed_name}') for user {user_id}")

        rewards_to_shift_resp = supabase.table('rewards') \
                                      .select('id, priority') \
                                      .eq('user_id', user_id) \
                                      .gt('priority', removed_priority) \
                                      .execute()

        rewards_to_shift = rewards_to_shift_resp.data

        for reward in sorted(rewards_to_shift, key=lambda x: x['priority']):
            update_resp = supabase.table('rewards') \
                                .update({'priority': reward['priority'] - 1}) \
                                .eq('id', reward['id']) \
                                .execute()

        flash(f"Reward '{removed_name}' removed successfully!", "success")
        logging.info(f"Shifted priorities after removing reward {reward_id} for user {user_id}")


    except Exception as e:
        logging.error(f"Error removing reward {reward_id} for user {user_id}: {e}")
        flash(f"An error occurred during removal: {e}", "error")

    return redirect(url_for('rewards'))

@app.route('/rewards/claim/<int:reward_id>', methods=['POST'])
def claim_reward(reward_id):
    user = supabase.auth.get_user()
    if user is None:
        return redirect(url_for("login"))
    
    user_id = user.user.id

    try:
        user_resp = supabase.table("users").select("points").eq("id", user_id).execute()
        user_points = user_resp.data[0]["points"]

        logging.info(f"Retrieved user points: {user_points} for user {user_id}")

        reward_resp = supabase.table("rewards").select("points", "priority").eq("user_id", user_id).eq("id", reward_id).execute()
        
        reward_points = reward_resp.data[0]["points"]
        reward_priority = reward_resp.data[0]["priority"]

        logging.info(f"Retrieved reward priority: {reward_priority} for reward {reward_points}")

        if user_points < reward_points:
            flash("You don't have enough points to claim this reward.", "error")
            return redirect(url_for("rewards"))
        
        new_points = user_points - reward_points
        supabase.table("users").update({"points": new_points}).eq("id", user_id).execute()

        supabase.table("rewards").delete().eq("user_id", user_id).eq("id", reward_id).execute()

        logging.info(f"Deleted reward {reward_id} for user {user_id}")
        
        rewards_to_shift = supabase.table("rewards").select("id, priority").eq("user_id", user_id).gt("priority", reward_priority).execute().data
        
        for r in rewards_to_shift:
            supabase.table("rewards").update({"priority": r["priority"] - 1}).eq("id", r["id"]).execute()

        flash("Reward claimed successfully!", "success")
        return redirect(url_for("rewards"))
    

    except Exception as e:
        return f"Error fetching user points: {str(e)}"
    
    


if __name__ == "__main__":
    app.run(debug=True)
