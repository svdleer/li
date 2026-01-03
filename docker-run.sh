#!/bin/bash
# Docker Build and Run Script for EVE LI XML Generator
# This script provides convenient commands for managing the Docker deployment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Check if .env exists
check_env() {
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        print_info "Creating from template..."
        cp .env.template .env
        print_warning "Please edit .env file with your configuration"
        exit 1
    fi
    print_success ".env file found"
}

# Build Docker image
build() {
    print_info "Building Docker image..."
    docker-compose build
    print_success "Build completed"
}

# Start services
start() {
    print_info "Starting EVE LI services..."
    docker-compose up -d
    print_success "Services started"
    print_info "Web interface: http://localhost:5000"
}

# Start with production profile (includes Nginx)
start_production() {
    print_info "Starting EVE LI services with Nginx..."
    docker-compose --profile production up -d
    print_success "Production services started"
    print_info "Web interface: https://localhost"
}

# Stop services
stop() {
    print_info "Stopping EVE LI services..."
    docker-compose down
    print_success "Services stopped"
}

# Restart services
restart() {
    print_info "Restarting EVE LI services..."
    docker-compose restart
    print_success "Services restarted"
}

# View logs
logs() {
    print_info "Showing logs (Ctrl+C to exit)..."
    docker-compose logs -f
}

# Show status
status() {
    print_info "Service status:"
    docker-compose ps
}

# Run tests
test() {
    print_info "Running connection tests..."
    docker-compose exec eve-li-web python netshot_api.py
    docker-compose exec eve-li-web python dhcp_integration.py
}

# Clean up
clean() {
    print_warning "This will remove containers, volumes, and images. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "Cleaning up..."
        docker-compose down -v --rmi all
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Backup
backup() {
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    print_info "Creating backup in ${BACKUP_DIR}..."
    mkdir -p "${BACKUP_DIR}"
    
    # Backup output and logs
    if [ -d output ]; then
        cp -r output "${BACKUP_DIR}/"
    fi
    if [ -d logs ]; then
        cp -r logs "${BACKUP_DIR}/"
    fi
    
    # Backup .env (without secrets)
    cp .env.template "${BACKUP_DIR}/"
    
    print_success "Backup created: ${BACKUP_DIR}"
}

# Show help
show_help() {
    echo ""
    echo "EVE LI XML Generator - Docker Management Script"
    echo ""
    echo "Usage: ./docker-run.sh [command]"
    echo ""
    echo "Commands:"
    echo "  build       Build Docker images"
    echo "  start       Start services (development mode)"
    echo "  prod        Start services with Nginx (production mode)"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  logs        View service logs"
    echo "  status      Show service status"
    echo "  test        Run connection tests"
    echo "  backup      Backup output and logs"
    echo "  clean       Remove all containers, volumes, and images"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./docker-run.sh build && ./docker-run.sh start"
    echo "  ./docker-run.sh logs"
    echo "  ./docker-run.sh test"
    echo ""
}

# Main script
case "${1}" in
    build)
        check_env
        build
        ;;
    start)
        check_env
        start
        ;;
    prod|production)
        check_env
        start_production
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    test)
        test
        ;;
    backup)
        backup
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: ${1}"
        show_help
        exit 1
        ;;
esac
