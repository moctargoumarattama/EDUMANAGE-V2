# Lesson Flow Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre les pages de leçon lisibles, corriger le contenu arabe dégradé des leçons de démonstration, et améliorer l'expérience visuelle du flux de leçon.

**Architecture:** La correction repose sur trois couches coordonnées. D'abord, on sécurise le comportement avec un test de régression HTTP/CSS sur `/lecons/6/start`. Ensuite, on corrige la source de vérité des données de démonstration dans `app/__init__.py` pour que les leçons seedées contiennent du texte arabe réel et des libellés français propres. Enfin, on enrichit le shell de `lesson_flow.html`, `lesson.js` et `lesson.css` pour donner plus de vie à l'écran sans changer le flux métier de la leçon.

**Tech Stack:** Flask, Jinja2, SQLAlchemy, unittest, CSS, JavaScript vanilla

---

### Task 1: Regression Coverage For Lesson Flow

**Files:**
- Modify: `tests/test_navigation_shell.py`
- Test: `tests/test_navigation_shell.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_lesson_start_page_uses_readable_copy_and_lively_shell(self):
        with self.client.session_transaction() as session:
            session["_user_id"] = self.eleve_id
            session["_fresh"] = True

        html = self.client.get("/lecons/6/start").get_data(as_text=True)
        css = self.client.get("/static/css/lesson.css").get_data(as_text=True)

        self.assertIn("كتاب", html)
        self.assertIn("Choisissez la bonne réponse", html)
        self.assertNotIn("rÃ©ponse", html)
        self.assertIn("lesson-shell", html)
        self.assertIn("lesson-stage-card", html)
        self.assertIn(".lesson-shell::before", css)
        self.assertIn("animation: floatGlow", css)
        self.assertIn("backdrop-filter:", css)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_navigation_shell.py::NavigationShellSecurityTestCase::test_lesson_start_page_uses_readable_copy_and_lively_shell -v`
Expected: FAIL because the page still contains broken French strings, placeholder Arabic content, and missing lively-shell CSS hooks.

- [ ] **Step 3: Write minimal implementation**

```python
# Update demo lesson content in app/__init__.py so lesson 6 seeds real Arabic words.
# Update lesson_flow.html i18n strings so French labels are stored with proper accents.
# Update lesson.css and lesson_flow.html to expose a richer shell class such as lesson-stage-card.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_navigation_shell.py::NavigationShellSecurityTestCase::test_lesson_start_page_uses_readable_copy_and_lively_shell -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_navigation_shell.py app/__init__.py app/templates/lecons/lesson_flow.html app/static/js/lesson.js app/static/css/lesson.css
git commit -m "fix: restore readable lesson flow content"
```

### Task 2: Repair Demo Lesson Content And Labels

**Files:**
- Modify: `app/__init__.py`
- Modify: `app/templates/lecons/lesson_flow.html`
- Modify: `app/static/js/lesson.js`

- [ ] **Step 1: Write the failing test**

```python
        self.assertIn("Quel mot arabe signifie livre ?", html)
        self.assertIn("Écoutez et choisissez le mot école", html)
        self.assertIn("Quitter la leçon", html)
        self.assertIn("Bonne réponse :", html)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_navigation_shell.py::NavigationShellSecurityTestCase::test_lesson_start_page_uses_readable_copy_and_lively_shell -v`
Expected: FAIL because the current page still includes mojibake and `????` placeholders.

- [ ] **Step 3: Write minimal implementation**

```python
# Replace broken French copy and placeholder lesson text in the demo course seed:
# - "Écoutez et choisissez le mot école"
# - Arabic choices like "كتاب", "مدرسة", "قلم", "سبورة"
# - readable Arabic lesson paragraphs for seeded lessons
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_navigation_shell.py::NavigationShellSecurityTestCase::test_lesson_start_page_uses_readable_copy_and_lively_shell -v`
Expected: PASS with readable Arabic and French labels in the rendered HTML.

- [ ] **Step 5: Commit**

```bash
git add app/__init__.py app/templates/lecons/lesson_flow.html app/static/js/lesson.js tests/test_navigation_shell.py
git commit -m "fix: clean lesson demo content and labels"
```

### Task 3: Refresh The Lesson UI

**Files:**
- Modify: `app/templates/lecons/lesson_flow.html`
- Modify: `app/static/css/lesson.css`

- [ ] **Step 1: Write the failing test**

```python
        self.assertIn("lesson-stage-card", html)
        self.assertIn(".lesson-progress-pill", css)
        self.assertIn(".lesson-stage-card", css)
        self.assertIn("@keyframes floatGlow", css)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_navigation_shell.py::NavigationShellSecurityTestCase::test_lesson_start_page_uses_readable_copy_and_lively_shell -v`
Expected: FAIL because the current UI has no richer stage card, progress pill, or background motion hooks.

- [ ] **Step 3: Write minimal implementation**

```css
.lesson-shell::before { /* ambient glow */ }
.lesson-stage-card { /* glassy card shell */ }
.lesson-progress-pill { /* compact lesson context chip */ }
@keyframes floatGlow { /* subtle motion */ }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_navigation_shell.py::NavigationShellSecurityTestCase::test_lesson_start_page_uses_readable_copy_and_lively_shell -v`
Expected: PASS with the new structural classes and animation hooks present.

- [ ] **Step 5: Commit**

```bash
git add app/templates/lecons/lesson_flow.html app/static/css/lesson.css tests/test_navigation_shell.py
git commit -m "feat: refresh lesson flow visual shell"
```

### Task 4: Full Verification

**Files:**
- Test: `tests/test_navigation_shell.py`

- [ ] **Step 1: Run targeted regression coverage**

Run: `python -m pytest tests/test_navigation_shell.py -v`
Expected: PASS for lesson-flow coverage and no regressions in neighboring navigation-shell assertions.

- [ ] **Step 2: Manual spot-check checklist**

```text
1. Open /lecons/6/start as student
2. Verify Arabic options render as real words, not question marks
3. Verify French labels contain proper accents
4. Verify background, card depth, and feedback areas feel more alive
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-04-21-lesson-flow-cleanup.md
git commit -m "docs: add lesson flow cleanup plan"
```
