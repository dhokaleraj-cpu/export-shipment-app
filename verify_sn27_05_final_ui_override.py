from pathlib import Path
APP_VERSION='SN 27.05'
common=Path('common.py').read_text(encoding='utf-8',errors='ignore')
config=Path('.streamlit/config.toml').read_text(encoding='utf-8',errors='ignore')
checks={'version_file':Path('APP_VERSION.txt').read_text().strip()==APP_VERSION,'final_override':'SN 27.05 final UI override marker' in common,'css':'sn27-05-final-ui' in common,'page_setup_overridden':common.rfind('def page_setup')>common.rfind('SN 27.05 FINAL UI OVERRIDE'),'shell':'sn27-shell' in common,'nav':'sn27-nav' in common,'title':'sn27-page' in common,'theme':'#0F6CBD' in config}
for k,v in checks.items(): print(k,v)
assert all(checks.values())
print('OK: SN 27.05 final UI override build is ready.')
