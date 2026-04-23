import csv
import io
import json
import os
import secrets
from datetime import datetime

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, send_from_directory, session, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import and_, or_, text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app.blueprints.placement import placement_test_is_ready
from app.maintenance_tools import (
    ACTIVE_SESSION_TOKEN_KEY,
    create_active_session,
    is_site_maintenance_enabled,
    revoke_active_session_by_token,
    revoke_sessions_for_user,
)
from app.notification_center import create_support_message, get_or_create_support_thread, notify_admins_about_support_thread
from app.storage import build_asset_url, delete_asset_file, resolve_asset_path

from . import db
from .authorization import admin_required
from .forms import (
    CreateUserForm,
    DeleteUserForm,
    LoginForm,
    ProfileForm,
    RegisterForm,
    RequestResetPasswordForm,
    ResetPasswordConfirmForm,
    UpdateUserForm,
)
from .models import Cours, Log, PasswordResetGrant, ResultatPlacement, Utilisateur, Vocabulaire
from .utils import log_action
main = Blueprint("main", __name__)

PROFILE_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
SUPPORT_GUEST_THREAD_ID = "support_guest_thread_id"
SUPPORT_GUEST_STUDENT_ID = "support_guest_student_id"
PROTECTED_MANAGEMENT_ROLES = {"admin", "maintenance"}
STUDENT_ONBOARDING_EXEMPT_ENDPOINTS = {
    "main.changer_langue",
    "main.choix_langue",
    "main.favicon",
    "main.legacy_service_worker",
    "main.logout",
    "main.media_file",
    "notifications.post_support_message",
    "notifications.support_thread_guest",
    "main.service_worker",
    "placement.complete",
    "placement.intro",
    "placement.start",
    "static",
}


def _is_ajax_request():
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _normalize_language_code(code):
    normalized = (code or "").strip().lower()
    if normalized in current_app.config.get("LANGUAGES", {}):
        return normalized
    return None


def _saved_language_for_user(user):
    if user is None:
        return None
    return _normalize_language_code(getattr(user, "langue_preferee", None))


def _set_language_selection(code, user=None):
    normalized = _normalize_language_code(code)
    if normalized is None:
        return None

    session["langue"] = normalized
    session["lang"] = normalized
    if user is not None and getattr(user, "id", None) is not None:
        user.langue_preferee = normalized
    return normalized


def _selected_language_for_user(user=None):
    session_lang = _normalize_language_code(session.get("langue") or session.get("lang"))
    if session_lang is not None:
        session["langue"] = session_lang
        session["lang"] = session_lang
        return session_lang

    saved_lang = _saved_language_for_user(user)
    if saved_lang is not None:
        session["langue"] = saved_lang
        session["lang"] = saved_lang
        return saved_lang

    return None


def _required_student_onboarding_endpoint(user):
    if getattr(user, "role", None) != "eleve" or getattr(user, "id", None) is None:
        return None

    if _selected_language_for_user(user) is None:
        return "main.choix_langue"

    has_placement_result = ResultatPlacement.query.filter_by(eleve_id=user.id).first() is not None
    if not has_placement_result and placement_test_is_ready():
        return "placement.intro"
    return None


def _needs_language_choice(user):
    return _required_student_onboarding_endpoint(user) == "main.choix_langue"


def maybe_redirect_new_student_to_onboarding():
    if not current_user.is_authenticated:
        return None

    endpoint = request.endpoint
    required_endpoint = _required_student_onboarding_endpoint(current_user)
    if required_endpoint is None or endpoint is None or endpoint in STUDENT_ONBOARDING_EXEMPT_ENDPOINTS:
        return None
    return redirect(url_for(required_endpoint))


def _dashboard_endpoint_for_user(user):
    role = getattr(user, "role", None)
    if role == "admin":
        return "admin.dashboard"
    if role == "maintenance":
        return "maintenance.dashboard"
    if role == "enseignant":
        return "courses.liste"
    onboarding_endpoint = _required_student_onboarding_endpoint(user)
    if onboarding_endpoint is not None:
        return onboarding_endpoint
    return "progress.dashboard_eleve"


