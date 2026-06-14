from datetime import datetime, date

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import Patient, Consultation, AuditLog

api_bp = Blueprint("api", __name__)


def _parse_date(value):
    """Convertit une chaîne 'YYYY-MM-DD' en date Python, ou None."""
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _serialize_consultation(c):
    return {
        "id": c.id,
        "patient_id": c.patient_id,
        "date_consultation": c.date_consultation.isoformat() if c.date_consultation else None,
        "lieu_consultation": c.lieu_consultation,
        "donnees": c.donnees or {},
        "compte_rendu": c.compte_rendu,
        "date_modification": c.date_modification.isoformat() if c.date_modification else None,
        "auteur": c.auteur.nom if c.auteur else None,
    }


def _serialize_patient_summary(p):
    derniere = p.consultations[0] if p.consultations else None
    return {
        "id": p.id,
        "nom_prenom": p.nom_prenom or "—",
        "date_naissance": p.date_naissance.isoformat() if p.date_naissance else None,
        "date_derniere_consultation": (
            derniere.date_consultation.isoformat()
            if derniere and derniere.date_consultation else None
        ),
        "lieu_derniere_consultation": derniere.lieu_consultation if derniere else None,
        "date_modification": p.date_modification.isoformat() if p.date_modification else None,
        "derniere_consultation_id": derniere.id if derniere else None,
    }


# ──────────────────────────────────────────────────────────────
# Liste des patients (tableau de bord)
# ──────────────────────────────────────────────────────────────
@api_bp.route("/patients", methods=["GET"])
@login_required
def list_patients():
    q = (request.args.get("q") or "").strip().lower()
    patients = Patient.query.order_by(Patient.date_modification.desc()).all()

    result = [_serialize_patient_summary(p) for p in patients]

    if q:
        result = [
            r for r in result
            if q in (r["nom_prenom"] or "").lower()
            or q in (r["date_naissance"] or "")
            or q in (r["lieu_derniere_consultation"] or "").lower()
        ]

    return jsonify(result)


# ──────────────────────────────────────────────────────────────
# Récupérer une consultation (pour pré-remplir le formulaire)
# ──────────────────────────────────────────────────────────────
@api_bp.route("/consultations/<consultation_id>", methods=["GET"])
@login_required
def get_consultation(consultation_id):
    c = Consultation.query.get_or_404(consultation_id)
    return jsonify(_serialize_consultation(c))


# ──────────────────────────────────────────────────────────────
# Enregistrer (créer ou mettre à jour) une consultation
# Équivalent de MP.enregistrerPatient() côté client
# ──────────────────────────────────────────────────────────────
@api_bp.route("/consultations", methods=["POST"])
@login_required
def save_consultation():
    payload = request.get_json(force=True) or {}

    donnees = payload.get("donnees") or {}
    patient_id = payload.get("patient_id")
    consultation_id = payload.get("consultation_id")

    # ── Patient : créer ou mettre à jour ──────────────────────
    if patient_id:
        patient = Patient.query.get(patient_id)
        if patient is None:
            return jsonify({"error": "Patient introuvable"}), 404
    else:
        patient = Patient(cree_par_id=current_user.id)
        db.session.add(patient)

    patient.nom_prenom = donnees.get("nomPrenom") or patient.nom_prenom
    patient.date_naissance = _parse_date(donnees.get("dateNaissance")) or patient.date_naissance
    patient.sexe = donnees.get("sexe") or patient.sexe
    patient.structure_orientation = donnees.get("structureOrientation") or patient.structure_orientation
    patient.lieu_vie = donnees.get("lieuVie") or patient.lieu_vie

    db.session.flush()  # pour obtenir patient.id si nouveau

    # ── Consultation : créer ou mettre à jour ─────────────────
    if consultation_id:
        consultation = Consultation.query.get(consultation_id)
        if consultation is None:
            return jsonify({"error": "Consultation introuvable"}), 404
        action = "update"
    else:
        consultation = Consultation(patient_id=patient.id, auteur_id=current_user.id)
        db.session.add(consultation)
        action = "create"

    consultation.date_consultation = (
        _parse_date(donnees.get("dateConsultation")) or consultation.date_consultation
    )
    consultation.lieu_consultation = donnees.get("lieuConsultation") or consultation.lieu_consultation
    consultation.donnees = donnees
    consultation.compte_rendu = payload.get("compte_rendu") or donnees.get("__cr__")

    db.session.flush()

    db.session.add(AuditLog(
        user_id=current_user.id,
        action=action,
        entite="consultation",
        entite_id=consultation.id,
        details={"patient_id": patient.id},
    ))

    db.session.commit()

    return jsonify({
        "patient_id": patient.id,
        "consultation_id": consultation.id,
        "status": "ok",
    })


# ──────────────────────────────────────────────────────────────
# Supprimer un patient (et ses consultations, en cascade)
# ──────────────────────────────────────────────────────────────
@api_bp.route("/patients/<patient_id>", methods=["DELETE"])
@login_required
def delete_patient(patient_id):
    if current_user.role not in ("admin", "medecin"):
        return jsonify({"error": "Action non autorisée"}), 403

    patient = Patient.query.get_or_404(patient_id)

    db.session.add(AuditLog(
        user_id=current_user.id,
        action="delete",
        entite="patient",
        entite_id=patient.id,
        details={"nom_prenom": patient.nom_prenom},
    ))

    db.session.delete(patient)
    db.session.commit()

    return jsonify({"status": "ok"})
