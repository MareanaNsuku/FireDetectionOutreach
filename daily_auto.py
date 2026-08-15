#!/usr/bin/env python3
import os, sys, time, re, sqlite3, smtplib, mimetypes, csv
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from dotenv import dotenv_values
from dns import resolver, exception
import requests
from company_finder.email_utils import scrape_emails

cfg = dotenv_values('.env')
UCT_USER = cfg.get('UCT_EMAIL')
UCT_PASS = cfg.get('UCT_PASSWORD')
UCT_HOST = cfg.get('UCT_SMTP_HOST', 'smtp.uct.ac.za')
UCT_PORT = int(cfg.get('UCT_SMTP_PORT', '587'))
FROM_EMAIL = UCT_USER
CC_ADDR = 'ashleymwaramba@gmail.com'
ATTACH_FOLDER = '/workspaces/FireDetectionOutreach/attachments'
SENT_DB = 'data/sent_emails.db'
MASTER_CSV = 'master_companies.csv'
DAILY_BATCH = 30

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; OutreachBot/1.0)'}

def init_db():
    conn = sqlite3.connect(SENT_DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sent (email TEXT PRIMARY KEY, date TEXT, bounced INTEGER DEFAULT 0)''')
    try: c.execute("ALTER TABLE sent ADD COLUMN bounced INTEGER DEFAULT 0")
    except: pass
    conn.commit()
    conn.close()

def is_sent(email):
    conn = sqlite3.connect(SENT_DB)
    c = conn.cursor()
    c.execute('SELECT 1 FROM sent WHERE email=?', (email,))
    res = c.fetchone()
    conn.close()
    return res is not None

def mark_sent(email):
    conn = sqlite3.connect(SENT_DB)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO sent (email, date, bounced) VALUES (?, datetime("now"), 0)', (email,))
    conn.commit()
    conn.close()

def has_mx(domain):
    try: answers = resolver.resolve(domain, 'MX'); return len(answers) > 0
    except: return False

def mailbox_exists(email, timeout=10):
    domain = email.split('@')[1]
    try:
        mx_records = resolver.resolve(domain, 'MX')
        mx_host = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records])[0][1]
    except: return False
    try:
        server = smtplib.SMTP(mx_host, 25, timeout=timeout)
        server.helo(); server.mail('test@example.com'); code, msg = server.rcpt(email)
        server.quit()
        return code == 250 or code == 251
    except: return False

def website_alive(url):
    try:
        resp = requests.head(url, headers=HEADERS, timeout=5, allow_redirects=True)
        if resp.status_code == 200: return True
        resp = requests.get(url, headers=HEADERS, timeout=5, stream=True)
        return resp.status_code == 200
    except: return False

def send_email(to_addr, company_name, attachments):
    name = company_name or to_addr
    subject = 'FireGuard – AI Fire Detection & Community Alert System | Sponsorship Request'
    body_plain = f"""Dear {name},
The project was founded by Ashley Mwaramba, a Grade 12 student, who has been developing the concept since October 2025. I, Nsuku Mareana, a third-year Mechanical & Mechatronics Engineering student at the University of Cape Town, am collaborating with her. Together, we have developed FireGuard – a low-cost, AI-powered early fire detection and community alert system designed specifically for rural and informal settlements in South Africa.

ABOUT THE PROJECT:
FireGuard combines a smoke/gas sensor, an infrared flame sensor, and a precision temperature sensor, feeding their data into a lightweight on‑device AI model. This AI learns the difference between normal cooking smoke and a genuine fire threat, drastically reducing false alarms. When a real fire risk is detected, FireGuard sounds a loud local alarm, flashes high‑intensity LEDs, and simultaneously alerts nearby homes via a low‑power mesh network (ESP‑NOW). A central gateway then sends SMS alerts to community leaders and emergency contacts using a SIM800L GSM module — all without needing internet or mains electricity. The system runs on rechargeable batteries with solar support, making it completely off‑grid.

WHY THIS MATTERS:
In informal settlements, fires spread with devastating speed due to overcrowding, highly flammable building materials, and the near-total absence of early warning. By the time smoke is visible, it’s often too late. FireGuard predicts dangerous conditions before ignition, giving families precious extra minutes to escape. Every component has been chosen for affordability and local availability, so a single unit costs a fraction of traditional alarm systems.

HOW YOU CAN HELP:
We are looking for:
- Expert advice on coding and AI language models suitable for integration with the ESP32 microcontroller
- Information on different smoke profiles, fire treatments, and detection methods
- Potential sponsorship which may include access to components, sensors, and software experts in the field of software development
- Industry connections that could help us test the device in a real‑world environment

📁 Access All Project Files (presentations, technical slides, poster): https://drive.google.com/drive/folders/1fCTv_8V0Cg0h9ubzFe2_LDSpGb_xE_tf?usp=share_link

For companies based in Johannesburg / Gauteng: I will be available during the holidays for an in‑person meeting with your team.

My availability for a call or meeting (SAST):
Monday 07:00–08:30 & 10:00–11:00
Tuesday 14:00–18:00
Wednesday 14:00–18:00
Thursday 12:00–14:00
Friday 12:00–14:00
Saturday 08:00–17:00
Sunday 12:00–17:00

Thank you for supporting student innovation and community safety.

Warm regards,
Ashley Mwaramba (Project Founder)
Phone: 069 625 1572
LinkedIn: https://www.linkedin.com/in/ashley-mwaramba-04036a269/

Nsuku Mareana (Collaborator)
Phone: 068 078 9360
LinkedIn: https://www.linkedin.com/in/nsukumareana/"""

    body_html = f"""<html><body>
<p>Dear {name},</p>
<p>The project was founded by Ashley Mwaramba, a Grade 12 student, who has been developing the concept since October 2025. I, Nsuku Mareana, a third-year Mechanical & Mechatronics Engineering student at the University of Cape Town, am collaborating with her. Together, we have developed FireGuard – a low-cost, AI-powered early fire detection and community alert system designed specifically for rural and informal settlements in South Africa.</p>
<b>ABOUT THE PROJECT:</b>
<p>FireGuard combines a smoke/gas sensor, an infrared flame sensor, and a precision temperature sensor, feeding their data into a lightweight on‑device AI model. This AI learns the difference between normal cooking smoke and a genuine fire threat, drastically reducing false alarms. When a real fire risk is detected, FireGuard sounds a loud local alarm, flashes high‑intensity LEDs, and simultaneously alerts nearby homes via a low‑power mesh network (ESP‑NOW). A central gateway then sends SMS alerts to community leaders and emergency contacts using a SIM800L GSM module — all without needing internet or mains electricity. The system runs on rechargeable batteries with solar support, making it completely off‑grid.</p>
<b>WHY THIS MATTERS:</b>
<p>In informal settlements, fires spread with devastating speed due to overcrowding, highly flammable building materials, and the near-total absence of early warning. By the time smoke is visible, it’s often too late. FireGuard predicts dangerous conditions before ignition, giving families precious extra minutes to escape. Every component has been chosen for affordability and local availability, so a single unit costs a fraction of traditional alarm systems.</p>
<b>HOW YOU CAN HELP:</b>
<p>We are looking for:<br>
- Expert advice on coding and AI language models suitable for integration with the ESP32 microcontroller<br>
- Information on different smoke profiles, fire treatments, and detection methods<br>
- Potential sponsorship which may include access to components, sensors, and software experts in the field of software development<br>
- Industry connections that could help us test the device in a real‑world environment</p>
<p>📁 <b><a href="https://drive.google.com/drive/folders/1fCTv_8V0Cg0h9ubzFe2_LDSpGb_xE_tf?usp=share_link">Access All Project Files (presentations, technical slides, poster)</a></b></p>
<p>For companies based in Johannesburg / Gauteng: I will be available during the holidays for an in‑person meeting with your team.</p>
<p>My availability for a call or meeting (SAST):<br>
Monday 07:00–08:30 & 10:00–11:00<br>
Tuesday 14:00–18:00<br>
Wednesday 14:00–18:00<br>
Thursday 12:00–14:00<br>
Friday 12:00–14:00<br>
Saturday 08:00–17:00<br>
Sunday 12:00–17:00</p>
<p>Thank you for supporting student innovation and community safety.</p>
<p>Warm regards,<br>
Ashley Mwaramba (Project Founder)<br>
Phone: 069 625 1572<br>
LinkedIn: https://www.linkedin.com/in/ashley-mwaramba-04036a269/</p>
<p>Nsuku Mareana (Collaborator)<br>
Phone: 068 078 9360<br>
LinkedIn: https://www.linkedin.com/in/nsukumareana/</p>
</body></html>"""

    msg = MIMEMultipart('alternative')
    msg['From'] = FROM_EMAIL
    msg['To'] = to_addr
    msg['Cc'] = CC_ADDR
    msg['Subject'] = subject
    msg['X-Priority'] = '1'; msg['Importance'] = 'High'
    msg.attach(MIMEText(body_plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    overview_file = os.path.join(ATTACH_FOLDER, 'FireGuard_Project_Overview.docx')
    if os.path.isfile(overview_file):
        ctype, encoding = mimetypes.guess_type(overview_file)
        if ctype is None or encoding is not None: ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        with open(overview_file, 'rb') as fp:
            part = MIMEBase(maintype, subtype); part.set_payload(fp.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(overview_file)}"')
        msg.attach(part)

    for attempt in range(3):
        try:
            with smtplib.SMTP(UCT_HOST, UCT_PORT) as s:
                s.starttls(); s.login(UCT_USER, UCT_PASS); s.send_message(msg)
            return True, 'UCT'
        except smtplib.SMTPDataError as e:
            if '4.4.2' in str(e) and attempt < 2:
                wait = (attempt + 1) * 10
                print(f'     rate limit hit, retrying in {wait}s...')
                time.sleep(wait)
            else: return False, str(e)
        except Exception as e: return False, str(e)
    return False, 'max retries'

def load_rejected_domains():
    domains = set()
    try:
        with open('rejected_domains.txt', 'r') as f:
            for line in f: domains.add(line.strip().lower())
    except: pass
    return domains

def load_responded_domains():
    domains = set()
    try:
        with open('responded_domains.txt', 'r') as f:
            for line in f: domains.add(line.strip().lower())
    except: pass
    return domains

def main():
    init_db()
    if not os.path.exists(MASTER_CSV):
        print(f'❌ {MASTER_CSV} not found. Run the discovery bot first (python live_scraper.py).')
        sys.exit(1)
    rejected = load_rejected_domains()
    responded = load_responded_domains()
    excluded = rejected | responded

    rows = []
    with open(MASTER_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row['Status'].strip(): rows.append(row)

    if not rows:
        print('✅ All companies processed. Run live_scraper.py again for fresh companies.')
        return

    batch = rows[:DAILY_BATCH]
    print(f'🔍 Processing {len(batch)} companies today…')

    attachments = []
    overview = os.path.join(ATTACH_FOLDER, 'FireGuard_Project_Overview.docx')
    if os.path.isfile(overview): attachments.append(overview)
    print(f'📎 {len(attachments)} attachment(s) ready.')

    total_sent = 0
    all_rows = []
    with open(MASTER_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader: all_rows.append(row)

    for row in batch:
        company = row['Company Name'].strip()
        website = row['Website'].strip()
        print(f'\n🔍 {company} ({website})')
        from urllib.parse import urlparse
        domain = urlparse(website).netloc.replace('www.','').lower()
        if domain in excluded:
            print('   ⏭️  already contacted/rejected – skipping.')
            for r in all_rows:
                if r['Website'] == website and r['Company Name'] == company: r['Status'] = 'skipped'
            continue
        if not website_alive(website):
            print('   ❌ website not reachable, skipping.')
            for r in all_rows:
                if r['Website'] == website and r['Company Name'] == company: r['Status'] = 'no website'
            continue

        emails = scrape_emails(website)
        status = ''
        if emails:
            print(f'   scraped: {emails}')
            for r in all_rows:
                if r['Website'] == website and r['Company Name'] == company: r['Emails Found'] = emails
            addresses = set()
            for addr in emails.split(','):
                addr = addr.strip()
                if not addr or '@' not in addr: continue
                addresses.add(addr)
            verified = [a for a in addresses if has_mx(a.split('@')[1]) and mailbox_exists(a)]
            new_emails = [e for e in verified if not is_sent(e)]
            print(f'   {len(verified)} mailboxes confirmed, {len(new_emails)} new')
            all_sent = True
            for email in new_emails:
                success, method = send_email(email, company, attachments)
                if success:
                    print(f'   ✅ {email} via {method}')
                    mark_sent(email)
                    total_sent += 1
                else:
                    print(f'   ❌ send failed {email}: {method}')
                    all_sent = False
                time.sleep(15)
            status = 'done' if all_sent else ''
            for r in all_rows:
                if r['Website'] == website and r['Company Name'] == company: r['Status'] = status
        else:
            print('   no emails found')
            for r in all_rows:
                if r['Website'] == website and r['Company Name'] == company:
                    r['Emails Found'] = ''
                    r['Status'] = 'no email'
            status = 'no email'
        with open(MASTER_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

    print(f'\n🎉 Done! Sent {total_sent} new emails today. {len(rows)-len(batch)} companies remaining.')

if __name__ == '__main__':
    main()
