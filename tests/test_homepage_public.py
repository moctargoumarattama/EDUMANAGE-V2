import unittest
from pathlib import Path

from app import create_app


class PublicHomepageLayoutTest(unittest.TestCase):
    def test_public_homepage_uses_wide_professional_card_layout(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.test_client() as client:
            response = client.get("/")

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('class="home-hero-shell"', html)
        self.assertIn('class="home-learning-board"', html)
        self.assertIn('class="home-path-grid"', html)
        self.assertNotIn('class="home-level-grid"', html)
        self.assertNotIn('class="home-feature-grid"', html)
        self.assertIn("home-level-card", html)
        self.assertIn("home-feature-card", html)
        self.assertNotIn("home-feature-diamond", html)
        self.assertNotIn("home-feature-triangle", html)
        self.assertNotIn("home-hero-actions", html)
        self.assertNotIn("home-hero-primary", html)
        self.assertNotIn("home-hero-login-link", html)
        self.assertIn("Des séquences courtes", html)
        self.assertIn("Feedback immédiat", html)
        self.assertIn("Parcours clair", html)
        self.assertNotIn("Pedagogie", html)

    def test_homepage_css_keeps_background_pattern_visible(self):
        css = Path("app/static/css/main.css").read_text(encoding="utf-8")

        self.assertIn('url("../images/back.jpeg") center center / auto 100% repeat-x', css)
        self.assertIn("background: linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.7));", css)

    def test_homepage_css_keeps_eyebrow_visible_and_cards_responsive(self):
        css = Path("app/static/css/main.css").read_text(encoding="utf-8")

        self.assertIn(".home-hero-copy .home-hero-eyebrow", css)
        self.assertIn("color: #17355c;", css)
        self.assertIn("white-space: nowrap;", css)
        self.assertIn(".home-learning-board", css)
        self.assertIn(".home-path-grid", css)
        self.assertIn("grid-template-columns: repeat(5, minmax(0, 1fr));", css)
        self.assertIn("max-width: 1760px;", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(240px, 1fr));", css)
        self.assertIn(".home-feature-card", css)
        self.assertIn(".home-feature-meta", css)
        self.assertIn(".home-feature-icon", css)
        self.assertIn("@media (max-width: 768px)", css)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr));", css)
        self.assertIn("width: min(calc(100% - 0.5rem), 380px);", css)
        self.assertIn("min-height: 52px;", css)
        self.assertIn(".home-feature-card p,", css)
        self.assertIn(".home-feature-meta {", css)
        self.assertIn("display: none;", css)

    def test_homepage_css_softly_recenters_hero_copy(self):
        css = Path("app/static/css/main.css").read_text(encoding="utf-8")

        self.assertIn("--home-hero-copy-shift: clamp(1.5rem, 5vw, 4.75rem);", css)
        self.assertIn("width: min(calc(100% - var(--home-hero-copy-shift)), 500px);", css)
        self.assertIn("margin-left: var(--home-hero-copy-shift);", css)
        self.assertIn("--home-hero-copy-shift: clamp(1.8rem, 11vw, 3rem);", css)

    def test_homepage_mobile_learning_board_balances_last_card(self):
        css = Path("app/static/css/main.css").read_text(encoding="utf-8")

        self.assertIn("min-height: calc(100svh - var(--app-shell-offset) - 1rem);", css)
        self.assertIn("padding-bottom: clamp(1.25rem, 5svh, 3.25rem);", css)
        self.assertIn("margin: clamp(1.35rem, 5.5svh, 2.75rem) auto 0.95rem !important;", css)
        self.assertIn("padding: 0.92rem 0.82rem 1rem;", css)
        self.assertIn("gap: 0.62rem 0.6rem;", css)
        self.assertIn("grid-template-columns: auto auto;", css)
        self.assertIn("justify-content: center;", css)
        self.assertIn("text-align: center;", css)
        self.assertIn("min-height: 50px;", css)


if __name__ == "__main__":
    unittest.main()
