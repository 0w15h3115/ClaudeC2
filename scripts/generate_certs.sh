#!/bin/bash
# Generate SSL certificates for C2 infrastructure

set -e

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}[+] Generating SSL certificates...${NC}"

# Create certs directory if it doesn't exist
mkdir -p certs

# Generate CA private key
openssl genrsa -out certs/ca.key 2048

# Generate CA certificate
openssl req -new -x509 -days 3650 -key certs/ca.key -out certs/ca.crt \
    -subj "/C=US/ST=State/L=City/O=C2 Framework/CN=C2 Framework CA"

# Generate server private key
openssl genrsa -out certs/server.key 2048

# Generate server certificate signing request
openssl req -new -key certs/server.key -out certs/server.csr \
    -subj "/C=US/ST=State/L=City/O=C2 Framework/CN=c2.local"

# Create extensions file for SAN
cat > certs/server.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = c2.local
DNS.3 = *.c2.local
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOF

# Generate server certificate signed by CA
openssl x509 -req -in certs/server.csr -CA certs/ca.crt -CAkey certs/ca.key \
    -CAcreateserial -out certs/server.crt -days 365 \
    -extensions v3_ext -extfile certs/server.ext

# Generate client private key
openssl genrsa -out certs/client.key 2048

# Generate client certificate signing request
openssl req -new -key certs/client.key -out certs/client.csr \
    -subj "/C=US/ST=State/L=City/O=C2 Framework/CN=c2-client"

# Generate client certificate signed by CA
openssl x509 -req -in certs/client.csr -CA certs/ca.crt -CAkey certs/ca.key \
    -CAcreateserial -out certs/client.crt -days 365

# Clean up CSRs and extensions file
rm certs/*.csr certs/server.ext

# Set appropriate permissions
chmod 600 certs/*.key
chmod 644 certs/*.crt

echo -e "${GREEN}[+] SSL certificates generated successfully!${NC}"
echo "Certificates location: ./certs/"
echo "Add 'c2.local' to your /etc/hosts file for local testing"