def _profile_images_folder():
    folder = current_app.config["PROFILE_IMAGE_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    return folder


def _profile_images_index_path():
    os.makedirs(current_app.instance_path, exist_ok=True)
    return os.path.join(current_app.instance_path, "profile_images.json")


def _load_profile_images_index():
    path = _profile_images_index_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return {}

    return data if isinstance(data, dict) else {}


def _save_profile_images_index(index_data):
    with open(_profile_images_index_path(), "w", encoding="utf-8") as handle:
        json.dump(index_data, handle, ensure_ascii=False, indent=2)


def _remove_profile_image_file(relative_path):
    delete_asset_file(relative_path, "uploads/profiles/")


def _profile_image_relative_path(user_id):
    return _load_profile_images_index().get(str(user_id))


def _profile_image_url(user):
    relative_path = _profile_image_relative_path(getattr(user, "id", None))
    if not relative_path:
        return None
    return build_asset_url(relative_path)


def _save_profile_image(user, file_storage):
    if not file_storage or not file_storage.filename:
        return _profile_image_relative_path(user.id)

    extension = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if extension not in PROFILE_IMAGE_EXTENSIONS:
        raise ValueError("La photo de profil doit etre au format png, jpg, jpeg, gif ou webp.")

    filename = secure_filename(file_storage.filename)
    final_name = f"profile_{user.id}_{secrets.token_hex(8)}.{extension}"
    destination = os.path.join(_profile_images_folder(), final_name)
    file_storage.save(destination)

    index_data = _load_profile_images_index()
    previous_path = index_data.get(str(user.id))
    relative_path = f"uploads/profiles/{final_name}"
    index_data[str(user.id)] = relative_path
    _save_profile_images_index(index_data)

    if previous_path and previous_path != relative_path:
        _remove_profile_image_file(previous_path)

    return relative_path


def _admin_would_be_missing_after_change(current_admin_count, current_role, requested_role=None, deleting=False):
    if current_role != "admin":
        return False

    remaining_admins = current_admin_count - 1 if deleting or requested_role != "admin" else current_admin_count
    return remaining_admins < 1


def _current_admin_count():
    return Utilisateur.query.filter_by(role="admin").count()


def _is_protected_management_role(role):
    return (role or "").strip().lower() in PROTECTED_MANAGEMENT_ROLES


def _is_protected_management_user(utilisateur):
    return _is_protected_management_role(getattr(utilisateur, "role", None))


def _inactive_account_message(utilisateur):
    if getattr(utilisateur, "statut", None) == "bloque":
        return _("Votre compte a ete bloque. Contactez l administrateur.")
    return _("Votre compte attend la validation de l administrateur.")


def _pending_student_query():
    return Utilisateur.query.filter_by(role="eleve", statut="en_attente")


def _apply_user_form_data(utilisateur, form):
    utilisateur.nom = form.nom.data.strip()
    utilisateur.prenom = form.prenom.data.strip() if form.prenom.data else None
    utilisateur.email = form.email.data.strip().lower()
    utilisateur.telephone = form.telephone.data.strip() if form.telephone.data else None
    utilisateur.role = form.role.data
    if form.password.data:
        utilisateur.set_mot_de_passe(form.password.data)


def _prefill_update_user_form(form, utilisateur):
    form.nom.data = utilisateur.nom
    form.prenom.data = utilisateur.prenom
    form.email.data = utilisateur.email
    form.telephone.data = utilisateur.telephone
    form.role.data = utilisateur.role


def _detach_user_relationships(utilisateur):
    Cours.query.filter_by(enseignant_id=utilisateur.id).update({"enseignant_id": None}, synchronize_session=False)
    Log.query.filter_by(utilisateur_id=utilisateur.id).update({"utilisateur_id": None}, synchronize_session=False)


@main.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_endpoint_for_user(current_user)))
    return render_template("index.html")


@main.route("/offline")
def offline():
    return render_template("offline.html")


