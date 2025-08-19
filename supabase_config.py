# Supabase Configuration
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase credentials
SUPABASE_URL = "https://youohevduvkkptdcrmut.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvdW9oZXZkdXZra3B0ZGNybXV0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTU2MjgyOTQsImV4cCI6MjA3MTIwNDI5NH0.VTg8bqARO-R11D-vNw6epmK6XkGVrT05BcdXyOkBW24"

# Initialize Supabase client
from supabase import create_client, Client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

print("✅ Supabase client initialized successfully!")
print(f"URL: {SUPABASE_URL}")
print(f"Key: {SUPABASE_ANON_KEY[:20]}...")
