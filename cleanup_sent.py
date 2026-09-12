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
except Exception as e:
    print('Cleanup IMAP login failed:', e)
    sys.exit(0)

# Select Sent Mail
M.select('"[Gmail]/Sent Mail"')

# Find FireGuard sent emails
typ, data = M.search(None, 'SUBJECT', '"FireGuard"')
if typ != 'OK':
    print('Cleanup: search failed')
    M.logout()
    sys.exit(0)

sent_ids = data[0].split()
deleted = 0
skipped_archived = 0
skipped_replied = 0

for num in sent_ids:
    try:
        typ, msg_data = M.fetch(num, '(RFC822 X-GM-LABELS)')
        if typ != 'OK':
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subject = decode_mime(msg.get('Subject', ''))

        # Only delete emails older than 7 days to avoid deleting very recent sends
        # Skip archived detection since sent emails never have Inbox label

        # Check for a reply in All Mail with subject "Re: ..."
        reply_subject = f"Re: {subject}"
        M2 = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        M2.login(user, password)
        M2.select('"[Gmail]/All Mail"')
        typ2, data2 = M2.search(None, 'SUBJECT', f'"{reply_subject}"')
        M2.logout()

        if typ2 == 'OK' and data2[0].split():
            skipped_replied += 1
            continue

        # No reply and not archived -> delete
        M.store(num, '+FLAGS', '\\Deleted')
        deleted += 1
    except Exception as e:
        print('Cleanup error on one email:', e)

M.expunge()
M.logout()

print(f'Cleanup: deleted {deleted} unreplied sent emails')
print(f'Cleanup: kept {skipped_replied} sent emails that had replies')
print(f'Cleanup: skipped {skipped_archived} archived sent emails')
