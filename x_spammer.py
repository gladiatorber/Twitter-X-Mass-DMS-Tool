import os
import random
import time
import tweepy
from bs4 import BeautifulSoup
import requests
from datetime import datetime

# Configuration
ACCOUNTS_FILE = "accounts.txt"
MESSAGE_FILE = "message.txt"
TARGETS_FILE = "targets.txt"
PROXY_FILE = "proxies.txt"
SLEEP_BETWEEN_ACCOUNTS = 60  # seconds
MAX_ATTEMPTS = 3
RATE_LIMIT_DELAY = 30  # seconds between messages to avoid rate limits

def scrape_proxies():
    """Scrape proxies from free proxy websites"""
    print("Scraping proxies...")
    proxy_urls = [
        "https://www.sslproxies.org/",
        "https://free-proxy-list.net/",
        "https://hidemy.name/en/proxy-list/"
    ]
    
    proxies = []
    
    for url in proxy_urls:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse proxy list (adjust selectors based on website)
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')[1:11]  # Get first 10 proxies
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        proxies.append(f"{ip}:{port}")
        except Exception as e:
            print(f"Error scraping proxies from {url}: {e}")
    
    # Save proxies to file
    with open(PROXY_FILE, 'w') as f:
        f.write('\n'.join(proxies))
    
    return proxies

def load_proxies():
    """Load proxies from file or scrape new ones if file doesn't exist"""
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, 'r') as f:
            proxies = [line.strip() for line in f.readlines() if line.strip()]
    else:
        proxies = scrape_proxies()
    return proxies

def load_accounts():
    """Load Twitter accounts from file"""
    if not os.path.exists(ACCOUNTS_FILE):
        raise FileNotFoundError(f"{ACCOUNTS_FILE} not found")
    
    with open(ACCOUNTS_FILE, 'r') as f:
        accounts = [line.strip().split(':') for line in f.readlines() if line.strip()]
    return accounts

def load_message():
    """Load message from file"""
    if not os.path.exists(MESSAGE_FILE):
        raise FileNotFoundError(f"{MESSAGE_FILE} not found")
    
    with open(MESSAGE_FILE, 'r') as f:
        message = f.read().strip()
    return message

def load_targets():
    """Load target users from file"""
    if not os.path.exists(TARGETS_FILE):
        raise FileNotFoundError(f"{TARGETS_FILE} not found")
    
    with open(TARGETS_FILE, 'r') as f:
        targets = [line.strip() for line in f.readlines() if line.strip()]
    return targets

def init_twitter_client(consumer_key, consumer_secret, access_token, access_token_secret, proxy=None):
    """Initialize Twitter client with optional proxy"""
    try:
        # Configure proxy if provided
        if proxy:
            proxy_host, proxy_port = proxy.split(':')
            proxy_auth = None  # Add if your proxy requires authentication
            
            # Tweepy doesn't directly support proxies in the latest version,
            # so we'll use requests with proxy and pass to tweepy
            session = requests.Session()
            session.proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            auth = tweepy.OAuth1UserHandler(
                consumer_key,
                consumer_secret,
                access_token,
                access_token_secret
            )
            
            api = tweepy.API(auth, wait_on_rate_limit=True, session=session)
        else:
            auth = tweepy.OAuth1UserHandler(
                consumer_key,
                consumer_secret,
                access_token,
                access_token_secret
            )
            api = tweepy.API(auth, wait_on_rate_limit=True)
        
        # Verify credentials
        api.verify_credentials()
        return api
    except Exception as e:
        print(f"Error initializing Twitter client: {e}")
        return None

def send_dm(api, target_username, message):
    """Send direct message to target user"""
    try:
        # Get user ID from username
        user = api.get_user(screen_name=target_username)
        user_id = user.id_str
        
        # Send direct message
        api.send_direct_message(user_id, message)
        print(f"Message sent to @{target_username}")
        return True
    except tweepy.TweepyException as e:
        print(f"Failed to send message to @{target_username}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error sending to @{target_username}: {e}")
        return False

def main():
    # Load data
    accounts = load_accounts()
    message = load_message()
    targets = load_targets()
    proxies = load_proxies()
    
    if not accounts:
        print("No accounts found")
        return
    
    if not targets:
        print("No targets found")
        return
    
    if not message:
        print("No message found")
        return
    
    # Process each account
    for i, (consumer_key, consumer_secret, access_token, access_token_secret) in enumerate(accounts):
        print(f"\nProcessing account {i+1}/{len(accounts)}")
        
        # Select proxy (if available)
        proxy = None
        if proxies:
            proxy = random.choice(proxies)
            print(f"Using proxy: {proxy}")
        
        # Initialize client
        api = init_twitter_client(consumer_key, consumer_secret, access_token, access_token_secret, proxy)
        if not api:
            print("Failed to initialize Twitter client")
            continue
        
        # Process targets
        successful_sends = 0
        for target in targets:
            attempts = 0
            while attempts < MAX_ATTEMPTS:
                if send_dm(api, target, message):
                    successful_sends += 1
                    break
                attempts += 1
                time.sleep(RATE_LIMIT_DELAY)  # Wait before retry
            
            # Add delay between messages to avoid rate limits
            if successful_sends > 0 and successful_sends < len(targets):
                time.sleep(RATE_LIMIT_DELAY)
        
        print(f"Account sent {successful_sends}/{len(targets)} messages successfully")
        
        # Sleep between accounts if not last account
        if i < len(accounts) - 1:
            print(f"Waiting {SLEEP_BETWEEN_ACCOUNTS} seconds before next account...")
            time.sleep(SLEEP_BETWEEN_ACCOUNTS)

if __name__ == "__main__":
    main()