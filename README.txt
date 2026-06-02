Export Shipment Management App V43

Important:
This version keeps your existing shipment_app.db data.
Do NOT delete shipment_app.db.

Updates:
- Removed New Payment Transaction button from Payment Entry.
- Coverage Dashboard product filter is bold, centered, with light background.
- Product filter moved to the left of Next Shipment Date.
- Coverage dashboard now shows filter + three main KPI items in one row.
- Multiple field filter is expanded and available for tables/grids/reports that use table helpers.
- Main login page logo spacing reduced to remove blank-looking area below logo.
- Windows 11 executable build instructions included in WINDOWS_EXE_GUIDE.txt.
- Existing database is preserved.

Run:
cd ~/export_shipment_app
pip install -r requirements.txt
rm -rf __pycache__
python3 unlock_database.py
streamlit run app.py

Do NOT delete shipment_app.db.
