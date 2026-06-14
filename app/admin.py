import secrets
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from app import db
from app.models import User, AuditLog

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("Accès réservé aux administrateurs.", "error")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)
    return wrapped


ROLES = [
    ("admin", "Administrateur"),
    ("medecin", "Médecin"),
    ("educateur", "Éducateur / IDE"),
    ("lecture", "Lecture seule"),
]


@admin_bp.route("/")
@admin_required
def index():
    users = User.query.order_by(User.date_creation.desc()).all()
    return render_template("admin/index.html", users=users, roles=ROLES)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def new_user():
    if request.method == "POST":
        nom = (request.form.get("nom") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        role = request.form.get("role") or "medecin"

        if not nom or not email:
            flash("Le nom et l'email sont obligatoires.", "error")
            return render_template("admin/new_user.html", roles=ROLES)

        if User.query.filter_by(email=email).first():
            flash("Un compte avec cet email existe déjà.", "error")
            return render_template("admin/new_user.html", roles=ROLES)

        if role not in dict(ROLES):
            role = "medecin"

        # Mot de passe temporaire généré aléatoirement, à transmettre
        # à l'utilisateur (il pourra le changer ensuite).
        temp_password = secrets.token_urlsafe(9)

        user = User(nom=nom, email=email, role=role, actif=True)
        user.set_password(temp_password)
        db.session.add(user)
        db.session.add(AuditLog(
            user_id=current_user.id, action="create", entite="user",
            entite_id=user.id, details={"nom": nom, "email": email, "role": role},
        ))
        db.session.commit()

        flash(
            f"Compte créé pour {nom} ({email}). "
            f"Mot de passe temporaire : {temp_password} — "
            f"transmettez-le de façon sécurisée, il ne sera plus affiché.",
            "success",
        )
        return redirect(url_for("admin.index"))

    return render_template("admin/new_user.html", roles=ROLES)


@admin_bp.route("/users/<user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("Vous ne pouvez pas désactiver votre propre compte.", "error")
        return redirect(url_for("admin.index"))

    user.actif = not user.actif
    db.session.add(AuditLog(
        user_id=current_user.id, action="update", entite="user",
        entite_id=user.id, details={"actif": user.actif},
    ))
    db.session.commit()

    flash(f"Compte {'activé' if user.actif else 'désactivé'} pour {user.nom}.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<user_id>/role", methods=["POST"])
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")

    if new_role not in dict(ROLES):
        flash("Rôle invalide.", "error")
        return redirect(url_for("admin.index"))

    if user.id == current_user.id and new_role != "admin":
        flash("Vous ne pouvez pas retirer vos propres droits administrateur.", "error")
        return redirect(url_for("admin.index"))

    user.role = new_role
    db.session.add(AuditLog(
        user_id=current_user.id, action="update", entite="user",
        entite_id=user.id, details={"role": new_role},
    ))
    db.session.commit()

    flash(f"Rôle de {user.nom} mis à jour : {dict(ROLES)[new_role]}.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<user_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    temp_password = secrets.token_urlsafe(9)
    user.set_password(temp_password)
    db.session.add(AuditLog(
        user_id=current_user.id, action="update", entite="user",
        entite_id=user.id, details={"action": "reset_password"},
    ))
    db.session.commit()

    flash(
        f"Nouveau mot de passe temporaire pour {user.nom} : {temp_password} — "
        f"transmettez-le de façon sécurisée, il ne sera plus affiché.",
        "success",
    )
    return redirect(url_for("admin.index"))


@admin_bp.route("/audit")
@admin_required
def audit():
    logs = AuditLog.query.order_by(AuditLog.horodatage.desc()).limit(200).all()
    return render_template("admin/audit.html", logs=logs)
