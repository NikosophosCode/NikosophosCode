#!/usr/bin/env python3
"""Offline checks for the profile's links, headings and self-contained visuals."""

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


MAX_VISUAL_BYTES = 1024 * 1024


class ProfileHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.sources = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "img":
            self.images.append(attributes)
        elif tag == "source":
            self.sources.append(attributes)
        elif tag == "a":
            self.links.append(attributes.get("href", ""))


def headings_in(text):
    """Ignore fenced examples when inspecting the Markdown heading hierarchy."""
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            character = marker[1][0]
            if fence is None:
                fence = (character, len(marker[1]))
            elif character == fence[0] and len(marker[1]) >= fence[1]:
                fence = None
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$", line)
        if fence is None and heading:
            yield len(heading[1]), heading[2]


def validate_svg(path, errors):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        errors.append(f"Invalid SVG {path.name}: {error}")
        return

    tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
    if not {"title", "desc"}.issubset(tags):
        errors.append(f"{path.name} needs a title and description.")
    if root.get("role") != "img" or not root.get("aria-labelledby"):
        errors.append(f"{path.name} needs an accessible image role and label.")
    if not root.get("viewBox") and not (root.get("width") and root.get("height")):
        errors.append(f"{path.name} needs intrinsic dimensions or a viewBox.")
    if tags & {"script", "foreignObject", "animate", "animateTransform", "set"}:
        errors.append(f"{path.name} must be static, without scripts or embedded HTML.")
    for element in root.iter():
        for attribute, value in element.attrib.items():
            name = attribute.rsplit("}", 1)[-1]
            if name.startswith("on") or (
                name in {"href", "src"} and not value.startswith("#")
            ):
                errors.append(f"{path.name} contains an active or external reference.")
            for target in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", value):
                if not target.startswith("#"):
                    errors.append(f"{path.name} contains an external CSS reference.")
        if element.tag.rsplit("}", 1)[-1] == "style" and element.text:
            if re.search(r"@import|url\s*\(", element.text, re.IGNORECASE):
                errors.append(f"{path.name} must not import CSS or external resources.")


def validate_profile(directory):
    root = Path(directory).resolve()
    errors = []
    readme = root / "README.md"
    if not readme.is_file():
        return ["README.md is missing."]
    text = readme.read_text(encoding="utf-8")
    document = ProfileHTML()
    document.feed(text)

    headings = list(headings_in(text))
    if sum(level == 1 for level, _ in headings) != 1:
        errors.append("Use exactly one H1 for the profile name.")
    previous = 0
    anchors = set()
    duplicates = Counter()
    for level, title in headings:
        if level > previous + 1:
            errors.append(f"Heading levels jump before {title!r}.")
        previous = level
        slug = re.sub(r"[^\w\s-]", "", title.lower()).replace(" ", "-")
        suffix = f"-{duplicates[slug]}" if duplicates[slug] else ""
        anchors.add(slug + suffix)
        duplicates[slug] += 1

    def local_file(target):
        parsed = urlsplit(target)
        path = (root / unquote(parsed.path)).resolve()
        if not path.is_relative_to(root):
            errors.append(f"Local reference escapes the repository: {target}")
        elif not path.is_file():
            errors.append(f"Missing local file: {target}")
        else:
            return path
        return None

    visuals = set()
    for image in document.images:
        if not image.get("alt", "").strip():
            errors.append("Every profile image needs descriptive alt text.")
        for attribute in ("width", "height"):
            # GitHub's picture renderer keeps a fixed HTML height on mobile.
            # SVGs provide an intrinsic ratio, so let the browser calculate it.
            if (
                attribute == "height"
                and "height" not in image
                and urlsplit(image.get("src", "")).path.endswith(".svg")
            ):
                continue
            if not re.fullmatch(r"[1-9]\d*", image.get(attribute, "")):
                errors.append(f"Image {image.get('src')} needs a positive {attribute}.")

    image_targets = [image.get("src", "") for image in document.images]
    for source in document.sources:
        image_targets.extend(
            entry.strip().split()[0]
            for entry in source.get("srcset", "").split(",")
            if entry.strip()
        )
    # The profile uses inline Markdown links/images, not reference-style links.
    markdown_links = re.findall(r"(!?)\[[^\]\n]*\]\(([^)\s]+)\)", text)
    image_targets.extend(target for prefix, target in markdown_links if prefix)
    for target in image_targets:
        if not target or urlsplit(target).scheme or urlsplit(target).netloc:
            errors.append(f"Profile images must be local files: {target!r}")
            continue
        path = local_file(target)
        if path:
            visuals.add(path)

    links = document.links + [
        target for prefix, target in markdown_links if not prefix
    ]
    for target in links:
        parsed = urlsplit(target)
        if target.startswith("#"):
            if unquote(target[1:]) not in anchors:
                errors.append(f"Unknown section anchor: {target}")
        elif parsed.scheme == "https" and parsed.netloc:
            continue
        elif parsed.scheme == "mailto" and "@" in parsed.path:
            continue
        elif parsed.scheme or parsed.netloc or not target:
            errors.append(f"Unsupported or empty link: {target!r}")
        else:
            local_file(target)

    if sum(path.stat().st_size for path in visuals) > MAX_VISUAL_BYTES:
        errors.append("Referenced visual assets exceed the 1 MiB budget.")
    for path in sorted(visuals):
        if path.suffix.lower() == ".svg":
            validate_svg(path, errors)
    if "<!--RECENT_ACTIVITY:" in text:
        errors.append("Remove obsolete recent-activity placeholders.")
    return errors


if __name__ == "__main__":
    problems = validate_profile(Path(__file__).resolve().parents[1])
    if problems:
        print("\n".join(f"ERROR: {problem}" for problem in problems), file=sys.stderr)
        sys.exit(1)
    print("Profile checks passed: headings, links, image accessibility and local assets.")
