"""
Card checker module using autoshopify API
"""

import time
import random
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class ShopifyChecker:
    def __init__(self, sites: list, proxies: list, timeout: int = 30, retries: int = 2):
        self.sites = sites
        self.proxies = proxies
        self.timeout = timeout
        self.retries = retries
    
    def get_random_proxy(self) -> Optional[str]:
        """Get random proxy from list"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def parse_card(self, card_string: str) -> Optional[Dict[str, str]]:
        """Parse card string format: number|month|year|cvv"""
        try:
            parts = card_string.strip().split('|')
            if len(parts) != 4:
                return None
            
            return {
                'number': parts[0].strip(),
                'month': parts[1].strip(),
                'year': parts[2].strip(),
                'cvv': parts[3].strip()
            }
        except Exception:
            return None
    
    def get_bin_info(self, card_number: str) -> Dict[str, str]:
        """Get BIN information for card"""
        bin_number = card_number[:6]
        
        try:
            # Using free BIN lookup API
            response = requests.get(f'https://lookup.binlist.net/{bin_number}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                bank = data.get('bank', {}).get('name', 'UNKNOWN')
                brand = data.get('brand', 'UNKNOWN').upper()
                card_type = data.get('type', 'UNKNOWN').upper()
                country = data.get('country', {}).get('name', 'UNKNOWN')
                country_emoji = data.get('country', {}).get('emoji', '🌍')
                
                return {
                    'bank': bank,
                    'brand': brand,
                    'type': card_type,
                    'country': country,
                    'emoji': country_emoji
                }
        except Exception:
            pass
        
        return {
            'bank': 'UNKNOWN',
            'brand': 'UNKNOWN',
            'type': 'UNKNOWN',
            'country': 'UNKNOWN',
            'emoji': '🌍'
        }
    
    def check_card_with_autoshopify(self, card: Dict[str, str], site: str, proxy: Optional[str]) -> Dict[str, Any]:
        """
        Check card using autoshopify-like method
        Note: This is a simulation since autoshopify is not a public library
        In production, you would use the actual autoshopify.stormxcc() function
        """
        start_time = time.time()
        
        try:
            # Format proxy for requests
            proxy_dict = None
            if proxy:
                # Format: host:port:username:password
                parts = proxy.split(':')
                if len(parts) == 4:
                    proxy_url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                    proxy_dict = {
                        'http': proxy_url,
                        'https': proxy_url
                    }
            
            # Simulate autoshopify check
            # In real implementation, use: resp = stormxcc(site=site, cc=card_string, proxy=proxy, tries=self.retries, timeout=self.timeout)
            
            # For now, we'll simulate different responses
            card_string = f"{card['number']}|{card['month']}|{card['year']}|{card['cvv']}"
            
            # Simulate API call
            time.sleep(random.uniform(1, 3))  # Simulate processing time
            
            # Simulate different response scenarios
            responses = [
                {'status': 'charged', 'message': 'Thanks for your purchase!', 'amount': '1'},
                {'status': 'charged', 'message': 'Payment successful', 'amount': '1'},
                {'status': 'charged', 'message': 'Your order has been confirmed', 'amount': '1'},
                {'status': 'declined', 'message': 'CARD_DECLINED'},
                {'status': 'declined', 'message': 'RISKY'},
                {'status': 'declined', 'message': 'Insufficient funds'},
                {'status': 'error', 'message': 'Payment processing error'},
            ]
            
            # Randomly select response (in production, this would be actual API response)
            response = random.choice(responses)
            
            elapsed_time = time.time() - start_time
            
            return {
                'success': response['status'] == 'charged',
                'status': response['status'],
                'message': response['message'],
                'amount': response.get('amount', '0'),
                'site': site,
                'time_taken': round(elapsed_time, 2),
                'proxy_used': proxy if proxy else 'None'
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            return {
                'success': False,
                'status': 'error',
                'message': str(e),
                'amount': '0',
                'site': site,
                'time_taken': round(elapsed_time, 2),
                'proxy_used': proxy if proxy else 'None'
            }
    
    def check_card(self, card_string: str, retry_count: int = 0) -> Dict[str, Any]:
        """Main card checking function"""
        # Parse card
        card = self.parse_card(card_string)
        if not card:
            return {
                'success': False,
                'status': 'error',
                'message': 'Invalid card format. Use: number|month|year|cvv',
                'card': card_string,
                'time_taken': 0
            }
        
        # Get random site and proxy
        site = random.choice(self.sites)
        proxy = self.get_random_proxy()
        
        # Check card
        result = self.check_card_with_autoshopify(card, site, proxy)
        
        # Add card info to result
        result['card'] = card_string
        result['bin_info'] = self.get_bin_info(card['number'])
        result['retries'] = retry_count
        
        # Retry logic for errors (not for declined cards)
        if result['status'] == 'error' and retry_count < self.retries:
            time.sleep(1)
            return self.check_card(card_string, retry_count + 1)
        
        return result
    
    def check_multiple_cards(self, cards: list, callback=None) -> list:
        """Check multiple cards and return only charged ones"""
        charged_cards = []
        
        for i, card in enumerate(cards):
            result = self.check_card(card)
            
            # Only keep charged cards
            if result['success'] and result['status'] == 'charged':
                charged_cards.append(result)
                
                # Call callback if provided (for real-time updates)
                if callback:
                    callback(result, i + 1, len(cards))
            
            # Small delay between checks
            time.sleep(random.uniform(1, 3))
        
        return charged_cards


# For production use with actual autoshopify library:
"""
from autoshopify import stormxcc

def check_card_with_autoshopify_real(card: Dict[str, str], site: str, proxy: Optional[str], timeout: int, retries: int) -> Dict[str, Any]:
    start_time = time.time()
    
    try:
        card_string = f"{card['number']}|{card['month']}|{card['year']}{card['cvv']}"
        
        resp = stormxcc(
            site=site,
            cc=card_string,
            proxy=proxy,
            tries=retries,
            timeout=timeout,
        )
        
        elapsed_time = time.time() - start_time
        
        # Parse response
        response_text = str(resp.text)
        
        # Check if card was charged
        if "CARD_DECLINED" not in response_text and "RISKY" not in response_text:
            # Determine if it's a successful charge
            success_indicators = ['purchase', 'success', 'confirmed', 'thank you', 'charged']
            is_charged = any(indicator in response_text.lower() for indicator in success_indicators)
            
            return {
                'success': is_charged,
                'status': 'charged' if is_charged else 'unknown',
                'message': response_text[:200],
                'amount': '1',  # Most test charges are $1
                'site': site,
                'time_taken': round(elapsed_time, 2),
                'proxy_used': proxy if proxy else 'None'
            }
        else:
            return {
                'success': False,
                'status': 'declined',
                'message': response_text[:200],
                'amount': '0',
                'site': site,
                'time_taken': round(elapsed_time, 2),
                'proxy_used': proxy if proxy else 'None'
            }
    
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            'success': False,
            'status': 'error',
            'message': str(e),
            'amount': '0',
            'site': site,
            'time_taken': round(elapsed_time, 2),
            'proxy_used': proxy if proxy else 'None'
        }
"""
