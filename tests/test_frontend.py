import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
DOCS = ROOT / "docs"


class FrontendTests(unittest.TestCase):
    def test_page_has_phone_sections_and_help_line(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        for marker in ["viewport", "manifest.webmanifest", "apple-touch-icon", "budget", "pick-body", "new-list",
                       "feed-list", "game-list", "countdown", "log-form", "detail", "1-800-547-6133"]:
            self.assertIn(marker, html)

    def test_script_reads_static_data_and_supports_features(self):
        script = (DOCS / "app.js").read_text(encoding="utf-8")
        for marker in ["data/latest.json", "simulate", "check_minutes", "seen-ids", "results-log",
                       "Notification", "serviceWorker", "navigator.share", "is_new"]:
            self.assertIn(marker, script)

    def test_every_referenced_element_id_exists(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        script = (DOCS / "app.js").read_text(encoding="utf-8")
        ids = set(re.findall(r"\$\('#([\w-]+)'\)", script))
        for element_id in ids:
            self.assertIn(f'id="{element_id}"', html, element_id)

    def test_manifest_icons_exist(self):
        manifest = json.loads((DOCS / "manifest.webmanifest").read_text(encoding="utf-8"))
        for icon in manifest["icons"]:
            self.assertTrue((DOCS / icon["src"]).exists(), icon["src"])

    def test_schedule_matches_builder(self):
        import site_builder
        workflow = (ROOT / ".github" / "workflows" / "update-data.yml").read_text(encoding="utf-8")
        minutes = re.search(r'cron: "([\d,]+) \*', workflow).group(1)
        self.assertEqual([int(m) for m in minutes.split(",")], site_builder.CHECK_MINUTES)


if __name__ == "__main__":
    unittest.main()
