import unittest
from pathlib import Path


class StudentRegistrationActivationTest(unittest.TestCase):
    def test_register_route_creates_student_as_active(self):
        routes_py = Path("app/routes.py").read_text(encoding="utf-8")

        self.assertIn('role="eleve"', routes_py)
        self.assertIn('statut="actif"', routes_py)
        self.assertIn(
            'flash(_("Compte cree avec succes. Vous pouvez vous connecter maintenant."), "success")',
            routes_py,
        )

    def test_auth_templates_no_longer_mention_admin_validation_for_student_signup(self):
        register_html = Path("app/templates/register.html").read_text(encoding="utf-8")
        login_html = Path("app/templates/login.html").read_text(encoding="utf-8")

        self.assertIn("Inscrivez-vous avec votre email et commencez vos cours immediatement.", register_html)
        self.assertNotIn("Un administrateur validera ensuite votre compte.", register_html)
        self.assertNotIn(
            "Les nouveaux comptes etudiants doivent etre valides par un administrateur.",
            login_html,
        )


if __name__ == "__main__":
    unittest.main()
