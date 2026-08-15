import re, requests, time
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
from urllib.parse import urljoin, urlparse

HEADERS={"User-Agent":"Mozilla/5.0"}
EMAIL_RE=re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}')

PLACEHOLDER={"firstname","lastname","example","test","user","someone","demo","sample","your-email","email","name","john.doe","jane.doe","noreply","no-reply"}

def extract_emails_from_page(url, timeout=8):
    emails=set()
    try:
        r=requests.get(url,headers=HEADERS,timeout=timeout,allow_redirects=True)
        if r.status_code!=200: return emails
        emails.update(EMAIL_RE.findall(r.text))
        soup=BeautifulSoup(r.text,'html.parser')
        for a in soup.find_all('a',href=True):
            if a['href'].startswith('mailto:'):
                e=a['href'][7:].split('?')[0].strip().lower()
                if EMAIL_RE.match(e): emails.add(e)
        for tag in soup.find_all(attrs={"data-email":True}): emails.add(tag['data-email'].strip().lower())
    except: pass
    return emails

def find_internal_links(base_url, soup):
    domain=urlparse(base_url).netloc
    links=set()
    for a in soup.find_all('a',href=True):
        full=urljoin(base_url,a['href'])
        if urlparse(full).netloc==domain and not full.endswith(('.pdf','.jpg','.png','.zip')): links.add(full)
    return list(links)[:30]

def crawl_website(base_url, max_pages=30):
    visited=set()
    to_visit=[base_url]+[urljoin(base_url,p) for p in ['/contact','/contact-us','/about','/enquiries','/support','/help','/sales','/hr','/media','/press','/careers','/team','/people']]
    all_emails=set()
    while to_visit and len(visited)<max_pages:
        url=to_visit.pop(0)
        if url in visited: continue
        visited.add(url)
        try:
            r=requests.get(url,headers=HEADERS,timeout=8)
            if r.status_code!=200: continue
            all_emails.update(extract_emails_from_page(url))
            soup=BeautifulSoup(r.text,'html.parser')
            for link in find_internal_links(base_url, soup):
                if link not in visited: to_visit.append(link)
            time.sleep(0.3)
        except: pass
    return all_emails

def scrape_emails(website):
    if not website or 'google.com' in website: return ''
    emails=crawl_website(website, max_pages=30)
    clean=set()
    for e in emails:
        parts = e.split('@')
        if len(parts) != 2: continue
        local, domain = parts
        if local.lower() in PLACEHOLDER: continue
        if re.search(r'\.(webp|png|jpg|jpeg|gif|svg)(@|$)', e): continue
        if domain.endswith('.co') and not domain.endswith('.co.za'): domain+='.za'; e=f'{local}@{domain}'
        if domain.count('.')<1: continue
        clean.add(e)
    return ','.join(sorted(clean)) if clean else ''
