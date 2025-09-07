# ClaudeC2 Framework

A modern Command and Control (C2) framework designed for authorized security testing, red team exercises, and defensive security research.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Node.js](https://img.shields.io/badge/node.js-16%2B-green.svg)
![Docker](https://img.shields.io/badge/docker-compose-blue.svg)

## ⚠️ Legal Notice

**THIS FRAMEWORK IS INTENDED FOR AUTHORIZED SECURITY TESTING ONLY**

- Use only on systems you own or have explicit written permission to test
- Unauthorized use is illegal and unethical
- Always follow responsible disclosure practices
- Comply with all applicable laws and regulations
- Use for defensive security research and authorized penetration testing only

## 🎯 Purpose & Use Cases

This framework is designed for:

- **Authorized Penetration Testing**: Simulate real-world attacks in controlled environments
- **Red Team Exercises**: Test organizational security posture and incident response
- **Security Research**: Study attack patterns and develop defensive strategies  
- **Training & Education**: Learn about C2 techniques in safe, isolated environments
- **Blue Team Training**: Understand attacker tools to improve detection capabilities

## ✨ Features

### 🖥️ Modern Web Interface
- **React-based Dashboard**: Clean, responsive UI with real-time updates
- **Authentication System**: Secure login with role-based access control
- **Session Management**: Organize and track testing sessions
- **Real-time Monitoring**: Live agent status and activity feeds

### 🔧 Technical Capabilities  
- **Multi-platform Support**: Windows, Linux, and macOS compatibility
- **Multiple Communication Protocols**: HTTP/HTTPS, DNS, WebSocket
- **Modular Architecture**: Easily extensible plugin system
- **End-to-end Encryption**: Secure communications with strong cryptography
- **Comprehensive Logging**: Detailed audit trails for compliance

### 🛡️ Security Features
- **Anti-detection Techniques**: Evasion capabilities for realistic testing
- **Sandbox Detection**: Identify virtualized environments
- **Process Management**: Advanced process injection and hollowing
- **Network Tools**: Port scanning, lateral movement simulation

### 📊 Reporting & Analytics
- **Executive Reports**: High-level summaries for management
- **Technical Reports**: Detailed findings with remediation steps
- **MITRE ATT&CK Mapping**: Align activities with established frameworks
- **IOC Generation**: Indicators of Compromise for detection teams

## 🚀 Quick Start

### Prerequisites

Ensure you have the following installed:

- **Docker** and **Docker Compose** (recommended)
- **Python 3.8+** (for development)
- **Node.js 16+** (for development)
- **Git** (for version control)

### Installation Methods

#### Option 1: Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/0w15h3115/ClaudeC2.git
   cd ClaudeC2
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the services:**
   ```bash
   docker-compose up -d
   ```

4. **Access the web interface:**
   - URL: http://localhost:3000
   - Username: `owlshells`
   - Password: `KimPossible2`

#### Option 2: Manual Installation

1. **Setup the server:**
   ```bash
   cd server
   pip install -r requirements.txt
   python run.py
   ```

2. **Setup the client:**
   ```bash
   cd client
   npm install
   npm run dev
   ```

### First Steps

1. **Change Default Credentials**: Immediately update the default admin password
2. **Configure SSL/TLS**: Enable HTTPS for production deployments
3. **Review Configuration**: Customize settings in `config/server.yaml`
4. **Create Test Session**: Start your first authorized testing session

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React Client  │────▶│  FastAPI Server │────▶│   PostgreSQL    │
│   (Port 3000)   │     │   (Port 8000)   │     │   (Port 5432)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────┴────────┐
                        │  Redis Cache    │
                        │  (Port 6379)    │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
         ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
         │ Agent 1 │       │ Agent 2 │      │ Agent N │
         │ Windows │       │  Linux  │      │  macOS  │
         └─────────┘       └─────────┘      └─────────┘
```

### Core Components

- **Client**: React-based web interface with modern UI/UX
- **Server**: FastAPI backend with RESTful API architecture  
- **Database**: PostgreSQL for persistent data storage
- **Cache**: Redis for session management and real-time features
- **Agents**: Cross-platform implants with modular capabilities

## 📚 Usage Guide

### Creating a New Session

1. Navigate to the **Sessions** page
2. Click **"New Session"** 
3. Configure session parameters:
   - Name and description
   - Target environment details
   - Authorization documentation
4. Set up listeners on appropriate ports
5. Generate and deploy agents

### Agent Management

#### Generating Agents
```bash
# Using make commands
make payload-windows    # Generate Windows executable
make payload-linux      # Generate Linux payload  
make payload-macos      # Generate macOS payload

# Or use the web UI payload generator for custom options
```

#### Agent Interaction
- **Command Execution**: Run commands remotely
- **File Operations**: Upload, download, and manage files
- **Process Management**: List, create, and terminate processes
- **Network Tools**: Port scans, network discovery
- **Screenshot Capture**: Visual reconnaissance

### Listener Configuration

Configure listeners for different protocols:

```yaml
listeners:
  http:
    port: 8080
    ssl: false
  https:  
    port: 8443
    ssl: true
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
  dns:
    port: 53
    domain: "example.com"
```

## 🛠️ Development

### Project Structure

```
ClaudeC2/
├── server/              # Backend API server
│   ├── api/            # REST API endpoints
│   ├── core/           # Core functionality
│   ├── listeners/      # Protocol listeners
│   └── services/       # Business logic
├── client/             # React frontend
│   ├── src/
│   │   ├── components/ # React components
│   │   ├── services/   # API clients
│   │   └── contexts/   # State management
├── agent/              # Agent/implant code
│   ├── core/          # Core agent functionality
│   ├── modules/       # Feature modules
│   └── transports/    # Communication protocols
├── shared/             # Shared libraries
├── config/             # Configuration files
├── scripts/            # Utility scripts
├── docs/              # Documentation
└── tests/             # Test suites
```

### Development Setup

1. **Backend Development:**
   ```bash
   cd server
   pip install -r requirements.txt
   uvicorn api.main:app --reload
   ```

2. **Frontend Development:**
   ```bash
   cd client  
   npm install
   npm run dev
   ```

3. **Running Tests:**
   ```bash
   # All tests
   make test

   # Specific components
   make test-server
   make test-client
   make test-agent
   ```

### Building from Source

```bash
# Build all components
make build

# Individual components
make build-server
make build-client  
make build-agent
```

## ⚙️ Configuration

### Server Configuration

Edit `config/server.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

database:
  url: "postgresql://user:password@localhost:5432/c2db"
  pool_size: 10
  
security:
  secret_key: "your-secret-key-here"
  token_expire_minutes: 30
  password_hash_rounds: 12

logging:
  level: "INFO"
  file: "/var/log/c2/server.log"
```

### Environment Variables

Create `.env` file:

```bash
# Database
POSTGRES_USER=c2user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=c2database

# Security  
SECRET_KEY=your-super-secret-jwt-key
ADMIN_PASSWORD=your-admin-password

# Optional
DEBUG=false
LOG_LEVEL=INFO
```

## 🔒 Security Best Practices

### Deployment Security

- **Change Default Credentials**: Update all default passwords immediately
- **Use HTTPS**: Always enable SSL/TLS in production
- **Network Segmentation**: Isolate C2 infrastructure from production networks
- **Access Control**: Implement strong authentication and authorization
- **Regular Updates**: Keep all components updated with security patches

### Operational Security

- **Audit Logging**: Enable comprehensive logging for all activities
- **Session Management**: Use proper session timeouts and controls
- **Data Encryption**: Ensure all communications are encrypted
- **Secure Storage**: Protect configuration files and certificates
- **Incident Response**: Have procedures for security incidents

## 🤝 Contributing

We welcome contributions from the security community!

### How to Contribute

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow existing code style and conventions
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting
- Include clear commit messages

### Bug Reports

When reporting bugs, please include:

- Operating system and version
- Python/Node.js versions
- Steps to reproduce the issue
- Expected vs actual behavior
- Log files and error messages

## 📖 Documentation

- [API Documentation](docs/api.md) - Complete API reference
- [Agent Development](docs/agent-development.md) - Building custom agents
- [Deployment Guide](docs/deployment.md) - Production deployment
- [Contributing Guide](docs/contributing.md) - Development guidelines
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/0w15h3115/ClaudeC2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/0w15h3115/ClaudeC2/discussions)
- **Security**: For security issues, please email security@example.com

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

**IMPORTANT: This tool is provided for educational and authorized testing purposes only.**

- The authors are not responsible for any misuse or damage caused by this software
- Users are solely responsible for ensuring they have proper authorization before use  
- This tool should only be used in compliance with applicable laws and regulations
- Use of this tool against systems without explicit permission is illegal
- Always follow responsible disclosure practices when conducting security research

## 🙏 Acknowledgments

- Security researchers and ethical hackers who contribute to making systems safer
- The open-source community for providing foundational tools and libraries
- Organizations that support security research and responsible disclosure
- Red and blue team professionals who help test and improve security postures

---

**Remember: With great power comes great responsibility. Use this tool ethically and legally.**