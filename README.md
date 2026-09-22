# stepup-legal

The Privacy Policy, Terms & Conditions and Support pages for **StepUp**, hosted
on GitHub Pages.

**Live:** https://dheerajghub.github.io/stepup-legal/

| Page | URL |
| --- | --- |
| Privacy Policy | `https://dheerajghub.github.io/stepup-legal/privacy/` |
| Terms & Conditions | `https://dheerajghub.github.io/stepup-legal/terms/` |
| Support | `https://dheerajghub.github.io/stepup-legal/support/` |

Those three go into App Store Connect as the Privacy Policy URL, the Terms of
Use (EULA) URL on the subscription, and the Support URL.

---

## The source of truth is the app repo

Do **not** edit the HTML by hand. The documents live as markdown in the StepUp
app repo, and this site is generated from them:

```text
stepup/docs/legal/privacy-policy.md   ->  privacy/index.html
stepup/docs/legal/terms-of-service.md ->  terms/index.html
```

Editing the markdown in one place keeps the published policy, the App Store
privacy questionnaire (`stepup/docs/app-store/app-privacy.md`) and the
engineering notes (`stepup/docs/privacy.md`) from drifting apart. That is the
failure that gets an app pulled, not a typo.

Regions fenced like this in the markdown are developer notes and never reach the
site:

```markdown
<!-- publish:skip-start -->
> Internal note nobody outside the team should read.
<!-- publish:skip-end -->
```

## Rebuilding

Both repos must sit side by side:

```text
step-tracker-app/
├── stepup/         the app
└── stepup-legal/   this site
```

Then:

```sh
python3 build.py
```

No dependencies, just plain Python 3. It regenerates every page, and **exits
non-zero if any `[PLACEHOLDER]` is still unfilled**, so you cannot accidentally
publish a privacy policy that says `[POSTAL ADDRESS]`. Unfilled placeholders are
also rendered in orange on the page itself.

Commit the generated HTML. GitHub Pages serves these files directly.

## Publishing

1. Create a **public** repo named `stepup-legal` on GitHub.
2. Push this directory to `main`.
3. **Settings → Pages → Build and deployment**: Source `Deploy from a branch`,
   Branch `main`, Folder `/ (root)`. Save.
4. Wait a minute, then load the URL above.

The repo must be public. GitHub Pages from a private repo needs a paid plan.

`.nojekyll` is committed so GitHub serves the files as-is instead of running
Jekyll over them.

## Moving to a custom domain later

Nothing in the documents has to change, because every internal link the build
emits is relative, so the site works at a `github.io` subpath and at a domain root
without being rebuilt.

1. Put the domain in a `CNAME` file at the repo root, e.g. `legal.getstepup.app`.
2. Point the DNS record at GitHub Pages.
3. Update `SITE_URL` in `build.py` (it only affects the `<link rel="canonical">`
   and the Open Graph tags) and rebuild.
4. Update `LegalLinks.swift` in the app, and the three URLs in App Store Connect.

## Files

```text
build.py           the generator, and the only thing you run
assets/style.css   design tokens taken from the app's AppColors.swift
index.html         landing page
privacy/index.html generated
terms/index.html   generated
support/index.html hand-written FAQ
404.html           fallback
.nojekyll          tells GitHub Pages to skip Jekyll
```
