myapp/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   └── routers/
│       ├── __init__.py
│       └── users.py
├── db/
│   └── init.sql
├── docker-compose.db.yml      # For VM 1
├── docker-compose.app.yml     # For VM 2
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── deploy/
│   ├── setup-db-vm.sh         # Setup script for VM 1
│   ├── setup-app-vm.sh        # Setup script for VM 2
│   └── deploy.sh              # Deploy script
└── .github/
    └── workflows/
        └── deploy.yml         # Deploys to both VMs
