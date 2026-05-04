from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Proxmox
    PROXMOX_HOST: str = "192.168.1.100"   # IP/hostname de ton Proxmox
    PROXMOX_PORT: int = 8006
    PROXMOX_NODE: str = "pve"             # nom du nœud Proxmox (voir dashboard)
    PROXMOX_VERIFY_SSL: bool = False      # False si certificat auto-signé

    # JWT (pour l'API wrapper)
    JWT_SECRET: str = "change-moi-en-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480         # 8h

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
