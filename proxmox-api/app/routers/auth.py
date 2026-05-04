from fastapi import APIRouter
from app.models.schemas import LoginRequest, TokenResponse
from app.services.proxmox import ProxmoxClient
from app.core.security import create_token

router = APIRouter()

@router.post("/login", response_model=TokenResponse, summary="S'authentifier via Proxmox")
def login(body: LoginRequest):
    """
    Authentification user/password auprès de Proxmox.
    Retourne un token JWT ProxAPI qui encapsule le ticket Proxmox.
    """
    data  = ProxmoxClient.login(body.username, body.password)
    token = create_token({
        "sub":      data["username"],
        "ticket":   data["ticket"],
        "csrf":     data["csrf"],
    })
    return TokenResponse(access_token=token, username=data["username"])
