import os


class Config:
    # Clever Cloud injecte automatiquement POSTGRESQL_ADDON_URI (ou DATABASE_URL)
    # On normalise vers le format attendu par SQLAlchemy (postgresql://)
    _raw_db_url = (
        os.environ.get("POSTGRESQL_ADDON_URI")
        or os.environ.get("DATABASE_URL")
        or "postgresql://localhost/pass_mna_dev"
    )
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-changer-en-production")

    # Durée de session (en secondes) — déconnexion auto après inactivité
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8  # 8 heures
