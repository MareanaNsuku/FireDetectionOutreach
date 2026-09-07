import imaplib
import email
import re
import sqlite3
import sys
from pathlib import Path
from dotenv import dotenv_values
from email.header import decode_header

cfg = dotenv_values('.env')
user = cfg.get('UCT_EMAIL')
password = cfg.get('UCT_PASSWORD')

if not user or not password:
    print('Bounce checker: no Gmail credentials, skipping')
    sys.exit(0)

def decode_mime(value):
    if not value:
        return ''
    parts = decode_header(value)
    result = ''
    for text, charset in parts:
        if isinstance(text, bytes):
            result += text.decode(charset or 'utf-8', 'ignore')
        else:
            result += text
    return result

def get_text(msg):
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
    return text

try:
    M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    M.login(user, password)
    M.select('INBOX')
except Exception as e:
    print('Bounce checker IMAP login failed:', e)
    sys.exit(0)

EXCLUDE = {
    user.lower(),
    (cfg.get('BRV_FROM_EMAIL') or '').lower(),
    'ashleymwaramba@gmail.com',
    'ashley@fireguardsa.co.za',
    'mailer-daemon@googlemail.com',
    'mailer-daemon@gmail.com',
    'postmaster@googlemail.com',
    'postmaster@gmail.com',
    'noreply@google.com',
}

failed = set()

search_queries = [
    ('FROM', 'mailer-daemon@googlemail.com'),
    ('FROM', 'mailer-daemon@gmail.com'),
    ('FROM', 'postmaster@googlemail.com'),
    ('FROM', 'postmaster@gmail.com'),
    ('SUBJECT', '"Undeliverable"'),
    ('SUBJECT', '"Returned mail"'),
    ('SUBJECT', '"Delivery Status Notification (Failure)"'),
]

for criterion, value in search_queries:
    try:
        typ, data = M.search(None, 'UNSEEN', criterion, value)
        if typ != 'OK':
            continue
        for num in data[0].split():
            try:
                typ2, msg_data = M.fetch(num, '(RFC822)')
                if typ2 != 'OK':
                    continue
                msg = email.message_from_bytes(msg_data[0][1])

                # 1. Try standard headers first
                for header in ['Final-Recipient', 'Original-Recipient', 'X-Failed-Recipients']:
                    raw = msg.get(header)
                    if raw:
                        decoded = decode_mime(raw)
                        addrs = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', decoded)
                        for a in addrs:
                            failed.add(a.lower())

                # 2. Parse body text with known patterns
                body = get_text(msg)
                patterns = [
                    r"Your message wasn['’]?t delivered to\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                    r"The following address(?:es)? failed:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                    r"Final-Recipient:\s*[^;]*;([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                    r"Original-Recipient:\s*[^;]*;([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                    r"X-Failed-Recipients:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
                ]
                for pat in patterns:
                    for m in re.finditer(pat, body, re.IGNORECASE):
                        failed.add(m.group(1).lower())

                # 3. General fallback only if text clearly indicates failure
                if not failed:
                    if 'failed' in body.lower() or 'undeliverable' in body.lower() or 'couldn\'t be delivered' in body.lower():
                        addrs = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', body)
                        for a in addrs:
                            a = a.lower()
                            if a not in EXCLUDE:
                                failed.add(a)

                M.store(num, '+FLAGS', '\\Seen')
            except Exception:
                pass
    except Exception:
        pass

M.logout()

clean_failed = {a for a in failed if a not in EXCLUDE}

if not clean_failed:
    print('Bounce checker: no new bounced addresses')
    sys.exit(0)

Path('data').mkdir(exist_ok=True)
conn = sqlite3.connect('data/sent_emails.db')
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS sent (email TEXT PRIMARY KEY, date TEXT, bounced INTEGER DEFAULT 0)')

for a in clean_failed:
    c.execute('INSERT OR IGNORE INTO sent (email, date, bounced) VALUES (?, datetime("now"), 0)', (a,))
    c.execute('UPDATE sent SET bounced=1 WHERE email=?', (a,))

conn.commit()
conn.close()

with open('bounced_emails.txt', 'a') as f:
    for a in sorted(clean_failed):
        f.write(a + '\n')

print(f'Bounce checker: marked {len(clean_failed)} addresses as bounced')
print('Emails marked:')
for a in sorted(clean_failed):
    print('  -', a)
