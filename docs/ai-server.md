# AI Server setup (Forge / Stability Matrix)

The Flask backend (`webapp/app.py`) talks to a Stable Diffusion Forge instance
(commonly run via Stability Matrix) over its REST API. This machine is the
"AI Server" box in `project.pdf` (`192.168.1.30` in the example diagram).

## Requirements
- A GPU capable of running Stable Diffusion (this app does not need the GPU
  machine to be the same one running Flask/Nginx)
- Stability Matrix with the **Forge** (or A1111-compatible) package installed
- At least one checkpoint whose title/model name contains one of the strings in
  `ALLOWED_CHECKPOINTS` in `webapp/app.py` (currently `realSimpleAnime` and
  `realismIllustriousBy` — update that list if your team uses different models)

## Launch options
Forge must be started with its API enabled and with basic-auth credentials, e.g.
(Stability Matrix → Forge package → Launch Options):

```
--api --api-auth admin:cdti1234 --listen --port 7860
```

- `--api` — required, exposes `/sdapi/v1/...` endpoints the backend calls
- `--api-auth user:pass` — must match `FORGE_API_USER` / `FORGE_API_PASS` in
  the backend's `.env`
- `--listen` — required so other machines on the LAN can reach it (otherwise
  Forge only binds to localhost)
- `--port` — must match the port in `FORGE_API_URL`

## Verifying it's reachable
From the backend machine:

```
curl -u admin:cdti1234 http://<ai-server-ip>:7860/sdapi/v1/sd-models
```

Should return a JSON list of installed checkpoints. If this fails, the backend's
`/api/checkpoints` and `/api/generate` routes will return errors/empty lists
(they fail gracefully — see `app.py`'s `requests.exceptions.RequestException`
handlers — but generation obviously won't work).

## What the backend actually calls
| Backend route | Forge endpoint | Notes |
|---|---|---|
| `/api/samplers` | `GET /sdapi/v1/samplers` | falls back to a hardcoded list if unreachable |
| `/api/checkpoints` | `GET /sdapi/v1/sd-models` | filtered down to `ALLOWED_CHECKPOINTS` |
| `/api/png-info` | `POST /sdapi/v1/png-info` | reads embedded generation params from an uploaded PNG |
| `/api/generate` | `POST /sdapi/v1/txt2img` | rate-limited per user (see `GENERATE_COOLDOWN_SECONDS`) |

## Not yet implemented (see TODO.md section 4)
- **Queueing**: concurrent `/api/generate` calls from different users will hit
  Forge simultaneously; Forge itself will just process them serially, but there's
  no queue/status UI on the backend side yet.
- **LoRA support**: not wired up in `app.py` — only checkpoint switching is.
