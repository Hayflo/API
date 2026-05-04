from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.core.security import get_current_user
from app.services.proxmox import ProxmoxClient
from app.models.schemas import (
    VMCreateRequest, VMUpdateRequest, VMActionRequest,
    SnapshotCreateRequest, SnapshotRollbackRequest,
    BackupRequest, MigrateRequest,
)

router = APIRouter()

ACTIONS = {
    "power_on":  "power_on",
    "power_off": "power_off",
    "shutdown":  "shutdown",
    "suspend":   "suspend",
    "resume":    "resume",
    "reset":     "reset",
}

def _client(user: dict) -> ProxmoxClient:
    return ProxmoxClient(ticket=user["ticket"], csrf=user["csrf"])


# ── Nœuds ─────────────────────────────────────────────────────────────────────

@router.get("/nodes", summary="Lister les nœuds Proxmox")
def list_nodes(user: dict = Depends(get_current_user)):
    return _client(user).list_nodes()


# ── VMs — CRUD ────────────────────────────────────────────────────────────────

@router.get("/vms", summary="Lister toutes les VMs")
def list_vms(node: Optional[str] = None, user: dict = Depends(get_current_user)):
    return _client(user).list_vms(node)


@router.post("/vms", status_code=202, summary="Créer une VM")
def create_vm(body: VMCreateRequest, user: dict = Depends(get_current_user)):
    params = {
        "vmid":   body.vmid,
        "name":   body.name,
        "cores":  body.cores,
        "memory": body.memory,
        "scsi0":  body.scsi0,
        "net0":   body.net0,
        "ostype": body.ostype,
    }
    if body.iso:
        params["ide2"] = f"{body.iso},media=cdrom"
    if body.description:
        params["description"] = body.description
    upid = _client(user).create_vm(params, body.node)
    return {"message": "Création lancée", "task_upid": upid}


@router.get("/vms/search", summary="Rechercher des VMs")
def search_vms(
    name:    Optional[str] = Query(None),
    status:  Optional[str] = Query(None, description="running | stopped | paused"),
    min_cpu: Optional[int] = Query(None),
    max_cpu: Optional[int] = Query(None),
    min_ram: Optional[int] = Query(None, description="RAM minimum en Mo"),
    node:    Optional[str] = Query(None),
    user: dict = Depends(get_current_user)
):
    return _client(user).search_vms(name, status, min_cpu, max_cpu, min_ram, node)


@router.get("/vms/{vmid}", summary="Détail d'une VM")
def get_vm(vmid: int, node: Optional[str] = None, user: dict = Depends(get_current_user)):
    return _client(user).get_vm(vmid, node)


@router.put("/vms/{vmid}", summary="Mettre à jour une VM")
def update_vm(vmid: int, body: VMUpdateRequest, user: dict = Depends(get_current_user)):
    params = {k: v for k, v in body.model_dump(exclude={"node"}).items() if v is not None}
    upid = _client(user).update_vm(vmid, params, body.node)
    return {"message": "Mise à jour appliquée", "task_upid": upid}


@router.delete("/vms/{vmid}", status_code=202, summary="Supprimer une VM")
def delete_vm(vmid: int, node: Optional[str] = None, user: dict = Depends(get_current_user)):
    upid = _client(user).delete_vm(vmid, node)
    return {"message": f"Suppression VM {vmid} lancée", "task_upid": upid}


# ── VMs — Statut ──────────────────────────────────────────────────────────────

@router.get("/vms/{vmid}/status", summary="État courant d'une VM")
def vm_status(vmid: int, node: Optional[str] = None, user: dict = Depends(get_current_user)):
    return _client(user).vm_status(vmid, node)


# ── VMs — Actions cycle de vie ────────────────────────────────────────────────

@router.post("/vms/{vmid}/action", status_code=202, summary="Action sur une VM")
def vm_action(vmid: int, body: VMActionRequest, user: dict = Depends(get_current_user)):
    """
    Actions disponibles : `power_on`, `power_off`, `shutdown`, `suspend`, `resume`, `reset`
    """
    c = _client(user)
    action_map = {
        "power_on":  c.power_on,
        "power_off": c.power_off,
        "shutdown":  c.shutdown,
        "suspend":   c.suspend,
        "resume":    c.resume,
        "reset":     c.reset,
    }
    if body.action not in action_map:
        from fastapi import HTTPException
        raise HTTPException(400, detail=f"Action inconnue. Valeurs : {list(action_map)}")
    upid = action_map[body.action](vmid, body.node)
    return {"message": f"Action '{body.action}' lancée sur VM {vmid}", "task_upid": upid}


# ── Snapshots ─────────────────────────────────────────────────────────────────

@router.get("/vms/{vmid}/snapshots", summary="Lister les snapshots")
def list_snapshots(vmid: int, node: Optional[str] = None, user: dict = Depends(get_current_user)):
    return _client(user).list_snapshots(vmid, node)


@router.post("/vms/{vmid}/snapshots", status_code=202, summary="Créer un snapshot")
def create_snapshot(vmid: int, body: SnapshotCreateRequest, user: dict = Depends(get_current_user)):
    upid = _client(user).create_snapshot(vmid, body.snapname, body.description, body.node)
    return {"message": f"Snapshot '{body.snapname}' créé", "task_upid": upid}


@router.delete("/vms/{vmid}/snapshots/{snapname}", status_code=202, summary="Supprimer un snapshot")
def delete_snapshot(vmid: int, snapname: str, node: Optional[str] = None, user: dict = Depends(get_current_user)):
    upid = _client(user).delete_snapshot(vmid, snapname, node)
    return {"message": f"Snapshot '{snapname}' supprimé", "task_upid": upid}


@router.post("/vms/{vmid}/snapshots/rollback", status_code=202, summary="Restaurer un snapshot")
def rollback_snapshot(vmid: int, body: SnapshotRollbackRequest, user: dict = Depends(get_current_user)):
    upid = _client(user).rollback_snapshot(vmid, body.snapname, body.node)
    return {"message": f"Rollback vers '{body.snapname}' lancé", "task_upid": upid}


# ── Backup ───────────────────────────────────────────────────────────────────

@router.post("/vms/{vmid}/backup", status_code=202, summary="Lancer un backup")
def backup_vm(vmid: int, body: BackupRequest, user: dict = Depends(get_current_user)):
    upid = _client(user).backup_vm(vmid, body.storage, body.mode, body.compress, body.node)
    return {"message": f"Backup VM {vmid} lancé", "task_upid": upid}


@router.get("/nodes/{node}/backups", summary="Lister les backups d'un stockage")
def list_backups(node: str, storage: str = "local", user: dict = Depends(get_current_user)):
    return _client(user).list_backups(storage, node)


# ── Migration ─────────────────────────────────────────────────────────────────

@router.post("/vms/{vmid}/migrate", status_code=202, summary="Migrer une VM vers un autre nœud")
def migrate_vm(vmid: int, body: MigrateRequest, user: dict = Depends(get_current_user)):
    upid = _client(user).migrate_vm(vmid, body.target_node, body.online, body.node)
    return {
        "message":     f"Migration VM {vmid} → {body.target_node} lancée",
        "online":      body.online,
        "task_upid":   upid,
    }


# ── Suivi de tâche ────────────────────────────────────────────────────────────

@router.get("/tasks/{upid}/status", summary="Statut d'une tâche asynchrone")
def task_status(upid: str, node: Optional[str] = None, user: dict = Depends(get_current_user)):
    return _client(user).task_status(upid, node)
