from common import *

page_setup()

require_page_view('overdue')
show_edit_permission_status('overdue')

show_header('Email Notification Settings')
st.info('Use Gmail App Password, not your normal Gmail password. Google Account → Security → 2-Step Verification → App Passwords.')
settings = get_notification_settings()
ns1, ns2 = st.columns(2)
with ns1:
    sender_email = st.text_input('Sender Email', settings.get('sender_email') or '', key='notif_sender_email')
    app_password = st.text_input('Gmail App Password', settings.get('app_password') or '', type='password', key='notif_app_password')
with ns2:
    smtp_server = st.text_input('SMTP Server', settings.get('smtp_server') or 'smtp.gmail.com', key='notif_smtp_server')
    smtp_port = st.number_input('SMTP Port', value=int(settings.get('smtp_port') or 587), step=1, key='notif_smtp_port')
    enable_email = st.checkbox('Enable Email Notifications', value=bool(settings.get('enable_email')), key='notif_enable_email')
if st.button('Save Email Settings', key='save_email_settings'):
    execute_query('\n                UPDATE notification_settings\n                SET sender_email=?, app_password=?, smtp_server=?, smtp_port=?, enable_email=?\n                WHERE id=1\n            ', (sender_email, app_password, smtp_server, int(smtp_port), int(enable_email)))
    st.success('Email settings saved.')
st.subheader('Notification Recipients')
rec_event = st.selectbox('Event Type', ['shipment', 'delivery', 'payment'], key='recipient_event')
rec_email = st.text_input('Recipient Email', key='recipient_email')
if st.button('Add Recipient', key='add_recipient'):
    if rec_email.strip():
        execute_query('INSERT INTO notification_recipients (event_type, recipient_email, is_active) VALUES (?, ?, 1)', (rec_event, rec_email.strip()))
        st.success('Recipient added.')
show_filtered_df(fetch_all('SELECT * FROM notification_recipients ORDER BY event_type, id DESC'), 'notification_recipients', total=False)
st.divider()
show_header('Overdue Payment Notification')
rows = overdue_rows()
df = show_filtered_df(rows, 'reports_filter', total=True)
export_buttons(df, 'overdue_payment_list')
st.warning('For WhatsApp, click the button to open WhatsApp message. Full auto-send needs WhatsApp Business API.')
for r in rows:
    message = f"Dear {r['customer_name']}, payment is overdue for invoice {r['delivery_invoice_no']}. Due date: {r['payment_due_date']}. Pending amount: {r['pending_amount']}."
    with st.expander(f"{r['delivery_invoice_no']} - {r['customer_name']} - Pending {r['pending_amount']}"):
        if r.get('whatsapp_no'):
            st.link_button('Open WhatsApp', whatsapp_link(r['whatsapp_no'], message))

render_slogan_footer()
