name: Deploy to Oracle Cloud

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  deploy-database:
    runs-on: ubuntu-latest
    name: Deploy Database to VM 1
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Deploy Database to VM 1
        uses: appleboy/ssh-action@master
        with:
          host: 92.4.143.135
          username: ${{ secrets.DB_VM_USER }}
          key: ${{ secrets.DB_VM_SSH_KEY }}
          script: |
            cd /home/ubuntu/stmon
            git pull origin master
            
            # Check if PostgreSQL is already running
            if docker ps | grep -q postgres; then
              echo "Database already running, checking for schema updates..."
              # Run migrations if needed
              if [ -f "db/migrations/new_migration.sql" ]; then
                docker exec -i postgres psql -U ${DB_USER} -d ${DB_NAME} < db/migrations/new_migration.sql
              fi
            else
              echo "Starting fresh database..."
              docker-compose -f docker-compose.db.yml up -d
            fi
            
            echo "✅ Database VM deployed!"

  deploy-application:
    runs-on: ubuntu-latest
    name: Deploy Application to VM 2 
    needs: deploy-database
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Deploy Application to VM 2
        uses: appleboy/ssh-action@master
        with:
          host: 129.151.184.220
          username: ${{ secrets.APP_VM_USER }}
          key: ${{ secrets.APP_VM_SSH_KEY }}
          script: |
            cd /home/ubuntu/stmon
            git pull origin master
            
            # Stop containers
            docker-compose -f docker-compose.app.yml down
            
            # Build and start
            docker-compose -f docker-compose.app.yml build --no-cache
            docker-compose -f docker-compose.app.yml up -d
            
            # Clean up
            docker system prune -f
            
            # Wait for services to start
            sleep 10
            
            # Health check
            curl -f http://localhost:8000/health || exit 1
            
            echo "✅ Application VM deployed!"
