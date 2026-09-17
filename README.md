# ImageProject (LUMA)

Class project: a Stable Diffusion web app built as a distributed system
(see `project.pdf` for the full assignment brief).

## Target architecture

```
Browser -> Nginx (reverse proxy)
             |-- Frontend (HTML/CSS/JS)      e.g. 192.168.1.10
             `-- Backend (Flask)             e.g. 192.168.1.20
                    |-- AI Server (Forge)     e.g. 192.168.1.30
                    `-- Database (SQLite)     same host as Backend
```

## Current state

Everything (auth, templates, static assets, image generation/editing API,
SQLite) runs as a single Flask app in `webapp/`. It has not yet been split
into separate frontend/backend/reverse-proxy machines — see
**[TODO.md](TODO.md)** for the restructuring plan and progress, and
**[docs/PROGRESS.md](docs/PROGRESS.md)** for what's been done so far and how
to use it.

## Quick start

```powershell
cd webapp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env   # then edit .env
python app.py
```

Full setup instructions: **[docs/setup.md](docs/setup.md)**.

## Docs

| Doc | Covers |
|---|---|
| [docs/setup.md](docs/setup.md) | Installing and running the backend, env vars, smoke tests |
| [docs/ai-server.md](docs/ai-server.md) | Setting up the Forge/Stability Matrix AI server |
| [docs/backup.md](docs/backup.md) | Backing up/restoring the database and generated images |
| [docs/PROGRESS.md](docs/PROGRESS.md) | Changelog of what's been done + how to use each piece |
| [TODO.md](TODO.md) | Full restructuring checklist against `project.pdf` |
| [nginx/luma.conf](nginx/luma.conf) | Reverse proxy config scaffold |

## Team roles (from project.pdf)

| Role | Deliverables |
|---|---|
| UX/UI Frontend | Web pages, Bootstrap, JavaScript |
| Flask Backend | Authentication, API, Database, Logging |
| AI Engineer | Image Generation, Image Editing, Model/LoRA, API testing, Queue |
| QA / DevOps | System testing, docs, Deployment, Dashboard, Backup |
| Reverse Proxy / Routing (optional 5th) | Nginx routing |
