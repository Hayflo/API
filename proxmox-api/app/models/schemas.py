from pydantic import BaseModel, Field
from typing import Optional, Dict, List

# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., example="root@pam")
    password: str = Field(..., example="monmotdepasse")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

# ── VM Création ───────────────────────────────────────────────────────────────

class VMCreateRequest(BaseModel):
    vmid:        int    = Field(...,  description="ID unique de la VM (ex: 100)")
    name:        str    = Field(...,  description="Nom de la VM")
    cores:       int    = Field(1,    description="Nombre de cœurs CPU")
    memory:      int    = Field(512,  description="RAM en Mo")
    # Disque : ex "local-lvm:32" = 32 Go sur storage local-lvm
    scsi0:       str    = Field("local-lvm:32", description="Disque principal (storage:taille_Go)")
    # Réseau : ex "virtio,bridge=vmbr0"
    net0:        str    = Field("virtio,bridge=vmbr0", description="Interface réseau")
    ostype:      str    = Field("l26", description="Type OS : l26=Linux, win10, etc.")
    iso:         Optional[str] = Field(None, description="ISO à monter (ex: local:iso/debian.iso)")
    description: Optional[str] = None
    node:        Optional[str] = None   # override du nœud par défaut

# ── VM Mise à jour ────────────────────────────────────────────────────────────

class VMUpdateRequest(BaseModel):
    name:        Optional[str] = None
    cores:       Optional[int] = None
    memory:      Optional[int] = None
    description: Optional[str] = None
    node:        Optional[str] = None

# ── Actions ───────────────────────────────────────────────────────────────────

class VMActionRequest(BaseModel):
    action: str = Field(..., description="power_on | power_off | shutdown | suspend | resume | reset")
    node:   Optional[str] = None

# ── Snapshot ─────────────────────────────────────────────────────────────────

class SnapshotCreateRequest(BaseModel):
    snapname:    str
    description: Optional[str] = ""
    node:        Optional[str] = None

class SnapshotRollbackRequest(BaseModel):
    snapname: str
    node:     Optional[str] = None

# ── Backup ───────────────────────────────────────────────────────────────────

class BackupRequest(BaseModel):
    storage:  str = Field("local", description="Stockage cible (ex: local, nfs-backup)")
    mode:     str = Field("snapshot", description="snapshot | suspend | stop")
    compress: str = Field("zstd",     description="zstd | lzo | gzip | 0")
    node:     Optional[str] = None

# ── Migration ─────────────────────────────────────────────────────────────────

class MigrateRequest(BaseModel):
    target_node: str  = Field(..., description="Nœud Proxmox de destination")
    online:      bool = Field(True, description="Migration live (True) ou à froid (False)")
    node:        Optional[str] = None

# ── Recherche ─────────────────────────────────────────────────────────────────

class SearchParams(BaseModel):
    name:    Optional[str] = None
    status:  Optional[str] = None   # running | stopped | paused
    min_cpu: Optional[int] = None
    max_cpu: Optional[int] = None
    min_ram: Optional[int] = None   # en Mo
    node:    Optional[str] = None
