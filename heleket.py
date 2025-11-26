#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heleket Payment Gateway Integration
"""

import requests
import json
import hashlib
import base64
from datetime import datetime
from typing import Optional, Dict


class HeleketPayment:
    """Heleket Payment Gateway Handler"""
    
    def __init__(self, merchant_id: str, api_key: str, api_url: str = "https://api.heleket.com/v1/payment"):
        self.merchant_id = merchant_id
        self.api_key = api_key
        self.api_url = api_url
        self.verify_url = "https://api.heleket.com/v1/verify"
    
    def _calculate_signature(self, payload: dict) -> tuple[str, str]:
        """Calculate MD5 signature for Heleket API"""
        # 1. Create compact JSON string (NO SORTING)
        json_body = json.dumps(payload, separators=(',', ':'))
        
        # 2. Base64 Encode the JSON string
        b64 = base64.b64encode(json_body.encode()).decode()
        
        # 3. Calculate MD5 hash of (Base64 + API_KEY)
        signature = hashlib.md5((b64 + self.api_key).encode()).hexdigest()
        
        return signature, json_body
    
    def create_invoice(self, amount: float, order_id: str, return_url: str = "https://t.me/your_bot", 
                      success_url: str = "https://t.me/your_bot", additional_data: str = "") -> Dict:
        """
        Create payment invoice
        
        Returns:
            {
                'success': True/False,
                'payment_url': 'https://...',
                'invoice_id': '...',
                'error': 'error message if failed'
            }
        """
        try:
            # Prepare payload
            payload = {
                "amount": f"{amount:.2f}",
                "currency": "USD",
                "order_id": order_id,
                "url_return": return_url,
                "url_success": success_url,
                "additional_data": additional_data or f"Recharge ${amount:.2f}"
            }
            
            # Calculate signature
            signature, json_body = self._calculate_signature(payload)
            
            # Prepare headers
            headers = {
                "merchant": self.merchant_id,
                "sign": signature,
                "Content-Type": "application/json"
            }
            
            # Send request
            response = requests.post(self.api_url, headers=headers, data=json_body, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if successful (adjust based on actual API response)
                if data.get('status') == 'success' or 'result' in data:
                    return {
                        'success': True,
                        'payment_url': data.get('result', {}).get('url', data.get('url', '')),
                        'invoice_id': data.get('result', {}).get('invoice_id', data.get('invoice_id', order_id)),
                        'order_id': order_id
                    }
                else:
                    return {
                        'success': False,
                        'error': data.get('message', 'Unknown error from Heleket')
                    }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error: {str(e)}"
            }
    
    def verify_payment(self, order_id: str) -> Dict:
        """
        Verify payment status
        
        Returns:
            {
                'success': True/False,
                'paid': True/False,
                'amount': 10.00,
                'currency': 'USD',
                'error': 'error message if failed'
            }
        """
        try:
            # Prepare payload for verification
            payload = {
                "order_id": order_id
            }
            
            # Calculate signature
            signature, json_body = self._calculate_signature(payload)
            
            # Prepare headers
            headers = {
                "merchant": self.merchant_id,
                "sign": signature,
                "Content-Type": "application/json"
            }
            
            # Send request
            response = requests.post(self.verify_url, headers=headers, data=json_body, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check payment status (adjust based on actual API response)
                status = data.get('status', '').lower()
                payment_status = data.get('payment_status', '').lower()
                
                is_paid = (status in ['success', 'completed', 'paid'] or 
                          payment_status in ['success', 'completed', 'paid'])
                
                return {
                    'success': True,
                    'paid': is_paid,
                    'amount': float(data.get('amount', 0)),
                    'currency': data.get('currency', 'USD'),
                    'order_id': order_id
                }
            else:
                return {
                    'success': False,
                    'paid': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'paid': False,
                'error': f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'paid': False,
                'error': f"Error: {str(e)}"
            }


# Test function
def test_heleket():
    """Test Heleket integration"""
    merchant_id = "YOUR_MERCHANT_ID"
    api_key = "YOUR_API_KEY"
    
    heleket = HeleketPayment(merchant_id, api_key)
    
    # Test create invoice
    print("Testing invoice creation...")
    result = heleket.create_invoice(
        amount=1.00,
        order_id=f"TEST_{int(datetime.now().timestamp())}",
        additional_data="Test Invoice"
    )
    
    print("Result:", json.dumps(result, indent=2))
    
    if result['success']:
        print(f"\n✅ Payment URL: {result['payment_url']}")
        
        # Test verification
        print("\nTesting payment verification...")
        verify_result = heleket.verify_payment(result['order_id'])
        print("Verification Result:", json.dumps(verify_result, indent=2))
    else:
        print(f"\n❌ Error: {result['error']}")


if __name__ == '__main__':
    test_heleket()
