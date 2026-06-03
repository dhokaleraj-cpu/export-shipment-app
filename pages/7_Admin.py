from common import *

page_setup()

require_roles(('admin', 'super_admin'))
show_header('Admin Control Panel', 'Settings, User Management, Profile and Company Management')
admin_tabs = st.tabs(['Profile', 'User Management', 'Company Management', 'System Settings'])
with admin_tabs[0]:
    st.subheader('Profile')
    current_user = st.session_state.user
    st.write(f"User: **{current_user['username']}**")
    st.write(f"Role: **{current_user['role']}**")
    old_password = st.text_input('Current Password', type='password', key='profile_old_password')
    new_password = st.text_input('New Password', type='password', key='profile_new_password')
    if st.button('Change My Password', key='profile_change_password'):
        if verify_user(current_user['username'], old_password):
            execute_query('UPDATE users SET password_hash=? WHERE username=?', (hash_password(new_password), current_user['username']))
            st.success('Password changed successfully.')
        else:
            st.error('Current password is incorrect.')
with admin_tabs[1]:
    require_roles(('super_admin',))
    st.subheader('User Management')
    uc1, uc2, uc3, uc4 = st.columns(4)
    with uc1:
        new_username = st.text_input('New User Name', key='admin_new_username')
    with uc2:
        new_user_password = st.text_input('New User Password', type='password', key='admin_new_user_password')
    with uc3:
        new_user_role = st.selectbox('Role', ['user', 'admin', 'super_admin'], key='admin_new_user_role')
    with uc4:
        new_user_active = st.checkbox('Active', value=True, key='admin_new_user_active')
    if st.button('Create / Update User', key='admin_create_user'):
        if new_username and new_user_password:
            existing = fetch_all('SELECT id FROM users WHERE username=?', (new_username,))
            if existing:
                execute_query('UPDATE users SET password_hash=?, role=?, is_active=? WHERE username=?', (hash_password(new_user_password), new_user_role, int(new_user_active), new_username))
                st.success('User updated.')
            else:
                execute_query('INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)', (new_username, hash_password(new_user_password), new_user_role, int(new_user_active)))
                st.success('User created.')
        else:
            st.error('User name and password are required.')
    show_filtered_df(fetch_all('SELECT id, username, role, is_active FROM users ORDER BY id'), 'admin_users', total=False)
with admin_tabs[2]:
    st.subheader('Company Management')
    company_rows = fetch_all('SELECT * FROM company_settings WHERE id=1')
    company = company_rows[0] if company_rows else {}
    cc1, cc2 = st.columns(2)
    with cc1:
        company_name = st.text_input('Company Name', company.get('company_name', 'FOUR STAR INDUSTRIES PVT. LTD.'), key='company_name')
        company_phone = st.text_input('Company Phone', company.get('phone', '') or '', key='company_phone')
        company_email = st.text_input('Company Email', company.get('email', '') or '', key='company_email')
        company_website = st.text_input('Website', company.get('website', '') or '', key='company_website')
    with cc2:
        company_address = st.text_area('Company Address', company.get('address', '') or '', key='company_address')
        company_tax = st.text_input('Tax ID', company.get('tax_id', '') or '', key='company_tax')
        company_logo = st.text_input('Logo Path', company.get('logo_path', 'FSI_LOGO_new.png') or 'FSI_LOGO_new.png', key='company_logo')
    if st.button('Save Company Settings', key='save_company_settings'):
        execute_query('\n  INSERT INTO company_settings\n(id, company_name, address, phone, email, website, tax_id, logo_path)\nVALUES (1, ?, ?, ?, ?, ?, ?, ?)\nON CONFLICT (id)\nDO UPDATE SET\n    company_name = EXCLUDED.company_name,\n    address = EXCLUDED.address,\n    phone = EXCLUDED.phone,\n    email = EXCLUDED.email,\n    website = EXCLUDED.website,\n    tax_id = EXCLUDED.tax_id,\n    logo_path = EXCLUDED.logo_path\n                ', (company_name, company_address, company_phone, company_email, company_website, company_tax, company_logo))
        st.success('Company settings saved.')
with admin_tabs[3]:
    st.subheader('System Settings')
    st.info('Use this page for user, profile, and company settings. Email/WhatsApp notification settings remain under the Overdue Notification module.')
    st.write('Database: shipment_app.db')
    st.write('Uploads Folder: uploads/')
    if st.button('Run Database Unlock / Optimize', key='admin_optimize_db'):
        conn = get_connection()
        try:
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
            conn.execute('PRAGMA optimize')
            conn.commit()
            st.success('Database optimized.')
        finally:
            conn.close()

st.markdown('<div class="footer">COPYRIGHT BY FOUR STAR INDUSTRIES PVT. LTD.</div>', unsafe_allow_html=True)
