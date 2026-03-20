from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HHH_DATAMINER_")

    port: int = 8008
    maps_service_url: str = "http://localhost:8003"
    ships_service_url: str = "http://localhost:8002"
    commodities_service_url: str = "http://localhost:8007"
    contracts_service_url: str = "http://localhost:8001"

    # No HHH_DATAMINER_ prefix — shared across all Hexadian services
    jwt_secret: str = Field("change-me-in-production", validation_alias="HEXADIAN_AUTH_JWT_SECRET")
