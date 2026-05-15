import re
import unittest
from pathlib import Path

from app import create_app


class PWACacheBustingTest(unittest.TestCase):
    def test_service_worker_route_is_never_http_cached(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.test_client() as client:
            response = client.get("/sw.js")
            response.get_data()
            response.close()

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))
        self.assertEqual(response.headers.get("Pragma"), "no-cache")
        self.assertEqual(response.headers.get("Expires"), "0")

    def test_pwa_registration_uses_asset_versioned_worker_url(self):
        pwa_js = Path("app/static/js/pwa.js").read_text(encoding="utf-8")
        base_html = Path("app/templates/base.html").read_text(encoding="utf-8")

        self.assertIn("window.APP_ASSET_VERSION", base_html)
        self.assertIn('updateViaCache: "none"', pwa_js)
        self.assertIn('`/sw.js?v=${encodeURIComponent(swVersion)}`', pwa_js)

    def test_cache_reset_endpoint_clears_client_data(self):
        app = create_app()
        app.config["TESTING"] = True

        with app.test_client() as client:
            response = client.get("/cache-reset")
            html = response.get_data(as_text=True)
            response.close()

        self.assertEqual(response.status_code, 200)
        self.assertIn('"cache"', response.headers.get("Clear-Site-Data", ""))
        self.assertIn('"storage"', response.headers.get("Clear-Site-Data", ""))
        self.assertIn('"cookies"', response.headers.get("Clear-Site-Data", ""))
        self.assertIn("unregister", html)
        self.assertIn("window.location.replace", html)

    def test_standalone_templates_version_cache_sensitive_assets(self):
        expected_refs = {
            "app/templates/lecons/lesson_flow.html": [
                "filename='css/lesson.css', v=asset_version",
                "filename='js/pwa.js', v=asset_version",
                "filename='js/lesson.js', v=asset_version",
                "window.APP_ASSET_VERSION = lessonBootstrapData.assetVersion || 'dev';",
            ],
            "app/templates/placement/test_flow.html": [
                "filename='css/lesson.css', v=asset_version",
                "filename='js/pwa.js', v=asset_version",
                "filename='js/placement.js', v=asset_version",
                "window.APP_ASSET_VERSION = placementBootstrapData.assetVersion || 'dev';",
            ],
            "app/templates/offline.html": [
                "filename='css/main.css', v=asset_version",
            ],
            "app/templates/maintenance/base_maintenance.html": [
                "filename='js/native-nav.js', v=asset_version",
            ],
        }

        for template_path, snippets in expected_refs.items():
            with self.subTest(template=template_path):
                template = Path(template_path).read_text(encoding="utf-8")
                for snippet in snippets:
                    self.assertIn(snippet, template)

    def test_standalone_executable_scripts_do_not_embed_jinja(self):
        script_pattern = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.DOTALL | re.IGNORECASE)

        for template_path in [
            "app/templates/lecons/lesson_flow.html",
            "app/templates/placement/test_flow.html",
        ]:
            with self.subTest(template=template_path):
                template = Path(template_path).read_text(encoding="utf-8")
                executable_bodies = [
                    match.group("body")
                    for match in script_pattern.finditer(template)
                    if "src=" not in match.group("attrs")
                    and "application/json" not in match.group("attrs")
                ]
                self.assertTrue(executable_bodies)
                for body in executable_bodies:
                    self.assertNotIn("{{", body)
                    self.assertNotIn("{%", body)


if __name__ == "__main__":
    unittest.main()