@main.route("/choix-langue")
def choix_langue():
    if current_user.is_authenticated:
        if current_user.role != "eleve":
            return redirect(url_for(_dashboard_endpoint_for_user(current_user)))
        if _selected_language_for_user(current_user) is not None:
            return redirect(url_for(_dashboard_endpoint_for_user(current_user)))
    return render_template("choix_langue.html")


@main.route("/langue/<code>")
def changer_langue(code):
    selected_lang = _set_language_selection(code, current_user if current_user.is_authenticated else None)
    if current_user.is_authenticated and selected_lang is not None:
        db.session.commit()
    next_url = request.args.get("next")
    if next_url:
        return redirect(next_url)
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_endpoint_for_user(current_user)))
    return redirect(request.referrer or url_for("main.index"))


@main.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")


@main.route("/service-worker.js")
def legacy_service_worker():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")


@main.route("/media/<path:filename>")
def media_file(filename):
    if not (filename or "").startswith("uploads/"):
        abort(404)
    absolute_path = resolve_asset_path(filename)
    if absolute_path is None or not os.path.isfile(absolute_path):
        abort(404)
    return send_file(absolute_path)


@main.route("/health")
def health():
    database = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        database = "error"

    return jsonify(
        {
            "status": "ok" if database == "ok" else "degraded",
            "database": database,
            "version": current_app.config["VERSION"],
        }
    )


@main.route("/favicon.ico")
def favicon():
    return send_from_directory("static/icons", "icon-192.png", mimetype="image/png")


@main.route("/login", methods=["GET", "POST"])
def login():
    if session.get("_user_id") and current_user.is_authenticated:
        redirect_url = url_for(_dashboard_endpoint_for_user(current_user))
        if _is_ajax_request():
            return jsonify({"success": True, "redirect_url": redirect_url})
        return redirect(redirect_url)

    form = LoginForm()
    if form.validate_on_submit():
        identifiant = form.email.data.strip().lower()
        utilisateur = Utilisateur.query.filter(Utilisateur.email.ilike(identifiant)).first()

        if utilisateur and check_password_hash(utilisateur.mot_de_passe, form.mot_de_passe.data):
            if utilisateur.statut != "actif":
                pending_message = _inactive_account_message(utilisateur)
                current_app.logger.info(
                    "Connexion bloquee pour %s: statut=%s",
                    utilisateur.email,
                    utilisateur.statut,
                )
                log_action(
                    module="auth",
                    action="Connexion bloquee",
                    level="WARNING",
                    user_id=utilisateur.id,
                    details=f"email={utilisateur.email}; statut={utilisateur.statut}",
                )
                if _is_ajax_request():
                    return jsonify({"success": False, "message": pending_message}), 403
                flash(pending_message, "warning")
                return render_template("login.html", form=form)

            if is_site_maintenance_enabled() and utilisateur.role not in {"admin", "maintenance"}:
                message = _("La plateforme est temporairement en maintenance.")
                log_action(
                    module="security",
                    action="Connexion refusee en mode maintenance",
                    level="WARNING",
                    user_id=utilisateur.id,
                    details=f"email={utilisateur.email}",
                )
                if _is_ajax_request():
                    return jsonify({"success": False, "message": message}), 503
                return render_template("maintenance/site_maintenance_public.html", maintenance_payload=None), 503

            previous_lang = _normalize_language_code(session.get("langue") or session.get("lang"))
            session.clear()
            login_user(utilisateur, remember=form.remember.data)
            active_session = create_active_session(
                utilisateur,
                ip_address=request.remote_addr or "",
                user_agent=request.user_agent.string or "",
            )
            session[ACTIVE_SESSION_TOKEN_KEY] = active_session.session_token
            selected_lang = previous_lang or _saved_language_for_user(utilisateur)
            if selected_lang is not None:
                _set_language_selection(selected_lang, utilisateur)
            utilisateur.dernier_acces = datetime.utcnow()
            db.session.commit()

            current_app.logger.info(
                "Connexion reussie pour %s depuis %s",
                utilisateur.email,
                request.remote_addr or "unknown",
            )
            log_action(
                module="auth",
                action="Connexion reussie",
                level="INFO",
                user_id=utilisateur.id,
                details=f"email={utilisateur.email}; role={utilisateur.role}",
            )
            flash(_("Connexion reussie."), "success")
            redirect_url = url_for(_dashboard_endpoint_for_user(utilisateur))
            if _is_ajax_request():
                return jsonify({"success": True, "redirect_url": redirect_url})
            return redirect(redirect_url)

        current_app.logger.warning("Tentative de connexion echouee pour %s", identifiant)
        log_action(
            module="auth",
            action="Connexion echouee",
            level="WARNING",
            details=f"email={identifiant}",
        )
        error_message = _("Identifiant ou mot de passe incorrect.")
        if _is_ajax_request():
            return jsonify({"success": False, "message": error_message}), 401
        flash(error_message, "danger")

    elif request.method == "POST" and _is_ajax_request():
        errors = []
        for field_errors in form.errors.values():
            errors.extend(field_errors)
        return jsonify(
            {
                "success": False,
                "message": errors[0] if errors else _("Le formulaire de connexion est invalide."),
            }
        ), 400

    return render_template("login.html", form=form)


