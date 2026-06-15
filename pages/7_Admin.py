from common import *
import pandas as pd

# Admin page rebuilt for stable saves.
# Non-destructive: only updates users, permissions and access-control tables.

def _admin_safe_clear_cache():
    """Local cache clear helper so Admin saves never fail because of missing cache helpers."""
    try:
        clear_cache_after_write()
        return
    except Exception:
        pass
    try:
        clear_permission_cache()
    except Exception:
        pass
    try:
        st.cache_data.clear()
    except Exception:
        pass
    try:
        st.cache_resource.clear()
    except Exception:
        pass


def _safe_rows(query, params=()):
    try:
        return fetch_all(query, params)
    except Exception as e:
        st.error(f"Database read failed: {e}")
        return []


def _safe_exec(query, params=()):
    try:
        execute_query(query, params)
        return True
    except Exception as e:
        st.error(f"Database save failed: {e}")
        return False


def _role_default_view(page, role):
    if role == "super_admin":
        return True
    key = page.get("key")
    if role == "admin":
        return key in ["dashboard", "masters", "shipment", "delivery", "payment", "coverage", "admin", "reports", "overdue"]
    if role == "user":
        return key in ["dashboard", "delivery", "coverage", "reports"]
    return False


def _role_default_edit(page, role):
    if role == "super_admin":
        return True
    key = page.get("key")
    if role == "admin":
        return key in ["masters", "shipment", "delivery", "payment", "coverage", "reports", "overdue"]
    if role == "user":
        return key in ["delivery"]
    return False


