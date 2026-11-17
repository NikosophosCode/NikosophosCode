# Profile assets

These assets support the root profile README. Keep essential project descriptions
and links in Markdown, not only inside images.

## Sources and scope

| Asset | Origin | Notes |
| --- | --- | --- |
| `hero-dark.svg`, `hero-light.svg` | Original artwork for this profile | Static, self-contained SVGs; no scripts, animation, external fonts or tracking. |
| `kevgo-1.webp` | `AIEmailKevgoAutomation/docs/screenshots/public-home-desktop-en.png` | Cropped/resized development UI from an isolated test harness. No live mailbox, credentials or customer data. Not evidence of production acceptance. |
| `torre-de-sofia.webp` | Existing portfolio screenshot: `NikosophosPage/public/assets/img/projects/torredesofia/image-1.webp` | Public-facing website preview. |
| `yeouth-face-oil.webp` | Screenshot of <https://faceoil.yeouth.com/> | Public landing page, captured without signing in or submitting forms. Product imagery and branding belong to their respective owners. |

The images were prepared on 2026-11-16 and are stored locally to avoid
third-party image-generation services, hotlinks and runtime API limits.

## Updating the profile

1. Check descriptions against the current implementation, not just project plans.
2. Use repository links only when the source is publicly accessible. Do not
   change repository visibility to make a profile link work.
3. Verify live URLs before replacing them. A successful HTTP response alone
   does not establish that an integration works.
4. Use public pages or explicitly synthetic test data for screenshots. Never
   publish private financial records, email content, tokens or admin screens.
5. Retain descriptive alt text and accurate image dimensions.
   The banner uses its SVG aspect ratio without an HTML `height` attribute:
   GitHub's `<picture>` renderer would otherwise reserve a fixed height on mobile.
6. Keep the referenced visual assets below 1 MiB in total.
7. Run the dependency-free local checks from the repository root:

   ```sh
   python3 scripts/check_profile.py
   python3 -m unittest discover -s tests
   ```

The checks run offline. They do not certify deployment availability or application
functionality; review those separately. The older files elsewhere in `assets/`
are retained rather than deleting existing resources.
