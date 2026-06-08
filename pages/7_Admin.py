from common import *

page_setup()

require_roles(('admin', 'super_admin'))

# --- Default View/Edit rules for Admin Page Controls ---
def _role_default_view(page, role):
    """Default page view permission by role."""
    if role == "super_admin":
        return True
    if role == "admin":
        return page.get("key") in [
            "dashboard", "masters", "shipment", "delivery",
            "payment", "coverage", "admin", "reports", "overdue"
        ]
    if role == "user":
        return page.get("key") in ["dashboard", "delivery", "coverage", "reports"]
    return False

def _role_default_edit(page, role):
    """Default page edit permission by role."""
    if role == "super_admin":
        return True
    if role == "admin":
        return page.get("key") in [
            "masters", "shipment", "delivery",
            "payment", "coverage", "reports", "overdue"
        ]
    if role == "user":
        return page.get("key") in ["delivery"]
    return False


show_header('Admin Control Panel', 'Settings, User Management, Profile and Company Management')
admin_tabs = st.tabs(['Profile', 'User Management', 'Page Controls', 'Company Management', 'System Settings'])
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
                execute_query('UPDATE users SET password_hash=?, role=?, is_active=? WHERE username=?', (hash_password(new_user_password), new_user_role, bool(new_user_active), new_username))
                st.success('User updated.')
            else:
                execute_query('INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)', (new_username, hash_password(new_user_password), new_user_role, bool(new_user_active)))
                st.success('User created.')
        else:
            st.error('User name and password are required.')
    show_filtered_df(fetch_all('SELECT id, username, role, is_active FROM users ORDER BY id'), 'admin_users', total=False)

    st.divider()
    st.subheader('Modify Existing User Details')
    st.info('Select one user, tick the fields you want to update, then save.')

    users_modify_rows = fetch_all('SELECT id, username, role, is_active FROM users ORDER BY username')
    if users_modify_rows:
        modify_labels = [f"{u['id']} | {u['username']} | {u['role']} | {'Active' if u.get('is_active') else 'Inactive'}" for u in users_modify_rows]
        selected_modify_label = searchable_selectbox('Select User to Modify', modify_labels, key='admin_modify_user_select')
        selected_modify_id = int(str(selected_modify_label).split('|')[0].strip())
        selected_modify_user = next((u for u in users_modify_rows if int(u['id']) == selected_modify_id), None)

        tick_username, tick_password, tick_role, tick_active = st.columns(4)
        with tick_username:
            update_username_tick = st.checkbox('Update User Name', key='tick_update_username')
        with tick_password:
            update_password_tick = st.checkbox('Update Password', key='tick_update_password')
        with tick_role:
            update_role_tick = st.checkbox('Update Role', key='tick_update_role')
        with tick_active:
            update_active_tick = st.checkbox('Update Active Status', key='tick_update_active')

        mu1, mu2, mu3, mu4 = st.columns(4)
        with mu1:
            modified_username = st.text_input('New / Current User Name', value=selected_modify_user.get('username','') if selected_modify_user else '', key='admin_modified_username')
        with mu2:
            modified_password = st.text_input('New Password', type='password', key='admin_modified_password')
        with mu3:
            current_role = selected_modify_user.get('role','user') if selected_modify_user else 'user'
            role_options = ['user', 'admin', 'super_admin']
            modified_role = st.selectbox('New / Current Role', role_options, index=role_options.index(current_role) if current_role in role_options else 0, key='admin_modified_role')
        with mu4:
            modified_active = st.checkbox('Active', value=bool(selected_modify_user.get('is_active')) if selected_modify_user else True, key='admin_modified_active')

        if st.button('Save Selected User Detail Changes', type='primary', key='admin_save_selected_user_detail_changes'):
            if not any([update_username_tick, update_password_tick, update_role_tick, update_active_tick]):
                st.warning('Please tick at least one field to update.')
            else:
                if update_username_tick and not modified_username.strip():
                    st.error('User Name cannot be blank.')
                elif update_password_tick and not modified_password.strip():
                    st.error('Password cannot be blank when password update is ticked.')
                else:
                    if update_username_tick:
                        execute_query('UPDATE users SET username=? WHERE id=?', (modified_username.strip(), selected_modify_id))
                    if update_password_tick:
                        execute_query('UPDATE users SET password_hash=? WHERE id=?', (hash_password(modified_password), selected_modify_id))
                    if update_role_tick:
                        execute_query('UPDATE users SET role=? WHERE id=?', (modified_role, selected_modify_id))
                    if update_active_tick:
                        execute_query('UPDATE users SET is_active=? WHERE id=?', (bool(modified_active), selected_modify_id))
                    clear_permission_cache()
                    st.success('Selected user details updated successfully.')
                    st.rerun()

