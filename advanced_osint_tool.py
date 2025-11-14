# OSINT Reverse Phone/Name Lookup Tool
# 
# WARNING: This tool is for educational and ethical OSINT purposes only.
# Respect privacy laws (e.g., GDPR, CCPA) and terms of service of websites.
# Do not use for harassment, stalking, or illegal activities.
# Some features rely on public APIs/scraping, which may break if sites change.
# Install required packages: pip install requests beautifulsoup4 googlesearch-python phonenumbers
# 
# Features:
# - Reverse phone lookup: Searches free public directories.
# - Name search: Searches people finder sites.
# - Extracts: Name, Phone, Email, Location, Social Media, Digital Footprints.
# - Limitations: IP/MAC/Network Provider are hard/impossible to get publicly from phone/name alone.
#   - IP: Only if leaked via breaches (via HaveIBeenPwned-like search).
#   - MAC: Not publicly available (local network only).
#   - Network Provider: Inferred from phone number via phonenumbers lib.
# 
# Usage: Run this script in Python (e.g., double-click or IDLE). It will prompt for input.

import requests
from bs4 import BeautifulSoup
from googlesearch import search
import phonenumbers
from phonenumbers import carrier, geocoder
import re
import json
import time

# Rate limiting to be respectful
def delay():
    time.sleep(1)

