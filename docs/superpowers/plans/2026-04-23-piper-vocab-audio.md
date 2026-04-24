# Piper Vocab Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Piper-based audio pack workflow that generates stable `.wav` files for pedagogical Arabic vocabulary and updates production `audio_url` values safely through a manifest.

**Architecture:** Add a small application service for stable audio path generation, file synthesis, and manifest application. Keep generation local, keep production read-only for audio playback, and use a separate manifest-apply step to update the live database safely.

**Tech Stack:** Flask, SQLAlchemy, unittest, argparse, CSV

---

### Task 1: Lock The Audio Pack Contract In Tests

**Files:**
- Create: `tests/test_vocab_audio_pack.py`
- Test: `tests/test_vocab_audio_pack.py`

- [ ] **Step 1: Write the failing test**

```python
def test_generate_vocab_audio_pack_creates_file_and_manifest():
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_vocab_audio_pack -v`
Expected: FAIL because the service module does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def generate_vocab_audio_pack(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_vocab_audio_pack -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_vocab_audio_pack.py app/vocab_audio_pack.py
git commit -m "feat: add piper vocab audio pack service"
```

### Task 2: Add Local Generation And Manifest Scripts

**Files:**
- Create: `scripts/generate_vocab_audio_pack.py`
- Create: `scripts/apply_vocab_audio_manifest.py`
- Modify: `app/audio.py`

- [ ] **Step 1: Write thin CLI wrappers**

```python
parser = argparse.ArgumentParser(...)
```

- [ ] **Step 2: Delegate to the service**

```python
stats = generate_vocab_audio_pack(...)
```

- [ ] **Step 3: Support manifest application**

```python
updated = apply_vocab_audio_manifest(...)
```

- [ ] **Step 4: Run tests**

Run: `.\.venv\Scripts\python.exe -m unittest tests.test_vocab_audio_pack -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_vocab_audio_pack.py scripts/apply_vocab_audio_manifest.py app/audio.py
git commit -m "feat: add vocab audio generation scripts"
```

### Task 3: Document The PythonAnywhere Production Flow

**Files:**
- Modify: `docs/pythonanywhere-deployment.md`

- [ ] **Step 1: Add the operator workflow**

```text
Generate locally -> upload wav files -> run manifest apply script on PythonAnywhere.
```

- [ ] **Step 2: Add verification commands**

```text
Check a sample popup payload and open a sample /media/uploads/... URL.
```

- [ ] **Step 3: Commit**

```bash
git add docs/pythonanywhere-deployment.md
git commit -m "docs: document piper vocab audio deployment"
```

### Task 4: Verify End To End

**Files:**
- Test: `tests/test_vocab_audio_pack.py`
- Test: `tests/test_vocab_popup_audio.py`

- [ ] **Step 1: Run targeted tests**

Run:
- `.\.venv\Scripts\python.exe -m unittest tests.test_vocab_audio_pack -v`
- `.\.venv\Scripts\python.exe -m unittest tests.test_vocab_popup_audio -v`

Expected: PASS

- [ ] **Step 2: Review resulting files**

Run: `git diff -- app/vocab_audio_pack.py scripts/generate_vocab_audio_pack.py scripts/apply_vocab_audio_manifest.py docs/pythonanywhere-deployment.md tests/test_vocab_audio_pack.py`
Expected: only the intended feature changes appear.