@main.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(_dashboard_endpoint_for_user(current_user)))

    form = RegisterForm()
    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        if Utilisateur.query.filter_by(email=normalized_email).first():
            flash(_("Cet email existe deja."), "danger")
            return render_template("register.html", form=form)

        utilisateur = Utilisateur(
            nom=form.nom.data.strip(),
            prenom=form.prenom.data.strip() if form.prenom.data else None,
            email=normalized_email,
            role="eleve",
            statut="en_attente",
            mot_de_passe="placeholder",
        )
        utilisateur.set_mot_de_passe(form.password.data)
        db.session.add(utilisateur)
        db.session.commit()
        flash(_("Compte cree. Un administrateur doit maintenant le valider."), "success")
        return redirect(url_for("main.login"))

    return render_template("register.html", form=form)


@main.route("/auth/google/start")
def google_start():
    flash(_("La connexion Google n est plus disponible. Utilisez votre email et votre mot de passe."), "warning")
    return redirect(url_for("main.login"))


@main.route("/auth/google/callback")
def google_callback():
    flash(_("La connexion Google n est plus disponible. Utilisez votre email et votre mot de passe."), "warning")
    return redirect(url_for("main.login"))


@main.route("/logout")
@login_required
def logout():
    active_session_token = session.get(ACTIVE_SESSION_TOKEN_KEY)
    user_id = current_user.id
    user_email = current_user.email
    previous_lang = _selected_language_for_user(current_user)
    revoke_active_session_by_token(active_session_token, reason="logout")
    db.session.commit()
    logout_user()
    remember_action = session.get("_remember")
    session.clear()
    if remember_action is not None:
        session["_remember"] = remember_action
    if previous_lang in current_app.config["LANGUAGES"]:
        session["langue"] = previous_lang
        session["lang"] = previous_lang
    flash(_("Vous etes maintenant deconnecte."), "info")
    response = redirect(url_for("main.login"))
    response.delete_cookie(current_app.config.get("SESSION_COOKIE_NAME", "session"))
    response.delete_cookie(
        current_app.config.get("REMEMBER_COOKIE_NAME", "remember_token"),
        domain=current_app.config.get("REMEMBER_COOKIE_DOMAIN"),
        path=current_app.config.get("REMEMBER_COOKIE_PATH", "/"),
    )
    response.headers["Clear-Site-Data"] = '"cache"'
    log_action(
        module="auth",
        action="Deconnexion",
        level="INFO",
        user_id=user_id,
        details=f"email={user_email}",
    )
    return response


@main.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for(_dashboard_endpoint_for_user(current_user)))


