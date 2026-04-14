import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv('local_secrets.env')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SECRET_KEY')

if not url or not key:
    print("Missing credentials")
    exit()

supabase: Client = create_client(url, key)

try:
    # Check cards table
    res = supabase.table("cards").select("count", count="exact").limit(1).execute()
    print(f"Total cards in Supabase: {res.count}")

    # Check settings
    settings = supabase.table("system_settings").select("*").execute()
    print(f"System Settings: {settings.data}")
except Exception as e:
    print(f"Error: {e}")
