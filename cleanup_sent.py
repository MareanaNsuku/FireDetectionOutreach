import imaplib
import email
import sys
from email.header import decode_header
from dotenv import dotenv_values

cfg = dotenv_values('.env')
user = cfg.get('UCT_EMAIL')
password = cfg.get('UCT_PASSWORD')

if not user or not password:
    print('Cleanup: no credentials, skipping')
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

try:
    M = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    M.login(user, password)
    M.select('"[Gmail]/Sent Mail"')
except Exception as e:
    print('Cleanup IMAP login failed:', e)
    sys.exit(0)

try:
    typ, data = M.search(None, 'SUBJECT', '"FireGuard"')
except Exception as e:
    print('Cleanup search failed:', e)
    M.logout()
    sys.exit(0)

if typ != 'OK' or not data[0]:
    print('Cleanup: no matching emails found')
    M.logout()
    sys.exit(0)

deleted = 0
for num in data[0].split():
    try:
        typ, msg_data = M.fetch(num, '(RFC822)')
        if typ != 'OK':
            continue
        
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_mime(msg.get('Subject', ''))
        
        # Safely search for the reply without crashing on special characters
        try:
            reply_subject = f"Re: {subject}"
            M2 = imaplib.IMAP4_SSL('imap.gmail.com', 993)
            M2.login(user, password)
            M2.select('"[Gmail]/All Mail"')
            typ2, data2 = M2.search(None, 'SUBJECT', f'"{reply_subject}"')
            M2.logout()
            
            if typ2 == 'OK' and data2[0].split():
                continue # Skip deleting, they replied!
        except Exception:
            pass # If search fails due to encoding, assume no reply and continue
            
        M.store(num, '+FLAGS', '\\Deleted')
        deleted += 1
    except Exception:
        pass

M.expunge()
M.logout()
print(f'Cleanup: deleted {deleted} unreplied sent emails')
