# Support Reset Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace email-based password reset with a single durable support thread per student, including admin notifications, admin approval, and a 30-minute reset token delivered inside the internal chat.

**Architecture:** Add dedicated support-thread models instead of overloading `notification`, reuse the existing notification bell to alert admins, and keep `/reset_password/<token>` as the final password-change page. The forgot-password entry point becomes a guest-access support flow that creates a signed browser session for the requesting student.

**Tech Stack:** Flask, Flask-Login, SQLAlchemy, Jinja2, unittest

---

## File Map

- Modify: `app/models.py`
  - Add `SupportThread`, `SupportMessage`, and `PasswordResetGrant`.
- Modify: `app/routes.py`
  - Replace the email reset request flow with guest support access and keep token reset consumption.
- Modify: `app/notification_center.py`
  - Add admin notification helpers for support events.
- Modify: `app/blueprints/notifications.py`
  - Add admin list/detail routes and student chat posting routes.
- Modify: `app/__init__.py`
  - Exempt the new guest support routes from login/onboarding guards and expose any shared support summary if needed.
- Modify: `app/templates/login.html`
  - Keep the `Mot de passe oublie ?` link pointed at the new support request page.
- Modify: `app/templates/request_reset_password.html`
  - Turn the page into the support-request entry screen.
- Create: `app/templates/notifications/support_thread.html`
  - Shared thread UI for admins and students.
- Create: `app/templates/notifications/admin_support_threads.html`
  - Admin list of student support threads.
- Modify: `app/templates/notifications/inbox.html`
  - Add entry points to support for students and admins.
- Modify: `app/templates/base.html`
  - Add an admin support shortcut when needed.
- Modify: `app/static/css/main.css`
  - Add chat layout and responsive support styles.
- Modify: `app/static/js/page-init.js`
  - Add lightweight auto-scroll or progressive enhancement for the support thread page if needed.
- Modify: `app/notifications.py`
  - Remove `envoyer_email` if no active usage remains after the refactor.
- Create: `tests/test_support_reset_chat_flow.py`
  - Cover end-to-end request, admin approval, token visibility, and password change behavior.
- Modify: `tests/test_notification_routes.py`
  - Add admin notification and inbox rendering assertions for support events.
- Remove or rewrite: `tests/test_password_reset_flow.py`
  - Replace email-reset expectations with support-thread expectations.

### Task 1: Add the support-thread data model

**Files:**
- Modify: `app/models.py`
- Create: `tests/test_support_reset_chat_flow.py`
- Test: `tests/test_support_reset_chat_flow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_request_reset_creates_single_support_thread_and_system_message(self):
    response = self.client.post(
        "/request_reset_password",
        data={"email": "aicha@example.com"},
        follow_redirects=False,
    )

    thread = self.SupportThread.query.filter_by(student_id=self.student.id).first()
    self.assertEqual(response.status_code, 302)
    self.assertIsNotNone(thread)
    self.assertEqual(thread.messages[0].message_type, "reset_requested")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow -v`