with admin_tabs[2]:
    require_roles(('super_admin',))
    st.subheader('Page Wise User Controls - View / Edit')
    st.info('Set View and Edit permission separately for each module/page. Super Admin always has View and Edit access to all pages.')
    ensure_page_access_table()
    users_for_access = fetch_all('SELECT username, role, is_active FROM users ORDER BY username')
    if not users_for_access:
        st.warning('No users found.')
    else:
        user_labels = [f"{u['username']} | {u['role']}" for u in users_for_access]
        selected_user_label = st.selectbox('Select User for Page Access', user_labels, key='page_access_user_select')
        selected_username = selected_user_label.split(' | ')[0]
        selected_user_row = next((u for u in users_for_access if u['username'] == selected_username), None)
        existing_perms = get_user_page_permissions(selected_username)
        is_super_selected = bool(selected_user_row and selected_user_row.get('role') == 'super_admin')

        st.markdown('<div class="sap-grid-card"><div class="sap-grid-card-title">Page Wise View / Edit Permissions</div>', unsafe_allow_html=True)
        selected_view_values = {}
        selected_edit_values = {}

        header_cols = st.columns([2.4, 1, 1])
        with header_cols[0]:
            st.markdown('**Page / Module**')
        with header_cols[1]:
            st.markdown('**View**')
        with header_cols[2]:
            st.markdown('**Edit**')

        for page in APP_PAGE_DEFINITIONS:
            existing = existing_perms.get(page['key'], {})
            if is_super_selected:
                default_view = True
                default_edit = True
            elif isinstance(existing, dict) and page['key'] in existing_perms:
                default_view = bool(existing.get('can_view', False))
                default_edit = bool(existing.get('can_edit', False))
            else:
                default_view = selected_user_row.get('role') in page.get('default_roles', []) if selected_user_row else False
                default_edit = _role_default_edit(page, selected_user_row.get('role')) if selected_user_row else False

            row_cols = st.columns([2.4, 1, 1])
            with row_cols[0]:
                st.markdown(f"**{page['label']}**")
            with row_cols[1]:
                selected_view_values[page['key']] = st.checkbox(
                    'View',
                    value=bool(default_view),
                    key=f"view_{selected_username}_{page['key']}",
                    disabled=is_super_selected,
                    label_visibility='collapsed'
                )
            with row_cols[2]:
                selected_edit_values[page['key']] = st.checkbox(
                    'Edit',
                    value=bool(default_edit),
                    key=f"edit_{selected_username}_{page['key']}",
                    disabled=is_super_selected,
                    label_visibility='collapsed'
                )
        st.markdown('</div>', unsafe_allow_html=True)

        csave, creset = st.columns([1, 1])
        with csave:
            if st.button('Save View / Edit Controls', type='primary', key='save_page_controls'):
                for page in APP_PAGE_DEFINITIONS:
                    can_view = bool(selected_view_values[page['key']])
                    can_edit = bool(selected_edit_values[page['key']]) and can_view
                    execute_query("""
                        INSERT INTO user_page_access (username, page_key, can_access, can_view, can_edit, can_modify)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (username, page_key)
                        DO UPDATE SET
                            can_access=EXCLUDED.can_view,
                            can_view=EXCLUDED.can_view,
                            can_edit=EXCLUDED.can_edit,
                            updated_at=CURRENT_TIMESTAMP
                    """, (selected_username, page['key'], can_view, can_view, can_edit, can_modify))
                clear_cache_after_write()
                st.success('Page View / Edit controls saved successfully.')
                st.rerun()
        with creset:
            if st.button('Reset to Role Default', key='reset_page_controls'):
                execute_query('DELETE FROM user_page_access WHERE username=?', (selected_username,))
                clear_cache_after_write()
                st.success('Page controls reset to role defaults.')
                st.rerun()
        access_rows = fetch_all('SELECT username, page_key, can_view, can_edit, can_modify, updated_at FROM user_page_access ORDER BY username, page_key')
        if access_rows:
            st.markdown('<div class="sap-grid-card-title">Saved Page Access Records</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(access_rows), use_container_width=True, hide_index=True)

with admin_tabs[3]:
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
with admin_tabs[4]:
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


st.divider()
st.subheader("Page Wise Modify Rights")

try:
    execute_query("ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_modify BOOLEAN DEFAULT FALSE")
except Exception:
    pass

users_for_modify = fetch_all("SELECT id, username, role FROM users ORDER BY username")
if users_for_modify:
    user_labels_modify = [f"{u['id']} | {u['username']} | {u['role']}" for u in users_for_modify]
    selected_user_modify_label = searchable_selectbox("Select User for Modify Rights", user_labels_modify, key="modify_rights_user_select")
    selected_user_modify_id = int(str(selected_user_modify_label).split("|")[0].strip())

    st.markdown("Assign page-wise Modify rights. View/Edit rights remain unchanged.")
    page_defs_for_modify = PAGE_DEFINITIONS if 'PAGE_DEFINITIONS' in globals() else []
    modify_rows = []
    for pdef in page_defs_for_modify:
        page_key = pdef.get("key") if isinstance(pdef, dict) else pdef[0]
        page_label = pdef.get("label") if isinstance(pdef, dict) else pdef[1]
        existing = fetch_all(
            "SELECT can_view, can_edit, can_modify, can_modify FROM user_page_access WHERE user_id=? AND page_key=? LIMIT 1",
            (selected_user_modify_id, page_key)
        )
        row = existing[0] if existing else {}
        modify_rows.append({
            "page_key": page_key,
            "Page": page_label,
            "Can View": bool(row.get("can_view", False)),
            "Can Edit": bool(row.get("can_edit", False)),
            "Can Modify": bool(row.get("can_modify", False)),
            "Can Modify": bool(row.get("can_modify", False)),
        })

    modify_df = pd.DataFrame(modify_rows)
    edited_modify_df = st.data_editor(
        modify_df,
        use_container_width=True,
        hide_index=True,
        disabled=["page_key", "Page"],
        key="page_modify_rights_editor"
    )
    if st.button("Save Page Wise Modify Rights", type="primary", key="save_page_modify_rights"):
        for _, rr in edited_modify_df.iterrows():
            existing = fetch_all(
                "SELECT id FROM user_page_access WHERE user_id=? AND page_key=? LIMIT 1",
                (selected_user_modify_id, rr["page_key"])
            )
            if existing:
                execute_query(
                    "UPDATE user_page_access SET can_view=?, can_edit=?, can_modify=?, can_modify=? WHERE user_id=? AND page_key=?",
                    (bool(rr["Can View"]), bool(rr["Can Edit"]), bool(rr["Can Modify"]), selected_user_modify_id, rr["page_key"])
                )
            else:
                execute_query(
                    "INSERT INTO user_page_access (user_id, page_key, can_view, can_edit, can_modify, can_modify) VALUES (?, ?, ?, ?, ?)",
                    (selected_user_modify_id, rr["page_key"], bool(rr["Can View"]), bool(rr["Can Edit"]), bool(rr["Can Modify"]))
                )
        clear_permission_cache()
        st.success("Page-wise View/Edit/Modify rights saved.")
else:
    st.info("No users available.")
