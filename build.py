#!/usr/bin/env python3
"""Build the StepUp legal site from the app repo's markdown.

The markdown in ../stepup/docs/legal/ stays the single source of truth. Run
this after editing it, then commit the generated HTML.

    python3 build.py

Regions fenced with <!-- publish:skip-start --> ... <!-- publish:skip-end -->
in the markdown are developer notes and never reach the site.
"""

import html
import os
import re
import sys
from datetime import date

# --------------------------------------------------------------------------
# Config. When you move to a custom domain, change SITE_URL and put the domain
# in a CNAME file. Nothing else needs to change: every internal link the build
# emits is relative, so the site works at a github.io subpath and at a domain
# root without being rebuilt.
# --------------------------------------------------------------------------

SITE_URL = "https://dheerajghub.github.io/stepup-legal"
APP_NAME = "StepUp"
OWNER = "Dheeraj Kumar Sharma"
SUPPORT_EMAIL = "dheerajsh.codes@gmail.com"
SOURCE_DIR = os.path.join("..", "stepup", "docs", "legal")

PAGES = [
    {
        "slug": "privacy",
        "source": "privacy-policy.md",
        "nav": "Privacy",
        "title": "Privacy Policy",
        "description": (
            f"How {APP_NAME} handles your data. Your health data never leaves "
            "your iPhone."
        ),
    },
    {
        "slug": "terms",
        "source": "terms-of-service.md",
        "nav": "Terms",
        "title": "Terms & Conditions",
        "description": f"The terms you agree to when you use {APP_NAME}.",
    },
]

NAV = [("", "Home"), ("privacy", "Privacy"), ("terms", "Terms"), ("support", "Support")]

# Absolute URLs that appear in the markdown, rewritten to relative links.
INTERNAL = {
    "https://getstepup.app/privacy": "privacy",
    "https://getstepup.app/terms": "terms",
    "https://getstepup.app/support": "support",
}


# --------------------------------------------------------------------------
# Markdown -> HTML. Deliberately small: it handles exactly the subset the two
# documents use, and raises on anything it does not understand rather than
# silently dropping a clause from a legal document.
# --------------------------------------------------------------------------

CODE_TOKEN = "\x00CODE%d\x00"
LINK_TOKEN = "\x00LINK%d\x00"
URL_RE = re.compile(r'https?://[^\s<>"\)]+')


def inline(text, rel):
    """Inline formatting for one run of text."""
    codes, links = [], []

    def stash_code(m):
        codes.append(html.escape(m.group(1)))
        return CODE_TOKEN % (len(codes) - 1)

    def stash_link(href, label):
        links.append(f'<a href="{href}">{label}</a>')
        return LINK_TOKEN % (len(links) - 1)

    text = re.sub(r"`([^`]+)`", stash_code, text)
    text = html.escape(text)

    # [label](url)
    def md_link(m):
        label, url = m.group(1), m.group(2)
        if url in INTERNAL:
            url = rel(INTERNAL[url])
        return stash_link(url, label)

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", md_link, text)

    # Bare URLs left in the prose become real links. An internal one is shown
    # as its canonical address but points at a relative path, so the page keeps
    # working if the site moves to a custom domain.
    def bare(m):
        url = m.group(0)
        trailing = ""
        while url and url[-1] in ".,;:!?":
            trailing = url[-1] + trailing
            url = url[:-1]
        if url in INTERNAL:
            slug = INTERNAL[url]
            return stash_link(rel(slug), f"{SITE_URL}/{slug}/") + trailing
        return stash_link(url, url) + trailing

    text = URL_RE.sub(bare, text)

    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)

    # [POSTAL ADDRESS] and friends: make an unfilled placeholder loud.
    text = re.sub(
        r"\[([A-Z][A-Z0-9 _/&.,\'-]{2,})\](?!\()",
        r'<span class="placeholder">[\1]</span>',
        text,
    )

    for i, link in enumerate(links):
        text = text.replace(LINK_TOKEN % i, link)
    for i, code in enumerate(codes):
        text = text.replace(CODE_TOKEN % i, f"<code>{code}</code>")
    return text


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", text)


def strip_skipped(md):
    return re.sub(
        r"<!--\s*publish:skip-start\s*-->.*?<!--\s*publish:skip-end\s*-->\n?",
        "",
        md,
        flags=re.S,
    )


