# Premium Loader Jewel Reveal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-screen premium boot splash plus a shorter premium navigation loader that reuse the LabeeB logo and feel polished on iPhone and Android.

**Architecture:** Extend the global shell in `app/templates/base.html` with a dedicated premium loader overlay that supports `boot`, `nav`, and `hidden` states. Drive the states from the existing shared navigation events in `app/static/js/native-nav.js`, keep the visual system in `app/static/css/main.css`, and lock the behavior with shell regression tests before implementation.

**Tech Stack:** Flask/Jinja templates, plain JavaScript, CSS animations, Python `unittest`

---

## File Structure

- Modify: `app/templates/base.html`
  Purpose: add premium loader markup, boot/navigation runtime state management, and boot timing orchestration.
- Modify: `app/static/css/main.css`
  Purpose: define the Jewel Reveal v4.0 visual language, animation states, mobile safe-area behavior, and reduced-motion fallback.
- Modify: `app/static/js/native-nav.js`
  Purpose: keep navigation events as the single source of truth and emit a page-ready event after shell replacement if needed.
- Modify: `tests/test_shell_resilience.py`
  Purpose: add regression coverage for premium loader markup, state names, timing hooks, and reduced-motion support.

### Task 1: Add failing premium loader shell tests

**Files:**
- Modify: `tests/test_shell_resilience.py`
- Test: `tests/test_shell_resilience.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_premium_loader_markup_and_states_exist(self):
        self.assertIn('id="app-premium-loader"', BASE_TEMPLATE)
        self.assertIn("app-premium-loader--boot", BASE_TEMPLATE)
        self.assertIn("app-premium-loader--nav", BASE_TEMPLATE)
        self.assertIn("app-premium-loader__logo-image", BASE_TEMPLATE)

    def test_premium_loader_runtime_tracks_boot_and_navigation_timing(self):
        self.assertIn("PREMIUM_BOOT_MIN_MS", BASE_TEMPLATE)
        self.assertIn("PREMIUM_NAV_MIN_MS", BASE_TEMPLATE)
        self.assertIn("showPremiumLoader", BASE_TEMPLATE)
        self.assertIn("hidePremiumLoader", BASE_TEMPLATE)
        self.assertIn("app:navigation-start", BASE_TEMPLATE)
        self.assertIn("app:navigation-stop", BASE_TEMPLATE)

    def test_premium_loader_styles_cover_mobile_and_reduced_motion(self):
        self.assertIn(".app-premium-loader", MAIN_CSS)
        self.assertIn("env(safe-area-inset-top)", MAIN_CSS)
        self.assertIn("@media (prefers-reduced-motion: reduce)", MAIN_CSS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: `FAIL` because the premium loader selectors and runtime symbols do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# No production code in this task.
# Only add the failing assertions above to the existing test file.
```

- [ ] **Step 4: Run test to verify it fails for the right reason**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: failures mention missing premium loader markup/state strings rather than syntax or import errors.

- [ ] **Step 5: Commit**

```bash
git add tests/test_shell_resilience.py
git commit -m "test: cover premium shell loader"
```

### Task 2: Add premium loader markup and runtime in the shell

**Files:**
- Modify: `app/templates/base.html`
- Test: `tests/test_shell_resilience.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_premium_loader_markup_and_states_exist(self):
        self.assertIn('id="app-premium-loader"', BASE_TEMPLATE)
        self.assertIn('data-premium-loader-state="boot"', BASE_TEMPLATE)
        self.assertIn('data-premium-loader-state="nav"', BASE_TEMPLATE)
        self.assertIn("app-premium-loader__brand", BASE_TEMPLATE)
        self.assertIn("app-premium-loader__glow", BASE_TEMPLATE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: `FAIL` on missing markup strings in `base.html`.

- [ ] **Step 3: Write minimal implementation**

```html
<div id="app-premium-loader" class="app-premium-loader app-premium-loader--hidden" aria-hidden="true">
  <div class="app-premium-loader__backdrop"></div>
  <div class="app-premium-loader__orb app-premium-loader__orb--one"></div>
  <div class="app-premium-loader__orb app-premium-loader__orb--two"></div>
  <div class="app-premium-loader__panel" data-premium-loader-state="boot">
    <span class="app-premium-loader__glow"></span>
    <span class="app-premium-loader__ring"></span>
    <span class="app-premium-loader__logo-shell">
      <img src="{{ url_for('static', filename='icons/labeeb-logo-round.svg') }}" alt="" class="app-premium-loader__logo-image">
    </span>
    <span class="app-premium-loader__brand">LabeeB Arabic</span>
    <span class="app-premium-loader__tagline">Douceur brillante</span>
  </div>
</div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: the markup assertions pass while style/runtime assertions may still fail.

- [ ] **Step 5: Commit**

