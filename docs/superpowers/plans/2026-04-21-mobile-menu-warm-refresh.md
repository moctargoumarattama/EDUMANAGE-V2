# Mobile Menu Warm Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the global mobile navigation so it feels premium, warm, and brand-forward while preserving existing role-based menu behavior.

**Architecture:** Keep all behavior inside the existing global navbar template and style sheet. Introduce a richer brand block, a custom hamburger toggle, and premium mobile navigation styles without changing route wiring or auth logic.

**Tech Stack:** Flask, Jinja templates, Bootstrap collapse, Bootstrap Icons, CSS

---

### Task 1: Lock current navbar behavior with a focused regression test

**Files:**
- Modify: `tests/test_navigation_shell.py`
- Test: `tests/test_navigation_shell.py`

- [ ] **Step 1: Extend the student navigation assertion**

```python
def test_student_navigation_hides_dashboard_link(self):
    with self.client.session_transaction() as session:
        session["_user_id"] = self.eleve_id
        session["_fresh"] = True

    html = self.client.get("/courses/").get_data(as_text=True)

    self.assertNotIn('href="/dashboard"', html)
    self.assertIn('href="/courses/"', html)
    self.assertIn('href="/progression/moi"', html)
    self.assertIn("brand-mark", html)
    self.assertIn("brand-tagline", html)
    self.assertIn("nav-profile-avatar", html)
```

- [ ] **Step 2: Run the navigation test suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_navigation_shell.py"`
Expected: FAIL before implementation if new design markers are absent

- [ ] **Step 3: Commit after test update**

```bash
git add tests/test_navigation_shell.py
git commit -m "test: cover warm mobile navigation shell"
```

### Task 2: Refresh navbar structure in the global base template

**Files:**
- Modify: `app/templates/base.html`
- Test: `tests/test_navigation_shell.py`

- [ ] **Step 1: Replace the simple emoji brand with a branded shell**

```html
<a class="navbar-brand brand-signature d-flex align-items-center gap-3" href="{{ url_for('main.index') }}">
    <span class="brand-mark" aria-hidden="true">
        <span class="brand-mark-core">LA</span>
        <span class="brand-mark-badge"><i class="bi bi-stars"></i></span>
    </span>
    <span class="brand-copy">
        <span class="brand-title">LabeeB <span class="brand-title-accent">Arabic</span></span>
        <span class="brand-tagline">apprendre l'arabe avec douceur</span>
    </span>
</a>
```

- [ ] **Step 2: Replace the default icon toggler with a custom premium toggle**

```html
<button class="navbar-toggler nav-premium-toggle border-0" type="button" data-bs-toggle="collapse" data-bs-target="#navbarMain" aria-controls="navbarMain" aria-expanded="false" aria-label="{{ _('Open menu') }}">
    <span class="nav-toggle-box" aria-hidden="true">
        <span class="nav-toggle-line"></span>
        <span class="nav-toggle-line"></span>
        <span class="nav-toggle-line"></span>
    </span>
</button>
```

- [ ] **Step 3: Upgrade profile and utility markup with dedicated classes**

```html
<button class="btn btn-sm dropdown-toggle nav-language-toggle" data-bs-toggle="dropdown">
    {{ lang_label }}
</button>
```

```html
<a class="nav-link nav-profile-card {% if endpoint == 'main.profile' %}active{% endif %}" href="{{ url_for('main.profile') }}">
    <span class="nav-profile-avatar">{{ current_user.prenom[0] if current_user.prenom else current_user.nom[0] if current_user.nom else 'U' }}</span>
    <span class="nav-profile-copy">
        <span class="nav-profile-name">{{ current_user.prenom or current_user.nom or current_user.email }}</span>
        <span class="nav-role-pill">{{ current_user.role }}</span>
    </span>
    <i class="bi bi-chevron-right nav-profile-chevron"></i>
</a>
```

- [ ] **Step 4: Commit after template update**

```bash
git add app/templates/base.html
git commit -m "feat: refresh mobile navbar markup"
```

### Task 3: Apply the premium warm visual system in CSS

**Files:**
- Modify: `app/static/css/main.css`
- Test: `tests/test_navigation_shell.py`

- [ ] **Step 1: Replace the current navbar block with richer brand and panel styling**

```css
.navbar-platform {
  background: linear-gradient(135deg, rgba(90, 42, 182, 0.97) 0%, rgba(118, 71, 221, 0.95) 58%, rgba(101, 48, 198, 0.97) 100%) !important;
}

.brand-mark {
  width: 56px;
  height: 56px;
  border-radius: 50%;
}

.brand-tagline {
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
```

- [ ] **Step 2: Add custom toggle, premium links, profile card, and mobile panel rules**

```css
.nav-premium-toggle { border-radius: 18px; }
.nav-toggle-line { height: 2px; border-radius: 999px; }
.nav-profile-avatar { width: 42px; height: 42px; border-radius: 14px; }

@media (max-width: 991.98px) {
  .navbar-platform-collapse {
    margin-top: 1rem;
  }

  .navbar-mobile-panel {
    border-radius: 28px;
    padding: 1rem;
  }
}
```

- [ ] **Step 3: Keep desktop compact while letting mobile carry the full premium treatment**

```css
@media (min-width: 992px) {
  .brand-tagline {
    opacity: 0.82;
  }
}
```

- [ ] **Step 4: Commit after CSS update**

```bash
git add app/static/css/main.css
git commit -m "feat: apply warm premium mobile nav styling"
```

### Task 4: Verify navigation behavior and rendered shell

**Files:**
- Test: `tests/test_navigation_shell.py`

- [ ] **Step 1: Run the navigation suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_navigation_shell.py"`
Expected: PASS

- [ ] **Step 2: Review the diff for touched files only**

Run: `git diff -- app/templates/base.html app/static/css/main.css tests/test_navigation_shell.py docs/superpowers/specs/2026-04-21-mobile-menu-warm-refresh-design.md docs/superpowers/plans/2026-04-21-mobile-menu-warm-refresh.md`
Expected: only warm-navigation changes appear

- [ ] **Step 3: Commit verification state**

```bash
git add tests/test_navigation_shell.py
git commit -m "test: verify warm premium mobile navbar refresh"
```
