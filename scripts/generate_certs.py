#!/usr/bin/env python3
"""
Generate SSL certificates for C2 infrastructure
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_private_key():
    """Generate RSA private key"""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

def generate_certificate(
    common_name: str,
    alternative_names: list,
    days_valid: int = 365,
    is_ca: bool = False
):
    """Generate X.509 certificate"""
    
    # Generate key
    private_key = generate_private_key()
    
    # Certificate details
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "State"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "City"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "C2 Framework"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    # Create certificate
    builder = x509.CertificateBuilder()
    builder = builder.subject_name(subject)
    builder = builder.issuer_name(issuer)
    builder = builder.public_key(private_key.public_key())
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.not_valid_before(datetime.utcnow())
    builder = builder.not_valid_after(datetime.utcnow() + timedelta(days=days_valid))
    
    # Add extensions
    if alternative_names:
        san_list = []
        for name in alternative_names:
            if name.replace('.', '').isdigit():  # IP address
                san_list.append(x509.IPAddress(ipaddress.ip_address(name)))
            else:  # DNS name
                san_list.append(x509.DNSName(name))
        
        builder = builder.add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
    
    if is_ca:
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
    
    # Sign certificate
    certificate = builder.sign(private_key, hashes.SHA256())
    
    return private_key, certificate

def save_certificate(private_key, certificate, base_path: str):
    """Save certificate and key to files"""
    
    # Save private key
    with open(f"{base_path}.key", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Save certificate
    with open(f"{base_path}.crt", "wb") as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))
    
    print(f"Generated: {base_path}.key and {base_path}.crt")

def main():
    parser = argparse.ArgumentParser(description='Generate SSL certificates for C2')
    parser.add_argument('--output-dir', default='./certs', help='Output directory')
    parser.add_argument('--days', type=int, default=365, help='Certificate validity in days')
    parser.add_argument('--ca', action='store_true', help='Generate CA certificate')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Generate CA certificate if requested
    if args.ca:
        print("Generating CA certificate...")
        key, cert = generate_certificate(
            "C2 Framework CA",
            [],
            args.days * 2,  # CA valid for twice as long
            is_ca=True
        )
        save_certificate(key, cert, str(output_dir / "ca"))
    
    # Generate server certificate
    print("Generating server certificate...")
    key, cert = generate_certificate(
        "c2.local",
        ["localhost", "127.0.0.1", "c2.local", "*.c2.local"],
        args.days
    )
    save_certificate(key, cert, str(output_dir / "server"))
    
    # Generate client certificate for mutual TLS (optional)
    print("Generating client certificate...")
    key, cert = generate_certificate(
        "c2-client",
        [],
        args.days
    )
    save_certificate(key, cert, str(output_dir / "client"))
    
    print("\nCertificates generated successfully!")
    print("Remember to add c2.local to your /etc/hosts file for local testing")

if __name__ == "__main__":
    # Add imports that might not be at top
    import ipaddress
    main()
