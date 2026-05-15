import unittest
from pathlib import Path


class DeploymentRequirementsTest(unittest.TestCase):
    def test_flask_babel_is_declared_for_translation_catalogs(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8").lower().splitlines()

        self.assertIn("flask-babel==4.0.0", requirements)


if __name__ == "__main__":
    unittest.main()