```bash
git add app/templates/base.html tests/test_shell_resilience.py
git commit -m "feat: add premium shell loader markup"
```

### Task 3: Style the Jewel Reveal loader

**Files:**
- Modify: `app/static/css/main.css`
- Test: `tests/test_shell_resilience.py`

- [ ] **Step 1: Write the failing test**

```python
MAIN_CSS = (ROOT / "app" / "static" / "css" / "main.css").read_text(encoding="utf-8")

    def test_premium_loader_styles_cover_mobile_and_reduced_motion(self):
        self.assertIn(".app-premium-loader", MAIN_CSS)
        self.assertIn(".app-premium-loader--visible", MAIN_CSS)
        self.assertIn(".app-premium-loader__ring", MAIN_CSS)
        self.assertIn("env(safe-area-inset-top)", MAIN_CSS)
        self.assertIn("@media (prefers-reduced-motion: reduce)", MAIN_CSS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: `FAIL` because the premium loader styles are missing from `main.css`.

- [ ] **Step 3: Write minimal implementation**

```css
.app-premium-loader {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  padding: calc(env(safe-area-inset-top) + 24px) 24px calc(env(safe-area-inset-bottom) + 24px);
  opacity: 0;
  pointer-events: none;
  transition: opacity 220ms ease;
}

.app-premium-loader--visible {
  opacity: 1;
}

.app-premium-loader__ring {
  border: 1px solid rgba(255, 215, 140, 0.8);
}

@media (prefers-reduced-motion: reduce) {
  .app-premium-loader,
  .app-premium-loader * {
    animation: none !important;
    transition-duration: 120ms !important;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: style assertions pass while runtime assertions may still fail.

- [ ] **Step 5: Commit**

```bash
git add app/static/css/main.css tests/test_shell_resilience.py
git commit -m "feat: style jewel reveal premium loader"
```

### Task 4: Implement boot and navigation timing orchestration

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/static/js/native-nav.js`
- Test: `tests/test_shell_resilience.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_premium_loader_runtime_tracks_boot_and_navigation_timing(self):
        self.assertIn("PREMIUM_BOOT_MIN_MS", BASE_TEMPLATE)
        self.assertIn("PREMIUM_NAV_MIN_MS", BASE_TEMPLATE)
        self.assertIn("showPremiumLoader", BASE_TEMPLATE)
        self.assertIn("hidePremiumLoader", BASE_TEMPLATE)
        self.assertIn("window.addEventListener('app:navigation-start'", BASE_TEMPLATE)
        self.assertIn("window.addEventListener('app:navigation-stop'", BASE_TEMPLATE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: `FAIL` because the timing constants and loader runtime are missing.

- [ ] **Step 3: Write minimal implementation**

```javascript
const PREMIUM_BOOT_MIN_MS = 980;
const PREMIUM_NAV_MIN_MS = 320;
let premiumLoaderState = "hidden";
let premiumLoaderShownAt = 0;

function showPremiumLoader(mode) {
  premiumLoaderState = mode;
  premiumLoaderShownAt = Date.now();
}

function hidePremiumLoader() {
  premiumLoaderState = "hidden";
}

window.addEventListener("app:navigation-start", () => showPremiumLoader("nav"));
window.addEventListener("app:navigation-stop", () => hidePremiumLoader());
document.addEventListener("DOMContentLoaded", () => showPremiumLoader("boot"));
window.addEventListener("pageshow", () => hidePremiumLoader());
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: runtime assertions pass and the full premium loader suite is green.

- [ ] **Step 5: Commit**

```bash
git add app/templates/base.html app/static/js/native-nav.js tests/test_shell_resilience.py
git commit -m "feat: orchestrate premium loader timing"
```

### Task 5: Full regression verification and polish

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/static/css/main.css`
- Modify: `app/static/js/native-nav.js`
- Modify: `tests/test_shell_resilience.py`

- [ ] **Step 1: Run the targeted regression suite**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: `OK`

- [ ] **Step 2: Manually verify the premium flow**

Run:

```bash
.venv\\Scripts\\python.exe run.py
```

Expected:
- first page load shows the full-screen Jewel Reveal splash for about one second;
- soft navigation shows the shorter premium transition;
- loader stays centered on iPhone/Android-sized viewports;
- reduced-motion mode removes shimmer/pulse intensity.

- [ ] **Step 3: Polish any timing or layout rough edges**

```css
/* Example of the kind of polish allowed here: */
.app-premium-loader__panel {
  width: min(100%, 320px);
  will-change: transform, opacity;
}
```

- [ ] **Step 4: Re-run the regression suite**

Run: `.venv\\Scripts\\python.exe -m unittest discover -s tests -p test_shell_resilience.py`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add app/templates/base.html app/static/css/main.css app/static/js/native-nav.js tests/test_shell_resilience.py
git commit -m "feat: ship premium jewel reveal loader"
```
