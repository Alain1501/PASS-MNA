import os

from flask import Blueprint

from app import db
from app.models import User

setup_bp = Blueprint("setup", __name__)


@setup_bp.route("/setup-db/<key>")
def setup_db(key):
    expected_key = os.environ.get("SECRET_KEY", "")
    if not expected_key or key != expected_key:
        return "Non autorisé.", 403

    db.create_all()
    messages = ["Tables créées (ou déjà existantes)."]

    admin_exists = User.query.filter_by(role="admin").first() is not None
    if admin_exists:
        messages.append("Un compte administrateur existe déjà.")
    else:
        email = os.environ.get("ADMIN_EMAIL")
        password = os.environ.get("ADMIN_PASSWORD")
        nom = os.environ.get("ADMIN_NOM", "Administrateur")

        if not email or not password:
            messages.append(
                "ADMIN_EMAIL / ADMIN_PASSWORD non définis : aucun compte créé."
            )
        else:
            admin = User(nom=nom, email=email.strip().lower(), role="admin", actif=True)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            messages.append(f"Compte administrateur créé : {email}")

    return "<br>".join(messages)
