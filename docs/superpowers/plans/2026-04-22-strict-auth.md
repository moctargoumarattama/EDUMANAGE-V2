# Strict Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add public student registration with admin approval, remove public Google login, and require email-only login.

**Architecture:** Keep the existing `Utilisateur` model and reuse its `statut` column as the account activation flag. Implement the new flow mainly in `app/routes.py`, `app/forms.py`, and a small admin validation page, with focused end-to-end tests using the real Flask app.

**Tech Stack:** Flask, Flask-WTF, Flask-Login, SQLAlchemy, Jinja2, unittest

---

### Task 1: Lock The Auth Requirements In Tests

**Files:**
- Create: `tests/test_account_approval_flow.py`
- Test: `tests/test_account_approval_flow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_public_register_creates_pending_student(self):
    response = self.client.post(
        "/register",
        data={
            "nom": "Diallo",
            "prenom": "Aicha",
            "email": "aicha@example.test",
            "password": "secret123",
            "confirm_password": "secret123",
        },
        follow_redirects=False,
    )

    user = self.Utilisateur.query.filter_by(email="aicha@example.test").first()
    self.assertEqual(response.status_code, 302)
    self.assertEqual(user.role, "eleve")
    self.assertEqual(user.statut, "en_attente")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_account_approval_flow`
Expected: FAIL because `/register` and approval flow do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@main.route("/register", methods=["GET", "POST"])
def register():
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_account_approval_flow`
Expected: PASS for the new registration behavior.

- [ ] **Step 5: Commit**

```bash
git add tests/test_account_approval_flow.py app/routes.py app/forms.py
git commit -m "feat: add pending student registration flow"
```

### Task 2: Enforce Approval At Login

**Files:**
- Modify: `app/routes.py`
- Modify: `app/forms.py`
- Modify: `app/templates/login.html`
- Test: `tests/test_account_approval_flow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_pending_student_cannot_login_and_phone_identifier_is_rejected(self):
    user = self.Utilisateur(...)
    user.set_mot_de_passe("secret123")
    user.statut = "en_attente"

    response = self.client.post(
        "/login",
        data={"email": "0600000000", "mot_de_passe": "secret123"},
        follow_redirects=True,
    )

    self.assertEqual(response.status_code, 200)
    self.assertIn("email", response.get_data(as_text=True).lower())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_account_approval_flow`
Expected: FAIL because the login still accepts telephone and does not block pending students.

- [ ] **Step 3: Write minimal implementation**

```python
utilisateur = Utilisateur.query.filter(Utilisateur.email.ilike(identifiant)).first()
if utilisateur and utilisateur.statut != "actif":
    flash("Votre compte attend la validation de l administrateur.", "warning")
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_account_approval_flow`
Expected: PASS for blocked pending logins and email-only authentication.

- [ ] **Step 5: Commit**

```bash
git add app/routes.py app/forms.py app/templates/login.html tests/test_account_approval_flow.py
git commit -m "feat: require account approval before student login"
```

### Task 3: Add Admin Validation Screen

**Files:**
- Modify: `app/routes.py`
- Create: `app/templates/valider_comptes.html`
- Modify: `app/templates/gestion_utilisateurs.html`
- Modify: `app/templates/base.html`
- Test: `tests/test_account_approval_flow.py`

- [ ] **Step 1: Write the failing test**

```python
def test_admin_can_view_and_validate_pending_students(self):
    response = self.client.get("/admin/valider-comptes")
    self.assertEqual(response.status_code, 200)
    self.assertIn("aicha@example.test", response.get_data(as_text=True))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_account_approval_flow`
Expected: FAIL because the admin validation page and action do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
@main.route("/admin/valider-comptes")
@login_required
@admin_required
def valider_comptes():
    pending_students = Utilisateur.query.filter_by(role="eleve", statut="en_attente").all()
    return render_template("valider_comptes.html", pending_students=pending_students)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_account_approval_flow`
Expected: PASS for the admin validation flow.

- [ ] **Step 5: Commit**

```bash
git add app/routes.py app/templates/valider_comptes.html app/templates/gestion_utilisateurs.html app/templates/base.html tests/test_account_approval_flow.py
git commit -m "feat: add admin validation page for student accounts"
```
