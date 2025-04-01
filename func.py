import os
from flask import session
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://gnslsajivcvhjomcairx.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "randomrandomeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imduc2xzYWppdmN2aGpvbWNhaXJ4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMyNTU5NzMsImV4cCI6MjA1ODgzMTk3M30.nbrw9uWK2Uxmp92RmZCLZCp_aGIXBJJkieJzNewJW7g")  # Keep it secret!

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# check if user is logged in
def is_logged_in():
    user = supabase.auth.get_user()
    if user != None:
        return user
    return session.get("user",None)