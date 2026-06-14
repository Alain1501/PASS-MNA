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


@auth_bp.route("/logout")
@login_required
def logout():
    db.session.add(AuditLog(user_id=current_user.id, action="logout", entite="user", entite_id=current_user.id))
    db.session.commit()
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))
