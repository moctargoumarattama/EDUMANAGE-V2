# A1 A2 Pedagogical Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Seed the project with a durable local Arabic beginner pack: 1000 pedagogical entries, 2 published paths, 20 published lessons, easy exercises, and a lightweight 10-question placement test.

**Architecture:** Introduce a dedicated pedagogical seed module and keep `app.__init__._bootstrap_runtime_data()` as the single bootstrap entrypoint. Generate lesson content, exercises, and placement questions from local Python specs to remain deterministic and idempotent.

**Tech Stack:** Flask, SQLAlchemy, unittest

---

### Task 1: Lock The Seed Contract In Tests

**Files:**
- Create: `tests/test_pedagogical_seed.py`

- [ ] **Step 1: Write failing tests for counts and publication**

Assert that `_bootstrap_runtime_data()` produces:
- exactly 1000 `Vocabulaire`
- exactly 500 `A1`
- exactly 500 `A2`
- exactly 2 published seeded `Cours`
- exactly 10 lessons per seeded course
- at least 4 questions per lesson

- [ ] **Step 2: Write a failing idempotence test**

Run the bootstrap twice and assert counts stay stable.

- [ ] **Step 3: Write a failing placement test**

Assert exactly 10 placement questions and a 5/5 logical split from the pedagogical seed helper.

### Task 2: Implement The Pedagogical Seed Module

**Files:**
- Create: `app/pedagogical_seed.py`

- [ ] **Step 1: Add local lesson specs**

Model 20 lessons with 50 Arabic/French entries each, grouped by level and theme.

- [ ] **Step 2: Add deterministic helpers**

Implement:
- transliteration helper
- example sentence helper
- lesson HTML builder
- exercise builder
- placement builder

- [ ] **Step 3: Add idempotent DB sync**

Upsert:
- vocabulaire
- cours
- lecons
- questions
- placement questions

### Task 3: Wire The Bootstrap To The New Seed

**Files:**
- Modify: `app/__init__.py`

- [ ] **Step 1: Replace the old demo vocab/course/placement seed**

Delegate the pedagogical content seed to the new module while keeping the existing demo users and student progress bootstrap.

- [ ] **Step 2: Preserve compatibility**

Keep existing admin/lesson/course/placement flows working without schema changes.

### Task 4: Verify End To End

**Files:**
- Test: `tests/test_pedagogical_seed.py`
- Test: `tests/test_admin_vocabulaire.py`

- [ ] **Step 1: Run targeted tests**

Run:
- `.\.venv\Scripts\python.exe -m unittest tests.test_pedagogical_seed -v`
- `.\.venv\Scripts\python.exe -m unittest tests.test_admin_vocabulaire -v`

- [ ] **Step 2: Fix any regressions**

Adjust the seed logic until all assertions pass.