def convert(md, rel):
    """Return (title, toc, body_html)."""
    md = strip_skipped(md)
    lines = md.split("\n")
    out, toc = [], []
    title = None
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level, text = len(m.group(1)), inline(m.group(2), rel)
            if level == 1:
                title = re.sub(r"<[^>]+>", "", text)
            else:
                anchor = slugify(text)
                if level == 2:
                    toc.append((anchor, text))
                out.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            i += 1
            continue

        if re.fullmatch(r"-{3,}", stripped):
            out.append("<hr>")
            i += 1
            continue

        # table
        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            out.append(render_table(rows, rel))
            continue

        # blockquote
        if stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(re.sub(r"^>\s?", "", lines[i].strip()))
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(quote), rel)}</p></blockquote>")
            continue

        # bullet list (with 2-space hanging continuations)
        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < len(lines):
                cur = lines[i]
                if re.match(r"^[-*]\s+", cur.strip()) and not cur.startswith("  "):
                    items.append(re.sub(r"^[-*]\s+", "", cur.strip()))
                elif cur.startswith("  ") and cur.strip() and items:
                    items[-1] += " " + cur.strip()
                elif not cur.strip():
                    nxt = lines[i + 1] if i + 1 < len(lines) else ""
                    if re.match(r"^[-*]\s+", nxt.strip()):
                        i += 1
                        continue
                    break
                else:
                    break
                i += 1
            body = "".join(f"<li>{inline(x, rel)}</li>" for x in items)
            out.append(f"<ul>{body}</ul>")
            continue

        # numbered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines):
                cur = lines[i]
                if re.match(r"^\d+\.\s+", cur.strip()) and not cur.startswith("  "):
                    items.append(re.sub(r"^\d+\.\s+", "", cur.strip()))
                elif cur.startswith("  ") and cur.strip() and items:
                    items[-1] += " " + cur.strip()
                else:
                    break
                i += 1
            body = "".join(f"<li>{inline(x, rel)}</li>" for x in items)
            out.append(f"<ol>{body}</ol>")
            continue

        # paragraph
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(
            r"^(#{1,4}\s|[-*]\s|\d+\.\s|\||>|-{3,}$)", lines[i].strip()
        ):
            para.append(lines[i].strip())
            i += 1
        if para:
            joined = " ".join(para)
            # A lone bold line right under the title is the date stamp.
            out.append(f"<p>{inline(joined, rel)}</p>")

    if title is None:
        raise SystemExit("No H1 found. Refusing to publish an untitled document.")
    return title, toc, "\n".join(out)


