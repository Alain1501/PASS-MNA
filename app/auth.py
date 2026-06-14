from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import User, AuditLog

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash("Email ou mot de passe incorrect.", "error")
            return render_template("auth/login.html")

        if not user.actif:
            flash("Ce compte a été désactivé. Contactez un administrateur.", "error")
            return render_template("auth/login.html")

        login_user(user, remember=True)
        user.derniere_connexion = datetime.utcnow()
        db.session.add(AuditLog(user_id=user.id, action="login", entite="user", entite_id=user.id))
        db.session.commit()

        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/mon-compte", methods=["GET", "POST"])
@login_required
def mon_compte():
    if request.method == "POST":
        mot_de_passe_actuel = request.form.get("mot_de_passe_actuel") or ""
        nouveau_mot_de_passe = request.form.get("nouveau_mot_de_passe") or ""
        confirmation = request.form.get("confirmation") or ""

        if not current_user.check_password(mot_de_passe_actuel):
            flash("Le mot de passe actuel est incorrect.", "error")
        elif len(nouveau_mot_de_passe) < 8:
            flash("Le nouveau mot de passe doit contenir au moins 8 caractères.", "error")
        elif nouveau_mot_de_passe != confirmation:
            flash("Les deux mots de passe ne correspondent pas.", "error")
        else:
            current_user.set_password(nouveau_mot_de_passe)
            db.session.add(
                AuditLog(
                    user_id=current_user.id,
                    action="update",
                    entite="user",
                    entite_id=current_user.id,
                    details={"champ": "password"},
                )
            )
            db.session.commit()
            flash("Votre mot de passe a été mis à jour.", "success")
            return redirect(url_for("auth.mon_compte"))

    return render_template("auth/mon_compte.html")


@auth_bp.route("/logout")
@login_required
def logout():
    db.session.add(AuditLog(user_id=current_user.id, action="logout", entite="user", entite_id=current_user.id))
    db.session.commit()
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))
