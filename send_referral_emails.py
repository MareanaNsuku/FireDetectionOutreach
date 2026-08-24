import smtplib, os
from email.message import EmailMessage
from dotenv import dotenv_values

cfg = dotenv_values('.env')

recipients = [
    "mark@olarm.com",
    "mark@rsaweb.co.za",
    "mslingsby@rsaweb.co.za"
]

cc = ["ashleymwaramba@gmail.com"]

subject = "FireGuard – AI Fire Detection & Community Alert System | Referred by Steven Sher, CEO Techtron Technologies"

body_plain = """Dear Sir/Madam,

I have been referred to you by Steven Sher, CEO of Techtron Technologies, to reach out to you.

My name is Nsuku Mareana, a third-year Mechanical & Mechatronics Engineering student at the University of Cape Town, collaborating with Ashley Mwaramba, the founder of FireGuard.

FireGuard is a low-cost, AI-powered early fire detection and community alert system designed specifically for rural and informal settlements in South Africa.

We are currently looking for:
- Technical advice and mentorship
- Potential sponsorship or component support
- Industry connections
- Software/AI guidance for on-device fire detection

We would appreciate the opportunity to discuss this further.

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

sender = cfg.get("UCT_EMAIL")
password = cfg.get("UCT_PASSWORD")
host = cfg.get("UCT_SMTP_HOST", "smtp.gmail.com")
port = int(cfg.get("UCT_SMTP_PORT", "587"))

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

    print(f"✅ Sent to {to}")

print("All referral emails sent.")
