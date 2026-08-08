from __future__ import annotations

import unittest
from importlib.resources import files


class StaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = files("mail_lantern").joinpath("static")
        cls.html = root.joinpath("index.html").read_text(encoding="utf-8")
        cls.css = root.joinpath("styles.css").read_text(encoding="utf-8")
        cls.js = root.joinpath("app.js").read_text(encoding="utf-8")

    def test_four_global_themes_exist(self) -> None:
        for theme in ("sky", "jade", "sunset", "graphite"):
            self.assertIn(f'data-theme-choice="{theme}"', self.html)
            if theme != "sky":
                self.assertIn(f'data-theme="{theme}"', self.css)

    def test_graphite_uses_required_deep_gray(self) -> None:
        self.assertIn("--bg:#17191d", self.css)

    def test_favicon_formats_are_linked(self) -> None:
        for path in ("/favicon.svg", "/favicon.ico", "/apple-touch-icon.png"):
            self.assertIn(f'href="{path}?v=1.0.1"', self.html)

    def test_no_external_runtime_assets(self) -> None:
        self.assertNotIn('<script src="http', self.html)
        self.assertNotIn('<link rel="stylesheet" href="http', self.html)

    def test_csp_compatible_assets_have_no_inline_handlers(self) -> None:
        self.assertNotIn("<script>", self.html)
        self.assertNotIn(" onclick=", self.html)
        self.assertNotIn(" style=", self.html)

    def test_untrusted_values_are_not_inserted_as_html(self) -> None:
        self.assertNotIn("innerHTML", self.js)
        self.assertIn("textContent", self.js)

    def test_credentials_and_token_are_never_persisted(self) -> None:
        self.assertNotIn('localStorage.setItem("token"', self.js)
        self.assertNotIn('sessionStorage.setItem("token"', self.js)
        self.assertNotIn('localStorage.setItem("account"', self.js)
        self.assertNotIn('localStorage.setItem("appPassword"', self.js)
        self.assertIn('localStorage.setItem("mail-lantern-theme"', self.js)

    def test_password_is_cleared_after_each_scan_case(self) -> None:
        self.assertIn('elements.password.value = ""', self.js)

    def test_privacy_and_theme_controls_are_accessible(self) -> None:
        self.assertIn('id="privacy-toggle"', self.html)
        self.assertIn('aria-pressed="false"', self.html)
        self.assertIn('role="radiogroup"', self.html)

    def test_official_readonly_boundary_is_visible(self) -> None:
        self.assertIn("imap.mail.me.com:993", self.html)
        self.assertIn("只读收件箱", self.html)
        self.assertIn("不保存凭据", self.html)
        self.assertIn("support.apple.com/102654", self.html)

    def test_reduced_motion_and_mobile_breakpoints_exist(self) -> None:
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("@media (max-width:640px)", self.css)


if __name__ == "__main__":
    unittest.main()
