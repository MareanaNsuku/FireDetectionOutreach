import imaplib, email, re, sqlite3, sys
from pathlib import Path
from dotenv import dotenv_values

cfg = dotenv_values('.env')
user = cfg.get('UCT_EMAIL')
password = cfg.get('UCT_PASSWORD')

if not user or not password:
    print('Bounce checker: no Gmail credentials, skipping')
    sys.exit(0)

try:
    M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    M.login(user, password)
    M.select('INBOX')
except Exception as e:
    print('Bounce checker IMAP login failed:', e)
    sys.exit(0)

exclude = {
    user.lower(),
    (cfg.get('BRV_FROM_EMAIL') or '').lower(),
    'ashleymwaramba@gmail.com',
    'ashley@fireguardsa.co.za',
    'mailer-daemon@googlemail.com',
    'mailer-daemon@gmail.com',
}

failed = set()
criteria = [
    ('FROM', 'mailer-daemon@googlemail.com'),
    ('FROM', 'mailer-daemon@gmail.com'),
    ('SUBJECT', '"Delivery Status Notification (Failure)"'),
    ('SUBJECT', '"Undeliverable"'),
]

for criterion, value in criteria:
    try:
        typ, data = M.search(None, 'UNSEEN', criterion, value)
        if typ != 'OK':
            continue
        for num in data[0].split():
            try:
                typ2, msg_data = M.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                text = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            payload = part.get_payload(decode=True)
                            if payload:
                                text += payload.decode('utf-8', 'ignore') + '\n'
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        text = payload.decode('utf-8', 'ignore')

                addrs = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
                for a in addrs:
                    a = a.lower()
                    if a not in exclude:
                        failed.add(a)

                M.store(num, '+FLAGS', '\\Seen')
            except Exception:
                pass
    except Exception:
        pass

M.logout()

if not failed:
    print('Bounce checker: no new bounced addresses')
    sys.exit(0)

Path('data').mkdir(exist_ok=True)
conn = sqlite3.connect('data/sent_emails.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS sent (email TEXT PRIMARY KEY, date TEXT, bounced INTEGER DEFAULT 0)')
for a in failed:
    c.execute('INSERT OR IGNORE INTO sent (email, date, bounced) VALUES (?, datetime("now"), 0)', (a,))
    c.execute('UPDATE sent SET bounced=1 WHERE email=?', (a,))
conn.commit()
conn.close()
print(f'Bounce checker: marked {len(failed)} addresses as bounced')