def _ensure_admin_tables():
    statements = [
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS can_modify BOOLEAN DEFAULT FALSE",
        "ALTER TABLE user_page_access ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        """CREATE TABLE IF NOT EXISTS user_warehouse_access (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            warehouse_id INTEGER NOT NULL,
            can_access BOOLEAN DEFAULT TRUE,
            UNIQUE(username, warehouse_id)
        )""",
        """CREATE TABLE IF NOT EXISTS user_product_access (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            can_access BOOLEAN DEFAULT TRUE,
            UNIQUE(username, product_id)
        )""",
    ]
    for sql in statements:
        try:
            execute_query(sql)
        except Exception:
            pass
page_setup()
st.markdown('<div id="admin-scroll-top-anchor"></div>', unsafe_allow_html=True)
show_header('Admin Control Panel', 'Settings, User Management, Page Controls, Warehouse and Product Access')
_ensure_admin_tables()

admin_tabs = st.tabs(['Profile','User Management','Page Controls','Warehouse Access','Product Access','Company Management','System Settings'])

with admin_tabs[0]:
    st.subheader('Profile')
    current_user = st.session_state.get("user", {})
    st.write(f"User: **{current_user.get('username','-')}**")
    st.write(f"Role: **{current_user.get('role','-')}**")
    old_password = st.text_input('Current Password', type='password', key='profile_old_password')
    new_password = st.text_input('New Password', type='password', key='profile_new_password')
    if st.button('Change My Password', key='profile_change_password'):
        if old_password and new_password and verify_user(current_user.get('username'), old_password):
            if _safe_exec('UPDATE users SET password_hash=? WHERE username=?', (hash_password(new_password), current_user.get('username'))):
                _admin_safe_clear_cache()
                set_success_message('Password changed successfully.')
        else:
            st.error('Current password is incorrect or new password is blank.')

with admin_tabs[1]:
    require_roles(('super_admin',))
    st.subheader('User Management')
    uc1, uc2, uc3, uc4 = st.columns(4)
    with uc1:
        new_username = st.text_input('User Name', key='admin_new_username')
    with uc2:
        new_user_password = st.text_input('Password', type='password', key='admin_new_user_password')
    with uc3:
        new_user_role = st.selectbox('Role', ['user', 'admin', 'super_admin'], key='admin_new_user_role')
    with uc4:
        new_user_active = st.checkbox('Active', value=True, key='admin_new_user_active')
    if st.button('Create / Update User', key='admin_create_user', type='primary'):
        if not new_username.strip():
            st.error('User name is required.')
        else:
            existing = _safe_rows('SELECT id FROM users WHERE username=?', (new_username.strip(),))
            if existing:
                if new_user_password.strip():
                    ok = _safe_exec('UPDATE users SET password_hash=?, role=?, is_active=? WHERE username=?', (hash_password(new_user_password), new_user_role, bool(new_user_active), new_username.strip()))
                else:
                    ok = _safe_exec('UPDATE users SET role=?, is_active=? WHERE username=?', (new_user_role, bool(new_user_active), new_username.strip()))
                if ok:
                    _admin_safe_clear_cache()
                    set_success_message('User updated.')
                    st.rerun()
            else:
                if not new_user_password.strip():
                    st.error('Password is required for new user.')
                else:
                    if _safe_exec('INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)', (new_username.strip(), hash_password(new_user_password), new_user_role, bool(new_user_active))):
                        _admin_safe_clear_cache()
                        set_success_message('User created.')
                        st.rerun()

    st.divider()
    st.subheader('Modify Existing User Details')
    users_modify_rows = _safe_rows('SELECT id, username, role, is_active FROM users ORDER BY username')
    if users_modify_rows:
        modify_labels = [f"{u['id']} | {u['username']} | {u['role']} | {'Active' if u.get('is_active') else 'Inactive'}" for u in users_modify_rows]
        selected_modify_label = searchable_selectbox('Select User to Modify', modify_labels, key='admin_modify_user_select')
        if selected_modify_label:
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
                role_options = ['user', 'admin', 'super_admin']
                current_role = selected_modify_user.get('role','user') if selected_modify_user else 'user'
                modified_role = st.selectbox('New / Current Role', role_options, index=role_options.index(current_role) if current_role in role_options else 0, key='admin_modified_role')
            with mu4:
                modified_active = st.checkbox('Active', value=bool(selected_modify_user.get('is_active')) if selected_modify_user else True, key='admin_modified_active')
            if st.button('Save Selected User Detail Changes', key='admin_save_selected_user_detail_changes', type='primary'):
                if not any([update_username_tick, update_password_tick, update_role_tick, update_active_tick]):
                    st.warning('Please tick at least one field to update.')
                elif update_username_tick and not modified_username.strip():
                    st.error('User Name cannot be blank.')
                elif update_password_tick and not modified_password.strip():
                    st.error('Password cannot be blank when password update is ticked.')
                else:
                    ok_all = True
                    old_username = selected_modify_user.get('username')
                    if update_username_tick:
                        ok_all = _safe_exec('UPDATE users SET username=? WHERE id=?', (modified_username.strip(), selected_modify_id)) and ok_all
                        _safe_exec('UPDATE user_page_access SET username=? WHERE username=?', (modified_username.strip(), old_username))
                        _safe_exec('UPDATE user_warehouse_access SET username=? WHERE username=?', (modified_username.strip(), old_username))
                        _safe_exec('UPDATE user_product_access SET username=? WHERE username=?', (modified_username.strip(), old_username))
                    if update_password_tick:
                        ok_all = _safe_exec('UPDATE users SET password_hash=? WHERE id=?', (hash_password(modified_password), selected_modify_id)) and ok_all
                    if update_role_tick:
                        ok_all = _safe_exec('UPDATE users SET role=? WHERE id=?', (modified_role, selected_modify_id)) and ok_all
                    if update_active_tick:
                        ok_all = _safe_exec('UPDATE users SET is_active=? WHERE id=?', (bool(modified_active), selected_modify_id)) and ok_all
                    if ok_all:
                        _admin_safe_clear_cache()
                        set_success_message('Selected user details updated successfully.')
                        st.rerun()
    user_rows = _safe_rows('SELECT id, username, role, is_active FROM users ORDER BY id')
    if user_rows:
        show_filtered_df(user_rows, 'admin_users', total=False)

with admin_tabs[2]:
    require_roles(('super_admin',))
    st.subheader('Page Wise User Controls - View / Edit / Modify')
    st.info('Set View, Edit and Modify permission separately. Super Admin always has all access.')
    ensure_page_access_table()
    users_for_access = _safe_rows('SELECT username, role, is_active FROM users ORDER BY username')
    if users_for_access:
        user_labels = [f"{u['username']} | {u['role']}" for u in users_for_access]
        selected_user_label = st.selectbox('Select User for Page Access', user_labels, key='page_access_user_select')
        selected_username = selected_user_label.split(' | ')[0]
        saved_access_preview = _safe_rows('SELECT page_key, can_view, can_edit, can_modify FROM user_page_access WHERE username=? ORDER BY page_key', (selected_username,))
        if saved_access_preview:
            st.markdown('<div class="admin-saved-data-card"><b>Saved controls currently linked to this user:</b> ' + ', '.join([f"{r.get('page_key')}: V={r.get('can_view')} E={r.get('can_edit')} M={r.get('can_modify')}" for r in saved_access_preview]) + '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="admin-saved-data-card"><b>Saved controls currently linked to this user:</b> No custom page controls saved. Role defaults are active.</div>', unsafe_allow_html=True)
        selected_user_row = next((u for u in users_for_access if u['username'] == selected_username), None)
        existing_perms = get_user_page_permissions(selected_username)
        is_super_selected = bool(selected_user_row and selected_user_row.get('role') == 'super_admin')
        selected_view_values = {}
        selected_edit_values = {}
        selected_modify_values = {}
        header_cols = st.columns([2.4, 1, 1, 1])
        with header_cols[0]: st.markdown('**Page / Module**')
        with header_cols[1]: st.markdown('**View**')
        with header_cols[2]: st.markdown('**Edit**')
        with header_cols[3]: st.markdown('**Modify**')
        for page in APP_PAGE_DEFINITIONS:
            existing = existing_perms.get(page['key'], {})
            if is_super_selected:
                default_view = default_edit = default_modify = True
            elif isinstance(existing, dict) and page['key'] in existing_perms:
                default_view = bool(existing.get('can_view', existing.get('can_access', False)))
                default_edit = bool(existing.get('can_edit', False))
                default_modify = bool(existing.get('can_modify', default_edit))
            else:
                default_view = _role_default_view(page, selected_user_row.get('role')) if selected_user_row else False
                default_edit = _role_default_edit(page, selected_user_row.get('role')) if selected_user_row else False
                default_modify = default_edit
            row_cols = st.columns([2.4, 1, 1, 1])
            with row_cols[0]: st.markdown(f"**{page['label']}**")
            with row_cols[1]: selected_view_values[page['key']] = st.checkbox('View', value=bool(default_view), key=f"view_{selected_username}_{page['key']}", disabled=is_super_selected, label_visibility='collapsed')
            with row_cols[2]: selected_edit_values[page['key']] = st.checkbox('Edit', value=bool(default_edit), key=f"edit_{selected_username}_{page['key']}", disabled=is_super_selected, label_visibility='collapsed')
            with row_cols[3]: selected_modify_values[page['key']] = st.checkbox('Modify', value=bool(default_modify), key=f"modify_{selected_username}_{page['key']}", disabled=is_super_selected, label_visibility='collapsed')
        csave, creset = st.columns([1, 1])
        with csave:
            if st.button('Save View / Edit / Modify Controls', type='primary', key='save_page_controls'):
                ok_all = True
                for page in APP_PAGE_DEFINITIONS:
                    can_view = bool(selected_view_values.get(page['key'], False))
                    can_edit = bool(selected_edit_values.get(page['key'], False)) and can_view
                    can_modify = bool(selected_modify_values.get(page['key'], False)) and can_view
                    ok_all = _safe_exec("""
                        INSERT INTO user_page_access (username, page_key, can_access, can_view, can_edit, can_modify)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT (username, page_key)
                        DO UPDATE SET
                            can_access=EXCLUDED.can_access,
                            can_view=EXCLUDED.can_view,
                            can_edit=EXCLUDED.can_edit,
                            can_modify=EXCLUDED.can_modify,
                            updated_at=CURRENT_TIMESTAMP
                    """, (selected_username, page['key'], can_view, can_view, can_edit, can_modify)) and ok_all
                if ok_all:
                    _admin_safe_clear_cache()
                    set_success_message('Page controls saved successfully.')
                    st.rerun()
        with creset:
            if st.button('Reset to Role Default', key='reset_page_controls'):
                if _safe_exec('DELETE FROM user_page_access WHERE username=?', (selected_username,)):
                    _admin_safe_clear_cache()
                    set_success_message('Page controls reset to role defaults.')
                    st.rerun()
        access_rows = _safe_rows('SELECT username, page_key, can_view, can_edit, can_modify, updated_at FROM user_page_access ORDER BY username, page_key')
        if access_rows:
            st.markdown('### Saved Page Access Records')
            st.dataframe(pd.DataFrame(access_rows), use_container_width=True, hide_index=True)
    else:
        st.warning('No users found.')

with admin_tabs[3]:
    require_roles(('super_admin',))
    st.subheader('Warehouse Data Access')
    st.info('Default: if no warehouse is selected for a user, the user can access all warehouse data. Select warehouses only when you want to restrict access.')
    access_users = _safe_rows('SELECT id, username, role FROM users ORDER BY username')
    access_warehouses = _safe_rows('SELECT id, warehouse_name FROM warehouses ORDER BY warehouse_name')
    if access_users and access_warehouses:
        user_labels = [f"{u['username']} | {u['role']}" for u in access_users]
        selected_access_user_label = searchable_selectbox('Select User for Warehouse Access', user_labels, key='warehouse_access_user_select')
        selected_access_username = selected_access_user_label.split('|')[0].strip()
        existing_access = _safe_rows('SELECT warehouse_id FROM user_warehouse_access WHERE username=? AND COALESCE(can_access, TRUE)=TRUE', (selected_access_username,))
        existing_ids = {int(r['warehouse_id']) for r in existing_access if r.get('warehouse_id') is not None}
        if existing_ids:
            saved_wh_names = [str(w.get('warehouse_name')) for w in access_warehouses if int(w.get('id')) in existing_ids]
            st.markdown('<div class="admin-saved-data-card"><b>Saved warehouses linked to this user:</b> ' + ', '.join(saved_wh_names) + '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="admin-saved-data-card"><b>Saved warehouses linked to this user:</b> All Warehouses (blank access selection)</div>', unsafe_allow_html=True)
        warehouse_options = [f"{w['warehouse_name']} | {w['id']}" for w in access_warehouses]
        default_selected = [opt for opt in warehouse_options if int(opt.split('|')[-1].strip()) in existing_ids]
        selected_warehouse_access = st.multiselect('Select Warehouses for this User (blank = all warehouses)', warehouse_options, default=default_selected, key='warehouse_access_multiselect')
        if st.button('Save Warehouse Access', key='save_user_warehouse_access', type='primary'):
            ok_all = _safe_exec('DELETE FROM user_warehouse_access WHERE username=?', (selected_access_username,))
            for wh_opt in selected_warehouse_access:
                wh_id = int(wh_opt.split('|')[-1].strip())
                ok_all = _safe_exec('INSERT INTO user_warehouse_access (username, warehouse_id, can_access) VALUES (?, ?, TRUE) ON CONFLICT (username, warehouse_id) DO UPDATE SET can_access=EXCLUDED.can_access', (selected_access_username, wh_id)) and ok_all
            if ok_all:
                _admin_safe_clear_cache()
                set_success_message('Warehouse access saved. Blank selection means all warehouses.')
                st.rerun()
    else:
        st.info('Create users and warehouses first.')

with admin_tabs[4]:
    require_roles(('super_admin',))
    st.subheader('Product / Part Number Data Access')
    st.info('Default: if no product is selected for a user, the user can access all part numbers. Select part numbers only when you want to restrict access.')
    product_access_users = _safe_rows('SELECT id, username, role FROM users ORDER BY username')
    product_access_rows = _safe_rows('SELECT id, product_code, product_name FROM products ORDER BY product_code')
    if product_access_users and product_access_rows:
        product_user_labels = [f"{u['username']} | {u['role']}" for u in product_access_users]
        selected_product_user_label = searchable_selectbox('Select User for Product / Part Number Access', product_user_labels, key='product_access_user_select')
        selected_product_username = selected_product_user_label.split('|')[0].strip()
        existing_product_access = _safe_rows('SELECT product_id FROM user_product_access WHERE username=? AND COALESCE(can_access, TRUE)=TRUE', (selected_product_username,))
        existing_product_ids = {int(r['product_id']) for r in existing_product_access if r.get('product_id') is not None}
        if existing_product_ids:
            saved_product_names = [f"{p.get('product_code')} | {p.get('product_name','')}" for p in product_access_rows if int(p.get('id')) in existing_product_ids]
            st.markdown('<div class="admin-saved-data-card"><b>Saved part numbers linked to this user:</b> ' + ', '.join(saved_product_names) + '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="admin-saved-data-card"><b>Saved part numbers linked to this user:</b> All Part Numbers (blank access selection)</div>', unsafe_allow_html=True)
        product_options = [f"{p['product_code']} | {p.get('product_name','')} | {p['id']}" for p in product_access_rows]
        default_product_selected = [opt for opt in product_options if int(opt.split('|')[-1].strip()) in existing_product_ids]
        selected_product_access = st.multiselect('Select Part Numbers for this User (blank = all part numbers)', product_options, default=default_product_selected, key='product_access_multiselect')
        if st.button('Save Product / Part Number Access', key='save_user_product_access', type='primary'):
            ok_all = _safe_exec('DELETE FROM user_product_access WHERE username=?', (selected_product_username,))
            for product_opt in selected_product_access:
                product_id = int(product_opt.split('|')[-1].strip())
                ok_all = _safe_exec('INSERT INTO user_product_access (username, product_id, can_access) VALUES (?, ?, TRUE) ON CONFLICT (username, product_id) DO UPDATE SET can_access=EXCLUDED.can_access', (selected_product_username, product_id)) and ok_all
            if ok_all:
                _admin_safe_clear_cache()
                set_success_message('Product / Part Number access saved. Blank selection means all part numbers.')
                st.rerun()
    else:
        st.info('Create users and products first.')

with admin_tabs[5]:
    require_roles(('super_admin',))
    st.subheader('Company Management')
    if 'company_form' in globals():
        company_form()
    else:
        st.info('Company form is not available in this version.')

with admin_tabs[6]:
    require_roles(('super_admin',))
    st.subheader('System Settings')
    if 'system_settings_form' in globals():
        system_settings_form()
    elif 'notification_settings_form' in globals():
        notification_settings_form()
    else:
        st.info('System settings form is not available in this version.')

render_slogan_footer()

st.markdown('<div style="height:24px"></div><a href="#admin-scroll-top-anchor" style="font-weight:900;color:#003B73;">Back to Top - Admin</a>', unsafe_allow_html=True)
