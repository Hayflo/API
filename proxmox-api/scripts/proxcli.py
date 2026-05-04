#!/usr/bin/env python3
"""
proxcli.py — CLI pour automatiser des tâches Proxmox via ProxAPI
Usage : python proxcli.py --help
"""

import argparse, json, os, sys
import httpx

API  = os.getenv("PROXAPI_URL",  "http://localhost:8080")
USER = os.getenv("PROXAPI_USER", "root@pam")
PASS = os.getenv("PROXAPI_PASS", "")

def login():
    r = httpx.post(f"{API}/api/v1/login",
                   json={"username": USER, "password": PASS})
    r.raise_for_status()
    return r.json()["access_token"]

def req(method, path, token, body=None, params=None):
    h = {"Authorization": f"Bearer {token}"}
    r = httpx.request(method, f"{API}/api/v1{path}", headers=h,
                      json=body, params=params)
    if r.status_code >= 400:
        print(f"❌  {r.status_code} — {r.text}", file=sys.stderr)
        sys.exit(1)
    return r.json()

def out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ── Commandes ─────────────────────────────────────────────────────────────────

def cmd_list(args, tok):
    vms = req("GET", "/vms", tok)
    if args.format == "table":
        print(f"{'VMID':>6}  {'NOM':<25} {'STATUT':<10} {'CPU':>4}  {'RAM':>8}")
        print("─" * 60)
        for v in vms:
            ram = f"{v.get('maxmem',0)//1073741824:.0f} Go"
            print(f"{v['vmid']:>6}  {(v.get('name') or '—'):<25} {v.get('status','?'):<10} {v.get('cpus','?'):>4}  {ram:>8}")
    else:
        out(vms)

def cmd_status(args, tok):
    out(req("GET", f"/vms/{args.vmid}/status", tok))

def cmd_action(args, tok):
    r = req("POST", f"/vms/{args.vmid}/action", tok, {"action": args.action})
    print(f"✅  {r['message']}  |  task: {r.get('task_upid','—')}")

def cmd_snap_create(args, tok):
    r = req("POST", f"/vms/{args.vmid}/snapshots", tok,
            {"snapname": args.name, "description": args.desc or ""})
    print(f"✅  {r['message']}")

def cmd_snap_list(args, tok):
    out(req("GET", f"/vms/{args.vmid}/snapshots", tok))

def cmd_snap_rollback(args, tok):
    r = req("POST", f"/vms/{args.vmid}/snapshots/rollback", tok,
            {"snapname": args.name})
    print(f"✅  {r['message']}")

def cmd_snap_delete(args, tok):
    r = req("DELETE", f"/vms/{args.vmid}/snapshots/{args.name}", tok)
    print(f"✅  {r['message']}")

def cmd_backup(args, tok):
    r = req("POST", f"/vms/{args.vmid}/backup", tok,
            {"storage": args.storage, "mode": args.mode, "compress": args.compress})
    print(f"✅  {r['message']}  |  task: {r.get('task_upid','—')}")

def cmd_migrate(args, tok):
    r = req("POST", f"/vms/{args.vmid}/migrate", tok,
            {"target_node": args.target, "online": not args.cold})
    print(f"✅  {r['message']}")

def cmd_search(args, tok):
    p = {}
    if args.name:   p["name"]   = args.name
    if args.status: p["status"] = args.status
    if args.mincpu: p["min_cpu"]= args.mincpu
    if args.minram: p["min_ram"]= args.minram
    out(req("GET", "/vms/search", tok, params=p))

def cmd_task(args, tok):
    out(req("GET", f"/tasks/{args.upid}/status", tok))


# ── Parser ────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="proxcli", description="CLI ProxAPI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # list
    pl = sub.add_parser("list", help="Lister les VMs")
    pl.add_argument("--format", choices=["table","json"], default="table")

    # status
    ps = sub.add_parser("status", help="Statut d'une VM")
    ps.add_argument("vmid", type=int)

    # action
    pa = sub.add_parser("action", help="Action sur une VM")
    pa.add_argument("vmid", type=int)
    pa.add_argument("action", choices=["power_on","power_off","shutdown","suspend","resume","reset"])

    # snapshot
    psnap = sub.add_parser("snap", help="Gestion snapshots")
    snap_sub = psnap.add_subparsers(dest="snap_cmd", required=True)

    sc = snap_sub.add_parser("create")
    sc.add_argument("vmid", type=int); sc.add_argument("name"); sc.add_argument("--desc", default="")

    sl = snap_sub.add_parser("list")
    sl.add_argument("vmid", type=int)

    sr = snap_sub.add_parser("rollback")
    sr.add_argument("vmid", type=int); sr.add_argument("name")

    sd = snap_sub.add_parser("delete")
    sd.add_argument("vmid", type=int); sd.add_argument("name")

    # backup
    pb = sub.add_parser("backup", help="Lancer un backup")
    pb.add_argument("vmid", type=int)
    pb.add_argument("--storage", default="local")
    pb.add_argument("--mode",    default="snapshot", choices=["snapshot","suspend","stop"])
    pb.add_argument("--compress",default="zstd",    choices=["zstd","lzo","gzip","0"])

    # migrate
    pm = sub.add_parser("migrate", help="Migrer une VM")
    pm.add_argument("vmid", type=int); pm.add_argument("target")
    pm.add_argument("--cold", action="store_true", help="Migration à froid (offline)")

    # search
    psr = sub.add_parser("search", help="Recherche multi-critères")
    psr.add_argument("--name"); psr.add_argument("--status")
    psr.add_argument("--mincpu", type=int); psr.add_argument("--minram", type=int)

    # task
    pt = sub.add_parser("task", help="Statut d'une tâche Proxmox")
    pt.add_argument("upid")

    args = p.parse_args()

    if not PASS:
        print("⚠️  Définir la variable PROXAPI_PASS", file=sys.stderr); sys.exit(1)

    tok = login()

    dispatch = {
        "list":    cmd_list,
        "status":  cmd_status,
        "action":  cmd_action,
        "backup":  cmd_backup,
        "migrate": cmd_migrate,
        "search":  cmd_search,
        "task":    cmd_task,
    }
    if args.cmd == "snap":
        {"create": cmd_snap_create, "list": cmd_snap_list,
         "rollback": cmd_snap_rollback, "delete": cmd_snap_delete}[args.snap_cmd](args, tok)
    else:
        dispatch[args.cmd](args, tok)

if __name__ == "__main__":
    main()
