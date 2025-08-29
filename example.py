#!/usr/bin/env python3
"""
Example usage script for SMTP Checker
Demonstrates how to use the SMTPChecker programmatically
"""

import json
import os
from smtpcheck import SMTPChecker, CONFIG

def setup_example_config():
    """Setup example configuration for testing"""
    
    # Example configuration - update with your real values
    example_config = {
        "max_threads": 5,  # Lower threads for testing
        "delay_range": [0.5, 2],  # Shorter delays for testing
        "smtp_timeout": 5,
        "test_email_recipient": "test@example.com",  # Update this
        "telegram_bot_token": "",  # Add your bot token
        "telegram_chat_id": "",  # Add your chat ID
    }
    
    # Update global config
    CONFIG.update(example_config)
    
    print("✅ Configuration updated for example usage")

def create_test_combos():
    """Create a small test file with sample combos"""
    
    test_combos = [
        "# Example test combos",
        "test1@outlook.com:testpassword1",
        "test2@hotmail.com:testpassword2", 
        "invalid@format",  # This will be skipped
        "test3@live.com;testpassword3",
        "test4@office365.com|testpassword4"
    ]
    
    with open('test_combos.txt', 'w') as f:
        f.write('\n'.join(test_combos))
    
    # Update config to use test file
    CONFIG['input_file'] = 'test_combos.txt'
    
    print("✅ Test combos file created: test_combos.txt")

def run_example():
    """Run the SMTP checker with example configuration"""
    
    print("🚀 SMTP Checker Example Usage")
    print("=" * 40)
    
    # Setup
    setup_example_config()
    create_test_combos()
    
    # Create and run checker
    checker = SMTPChecker()
    
    print(f"\n📋 Current Configuration:")
    print(f"   - Max threads: {CONFIG['max_threads']}")
    print(f"   - Delay range: {CONFIG['delay_range']}")
    print(f"   - Timeout: {CONFIG['smtp_timeout']}s")
    print(f"   - Input file: {CONFIG['input_file']}")
    
    print(f"\n🔄 Starting SMTP checking...")
    
    try:
        checker.run()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Cleanup
        if os.path.exists('test_combos.txt'):
            os.remove('test_combos.txt')
            print("🧹 Cleaned up test files")

if __name__ == "__main__":
    run_example()