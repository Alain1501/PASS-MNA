"""
Script d'initialisation de la base de données.

- Crée les tables si elles n'existent pas (db.create_all()).
- Crée le tout premier compte administrateur si aucun admin n'existe encore,
  à partir des variables d'environnement ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NOM.

Ce script est appelé automatiquement après chaque déploiement sur Clever Cloud
(voir clevercloud/python.json -> build.post_build_hook), mais peut aussi être
exécuté manuellement :

    python init_db.py
"""

import os

from app import create_app, db
from app.models import User


def main():
    app = create_app()

    with app.app_context():
        db.create_all()
        print("Tables créées (ou déjà existantes).")

        admin_exists = User.query.filter_by(role="admin").first() is not None
        if admin_exists:
            print("Un compte administrateur existe déjà — rien à faire.")
            return

        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        nom = os.environ.get("ADMIN_NOM", "Administrateur")

        if not email or not password:
            print(
                "Aucun compte admin trouvé, et ADMIN_EMAIL / ADMIN_PASSWORD ne sont "
                "pas définis : aucun compte n'a été créé. Définissez ces variables "
                "d'environnement puis relancez ce script pour créer le premier admin."
            )
            return

        admin = User(nom=nom, email=email.strip().lower(), role="admin", actif=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Compte administrateur créé : {email}")


if __name__ == "__main__":
    main()
