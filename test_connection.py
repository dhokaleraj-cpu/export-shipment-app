from db import supabase

try:
    result = supabase.table("shipments").select("*").limit(1).execute()
    print("SUCCESS")
    print(result.data)

except Exception as e:
    print("ERROR")
    print(e)
    