@main.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm()

    if request.method == "GET":
        form.nom.data = current_user.nom
        form.prenom.data = current_user.prenom
        form.telephone.data = current_user.telephone

    if form.validate_on_submit():
        current_user.nom = form.nom.data.strip()
        current_user.prenom = form.prenom.data.strip() if form.prenom.data else None
        current_user.telephone = form.telephone.data.strip() if form.telephone.data else None

        try:
            if form.photo.data and form.photo.data.filename:
                _save_profile_image(current_user, form.photo.data)
        except ValueError as exc:
            flash(str(exc), "danger")
            return render_template("profile.html", form=form, profile_image_url=_profile_image_url(current_user))

        db.session.commit()
        flash(_("Profil mis a jour avec succes."), "success")
        return redirect(url_for("main.profile"))

    return render_template("profile.html", form=form, profile_image_url=_profile_image_url(current_user))


@main.route("/admin/utilisateurs")
@login_required
@admin_required
def gestion_utilisateurs():
    utilisateurs = Utilisateur.query.order_by(Utilisateur.nom.asc(), Utilisateur.prenom.asc()).all()
    delete_form = DeleteUserForm()
    pending_students_count = _pending_student_query().count()
    return render_template(
        "gestion_utilisateurs.html",
        utilisateurs=utilisateurs,
        delete_form=delete_form,
        pending_students_count=pending_students_count,
    )


@main.route("/admin/creer_utilisateur", methods=["GET", "POST"])
@login_required
@admin_required
def creer_utilisateur():
    form = CreateUserForm()

    if form.validate_on_submit():
        if Utilisateur.query.filter_by(email=form.email.data.lower()).first():
            flash(_("Cet email existe deja."), "danger")
            return render_template("creer_utilisateur.html", form=form)

        utilisateur = Utilisateur(
            nom=form.nom.data.strip(),
            prenom=form.prenom.data.strip() if form.prenom.data else None,
            email=form.email.data.lower(),
            telephone=form.telephone.data.strip() if form.telephone.data else None,
            role=form.role.data,
            statut="actif",
            mot_de_passe=generate_password_hash(form.password.data),
        )
        db.session.add(utilisateur)
        db.session.commit()
        flash(_("Utilisateur cree avec succes."), "success")
        return redirect(url_for("main.gestion_utilisateurs"))

    return render_template("creer_utilisateur.html", form=form)


@main.route("/admin/utilisateurs/<int:user_id>/modifier", methods=["GET", "POST"])
@login_required
@admin_required
def modifier_utilisateur(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)
    form = UpdateUserForm()

    if request.method == "GET":
        _prefill_update_user_form(form, utilisateur)

    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        email_owner = Utilisateur.query.filter(Utilisateur.email == normalized_email, Utilisateur.id != utilisateur.id).first()
        if email_owner:
            flash(_("Cet email existe deja."), "danger")
            return render_template("modifier_utilisateur.html", form=form, utilisateur=utilisateur)

        requested_role = form.role.data
        admin_count = _current_admin_count()
        if _is_protected_management_user(utilisateur) and requested_role != utilisateur.role:
            flash(_("Le role des comptes admin et maintenance ne peut pas etre modifie."), "danger")
            return render_template("modifier_utilisateur.html", form=form, utilisateur=utilisateur)

        if utilisateur.id == current_user.id and utilisateur.role == "admin" and requested_role != "admin":
            flash(_("Vous ne pouvez pas retirer votre propre role administrateur."), "danger")
            return render_template("modifier_utilisateur.html", form=form, utilisateur=utilisateur)

        if _admin_would_be_missing_after_change(admin_count, utilisateur.role, requested_role=requested_role):
            flash(_("Impossible de retirer le role du dernier administrateur."), "danger")
            return render_template("modifier_utilisateur.html", form=form, utilisateur=utilisateur)

        _apply_user_form_data(utilisateur, form)
        db.session.commit()
        flash(_("Utilisateur modifie avec succes."), "success")
        return redirect(url_for("main.gestion_utilisateurs"))

    return render_template("modifier_utilisateur.html", form=form, utilisateur=utilisateur)


