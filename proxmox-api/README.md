# ⚡ ProxAPI

Wrapper FastAPI + Dashboard web pour piloter Proxmox via son API REST native.

## Architecture

```
[CT/VM Proxmox  192.168.x.x:8080]
        │
        ▼  httpx (HTTPS)
[Proxmox API  :8006]
```

## Fonctionnalités

| Opération        | Endpoint                              |
|-----------------|---------------------------------------|
| Login JWT       | POST /api/v1/login                    |
| Liste VMs       | GET  /api/v1/vms                      |
| Créer VM        | POST /api/v1/vms                      |
| Détail VM       | GET  /api/v1/vms/{vmid}               |
| Modifier VM     | PUT  /api/v1/vms/{vmid}               |
| Supprimer VM    | DELETE /api/v1/vms/{vmid}             |
| Statut VM       | GET  /api/v1/vms/{vmid}/status        |
| Action VM       | POST /api/v1/vms/{vmid}/action        |
| Snapshots       | GET/POST/DELETE /api/v1/vms/{vmid}/snapshots |
| Rollback snap   | POST /api/v1/vms/{vmid}/snapshots/rollback |
| Backup          | POST /api/v1/vms/{vmid}/backup        |
| Migration       | POST /api/v1/vms/{vmid}/migrate       |
| Recherche       | GET  /api/v1/vms/search               |
| Nœuds           | GET  /api/v1/nodes                    |
| Suivi tâche     | GET  /api/v1/tasks/{upid}/status      |

## Déploiement dans un CT Proxmox (Debian/Ubuntu)

### 1. Créer le CT dans Proxmox
- Template : debian-12-standard
- CPU : 1 cœur, RAM : 256 Mo suffit
- Réseau : bridge vmbr0, IP statique ex. 192.168.1.200

### 2. Installation
```bash
apt update && apt install -y python3 python3-pip python3-venv git

useradd -m -s /bin/bash proxapi
mkdir -p /opt/proxapi
chown proxapi:proxapi /opt/proxapi

# Copier les fichiers du projet
git clone https://github.com/Hayflo/devops.git /opt/proxapi
# ou : scp -r proxmox-api/ proxapi@192.168.1.200:/opt/proxapi/

cd /opt/proxapi
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 3. Configuration
```bash
cp .env.example .env
nano .env
# → renseigner PROXMOX_HOST, PROXMOX_NODE, JWT_SECRET
```

### 4. Service systemd
```bash
cp proxapi.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now proxapi
systemctl status proxapi
```

### 5. Vérification
```bash
curl http://192.168.1.200:8080/api/v1/health
# → {"status":"ok","service":"ProxAPI"}

# Swagger UI disponible sur :
# http://192.168.1.200:8080/api/docs

# Dashboard sur :
# http://192.168.1.200:8080/
```

## CLI

```bash
export PROXAPI_URL=http://192.168.1.200:8080
export PROXAPI_USER=root@pam
export PROXAPI_PASS=votre_mot_de_passe

python scripts/proxcli.py list
python scripts/proxcli.py status 100
python scripts/proxcli.py action 100 power_on
python scripts/proxcli.py snap create 100 snap-avant-modif --desc "avant update"
python scripts/proxcli.py snap list 100
python scripts/proxcli.py snap rollback 100 snap-avant-modif
python scripts/proxcli.py backup 100 --storage local --mode snapshot
python scripts/proxcli.py migrate 100 pve2
python scripts/proxcli.py search --status running --mincpu 2
python scripts/proxcli.py task UPID:pve:1234:...
```

## Validation automatique

```bash
chmod +x scripts/validate.sh
./scripts/validate.sh http://192.168.1.200:8080 root@pam monpass 100
```

## Structure du projet

```
proxmox-api/
├── app/
│   ├── main.py                  # Point d'entrée FastAPI
│   ├── core/
│   │   ├── config.py            # Settings (.env)
│   │   └── security.py          # JWT helpers
│   ├── services/
│   │   └── proxmox.py           # Client API Proxmox (toutes les requêtes)
│   ├── models/
│   │   └── schemas.py           # Modèles Pydantic
│   └── routers/
│       ├── auth.py              # Login
│       └── vms.py               # Toutes les opérations VM
├── dashboard/
│   └── index.html               # Dashboard web complet
├── scripts/
│   ├── proxcli.py               # CLI Python
│   └── validate.sh              # Tests automatisés
├── requirements.txt
├── proxapi.service              # Service systemd
└── .env.example
```
