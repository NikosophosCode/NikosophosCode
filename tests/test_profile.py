import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_profile", ROOT / "scripts" / "check_profile.py"
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 1200 320"
aria-labelledby="title description">
<title id="title">Profile</title><desc id="description">Static artwork</desc>
</svg>"""


class ProfileChecks(unittest.TestCase):
    def validate(self, text, svg=SVG):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text(text, encoding="utf-8")
            (root / "hero.svg").write_text(svg, encoding="utf-8")
            return checker.validate_profile(root)

    def test_repository_profile(self):
        self.assertEqual(checker.validate_profile(ROOT), [])

    def test_valid_local_picture_and_links(self):
        self.assertEqual(
            self.validate(
                '# Name\n'
                '<picture><source srcset="./hero.svg">'
                '<img src="./hero.svg" alt="Profile artwork" '
                'width="1200" height="320"></picture>\n'
                '## Selected work\n'
                '[Work](#selected-work) · [Code](https://github.com/example)\n'
                '[Email](mailto:hello@example.com?subject=Project)\n'
            ),
            [],
        )

    def test_missing_image_accessibility(self):
        errors = self.validate('# Name\n<img src="./missing.webp">')
        self.assertTrue(any("alt text" in error for error in errors))
        self.assertTrue(any("positive width" in error for error in errors))
        self.assertTrue(any("positive height" in error for error in errors))

    def test_svg_can_use_its_intrinsic_aspect_ratio(self):
        self.assertEqual(
            self.validate(
                '# Name\n<picture><img src="./hero.svg" '
                'alt="Profile artwork" width="1200"></picture>'
            ),
            [],
        )

    def test_external_html_and_markdown_images(self):
        for image in (
            '<img src="https://example.com/stats.svg" alt="Stats" '
            'width="100" height="100">',
            "![Stats](https://example.com/stats.svg)",
            '<picture><source srcset="//example.com/hero.svg"></picture>',
        ):
            with self.subTest(image=image):
                self.assertTrue(
                    any("must be local" in error for error in self.validate("# Name\n" + image))
                )

    def test_missing_local_file(self):
        self.assertTrue(
            any("Missing local" in error for error in self.validate("# Name\n[File](./missing.md)"))
        )

    def test_repository_escape(self):
        self.assertTrue(
            any("escapes" in error for error in self.validate("# Name\n[File](../outside.md)"))
        )

    def test_broken_anchor(self):
        self.assertTrue(
            any("Unknown section" in error for error in self.validate("# Name\n[Work](#missing)"))
        )

    def test_duplicate_headings(self):
        self.assertEqual(
            self.validate("# Name\n## Work\n## Work\n[Second](#work-1)"), []
        )

    def test_heading_hierarchy(self):
        self.assertTrue(
            any("levels jump" in error for error in self.validate("# Name\n### Work"))
        )

    def test_fenced_examples_do_not_count_as_headings(self):
        self.assertEqual(
            self.validate("# Name\n````markdown\n# Example\n```\n````\n## Work"), []
        )

    def test_unsafe_link(self):
        self.assertTrue(
            any("Unsupported" in error for error in self.validate("# Name\n[Bad](javascript:alert)"))
        )

    def test_active_and_external_svg_content(self):
        for content in (
            "<script>alert(1)</script>",
            '<image href="https://example.com/image.png"/>',
            '<rect onclick="alert(1)"/>',
            '<rect fill="url(https://example.com/image.svg)"/>',
            "<style>@import 'https://example.com/style.css';</style>",
        ):
            with self.subTest(content=content):
                svg = SVG.replace("</svg>", content + "</svg>")
                errors = self.validate(
                    '# Name\n<img src="./hero.svg" alt="Art" width="1" height="1">',
                    svg,
                )
                self.assertTrue(errors)

    def test_visual_budget(self):
        svg = SVG.replace("</svg>", "<!--" + "x" * checker.MAX_VISUAL_BYTES + "--></svg>")
        self.assertTrue(
            any(
                "budget" in error
                for error in self.validate(
                    '# Name\n<img src="./hero.svg" alt="Art" width="1" height="1">',
                    svg,
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
