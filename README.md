# C2 Framework v2.0

A modern Command and Control (C2) framework for authorized security testing.

## ⚠️ Legal Notice

This framework is intended for authorized security testing only. Use of this framework without proper authorization is illegal and unethical. Always ensure you have explicit permission before testing any systems.

## Features

- **Multi-platform Support**: Windows, Linux, and macOS agents
- **Multiple Communication Protocols**: HTTP/S, DNS, WebSocket
- **Modern Web UI**: React-based dashboard with real-time updates
- **Modular Architecture**: Easily extensible with new modules and features
- **Encryption**: End-to-end encryption for all communications
- **Evasion Techniques**: Anti-debugging, sandbox detection, and more
- **Comprehensive Logging**: Detailed audit trails and operational logs
- **Report Generation**: Executive summaries, IOC reports, and MITRE ATT&CK mapping

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/c2-framework.git
cd c2-framework

Run the setup script:

bash./scripts/setup.sh

Start the services:

bashdocker-compose up -d

Access the web UI at http://localhost:3000

Default credentials: admin / changeme123!



Architecture
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Web UI    │────▶│  API Server │────▶│  Database   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │  Listeners  │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
   │ Agent 1 │       │ Agent 2 │      │ Agent N │
   └─────────┘       └─────────┘      └─────────┘
Usage
Creating a Session

Log in to the web UI
Navigate to Sessions
Click "New Session"
Configure listeners

Generating Payloads
bashmake payload-windows  # Windows executable
make payload-linux    # Linux payload
make payload-macos    # macOS payload
Or use the web UI payload generator.
Managing Agents

View connected agents in the Dashboard
Execute commands via the Command Interface
Browse files, manage processes, and more

Development
Project Structure
c2-framework/
├── server/         # Backend API server
├── client/         # React web UI
├── agent/          # Agent/implant code
├── shared/         # Shared libraries
├── config/         # Configuration files
├── scripts/        # Utility scripts
├── docs/           # Documentation
└── tests/          # Test suites
Running Tests
bashmake test           # Run all tests
make test-server    # Server tests only
make test-agent     # Agent tests only
Building from Source
bashmake build          # Build all components
make server         # Build server only
make client         # Build client only
make agent          # Build agent only
Configuration
Server Configuration
Edit config/server.yaml:
yamlserver:
  host: "0.0.0.0"
  port: 8000
  
database:
  url: "postgresql://user:pass@localhost/c2db"
  
security:
  secret_key: "your-secret-key-here"
Agent Configuration
See config/agent_template.yaml for agent options.
Security Considerations

Change Default Credentials: Always change default passwords
Use HTTPS: Enable SSL/TLS for production deployments
Network Segmentation: Isolate C2 infrastructure
Access Control: Implement proper authentication and authorization
Audit Logging: Monitor all activities

Contributing

Fork the repository
Create a feature branch
Commit your changes
Push to the branch
Create a Pull Request

Documentation

API Documentation
Agent Development
Deployment Guide
Contributing Guide

License
This project is licensed under the MIT License - see the LICENSE file for details.
Disclaimer
This tool is provided for educational and authorized testing purposes only. The authors are not responsible for any misuse or damage caused by this program.

**File 51: c2-framework/.flake8**

```ini
[flake8]
max-line-length = 100
exclude = 
    .git,
    __pycache__,
    venv,
    env,
    .venv,
    .eggs,
    *.egg,
    build,
    dist,
    migrations
ignore = 
    E203,  # whitespace before ':'
    W503,  # line break before binary operator
    E501   # line too long (handled by black)
per-file-ignores =
    __init__.py: F401
# ClaudeC2
