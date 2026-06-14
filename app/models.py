import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager


def gen_uuid():
    return str(uuid.uuid4())


# ────────────────────────────────────────────────────────────────
# Utilisateurs (médecins, éducateurs, administrateurs)
# ────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    nom = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # rôle : "admin", "medecin", "educateur", "lecture"
    role = db.Column(db.String(20), nullable=False, default="medecin")

    actif = db.Column(db.Boolean, default=True, nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# ────────────────────────────────────────────────────────────────
# Patients (un MNA = un patient, peut avoir plusieurs consultations)
# ────────────────────────────────────────────────────────────────
class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)

    nom_prenom = db.Column(db.String(200), nullable=True)
    date_naissance = db.Column(db.Date, nullable=True)
    sexe = db.Column(db.String(10), nullable=True)

    structure_orientation = db.Column(db.String(200), nullable=True)
    lieu_vie = db.Column(db.String(120), nullable=True)

    cree_par_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    consultations = db.relationship(
        "Consultation",
        backref="patient",
        lazy=True,
        order_by="Consultation.date_consultation.desc()",
        cascade="all, delete-orphan",
    )

    cree_par = db.relationship("User", foreign_keys=[cree_par_id])

    def __repr__(self):
        return f"<Patient {self.nom_prenom} ({self.id})>"


# ────────────────────────────────────────────────────────────────
# Consultations (une consultation = une instance du formulaire MNA)
# Toutes les données du formulaire sont stockées en JSONB :
# flexible, indexable, et permet d'ajouter des champs sans migration.
# ────────────────────────────────────────────────────────────────
class Consultation(db.Model):
    __tablename__ = "consultations"

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)

    patient_id = db.Column(db.String(36), db.ForeignKey("patients.id"), nullable=False)
    auteur_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    date_consultation = db.Column(db.Date, nullable=True)
    lieu_consultation = db.Column(db.String(200), nullable=True)

    # Toutes les valeurs du formulaire (input/select/textarea/checkbox)
    # + tableaux dynamiques (__parcours__, __examens__, etc.)
    donnees = db.Column(db.JSON, nullable=False, default=dict)

    # Compte rendu généré (texte libre, éditable par le médecin)
    compte_rendu = db.Column(db.Text, nullable=True)

    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    auteur = db.relationship("User", foreign_keys=[auteur_id])

    def __repr__(self):
        return f"<Consultation {self.id} - patient {self.patient_id}>"


# ────────────────────────────────────────────────────────────────
# Journal d'audit — qui a fait quoi, quand (traçabilité)
# ────────────────────────────────────────────────────────────────
class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # "create", "update", "delete", "view"
    entite = db.Column(db.String(50), nullable=False)  # "patient", "consultation", "user"
    entite_id = db.Column(db.String(36), nullable=True)
    horodatage = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.JSON, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])
