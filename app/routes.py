from flask import Blueprint, render_template, abort, request
from flask_login import login_required, current_user

from app.models import Patient, Consultation

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    """Tableau de bord — équivalent de l'écran 2 (liste des dossiers patients)."""
    patients = Patient.query.order_by(Patient.date_modification.desc()).all()
    return render_template("main/dashboard.html", patients=patients)


@main_bp.route("/consultation/nouvelle")
@login_required
def nouvelle_consultation():
    """Écran 3 — formulaire vierge (nouveau patient)."""
    return render_template("main/form.html", patient=None, consultation=None)


@main_bp.route("/patient/<patient_id>")
@login_required
def ouvrir_patient(patient_id):
    """Écran 3 — formulaire pré-rempli avec une consultation du patient.

    Si ?consultation_id=... est fourni, charge cette consultation précise
    (utilisé depuis l'historique). Sinon, charge la plus récente.
    """
    patient = Patient.query.get_or_404(patient_id)

    consultation_id = request.args.get("consultation_id")
    if consultation_id:
        consultation = Consultation.query.filter_by(
            id=consultation_id, patient_id=patient.id
        ).first_or_404()
    else:
        consultation = (
            Consultation.query.filter_by(patient_id=patient.id)
            .order_by(Consultation.date_consultation.desc())
            .first()
        )

    return render_template(
        "main/form.html", patient=patient, consultation=consultation
    )


@main_bp.route("/patient/<patient_id>/historique")
@login_required
def historique_patient(patient_id):
    """Liste de toutes les consultations d'un même patient."""
    patient = Patient.query.get_or_404(patient_id)
    consultations = (
        Consultation.query.filter_by(patient_id=patient.id)
        .order_by(Consultation.date_consultation.desc())
        .all()
    )
    return render_template(
        "main/historique.html", patient=patient, consultations=consultations
    )
