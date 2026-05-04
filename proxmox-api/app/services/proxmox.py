"""
ProxmoxClient — couche d'accès à l'API REST native Proxmox.
Toutes les opérations passent ici. Le reste de l'app ne connaît pas Proxmox.
"""

import httpx
from typing import Any
from fastapi import HTTPException
from app.core.config import get_settings


class ProxmoxClient:
    def __init__(self, ticket: str, csrf: str):
        cfg = get_settings()
        self.base = f"https://{cfg.PROXMOX_HOST}:{cfg.PROXMOX_PORT}/api2/json"
        self.node  = cfg.PROXMOX_NODE
        self.verify = cfg.PROXMOX_VERIFY_SSL
        # Auth Proxmox via cookie + header CSRF
        self.cookies = {"PVEAuthCookie": ticket}
        self.headers = {"CSRFPreventionToken": csrf}

    def _handle(self, r: httpx.Response) -> Any:
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code,
                                detail=r.json().get("errors") or r.text)
        return r.json().get("data")

    # ── Auth ─────────────────────────────────────────────────────────────────

    @staticmethod
    def login(username: str, password: str) -> dict:
        """Authentification Proxmox → retourne ticket + CSRFPreventionToken."""
        cfg = get_settings()
        url = f"https://{cfg.PROXMOX_HOST}:{cfg.PROXMOX_PORT}/api2/json/access/ticket"
        r = httpx.post(url, data={"username": username, "password": password},
                       verify=cfg.PROXMOX_VERIFY_SSL)
        if r.status_code != 200:
            raise HTTPException(status_code=401, detail="Identifiants Proxmox invalides")
        data = r.json()["data"]
        return {
            "ticket": data["ticket"],
            "csrf":   data["CSRFPreventionToken"],
            "username": username,
        }

    # ── Nœuds ────────────────────────────────────────────────────────────────

    def list_nodes(self) -> list:
        with httpx.Client(verify=self.verify) as c:
            r = c.get(f"{self.base}/nodes",
                      cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    # ── VMs — liste & détail ─────────────────────────────────────────────────

    def list_vms(self, node: str = None) -> list:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.get(f"{self.base}/nodes/{n}/qemu",
                      cookies=self.cookies, headers=self.headers)
        return self._handle(r) or []

    def get_vm(self, vmid: int, node: str = None) -> dict:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.get(f"{self.base}/nodes/{n}/qemu/{vmid}/config",
                      cookies=self.cookies, headers=self.headers)
        data = self._handle(r)
        data["vmid"] = vmid
        return data

    def vm_status(self, vmid: int, node: str = None) -> dict:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.get(f"{self.base}/nodes/{n}/qemu/{vmid}/status/current",
                      cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    # ── VMs — création / modification / suppression ──────────────────────────

    def create_vm(self, params: dict, node: str = None) -> str:
        """
        params minimaux : vmid, name, memory (Mo), cores, net0, scsi0 …
        Proxmox retourne un task UPID.
        """
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.post(f"{self.base}/nodes/{n}/qemu",
                       data=params,
                       cookies=self.cookies, headers=self.headers)
        return self._handle(r)   # UPID de la tâche

    def update_vm(self, vmid: int, params: dict, node: str = None) -> str:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.put(f"{self.base}/nodes/{n}/qemu/{vmid}/config",
                      data=params,
                      cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    def delete_vm(self, vmid: int, node: str = None) -> str:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.delete(f"{self.base}/nodes/{n}/qemu/{vmid}",
                         cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    # ── VMs — cycle de vie ───────────────────────────────────────────────────

    def _vm_action(self, vmid: int, action: str, node: str = None, params: dict = None) -> str:
        n = node or self.node
        url = f"{self.base}/nodes/{n}/qemu/{vmid}/status/{action}"
        with httpx.Client(verify=self.verify) as c:
            r = c.post(url, data=params or {},
                       cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    def power_on(self,  vmid: int, node: str = None) -> str:
        return self._vm_action(vmid, "start", node)

    def power_off(self, vmid: int, node: str = None) -> str:
        return self._vm_action(vmid, "stop", node)

    def shutdown(self, vmid: int, node: str = None) -> str:
        """Arrêt propre (ACPI)."""
        return self._vm_action(vmid, "shutdown", node)

    def suspend(self, vmid: int, node: str = None) -> str:
        return self._vm_action(vmid, "suspend", node)

    def resume(self, vmid: int, node: str = None) -> str:
        return self._vm_action(vmid, "resume", node)

    def reset(self, vmid: int, node: str = None) -> str:
        return self._vm_action(vmid, "reset", node)

    # ── Snapshots ────────────────────────────────────────────────────────────

    def list_snapshots(self, vmid: int, node: str = None) -> list:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.get(f"{self.base}/nodes/{n}/qemu/{vmid}/snapshot",
                      cookies=self.cookies, headers=self.headers)
        return self._handle(r) or []

    def create_snapshot(self, vmid: int, snapname: str,
                        description: str = "", node: str = None) -> str:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.post(f"{self.base}/nodes/{n}/qemu/{vmid}/snapshot",
                       data={"snapname": snapname, "description": description},
                       cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    def delete_snapshot(self, vmid: int, snapname: str, node: str = None) -> str:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.delete(f"{self.base}/nodes/{n}/qemu/{vmid}/snapshot/{snapname}",
                         cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    def rollback_snapshot(self, vmid: int, snapname: str, node: str = None) -> str:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.post(
                f"{self.base}/nodes/{n}/qemu/{vmid}/snapshot/{snapname}/rollback",
                cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    # ── Backup ───────────────────────────────────────────────────────────────

    def backup_vm(self, vmid: int, storage: str = "local",
                  mode: str = "snapshot", compress: str = "zstd",
                  node: str = None) -> str:
        """
        mode    : snapshot | suspend | stop
        compress: zstd | lzo | gzip | 0
        """
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.post(f"{self.base}/nodes/{n}/vzdump",
                       data={"vmid": vmid, "storage": storage,
                             "mode": mode, "compress": compress},
                       cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    def list_backups(self, storage: str = "local", node: str = None) -> list:
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.get(f"{self.base}/nodes/{n}/storage/{storage}/content",
                      params={"content": "backup"},
                      cookies=self.cookies, headers=self.headers)
        return self._handle(r) or []

    # ── Migration ────────────────────────────────────────────────────────────

    def migrate_vm(self, vmid: int, target_node: str,
                   online: bool = True, node: str = None) -> str:
        """Migration live (online=True) ou à froid."""
        n = node or self.node
        with httpx.Client(verify=self.verify) as c:
            r = c.post(f"{self.base}/nodes/{n}/qemu/{vmid}/migrate",
                       data={"target": target_node, "online": int(online)},
                       cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    # ── Tâches ───────────────────────────────────────────────────────────────

    def task_status(self, upid: str, node: str = None) -> dict:
        """Suivi d'une tâche asynchrone Proxmox via son UPID."""
        n = node or self.node
        upid_enc = upid.replace("/", "%2F")
        with httpx.Client(verify=self.verify) as c:
            r = c.get(f"{self.base}/nodes/{n}/tasks/{upid_enc}/status",
                      cookies=self.cookies, headers=self.headers)
        return self._handle(r)

    # ── Recherche ────────────────────────────────────────────────────────────

    def search_vms(self, name: str = None, status: str = None,
                   min_cpu: int = None, max_cpu: int = None,
                   min_ram: int = None, node: str = None) -> list:
        """Filtre côté ProxAPI (Proxmox n'a pas de recherche native)."""
        vms = self.list_vms(node)
        if name:
            vms = [v for v in vms if name.lower() in (v.get("name") or "").lower()]
        if status:
            vms = [v for v in vms if v.get("status") == status]
        if min_cpu:
            vms = [v for v in vms if (v.get("cpus") or 0) >= min_cpu]
        if max_cpu:
            vms = [v for v in vms if (v.get("cpus") or 0) <= max_cpu]
        if min_ram:
            # Proxmox retourne maxmem en octets
            min_bytes = min_ram * 1024 * 1024
            vms = [v for v in vms if (v.get("maxmem") or 0) >= min_bytes]
        return vms