Expected: FAIL because support-thread models and relationships do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class SupportThread(db.Model):
    __tablename__ = "support_thread"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("utilisateur.id"), nullable=False, unique=True)
    status = db.Column(db.String(20), default="open", nullable=False)
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class SupportMessage(db.Model):
    __tablename__ = "support_message"
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey("support_thread.id"), nullable=False)
    author_user_id = db.Column(db.Integer, db.ForeignKey("utilisateur.id"))
    author_role = db.Column(db.String(20), nullable=False)
    message_type = db.Column(db.String(30), default="message", nullable=False)
    body = db.Column(db.Text, nullable=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow -v`
Expected: PASS for the support-thread creation test.

- [ ] **Step 5: Commit**

```bash
git add app/models.py tests/test_support_reset_chat_flow.py
git commit -m "feat: add support thread persistence for reset chat"
```

### Task 2: Replace the reset request email flow with guest support access

**Files:**
- Modify: `app/routes.py`
- Modify: `app/templates/request_reset_password.html`
- Modify: `app/__init__.py`
- Modify: `tests/test_support_reset_chat_flow.py`
- Remove or rewrite: `tests/test_password_reset_flow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_request_reset_creates_guest_support_access_without_sending_email(self):
    with patch("app.routes.envoyer_email") as mocked_send:
        response = self.client.post(
            "/request_reset_password",
            data={"email": "aicha@example.com"},
            follow_redirects=False,
        )

    self.assertEqual(response.status_code, 302)
    self.assertIn("/notifications/support", response.headers["Location"])
    mocked_send.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow -v`
Expected: FAIL because the route still prepares an email reset flow.

- [ ] **Step 3: Write minimal implementation**

```python
if utilisateur:
    thread = get_or_create_support_thread(utilisateur)
    session["support_guest_thread_id"] = thread.id
    session["support_guest_student_id"] = utilisateur.id
    create_support_system_message(thread, "reset_requested", "Demande de reinitialisation du mot de passe.")
    notify_admins_about_support_thread(thread, "Nouvelle demande de reinitialisation")
    return redirect(url_for("notifications.support_thread_guest"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow -v`
Expected: PASS and no email helper call.

- [ ] **Step 5: Commit**

```bash
git add app/routes.py app/templates/request_reset_password.html app/__init__.py tests/test_support_reset_chat_flow.py tests/test_password_reset_flow.py
git commit -m "feat: replace email reset request with guest support access"
```

### Task 3: Add admin notifications and chat messaging routes

**Files:**
- Modify: `app/notification_center.py`
- Modify: `app/blueprints/notifications.py`
- Modify: `app/templates/notifications/inbox.html`
- Create: `app/templates/notifications/admin_support_threads.html`
- Create: `app/templates/notifications/support_thread.html`
- Modify: `app/static/css/main.css`
- Modify: `tests/test_notification_routes.py`
- Modify: `tests/test_support_reset_chat_flow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_admin_receives_support_notification_and_can_open_thread(self):
    self.create_reset_request_for_student()

    notification = self.Notification.query.filter_by(user_id=self.admin.id, type="support_request").first()
    self.assertIsNotNone(notification)

    response = self.admin_client.get(notification.cta_url)
    self.assertEqual(response.status_code, 200)
    self.assertIn("Demande de reinitialisation", response.get_data(as_text=True))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_notification_routes tests.test_support_reset_chat_flow -v`
Expected: FAIL because support notifications and admin support pages do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def notify_admins_about_support_thread(thread, title):
    admins = Utilisateur.query.filter_by(role="admin", statut="actif").all()
    for admin in admins:
        create_notification(
            admin.id,
            "support_request",
            title,
            f"{thread.student.display_name} a besoin d aide.",
            cta_url=url_for("notifications.admin_support_thread", thread_id=thread.id),
            event_key=f"support:{thread.id}:{thread.last_activity_at.isoformat()}",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_notification_routes tests.test_support_reset_chat_flow -v`
Expected: PASS for admin bell notifications and thread access.

- [ ] **Step 5: Commit**

```bash
git add app/notification_center.py app/blueprints/notifications.py app/templates/notifications/inbox.html app/templates/notifications/admin_support_threads.html app/templates/notifications/support_thread.html app/static/css/main.css tests/test_notification_routes.py tests/test_support_reset_chat_flow.py
git commit -m "feat: add admin support notifications and thread views"
```

### Task 4: Add admin approval and student-only reset link visibility

**Files:**
- Modify: `app/blueprints/notifications.py`
- Modify: `app/routes.py`
- Modify: `app/templates/notifications/support_thread.html`
- Modify: `tests/test_support_reset_chat_flow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_admin_can_grant_reset_and_only_student_sees_link(self):
    thread = self.create_reset_request_for_student()

    response = self.admin_client.post(
        f"/notifications/support/{thread.id}/grant-reset",
        follow_redirects=False,
    )

    self.assertEqual(response.status_code, 302)
    grant = self.PasswordResetGrant.query.filter_by(thread_id=thread.id).first()
    self.assertIsNotNone(grant)

    admin_html = self.admin_client.get(f"/notifications/support/{thread.id}").get_data(as_text=True)
    student_html = self.client.get("/notifications/support").get_data(as_text=True)
    self.assertNotIn(grant.token, admin_html)
    self.assertIn(f"/reset_password/{grant.token}", student_html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow -v`
Expected: FAIL because the grant route and student-only link rendering do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
@notifications_bp.route("/support/<int:thread_id>/grant-reset", methods=["POST"])
@login_required
@admin_required
def grant_support_reset(thread_id):
    grant = PasswordResetGrant(
        thread_id=thread.id,
        student_id=thread.student_id,
        granted_by_admin_id=current_user.id,
        token=serializer.dumps(thread.student.email, salt=current_app.config["SECURITY_PASSWORD_SALT"]),
        expires_at=datetime.utcnow() + timedelta(minutes=30),
    )
    db.session.add(grant)
    create_support_system_message(thread, "reset_granted", "Lien de reinitialisation accorde pour 30 minutes.", {"grant_id": grant.id})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow -v`
Expected: PASS for grant creation and student-only link visibility.

- [ ] **Step 5: Commit**

```bash
git add app/blueprints/notifications.py app/routes.py app/templates/notifications/support_thread.html tests/test_support_reset_chat_flow.py
git commit -m "feat: add admin-approved reset grant inside support chat"
```

### Task 5: Consume grants in the final reset page and remove obsolete email helper usage

**Files:**
- Modify: `app/routes.py`
- Modify: `app/notifications.py`
- Modify: `app/templates/login.html`
- Modify: `app/templates/base.html`
- Modify: `tests/test_support_reset_chat_flow.py`
- Modify: `tests/test_notification_routes.py`

- [ ] **Step 1: Write the failing test**

```python
def test_reset_token_from_support_grant_updates_password_once(self):
    grant = self.create_grant_for_student()

    response = self.client.post(
        f"/reset_password/{grant.token}",
        data={"new_password": "newsecret123", "confirm_password": "newsecret123"},
        follow_redirects=False,
    )

    self.db.session.refresh(grant)
    self.db.session.refresh(self.student)
    self.assertEqual(response.status_code, 302)
    self.assertIsNotNone(grant.used_at)
    self.assertTrue(self.student.check_mot_de_passe("newsecret123"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow -v`
Expected: FAIL because grant usage is not linked to the reset page yet.

- [ ] **Step 3: Write minimal implementation**

```python
grant = PasswordResetGrant.query.filter_by(token=token).first()
if not grant or grant.used_at or grant.expires_at < datetime.utcnow():
    flash(_("Le lien de reinitialisation est invalide ou expire."), "danger")
    return redirect(url_for("main.login"))

utilisateur = Utilisateur.query.get(grant.student_id)
utilisateur.set_mot_de_passe(form.new_password.data)
grant.used_at = datetime.utcnow()
db.session.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_support_reset_chat_flow tests.test_notification_routes -v`
Expected: PASS and no reset flow path depends on `envoyer_email`.

- [ ] **Step 5: Commit**

```bash
git add app/routes.py app/notifications.py app/templates/login.html app/templates/base.html tests/test_support_reset_chat_flow.py tests/test_notification_routes.py
git commit -m "feat: finalize support-driven password reset flow"
```

## Self-Review Checklist

- Spec coverage:
  - Single student thread: Tasks 1 and 3
  - Admin bell notifications: Task 3
  - Admin approval for 30 minutes: Task 4
  - Student-only reset link in chat: Task 4
  - Final password reset and no email path: Task 5
- Placeholder scan:
  - No `TODO`, `TBD`, or unnamed files remain.
- Type consistency:
  - `SupportThread`, `SupportMessage`, and `PasswordResetGrant` are used consistently across tasks.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-22-support-reset-chat.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
