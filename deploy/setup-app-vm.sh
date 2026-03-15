#!/bin/bash
# setup-app-vm.sh - Run on VM 2 (129.151.184.220)

set -e

echo "=== Setting Up Application VM (129.151.184.220) ==="

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

# Install NGINX for reverse proxy
sudo apt install nginx -y

# Configure firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000
sudo ufw allow 8080
sudo ufw --force enable

# Create project directory
mkdir -p /home/$USER/myapp
cd /home/$USER/myapp

# Clone repository
git clone https://github.com/mjmopperman/myapp.git .

# Create .env from example
cp .env.example .env

# Setup NGINX
sudo tee /etc/nginx/sites-available/myapp << 'EOF'
server {
    listen 80;
    server_name _;

    # FastAPI Backend
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Hasura GraphQL
    location /hasura/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "=== IMPORTANT ==="
echo "Edit .env file:"
echo "  nano /home/$USER/myapp/.env"
echo ""
echo "Set DB_HOST to your database VM IP: 92.4.143.135"
echo ""
echo "Then run: docker-compose -f docker-compose.app.yml up -d"
