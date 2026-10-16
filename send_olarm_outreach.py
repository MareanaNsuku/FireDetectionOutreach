import smtplib
from email.message import EmailMessage
from dotenv import dotenv_values

cfg = dotenv_values('.env')
sender = cfg.get('UCT_EMAIL')
password = cfg.get('UCT_PASSWORD')
host = cfg.get('UCT_SMTP_HOST', 'smtp.gmail.com')
port = int(cfg.get('UCT_SMTP_PORT', '587'))

recipients = ['sales@olarm.com', 'partners@olarm.com']
cc = ['support@olarm.com']

subject = "FireGuard – AI Fire Detection & Community Alert System | Partnership Enquiry"

body_plain = """Dear Olarm Team,

My name is Nsuku Mareana, a third-year Mechanical & Mechatronics Engineering student at the University of Cape Town, collaborating with Ashley Mwaramba, the founder of FireGuard.

FireGuard is a low-cost, AI-powered early fire detection and community alert system designed specifically for rural and informal settlements in South Africa. It combines smoke/gas, infrared flame, and temperature sensors with a lightweight on-device AI model to distinguish real fires from cooking smoke, then alerts nearby homes via a mesh network and sends SMS alerts through a GSM gateway.

We are reaching out to Olarm because of your expertise in IoT security hardware and your strong South African presence. We would appreciate:

- Technical advice on sensor integration and embedded systems
- Potential component or manufacturing support
- Industry connections for real-world testing

We would be happy to share our project documentation and discuss further.

📁 Project files:
https://drive.google.com/drive/folders/1dLSXFE-GMi38XNnMAVtw1_KkS38SVUIJ?usp=sharing

Warm regards,

Nsuku Mareana
Collaborator
Phone: 068 078 9360
LinkedIn: https://www.linkedin.com/in/nsukumareana/

Ashley Mwaramba
Project Founder
Phone: 069 625 1572
LinkedIn: https://www.linkedin.com/in/ashley-mwaramba-04036a269/
"""

body_html = body_plain.replace("\n", "<br>")

for to in recipients:
    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = to
    msg['Cc'] = ','.join(cc)
    msg['Subject'] = subject
    msg['X-Priority'] = '1'
    msg.set_content(body_plain)
    msg.add_alternative(body_html, subtype='html')
    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
    print(f'✅ Sent to {to}')

print('All Olarm outreach emails sent.')