class OSINTLookup:
    def __init__(self):
        self.results = {
            'name': '',
            'phone': '',
            'email': [],
            'location': '',
            'network_provider': '',
            'social_media': {},
            'digital_footprints': [],
            'ip_address': '',  # Rarely available
            'mac_address': 'Not publicly available'  # Impossible via OSINT
        }
    
    def parse_phone(self, phone):
        """Parse phone number to get carrier and location."""
        try:
            parsed = phonenumbers.parse(phone)
            self.results['network_provider'] = carrier.name_for_number(parsed, "en")
            self.results['location'] = geocoder.description_for_number(parsed, "en")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        except:
            return phone
    
    def search_reverse_phone(self, phone):
        """Search reverse phone on free sites: NumLookup, SpyTox."""
        formatted_phone = self.parse_phone(phone)
        self.results['phone'] = formatted_phone
        
        # NumLookup
        try:
            url = f"https://www.numlookup.com/search?phone={formatted_phone.replace('+', '').replace(' ', '').replace('-', '')}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')
            name_elem = soup.find('h1', class_='owner-name')
            if name_elem:
                self.results['name'] = name_elem.text.strip()
        except Exception as e:
            print(f"NumLookup error: {e}")
        
        # SpyTox (basic scrape)
        try:
            url = f"https://www.spytox.com/reverse-phone-lookup/{formatted_phone.replace('+', '').replace(' ', '').replace('-', '')}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')
            name_elem = soup.find('h2', string=re.compile('Name'))
            if name_elem:
                next_sib = name_elem.find_next_sibling('p')
                if next_sib:
                    self.results['name'] = next_sib.text.strip()
        except Exception as e:
            print(f"SpyTox error: {e}")
        
        delay()
    
    def search_name(self, name):
        """Search name on people finder sites: FastPeopleSearch, ThatsThem."""
        self.results['name'] = name
        
        # FastPeopleSearch
        try:
            url = f"https://www.fastpeoplesearch.com/name/{name.replace(' ', '-')}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Look for age/location as proxies
            location_elem = soup.find('div', class_='location')
            if location_elem:
                self.results['location'] = location_elem.text.strip()
        except Exception as e:
            print(f"FastPeopleSearch error: {e}")
        
        # ThatsThem
        try:
            url = f"https://thatsthem.com/name/{name.replace(' ', '-')}"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')
            phone_elem = soup.find('a', href=re.compile('phone'))
            if phone_elem:
                self.results['phone'] = phone_elem.text.strip()
            email_elem = soup.find('a', href=re.compile('email'))
            if email_elem:
                self.results['email'].append(email_elem.text.strip())
        except Exception as e:
            print(f"ThatsThem error: {e}")
        
        delay()
    
    def google_dorks(self, query):
        """Use Google dorks to find emails, socials, footprints."""
        emails = []
        socials = {'twitter': [], 'facebook': [], 'linkedin': [], 'instagram': []}
        footprints = []
        
        # Email dorks
        email_dork = f'"{query}" @gmail.com OR @yahoo.com OR @outlook.com -inurl:(login | sign)'
        try:
            for url in search(email_dork, num_results=5, sleep_interval=2):
                try:
                    resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resp.text)
                    for em in email_matches:
                        if em not in self.results['email']:
                            emails.append(em)
                except:
                    pass
        except Exception as e:
            print(f"Google email dork error: {e}")
        
        self.results['email'].extend(emails)
        
        # Social dorks
        for platform, domain in [('twitter', 'twitter.com'), ('facebook', 'facebook.com'), ('linkedin', 'linkedin.com'), ('instagram', 'instagram.com')]:
            social_dork = f'"{query}" site:{domain}'
            try:
                for url in search(social_dork, num_results=3, sleep_interval=2):
                    socials[platform].append(url)
            except Exception as e:
                print(f"Google social dork error for {platform}: {e}")
        
        self.results['social_media'] = socials
        
        # Footprints: Breaches, mentions
        breach_dork = f'"{query}" site:haveibeenpwned.com'
        try:
            for url in search(breach_dork, num_results=3, sleep_interval=2):
                footprints.append(f"Potential breach mention: {url}")
        except Exception as e:
            print(f"Google breach dork error: {e}")
        
        mentions_dork = f'"{query}" -site:facebook.com -site:twitter.com -site:linkedin.com'
        try:
            for url in search(mentions_dork, num_results=5, sleep_interval=2):
                footprints.append(f"Web mention: {url}")
        except Exception as e:
            print(f"Google mentions dork error: {e}")
        
        self.results['digital_footprints'] = footprints[:10]  # Limit
    
    def search_breaches_for_ip(self, email):
        """Check for leaked IPs via breaches (basic, using DeHashed-like logic; requires API for full)."""
        # Placeholder: Real impl would use API like HaveIBeenPwned or DeHashed
        # For demo, simulate
        if email:
            # Mock: In real, query API
            self.results['ip_address'] = 'Potential leak: Check HaveIBeenPwned for ' + email
        else:
            self.results['ip_address'] = 'No email found for IP leak search'
    
    def run_lookup(self, input_str):
        """Main lookup function."""
        if re.match(r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$', input_str):
            self.search_reverse_phone(input_str)
        else:
            self.search_name(input_str)
        
        # Cross-search with found name/phone
        query = self.results['name'] or input_str
        self.google_dorks(query)
        
        if self.results['email']:
            self.search_breaches_for_ip(self.results['email'][0])
        
        return self.results

def print_results(results):
    """Print results in a user-friendly format."""
    print("\n" + "="*50)
    print("OSINT LOOKUP RESULTS")
    print("="*50)
    
    print(f"Name: {results['name'] or 'Not found'}")
    print(f"Phone: {results['phone'] or 'Not found'}")
    print(f"Location: {results['location'] or 'Not found'}")
    print(f"Network Provider: {results['network_provider'] or 'Not found'}")
    print(f"IP Address: {results['ip_address'] or 'Not found'}")
    print(f"MAC Address: {results['mac_address']}")
    
    if results['email']:
        print("Emails:")
        for email in results['email']:
            print(f"  - {email}")
    else:
        print("Emails: Not found")
    
    print("Social Media:")
    for platform, urls in results['social_media'].items():
        if urls:
            print(f"  {platform.capitalize()}:")
            for url in urls:
                print(f"    - {url}")
        else:
            print(f"  {platform.capitalize()}: Not found")
    
    print("Digital Footprints:")
    for footprint in results['digital_footprints']:
        print(f"  - {footprint}")
    
    if not results['digital_footprints']:
        print("  No footprints found.")
    
    print("="*50 + "\n")

def main():
    print("Welcome to the OSINT Reverse Phone/Name Lookup Tool!")
    print("Enter a phone number (e.g., +1-555-123-4567) or a name (e.g., John Doe).")
    print("Note: Use international phone format for best results.\n")
    
    input_str = input("Enter phone or name: ").strip()
    
    if not input_str:
        print("No input provided. Exiting.")
        return
    
    print("\nSearching... This may take a few moments.\n")
    
    tool = OSINTLookup()
    results = tool.run_lookup(input_str)
    
    print_results(results)
    
    # Optional: Save to JSON
    save = input("\nSave results to JSON file? (y/n): ").strip().lower()
    if save == 'y':
        filename = "osint_results.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Results saved to {filename}")

if __name__ == "__main__":
    main()