@main.route("/admin/utilisateurs/<int:user_id>/bloquer", methods=["POST"])
@login_required
@admin_required
def bloquer_utilisateur(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)

    if _is_protected_management_user(utilisateur):
        flash(_("Les comptes admin et maintenance ne peuvent pas etre bloques."), "danger")
        return redirect(url_for("main.gestion_utilisateurs"))

    if utilisateur.statut == "bloque":
        flash(_("Cet utilisateur est deja bloque."), "info")
        return redirect(url_for("main.gestion_utilisateurs"))

    utilisateur.statut = "bloque"
    revoke_sessions_for_user(utilisateur.id, reason="user-blocked")
    db.session.commit()
    log_action(
        module="security",
        action="Utilisateur bloque",
        level="WARNING",
        user_id=current_user.id,
        details=f"target_user_id={utilisateur.id}; email={utilisateur.email}",
    )
    flash(_("Utilisateur bloque avec succes."), "success")
    return redirect(url_for("main.gestion_utilisateurs"))


@main.route("/admin/utilisateurs/<int:user_id>/debloquer", methods=["POST"])
@login_required
@admin_required
def debloquer_utilisateur(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)

    if utilisateur.statut == "actif":
        flash(_("Cet utilisateur est deja actif."), "info")
        return redirect(url_for("main.gestion_utilisateurs"))

    utilisateur.statut = "actif"
    db.session.commit()
    log_action(
        module="security",
        action="Utilisateur debloque",
        level="INFO",
        user_id=current_user.id,
        details=f"target_user_id={utilisateur.id}; email={utilisateur.email}",
    )
    flash(_("Utilisateur debloque avec succes."), "success")
    return redirect(url_for("main.gestion_utilisateurs"))


@main.route("/admin/utilisateurs/<int:user_id>/supprimer", methods=["POST"])
@login_required
@admin_required
def supprimer_utilisateur(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)

    if utilisateur.id == current_user.id:
        flash(_("Vous ne pouvez pas supprimer votre propre compte."), "danger")
        return redirect(url_for("main.gestion_utilisateurs"))

    if _is_protected_management_user(utilisateur):
        flash(_("Les comptes admin et maintenance ne peuvent pas etre supprimes."), "danger")
        return redirect(url_for("main.gestion_utilisateurs"))

    if _admin_would_be_missing_after_change(_current_admin_count(), utilisateur.role, deleting=True):
        flash(_("Impossible de supprimer le dernier administrateur."), "danger")
        return redirect(url_for("main.gestion_utilisateurs"))

    _detach_user_relationships(utilisateur)
    db.session.delete(utilisateur)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(_("Cet utilisateur ne peut pas etre supprime car des donnees liees existent encore."), "danger")
        return redirect(url_for("main.gestion_utilisateurs"))

    flash(_("Utilisateur supprime definitivement."), "success")
    return redirect(url_for("main.gestion_utilisateurs"))


@main.route("/admin/valider-comptes")
@login_required
@admin_required
def valider_comptes():
    pending_students = _pending_student_query().order_by(Utilisateur.date_creation.desc(), Utilisateur.id.desc()).all()
    return render_template("valider_comptes.html", pending_students=pending_students)


@main.route("/admin/utilisateurs/<int:user_id>/valider", methods=["POST"])
@login_required
@admin_required
def valider_utilisateur(user_id):
    utilisateur = Utilisateur.query.get_or_404(user_id)
    if utilisateur.role != "eleve":
        flash(_("Seuls les comptes etudiants peuvent etre valides ici."), "danger")
        return redirect(url_for("main.valider_comptes"))

    if utilisateur.statut != "actif":
        utilisateur.statut = "actif"
        db.session.commit()
        flash(_("Compte etudiant valide avec succes."), "success")
    else:
        flash(_("Ce compte etudiant est deja actif."), "info")
    return redirect(url_for("main.valider_comptes"))


