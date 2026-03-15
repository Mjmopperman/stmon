#!/bin/bash
# setup-db-vm.sh - Run on VM 1 (92.4.143.135)

set -e

echo "=== Setting Up Database VM (92.4.143.135) ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo apt install git -y

# Install PostgreSQL client (for testing)
sudo apt install postgresql-client -y

# Configure firewall
sudo ufw allow 22
sudo ufw allow 5432
sudo ufw --force enable

# Create project directory
mkdir -p /home/$USER/myapp
cd /home/$USER/myapp

# Clone repository
git clone https://github.com/mjmopperman/myapp.git .

# Create .env from example
cp .env.example .env

echo ""
echo "=== IMPORTANT ==="
echo "Edit .env file with your database credentials:"
echo "  nano /home/$USER/myapp/.env"
echo ""
echo "Then run: docker-compose -f docker-compose.db.yml up -d"
