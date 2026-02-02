#!/bin/bash

set -e

echo "========================================="
echo "  Baroque Backend Setup"
echo "========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo ""
    echo "No .env file found. Let's create one."
    echo ""

    # Generate a random password
    RANDOM_PASSWORD=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 16)

    read -p "Enter database name [baroque]: " POSTGRES_DB
    POSTGRES_DB=${POSTGRES_DB:-baroque}

    read -p "Enter database username [postgres]: " POSTGRES_USER
    POSTGRES_USER=${POSTGRES_USER:-postgres}

    read -p "Enter database password [$RANDOM_PASSWORD]: " POSTGRES_PASSWORD
    POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-$RANDOM_PASSWORD}

    read -p "Enter Anthropic Admin API Key: " ANTHROPIC_ADMIN_API_KEY

    if [ -z "$ANTHROPIC_ADMIN_API_KEY" ]; then
        echo "Warning: No Anthropic Admin API Key provided. Data fetching will be disabled."
    fi

    read -p "Enter Frontend URL [http://localhost:9000]: " FRONTEND_URL
    FRONTEND_URL=${FRONTEND_URL:-http://localhost:9000}

    # Create .env file
    cat > .env << EOF
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
ANTHROPIC_ADMIN_API_KEY=$ANTHROPIC_ADMIN_API_KEY
FRONTEND_URL=$FRONTEND_URL
EOF

    echo ""
    echo ".env file created successfully!"
fi

echo ""
echo "Starting containers..."
echo ""

# Detect docker compose command (plugin or standalone)
if docker compose version > /dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose > /dev/null 2>&1; then
    COMPOSE="docker-compose"
else
    echo "Docker Compose not found. Install docker-compose or the docker compose plugin."
    exit 1
fi

# Stop existing containers if running
$COMPOSE down 2>/dev/null || true

# Build and start containers
$COMPOSE up -d --build

echo ""
echo "Waiting for database to be ready..."

# Wait for database health check (read from .env or use defaults)
DB_USER=$(grep POSTGRES_USER .env 2>/dev/null | cut -d '=' -f2 || echo "postgres")
DB_NAME=$(grep POSTGRES_DB .env 2>/dev/null | cut -d '=' -f2 || echo "baroque")
until $COMPOSE exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; do
    sleep 1
done

echo "Database is ready!"

echo ""
echo "Waiting for backend to be ready..."

# Wait for backend to respond
MAX_ATTEMPTS=30
ATTEMPT=0
until curl -s http://localhost:8000/api/health > /dev/null 2>&1; do
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        echo "Backend failed to start. Check logs with: $COMPOSE logs backend"
        exit 1
    fi
    sleep 1
done

echo "Backend is ready!"

echo ""
echo "========================================="
echo "  Baroque Backend is running!"
echo "========================================="
echo ""
echo "  API:      http://localhost:8000"
echo "  Health:   http://localhost:8000/api/health"
echo "  Docs:     http://localhost:8000/docs"
echo ""
echo "  Useful commands:"
echo "    View logs:     $COMPOSE logs -f"
echo "    Stop:          $COMPOSE down"
echo "    Restart:       $COMPOSE restart"
echo ""
