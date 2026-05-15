import unittest
from types import SimpleNamespace

from flask import render_template, session

from app import create_app


class PageTranslationTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True

    def _set_language(self, client, language):
        with client.session_transaction() as sess:
            sess["langue"] = language
            sess["lang"] = language

    def _fake_student_user(self):
        return SimpleNamespace(
            is_authenticated=True,
            id=1,
            role="eleve",
            nom="goumar",
            prenom="goumar",
            photo_profil=None,
            xp=SimpleNamespace(points=0),
        )

    def _render_courses_template(self, language):
        with self.app.test_request_context("/courses"):
            session["langue"] = language
            session["lang"] = language
            return render_template(
                "courses/liste.html",
                current_user=self._fake_student_user(),
                summary=SimpleNamespace(courses=2, lessons=20),
                niveaux=["A1", "A2"],
                course_cards=[
                    SimpleNamespace(
                        cours=SimpleNamespace(
                            id=1,
                            nom="Sample course",
                            description="",
                            image_url=None,
                            niveau="A1",
                            est_publie=True,
                            enseignant_nom="Demo Teacher",
                        ),
                        is_enrolled=True,
                        can_manage=False,
                        progression=25,
                        lesson_count=1,
                        inscriptions_count=5,
                    )
                ],
            )

    def _render_progression_template(self, language):
        with self.app.test_request_context("/progression"):
            session["langue"] = language
            session["lang"] = language
            return render_template(
                "progression/dashboard_eleve.html",
                current_user=self._fake_student_user(),
                xp=SimpleNamespace(points=0, streak_jours=0, total_lecons_terminees=0),
                progression_data=[],
            )

    def test_public_homepage_is_fully_translated_to_english(self):
        with self.app.test_client() as client:
            self._set_language(client, "en")
            response = client.get("/")

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Learn Arabic at your own pace", html)
        self.assertIn("Choose a level", html)
        self.assertIn("Beginner", html)
        self.assertIn("Elementary", html)
        self.assertIn("Immersive lessons", html)
        self.assertIn("Register", html)
        self.assertNotIn("Choisir un niveau", html)
        self.assertNotIn("Débutant", html)
        self.assertNotIn("Leçons immersives", html)
        self.assertNotIn("Inscription", html)

    def test_public_homepage_is_fully_translated_to_spanish(self):
        with self.app.test_client() as client:
            self._set_language(client, "es")
            response = client.get("/")

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Aprende árabe a tu ritmo", html)
        self.assertIn("Elegir un nivel", html)
        self.assertIn("Principiante", html)
        self.assertIn("Elemental", html)
        self.assertIn("Lecciones inmersivas", html)
        self.assertIn("Registro", html)
        self.assertNotIn("Choisir un niveau", html)
        self.assertNotIn("Débutant", html)
        self.assertNotIn("Leçons immersives", html)
        self.assertNotIn("Inscription", html)

    def test_login_page_is_fully_translated_to_english(self):
        with self.app.test_client() as client:
            self._set_language(client, "en")
            response = client.get("/login")

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Sign in to LabeeB Arabic", html)
        self.assertIn("Use your email address and password", html)
        self.assertIn("Remember me", html)
        self.assertIn("Forgot password", html)
        self.assertIn("No student account yet?", html)
        self.assertIn("Create my student account", html)
        self.assertNotIn("Connectez-vous", html)
        self.assertNotIn("Utilisez votre adresse", html)
        self.assertNotIn("Mot de passe oublie", html)
        self.assertNotIn("Pas encore de compte", html)

    def test_register_page_is_fully_translated_to_english(self):
        with self.app.test_client() as client:
            self._set_language(client, "en")
            response = client.get("/register")

        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Create your access to LabeeB Arabic", html)
        self.assertIn("This form is reserved for students", html)
        self.assertIn("I already have an account", html)
        self.assertNotIn("Ce formulaire est reserve", html)
        self.assertNotIn("J ai deja un compte", html)

    def test_student_courses_template_is_translated_to_english(self):
        html = self._render_courses_template("en")

        self.assertIn("Courses", html)
        self.assertIn("No description yet.", html)
        self.assertIn("1 lesson", html)
        self.assertNotIn("Aucune description pour le moment.", html)
        self.assertNotIn("1 leçon", html)

    def test_student_courses_template_is_translated_to_spanish(self):
        html = self._render_courses_template("es")

        self.assertIn("Cursos", html)
        self.assertIn("No hay descripción por el momento.", html)
        self.assertIn("1 lección", html)
        self.assertNotIn("Aucune description pour le moment.", html)
        self.assertNotIn("1 leçon", html)

    def test_student_progress_template_is_translated_to_english(self):
        html = self._render_progression_template("en")

        self.assertIn("My learning path", html)
        self.assertIn("Consecutive days", html)
        self.assertIn("Lessons completed", html)
        self.assertIn("You are not enrolled in any course at the moment.", html)
        self.assertNotIn("Jours consécutifs", html)
        self.assertNotIn("Leçons terminées", html)
        self.assertNotIn("Vous n'êtes inscrit à aucun cours pour le moment.", html)

    def test_student_progress_template_is_translated_to_spanish(self):
        html = self._render_progression_template("es")

        self.assertIn("Mi ruta de aprendizaje", html)
        self.assertIn("Días consecutivos", html)
        self.assertIn("Lecciones completadas", html)
        self.assertIn("No estás inscrito en ningún curso por el momento.", html)
        self.assertNotIn("Jours consécutifs", html)
        self.assertNotIn("Leçons terminées", html)
        self.assertNotIn("Vous n'êtes inscrit à aucun cours pour le moment.", html)

    def test_admin_dashboard_template_is_fully_translated_to_english(self):
        with self.app.test_request_context("/admin/dashboard"):
            session["langue"] = "en"
            session["lang"] = "en"
            html = render_template(
                "admin_dashboard.html",
                stats={
                    "total_utilisateurs": 5,
                    "total_enseignants": 1,
                    "total_eleves": 2,
                },
                utilisateurs=[],
                cours=[],
                lesson_counts={},
            )

        self.assertIn("Dashboard", html)
        self.assertIn("Educational administration", html)
        self.assertIn("New course", html)
        self.assertIn("Users", html)
        self.assertIn("Teachers", html)
        self.assertIn("Enrolled students", html)
        self.assertIn("Quick actions", html)
        self.assertIn("View users", html)
        self.assertIn("Create a user", html)
        self.assertIn("Manage courses", html)
        self.assertIn("View progress", html)
        self.assertNotIn("Tableau de bord", html)
        self.assertNotIn("Administration pedagogique", html)
        self.assertNotIn("Nouveau cours", html)
        self.assertNotIn("Voir les utilisateurs", html)

    def test_admin_user_templates_are_translated_to_english(self):
        with self.app.test_request_context("/admin/users"):
            session["langue"] = "en"
            session["lang"] = "en"
            html = render_template(
                "gestion_utilisateurs.html",
                utilisateurs=[],
                pending_students_count=0,
                delete_form=None,
            )

        self.assertIn("Platform users", html)
        self.assertIn("Validate accounts", html)
        self.assertIn("No users found.", html)
        self.assertNotIn("Utilisateurs de la plateforme", html)
        self.assertNotIn("Aucun utilisateur trouve.", html)

        with self.app.test_request_context("/admin/validations"):
            session["langue"] = "en"
            session["lang"] = "en"
            html = render_template("valider_comptes.html", pending_students=[])

        self.assertIn("Student accounts to validate", html)
        self.assertIn("No student account is pending right now.", html)
        self.assertNotIn("Comptes etudiants a valider", html)
        self.assertNotIn("Aucun compte etudiant", html)


if __name__ == "__main__":
    unittest.main()
