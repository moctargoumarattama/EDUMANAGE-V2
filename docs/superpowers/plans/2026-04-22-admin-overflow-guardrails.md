# Admin Overflow Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add complete overflow guardrails for `admin/dashboard`, `/admin/utilisateurs`, `placement/admin/questions`, and `/admin/vocabulaire`.

**Architecture:** Add small page-level shell classes in the targeted templates, then centralize overflow protection in `app/static/css/main.css` with focused rules for cards, grids, forms, badges, and long text. Lock the behavior with a lightweight regression test that checks both template anchors and CSS guardrail rules.

**Tech Stack:** Flask/Jinja templates, CSS, Python `unittest`

---