@main.route("/admin/vocabulaire")
@login_required
@admin_required
def vocabulaire_admin():
    q = (request.args.get("q") or "").strip()
    niveau = (request.args.get("niveau") or "").strip().upper()
    pedagogique = (request.args.get("pedagogique") or "").strip()
    traduits = (request.args.get("traduits") or "").strip()
    if "pedagogique" not in request.args and not q and not niveau:
        pedagogique = "1"
    if "traduits" not in request.args and not q and not niveau:
        traduits = "1"
    page = request.args.get("page", 1, type=int)

    query = Vocabulaire.query
    if q:
        query = query.filter(
            or_(
                Vocabulaire.mot_arabe.ilike(f"%{q}%"),
                Vocabulaire.translitteration.ilike(f"%{q}%"),
                Vocabulaire.traduction_fr.ilike(f"%{q}%"),
                Vocabulaire.traduction_en.ilike(f"%{q}%"),
                Vocabulaire.traduction_es.ilike(f"%{q}%"),
            )
        )
    if niveau in {"A1", "A2"}:
        query = query.filter(Vocabulaire.niveau_cefr == niveau)
    if pedagogique == "1":
        query = query.filter(Vocabulaire.est_pedagogique.is_(True))
    if traduits == "1":
        query = query.filter(
            or_(
                and_(Vocabulaire.traduction_fr.isnot(None), Vocabulaire.traduction_fr != ""),
                and_(Vocabulaire.traduction_es.isnot(None), Vocabulaire.traduction_es != ""),
            )
        )

    total_count = query.count()
    pagination = query.order_by(
        Vocabulaire.est_pedagogique.desc(),
        Vocabulaire.niveau_cefr.asc().nullslast(),
        Vocabulaire.id.desc(),
    ).paginate(page=page, per_page=30, error_out=False)
    pedagogique_count = Vocabulaire.query.filter(Vocabulaire.est_pedagogique.is_(True)).count()
    a1_count = Vocabulaire.query.filter(Vocabulaire.niveau_cefr == "A1").count()
    a2_count = Vocabulaire.query.filter(Vocabulaire.niveau_cefr == "A2").count()
    template_name = "partials/_vocab_results_region.html" if _is_ajax_request() else "admin_vocabulaire.html"
    return render_template(
        template_name,
        vocabulaire=pagination.items,
        pagination=pagination,
        total_count=total_count,
        q=q,
        niveau=niveau,
        pedagogique=pedagogique,
        traduits=traduits,
        pedagogique_count=pedagogique_count,
        a1_count=a1_count,
        a2_count=a2_count,
    )


@main.route("/admin/vocabulaire/ajouter", methods=["POST"])
@login_required
@admin_required
def ajouter_vocabulaire():
    csv_file = request.files.get("csv_file")
    if csv_file and csv_file.filename:
        try:
            content = csv_file.stream.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(content))
        except Exception:
            flash(_("Le fichier CSV n'a pas pu etre lu."), "danger")
            return redirect(url_for("main.vocabulaire_admin"))

        ajoutes = 0
        mis_a_jour = 0
        for row in reader:
            mot_arabe = (row.get("mot_arabe") or "").strip()
            if not mot_arabe:
                continue

            entree = Vocabulaire.query.filter_by(mot_arabe=mot_arabe).first()
            if entree is None:
                entree = Vocabulaire(mot_arabe=mot_arabe)
                db.session.add(entree)
                ajoutes += 1
            else:
                mis_a_jour += 1

            entree.translitteration = (row.get("translitteration") or "").strip() or None
            entree.traduction_fr = (row.get("traduction_fr") or "").strip() or None
            entree.traduction_en = (row.get("traduction_en") or "").strip() or None
            entree.traduction_es = (row.get("traduction_es") or "").strip() or None
            entree.audio_url = (row.get("audio_url") or "").strip() or None
            entree.exemple_phrase = (row.get("exemple_phrase") or "").strip() or None

        db.session.commit()
        flash(
            _("Import CSV termine: %(added)s ajoute(s), %(updated)s mis a jour.", added=ajoutes, updated=mis_a_jour),
            "success",
        )
        return redirect(url_for("main.vocabulaire_admin"))

    mot_arabe = (request.form.get("mot_arabe") or "").strip()
    if not mot_arabe:
        flash(_("Le mot arabe est obligatoire."), "danger")
        return redirect(url_for("main.vocabulaire_admin"))

    entree = Vocabulaire.query.filter_by(mot_arabe=mot_arabe).first()
    created = False
    if entree is None:
        entree = Vocabulaire(mot_arabe=mot_arabe)
        db.session.add(entree)
        created = True

    entree.translitteration = (request.form.get("translitteration") or "").strip() or None
    entree.traduction_fr = (request.form.get("traduction_fr") or "").strip() or None
    entree.traduction_en = (request.form.get("traduction_en") or "").strip() or None
    entree.traduction_es = (request.form.get("traduction_es") or "").strip() or None
    entree.audio_url = (request.form.get("audio_url") or "").strip() or None
    entree.exemple_phrase = (request.form.get("exemple_phrase") or "").strip() or None
    db.session.commit()

    flash(
        _("Entree de vocabulaire ajoutee.") if created else _("Entree de vocabulaire mise a jour."),
        "success",
    )
    return redirect(url_for("main.vocabulaire_admin"))


