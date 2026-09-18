#!/usr/bin/env bash
# ==============================================================================
# Friday — One-Command Zero-Friction Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/friday-memory/friday/main/install.sh | bash
# ==============================================================================

set -eo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}"
echo "  ⚡ Friday — Persistent Cognitive Memory for AI Coding Agents"
echo "  -----------------------------------------------------------"
echo -e "${NC}"

# 1. Dependency checks
command -v docker >/dev/null 2>&1 || {
    echo -e "${RED}❌ Docker is required but not installed.${NC}"
    echo "   Please install Docker from https://docs.docker.com/get-docker/ and rerun."
    exit 1
}

# Determine docker compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}❌ Docker Compose is required but not installed.${NC}"
    exit 1
fi

# 2. Determine target directory
if [ -f "docker-compose.yml" ] && [ -d "mcp" ]; then
    INSTALL_DIR="$(pwd)"
    echo -e "${GREEN}✓ Installing in current workspace: ${INSTALL_DIR}${NC}"
else
    INSTALL_DIR="${HOME}/.friday"
    echo -e "${CYAN}→ Installing Friday into ${INSTALL_DIR}...${NC}"
    if [ -d "${INSTALL_DIR}" ]; then
        cd "${INSTALL_DIR}"
        git pull --quiet origin main || true
    else
        git clone --quiet https://github.com/friday-memory/friday.git "${INSTALL_DIR}"
        cd "${INSTALL_DIR}"
    fi
fi

# 3. Environment configuration
if [ ! -f ".env" ]; then
    echo -e "${CYAN}→ Generating secure configuration (.env)...${NC}"
    cp .env.example .env

    # Generate cryptographically secure keys
    SEC_KEY=$(openssl rand -hex 16 2>/dev/null || LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 32)
    NEO_PASS=$(openssl rand -hex 16 2>/dev/null || LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 32)

    # Safe sed replace for macOS and Linux
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/FRIDAY_API_KEY=.*/FRIDAY_API_KEY=${SEC_KEY}/" .env
        sed -i '' "s/NEO4J_PASSWORD=.*/NEO4J_PASSWORD=${NEO_PASS}/" .env
    else
        sed -i "s/FRIDAY_API_KEY=.*/FRIDAY_API_KEY=${SEC_KEY}/" .env
        sed -i "s/NEO4J_PASSWORD=.*/NEO4J_PASSWORD=${NEO_PASS}/" .env
    fi
    echo -e "${GREEN}✓ Generated secure FRIDAY_API_KEY and NEO4J_PASSWORD.${NC}"
else
    echo -e "${GREEN}✓ Existing .env detected.${NC}"
fi

# Source env to retrieve API key
# shellcheck disable=SC1091
source .env 2>/dev/null || true
API_KEY="${FRIDAY_API_KEY:-friday_secret_key}"

# 4. Launch containers
echo -e "${CYAN}→ Starting Friday services via Docker Compose...${NC}"
$DOCKER_COMPOSE up -d

# 5. Wait for healthy response
echo -n -e "${CYAN}→ Waiting for brain readiness...${NC}"
READY=false
for i in {1..30}; do
    if curl -s -f http://localhost/health >/dev/null 2>&1 || curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
        READY=true
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

if [ "$READY" = true ]; then
    echo -e "${GREEN}${BOLD}✓ Friday Cognitive Memory Engine is LIVE!${NC}\n"
else
    echo -e "${YELLOW}⚠️ Services started. Final health check still warming up.${NC}\n"
fi

# 6. Print Setup Summary Card
MCP_SCRIPT_PATH="${INSTALL_DIR}/mcp/server.py"

echo -e "${BOLD}================================================================${NC}"
echo -e "${BOLD} 🎉 Setup Complete — Your AI Agents Now Have a Brain${NC}"
echo -e "${BOLD}================================================================${NC}"
echo -e "  🌐 ${CYAN}Neural Studio Web UI:${NC}   http://localhost"
echo -e "  🔑 ${CYAN}Friday Server Key:${NC}      ${API_KEY}"
echo -e "  📁 ${CYAN}Installation Path:${NC}      ${INSTALL_DIR}"
echo -e ""
echo -e "${BOLD}🔌 Cursor IDE Setup (~/.cursor/mcp.json):${NC}"
cat << EOC
{
  "mcpServers": {
    "friday": {
      "command": "python3",
      "args": ["${MCP_SCRIPT_PATH}"],
      "env": {
        "FRIDAY_URL": "http://localhost",
        "FRIDAY_API_KEY": "${API_KEY}"
      }
    }
  }
}
EOC
echo -e ""
echo -e "${BOLD}🔌 Claude Desktop Setup (claude_desktop_config.json):${NC}"
cat << EOC
{
  "mcpServers": {
    "friday": {
      "command": "python3",
      "args": ["${MCP_SCRIPT_PATH}"],
      "env": {
        "FRIDAY_URL": "http://localhost",
        "FRIDAY_API_KEY": "${API_KEY}"
      }
    }
  }
}
EOC
echo -e ""
echo -e "  📖 Full Documentation: ${CYAN}https://github.com/friday-memory/friday${NC}"
echo -e "${BOLD}================================================================${NC}"
