#!/usr/bin/env python3
"""
Build agent payloads
"""

import os
import sys
import argparse
import json
import shutil
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.services.payload_generator import PayloadGenerator

def main():
    parser = argparse.ArgumentParser(description='Build C2 agent payloads')
    parser.add_argument('--name', required=True, help='Payload name')
    parser.add_argument('--type', required=True, 
                       choices=['exe', 'dll', 'shellcode', 'powershell', 'python', 'bash'],
                       help='Payload type')
    parser.add_argument('--platform', required=True,
                       choices=['windows', 'linux', 'darwin'],
                       help='Target platform')
    parser.add_argument('--arch', required=True,
                       choices=['x86', 'x64', 'arm64'],
                       help='Target architecture')
    parser.add_argument('--callback', required=True, help='Callback URL')
    parser.add_argument('--session', required=True, help='Session ID')
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--config', help='Additional configuration JSON file')
    
    args = parser.parse_args()
    
    # Load additional config
    config = {
        'callback_host': args.callback,
        'session_id': args.session
    }
    
    if args.config:
        with open(args.config, 'r') as f:
            config.update(json.load(f))
    
    # Create payload generator
    generator = PayloadGenerator()
    
    # Set output directory
    if args.output:
        generator.output_dir = Path(args.output)
        generator.output_dir.mkdir(exist_ok=True)
    
    print(f"Building {args.type} payload for {args.platform}/{args.arch}...")
    
    try:
        # Generate payload
        output_path = generator.generate_payload(
            name=args.name,
            payload_type=args.type,
            platform=args.platform,
            architecture=args.arch,
            listener_id='standalone',  # For standalone builds
            configuration=config,
            user_id='builder'
        )
        
        print(f"Payload generated: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
