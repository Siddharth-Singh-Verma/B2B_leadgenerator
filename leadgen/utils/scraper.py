import requests
from bs4 import BeautifulSoup
import re

TECH_KEYWORDS = [
    'AI', 'SaaS', 'ML', 'Machine Learning', 'Cloud', 'API', 'Analytics', 'Automation', 'CRM', 'Blockchain', 'Fintech', 'Data', 'Platform', 'Startup', 'B2B', 'B2C', 'IoT', 'Cybersecurity', 'DevOps', 'E-commerce', 'Marketplace'
]

PERSON_KEYWORDS = [
    'CEO', 'Chief Executive Officer', 'CTO', 'Chief Technology Officer', 'CMO', 'Chief Marketing Officer', 'COO', 'Founder', 'Co-Founder', 'President', 'Managing Director', 'Head of', 'Lead', 'Manager', 'Marketing', 'Sales', 'Business Development', 'Operations', 'Product', 'Engineering', 'Team', 'Leadership'
]


class LeadInsightScraper:
    def __init__(self, url):
        self.url = url
        self.html = ''
        self.soup = None
        self.result = {
            'title': '',
            'description': '',
            'emails': [],
            'phones': [],
            'phone_labels': {},
            'address': '',
            'key_people': [],
            'tech_keywords': [],
            'linkedin_search': ''
        }

    def fetch(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(self.url, headers=headers, timeout=10)
            resp.raise_for_status()
            self.html = resp.text
            self.soup = BeautifulSoup(self.html, 'html.parser')
        except Exception:
            self.html = ''
            self.soup = None

    def extract_title(self):
        if self.soup:
            title_tag = self.soup.find('title')
            if title_tag:
                self.result['title'] = title_tag.text.strip()

    def extract_description(self):
        if self.soup:
            desc_tag = self.soup.find('meta', attrs={'name': 'description'})
            if desc_tag and desc_tag.get('content'):
                self.result['description'] = desc_tag['content'].strip()
            else:
                # Try og:description
                og_desc = self.soup.find(
                    'meta', attrs={'property': 'og:description'})
                if og_desc and og_desc.get('content'):
                    self.result['description'] = og_desc['content'].strip()

    def extract_emails(self):
        if self.html:
            emails = re.findall(r'[\w\.-]+@[\w\.-]+', self.html)
            self.result['emails'] = list(set(emails))

    def extract_phones(self):
        if self.soup:
            phones = {}
            # Look for phone numbers in contact/about/team sections
            for section in self.soup.find_all(['section', 'div', 'footer', 'header']):
                section_text = section.get_text(separator=' ', strip=True)
                found_phones = re.findall(
                    r'\+?\d[\d\s\-\(\)]{7,}\d', section_text)
                for phone in found_phones:
                    # Try to find a label near the phone number
                    label = ''
                    # Look for a preceding few words that might indicate owner/role
                    match = re.search(
                        r'([\w\s]{0,40})' + re.escape(phone), section_text)
                    if match:
                        context = match.group(1)
                        for kw in PERSON_KEYWORDS:
                            if kw.lower() in context.lower():
                                label = kw
                                break
                    phones[phone] = label
            self.result['phones'] = list(phones.keys())
            self.result['phone_labels'] = phones

    def extract_address(self):
        if self.soup:
            # Look for address in footer or contact sections
            address = ''
            for tag in self.soup.find_all(['footer', 'section', 'div']):
                text = tag.get_text(separator=' ', strip=True)
                if re.search(r'\d{1,5} [\w\s\.,-]+\d{5,}', text):
                    address = text
                    break
            self.result['address'] = address

    def extract_key_people(self):
        if self.soup:
            people = set()
            # Look for names and roles in About/Team/Leadership sections
            for section in self.soup.find_all(['section', 'div']):
                section_text = section.get_text(separator=' ', strip=True)
                for kw in PERSON_KEYWORDS:
                    # Look for patterns like "John Doe, CEO" or "CEO: John Doe"
                    matches = re.findall(
                        r'([A-Z][a-z]+ [A-Z][a-z]+)[,\s]+(' + re.escape(kw) + r')', section_text)
                    for name, role in matches:
                        people.add(f"{name} ({role})")
                    matches2 = re.findall(
                        r'(' + re.escape(kw) + r')[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)', section_text)
                    for role, name in matches2:
                        people.add(f"{name} ({role})")
            self.result['key_people'] = sorted(people)

    def extract_tech_keywords(self):
        found = set()
        if self.html:
            for kw in TECH_KEYWORDS:
                if re.search(r'\b' + re.escape(kw) + r'\b', self.html, re.IGNORECASE):
                    found.add(kw)
        self.result['tech_keywords'] = sorted(found)

    def generate_linkedin_search(self):
        domain = re.sub(r'^https?://(www\.)?', '', self.url).split('/')[0]
        query = f"site:linkedin.com/company {domain}"
        self.result[
            'linkedin_search'] = f"https://www.google.com/search?q={requests.utils.quote(query)}"

    def fetch_linkedin_data(self, company_name_or_domain):
        api_key = "2221bcb8179cb73d93b58929d533c86ef85b863210c731c02a31fdd71b63351f"
        params = {
            "engine": "google",
            "q": f"site:linkedin.com/company {company_name_or_domain}",
            "api_key": api_key
        }
        search_url = "https://serpapi.com/search"
        try:
            resp = requests.get(search_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            linkedin_url = None
            for result in data.get("organic_results", []):
                link = result.get("link", "")
                if "linkedin.com/company" in link:
                    linkedin_url = link
                    break
            linkedin_data = {}
            if linkedin_url:
                linkedin_data['linkedin_url'] = linkedin_url
                for result in data.get("organic_results", []):
                    if result.get("link", "") == linkedin_url:
                        linkedin_data['linkedin_snippet'] = result.get(
                            "snippet", "")
                        for kw in PERSON_KEYWORDS:
                            if kw.lower() in result.get("snippet", "").lower():
                                linkedin_data.setdefault(
                                    'key_people', []).append(kw)
                        break
                # Try to fetch and parse the About page
                about_url = linkedin_url.rstrip('/') + '/about'
                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    about_resp = requests.get(
                        about_url, headers=headers, timeout=10)
                    about_resp.raise_for_status()
                    about_html = about_resp.text
                    about_soup = BeautifulSoup(about_html, 'html.parser')
                    # Extract structured fields from About page

                    def get_text_by_selector(selector):
                        tag = about_soup.select_one(selector)
                        return tag.get_text(strip=True) if tag else ''
                    # LinkedIn About page uses data-test selectors and class names, but may change
                    # Try to extract common fields
                    linkedin_data['about_overview'] = get_text_by_selector(
                        'section p')
                    linkedin_data['about_specialties'] = get_text_by_selector(
                        'dd[data-test-company-specialties]')
                    linkedin_data['about_size'] = get_text_by_selector(
                        'dd[data-test-company-size]')
                    linkedin_data['about_industry'] = get_text_by_selector(
                        'dd[data-test-company-industries]')
                    linkedin_data['about_headquarters'] = get_text_by_selector(
                        'dd[data-test-company-headquarters]')
                    linkedin_data['about_founded'] = get_text_by_selector(
                        'dd[data-test-company-founded]')
                    # Key people (may not always be available)
                    key_people = []
                    # fallback selector
                    for person in about_soup.select('li.org-people-profile-card__profile-title'):
                        key_people.append(person.get_text(strip=True))
                    if key_people:
                        linkedin_data['about_key_people'] = key_people
                except Exception:
                    pass
            return linkedin_data
        except Exception:
            return {}

    def run(self):
        self.fetch()
        self.extract_title()
        self.extract_description()
        self.extract_emails()
        self.extract_phones()
        self.extract_address()
        self.extract_key_people()
        self.extract_tech_keywords()
        self.generate_linkedin_search()
        domain = re.sub(r'^https?://(www\.)?', '', self.url).split('/')[0]
        linkedin_data = self.fetch_linkedin_data(domain)
        self.result['linkedin_data'] = linkedin_data
        return self.result