@main.route("/admin/vocabulaire/supprimer/<int:vocabulaire_id>", methods=["POST"])
@login_required
@admin_required
def supprimer_vocabulaire(vocabulaire_id):
    entree = Vocabulaire.query.filter_by(id=vocabulaire_id).first_or_404()
    db.session.delete(entree)
    db.session.commit()
    flash(_("Entree de vocabulaire supprimee."), "success")
    return redirect(url_for("main.vocabulaire_admin"))


@main.route("/request_reset_password", methods=["GET", "POST"])
def request_reset_password():
    form = RequestResetPasswordForm()
    if request.method == "POST" and isinstance(form.email.data, str):
        form.email.data = form.email.data.strip()

    if form.validate_on_submit():
        email = form.email.data.lower()
        utilisateur = Utilisateur.query.filter(Utilisateur.email.ilike(email), Utilisateur.role == "eleve").first()

        if utilisateur:
            thread = get_or_create_support_thread(utilisateur)
            session[SUPPORT_GUEST_THREAD_ID] = thread.id
            session[SUPPORT_GUEST_STUDENT_ID] = utilisateur.id

            reset_message = create_support_message(
                thread,
                body="Demande de reinitialisation du mot de passe.",
                author_role="system",
                message_type="reset_requested",
                payload={
                    "request_ip": request.remote_addr or "",
                    "request_user_agent": request.user_agent.string or "",
                    "requested_email": utilisateur.email,
                },
            )
            notify_admins_about_support_thread(
                thread,
                title="Nouvelle demande de reinitialisation",
                message=f"{utilisateur.nom_complet} a demande un changement de mot de passe.",
                event_key=f"support-reset:{reset_message.id}",
                payload={"message_id": reset_message.id},
                app=current_app._get_current_object(),
            )
            log_action(
                module="security",
                action="Demande reset mot de passe",
                level="WARNING",
                user_id=utilisateur.id,
                details=f"thread_id={thread.id}; email={utilisateur.email}",
            )
            flash(_("Votre demande a ete transmise a l administrateur."), "info")
            return redirect(url_for("notifications.support_thread_guest"))

        flash(_("Si un compte existe pour cet email, la demande a ete prise en compte."), "info")
        return redirect(url_for("main.login"))

    return render_template("request_reset_password.html", form=form)


@main.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password_token(token):
    grant = PasswordResetGrant.query.filter_by(token=token).first()
    if grant is None or grant.used_at is not None or grant.is_expired:
        flash(_("Le lien de reinitialisation est invalide ou expire."), "danger")
        return redirect(url_for("main.login"))

    form = ResetPasswordConfirmForm()
    if form.validate_on_submit():
        utilisateur = Utilisateur.query.filter_by(id=grant.student_id).first()
        if not utilisateur:
            flash(_("Utilisateur introuvable."), "danger")
            return redirect(url_for("main.login"))

        utilisateur.set_mot_de_passe(form.new_password.data)
        grant.used_at = datetime.utcnow()
        db.session.commit()
        log_action(
            module="security",
            action="Mot de passe reinitialise",
            level="INFO",
            user_id=utilisateur.id,
            details=f"grant_id={grant.id}",
        )
        flash(_("Mot de passe mis a jour. Vous pouvez vous reconnecter."), "success")
        return redirect(url_for("main.login"))

    return render_template("reset_password.html", form=form)
