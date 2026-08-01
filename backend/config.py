from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    secret_key: SecretStr
    debug : bool

    db_name: str
    db_user: str
    db_password: SecretStr
    db_host: str
    db_port: int
    db_url: SecretStr

    groq_api_key: SecretStr



    model_config= SettingsConfigDict(env_file= ".env",
                                     extra= 'ignore',
                                     case_sensitive=False)

settings= Settings()