def render_table(rows, rel):
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    if len(cells) < 2 or not all(re.fullmatch(r":?-{2,}:?", c) for c in cells[1]):
        raise SystemExit(f"Malformed table near: {rows[0][:60]}")
    aligns = []
    for spec in cells[1]:
        if spec.endswith(":") and spec.startswith(":"):
            aligns.append(" style=\"text-align:center\"")
        elif spec.endswith(":"):
            aligns.append(" style=\"text-align:right\"")
        else:
            aligns.append("")
    head = "".join(
        f"<th{aligns[j]}>{inline(c, rel)}</th>" for j, c in enumerate(cells[0])
    )
    body = ""
    for row in cells[2:]:
        tds = "".join(
            f"<td{aligns[j] if j < len(aligns) else ''}>{inline(c, rel)}</td>"
            for j, c in enumerate(row)
        )
        body += f"<tr>{tds}</tr>"
    return (
        '<div class="table-scroll"><table><thead><tr>'
        f"{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


# --------------------------------------------------------------------------
# Page chrome
# --------------------------------------------------------------------------

def relative_from(depth):
    """A function turning a slug into a link relative to a page at `depth`."""
    up = "../" * depth

    def rel(slug):
        return (up + (slug + "/" if slug else "")) or "./"

    return rel


def shell(*, title, description, depth, current, body, page_class=""):
    rel = relative_from(depth)
    up = "../" * depth
    assets = up + "assets/style.css"
    nav = "".join(
        '<a href="{href}"{aria}>{label}</a>'.format(
            href=rel(slug),
            aria=' aria-current="page"' if slug == current else "",
            label=label,
        )
        for slug, label in NAV
    )
    canonical = SITE_URL + "/" + (current + "/" if current else "")
    year = date.today().year
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · {APP_NAME}</title>
<meta name="description" content="{html.escape(description)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0d0d0d" media="(prefers-color-scheme: dark)">
<link rel="canonical" href="{canonical}">
<link rel="icon" type="image/png" sizes="32x32" href="{up}assets/icon-32.png">
<link rel="icon" type="image/png" sizes="192x192" href="{up}assets/icon-192.png">
<link rel="apple-touch-icon" sizes="180x180" href="{up}assets/icon-180.png">
<meta property="og:image" content="{SITE_URL}/assets/logo.png">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{APP_NAME}">
<meta property="og:title" content="{html.escape(title)} · {APP_NAME}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:url" content="{canonical}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap">
<link rel="stylesheet" href="{assets}">
</head>
<body{f' class="{page_class}"' if page_class else ""}>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap">
    <a class="brand" href="{rel("")}">
      <img class="brand-mark" src="{up}assets/logo.png" alt="" width="30" height="30">
      <span class="wordmark">StepUp<span class="dot">.</span></span>
    </a>
    <nav class="site-nav" aria-label="Primary">{nav}</nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <nav aria-label="Footer">
      <a href="{rel("privacy")}">Privacy Policy</a>
      <a href="{rel("terms")}">Terms &amp; Conditions</a>
      <a href="{rel("support")}">Support</a>
      <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>
    </nav>
    <p>&copy; {year} {OWNER}. All rights reserved.</p>
    <p>StepUp is a fitness app, not a medical device. Built for everyone, made in India.</p>
  </div>
</footer>
</body>
</html>
"""


def write(path, contents):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(contents)
    print(f"  wrote {path} ({len(contents):,} bytes)")


# --------------------------------------------------------------------------

def build_document(page):
    source = os.path.join(SOURCE_DIR, page["source"])
    if not os.path.exists(source):
        raise SystemExit(f"Missing source: {source}")
    md = open(source, encoding="utf-8").read()
    rel = relative_from(1)

    # The bold lines under the title become the pill badge, so they are lifted
    # out of the markdown before conversion rather than deleted from the HTML
    # afterwards.
    stamp_re = re.compile(r"^\*\*(Last updated|Effective):\s*(.+?)\*\*$", re.M)
    stamps = stamp_re.findall(md)
    md = stamp_re.sub("", md)

    stamp_html = ""
    if stamps:
        label = " · ".join(f"{k}: {v}" for k, v in stamps)
        stamp_html = f'<p class="stamp">{html.escape(label)}</p>'

    title, toc, body = convert(md, rel)

    toc_html = ""
    if toc:
        items = "".join(f'<li><a href="#{a}">{t}</a></li>' for a, t in toc)
        toc_html = f'<div class="toc"><h2>On this page</h2><ul>{items}</ul></div>'

    inner = f"""<div class="wrap">
  <div class="doc-head">
    <h1>{title.replace(APP_NAME + " ", "")}</h1>
    {stamp_html}
    {toc_html}
  </div>
  <article class="doc">
{body}
  </article>
</div>"""

    write(
        os.path.join(page["slug"], "index.html"),
        shell(
            title=page["title"],
            description=page["description"],
            depth=1,
            current=page["slug"],
            body=inner,
        ),
    )
    return body


def build_index():
    rel = relative_from(0)
    body = f"""<div class="wrap hero">
  <img class="hero-mark" src="assets/logo.png" alt="StepUp app icon" width="68" height="68">
  <h1>Legal<span class="muted">&amp; support</span></h1>
  <p class="lede">The documents behind {APP_NAME}, the step tracker that keeps your
  health data on your iPhone.</p>

  <div class="card-list">
    <a class="card" href="{rel('privacy')}">
      <span class="card-title">Privacy Policy</span>
      <p>What we collect, what we refuse to collect, and the choices you have.
      Your steps, distance, heart rate and gait never leave your device.</p>
    </a>
    <a class="card" href="{rel('terms')}">
      <span class="card-title">Terms &amp; Conditions</span>
      <p>The agreement covering your account, StepUp Pro, and the health
      disclaimer you should read before starting any exercise programme.</p>
    </a>
    <a class="card" href="{rel('support')}">
      <span class="card-title">Support</span>
      <p>Common questions, and how to reach a human.</p>
    </a>
  </div>

  <div class="promise">
    <h2>Your health data never leaves your iPhone</h2>
    <p>StepUp reads your activity from Apple Health, uses it on your device, and
    stores it on your device. It is never uploaded to our servers, never put in
    an analytics event, and never sold. That is how the app is built, not just
    how it is described.</p>
  </div>
</div>"""
    write(
        "index.html",
        shell(
            title="Legal & Support",
            description=(
                f"Privacy Policy, Terms & Conditions and support for {APP_NAME}, "
                "the step tracker for iPhone."
            ),
            depth=0,
            current="",
            body=body,
        ),
    )


def build_support():
    rel = relative_from(1)
    body = f"""<div class="wrap">
  <div class="doc-head">
    <h1>Support</h1>
    <p class="stamp">Replies within 2 business days</p>
  </div>
  <article class="doc">
    <a class="contact" href="mailto:{SUPPORT_EMAIL}">
      <span class="label">Email us</span>
      <span class="value">{SUPPORT_EMAIL}</span>
    </a>
    <p>Tell us your iPhone model, your iOS version, and the StepUp version from
    the bottom of the Profile tab. It gets you a useful answer far faster.</p>

    <h2 id="steps-are-wrong">My steps look wrong or missing</h2>
    <p>StepUp does not count steps itself. It reads whatever Apple Health already
    holds, so if a number looks wrong, open the Health app and check it there
    first. If Health disagrees with StepUp, that is a bug and we want to hear
    about it.</p>
    <p>If StepUp shows nothing at all, check
    <strong>Settings &rsaquo; Health &rsaquo; Data Access &amp; Devices &rsaquo;
    StepUp</strong> and make sure the categories are on. Apple deliberately does
    not tell apps which permissions were denied, so StepUp cannot warn you. It
    can only show an empty screen.</p>

    <h2 id="metrics-locked">A metric says it needs more data</h2>
    <p>Each metric needs a minimum number of readings before it can say anything
    honest. Pace, Effort and Fitness additionally need walking workouts and
    walking heart rate, which are written by an Apple Watch. Without a Watch,
    those three stay quiet. That is expected, not a fault.</p>

    <h2 id="subscription">Billing, refunds and cancelling</h2>
    <p>Apple handles every payment for StepUp Pro. To cancel, open
    <strong>Settings &rsaquo; your name &rsaquo; Subscriptions</strong> on your
    iPhone. Cancel at least 24 hours before your period ends to avoid the next
    charge.</p>
    <p>Refunds are issued by Apple, not by us, and we have no ability to grant
    or reverse one. Request yours at
    <a href="https://reportaproblem.apple.com">reportaproblem.apple.com</a>.</p>
    <p>Buying Lifetime does <strong>not</strong> cancel an existing subscription;
    Apple does not permit one purchase to cancel another. If you bought Lifetime
    while subscribed, cancel the subscription yourself using the steps above.</p>

    <h2 id="family">Family Sharing</h2>
    <p>A Family plan shares access with up to six people in your Apple Family
    group. Everyone needs their own StepUp account and grants their own Apple
    Health permission. No family member can see another member's steps, health
    data or walking plan.</p>

    <h2 id="delete">Deleting your account</h2>
    <p>Profile &rsaquo; Delete Account removes your account and its data from our
    servers and clears StepUp's data from your device. It cannot be undone.</p>
    <p>It does <strong>not</strong> cancel an active subscription. Only Apple
    can do that, using the steps above. Please cancel first.</p>

    <h2 id="privacy">Privacy</h2>
    <p>The short version: your health data never leaves your iPhone. The long
    version is the <a href="{rel('privacy')}">Privacy Policy</a>.</p>
  </article>
</div>"""
    write(
        "support/index.html",
        shell(
            title="Support",
            description=f"Help with {APP_NAME}: Apple Health, metrics, subscriptions and account deletion.",
            depth=1,
            current="support",
            body=body,
        ),
    )


def build_404():
    rel = relative_from(0)
    body = f"""<div class="wrap hero">
  <h1>Not found<span class="muted">404</span></h1>
  <p class="lede">That page does not exist. The documents you are probably after:</p>
  <div class="card-list">
    <a class="card" href="{rel('privacy')}"><span class="card-title">Privacy Policy</span></a>
    <a class="card" href="{rel('terms')}"><span class="card-title">Terms &amp; Conditions</span></a>
    <a class="card" href="{rel('support')}"><span class="card-title">Support</span></a>
  </div>
</div>"""
    write("404.html", shell(title="Not found", description="Page not found.",
                            depth=0, current="", body=body))


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"Building {SITE_URL}")
    rendered = ""
    for page in PAGES:
        rendered += build_document(page)
    build_index()
    build_support()
    build_404()
    write(".nojekyll", "")

    leftover = sorted(set(re.findall(r'<span class="placeholder">\[([^\]]+)\]', rendered)))
    print()
    if leftover:
        print("WARNING: unfilled placeholders are live on the site:")
        for item in leftover:
            print(f"  [{item}]")
        print(f"\n  Fix them in {SOURCE_DIR}/ and run this again.")
        return 1
    print("No unfilled placeholders. Ready to publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
