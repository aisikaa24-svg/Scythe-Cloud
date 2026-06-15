import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv('local_secrets.env')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SECRET_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing Supabase credentials.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    # Use exact=True to get the count
    res = supabase.table("cards").select("*", count="exact").limit(1).execute()
    print(f"Total cards in database: {res.count}")
except Exception as e:
    print(f"Error querying database: {e}")
