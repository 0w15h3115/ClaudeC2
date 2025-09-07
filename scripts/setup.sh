#!/bin/bash
# C2 Framework Setup Script

set -e

echo "╔═══════════════════════════════════╗"
echo "║   C2 Framework Setup Script       ║"
echo "╚═══════════════════════════════════╝"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root!${NC}"
   exit 1
fi

# Function to print status
print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    print_error "Unsupported OS: $OSTYPE"
    exit 1
fi

print_status "Detected OS: $OS"

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    print_error "Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi

print_status "Python version: $PYTHON_VERSION"

# Check for required commands
REQUIRED_COMMANDS=("docker" "docker-compose" "git")

for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if ! command -v $cmd &> /dev/null; then
        print_error "$cmd is required but not installed"
        exit 1
    fi
done

# Create directories
print_status "Creating directory structure..."
mkdir -p {uploads,downloads,payloads,logs,certs}
mkdir -p agent/{transports,evasion,builders}
mkdir -p docs
mkdir -p tests/{server,agent,integration}

# Install Python dependencies
print_status "Installing Python dependencies..."

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# Install server dependencies
cd server
pip install -r requirements.txt
cd ..

# Install agent dependencies (in separate venv)
cd agent
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Generate SSL certificates
print_status "Generating SSL certificates..."
./scripts/generate_certs.sh

# Initialize database
print_status "Initializing database..."
cd server
python -c "from core.database import init_db; init_db()"
cd ..

# Build Docker images
print_status "Building Docker images..."
docker-compose build

# Setup Git hooks
print_status "Setting up Git hooks..."
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run linting and tests before commit

# Python linting
echo "Running Python linting..."
cd server && flake8 . && cd ..
cd agent && flake8 . && cd ..

# Run basic tests
echo "Running tests..."
cd server && python -m pytest tests/ -v && cd ..
EOF

chmod +x .git/hooks/pre-commit

# Create .env file
if [ ! -f ".env" ]; then
    print_status "Creating .env file..."
    cat > .env << EOF
# Environment variables
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=sqlite:///./c2_teamserver.db
REDIS_URL=redis://localhost:6379
DEBUG=false
EOF
fi

print_status "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env file with your configuration"
echo "2. Run 'docker-compose up' to start services"
echo "3. Access the web UI at http://localhost:3000"
echo "4. Default admin credentials: admin / changeme123!"
echo ""
print_warning "Remember to change default passwords and generate new SSL certificates for production!"
