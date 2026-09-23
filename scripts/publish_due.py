"""Publish queued editions whose publish_at time has passed.

Each edition waits in _queue/NNN/ as edition.html (the finished
/editions/NNN/ page) plus meta.json. Jekyll ignores folders that start
with an underscore, so queued editions are not served before their date.
When due, this script:
  1. writes editions/NNN/index.html
  2. rebuilds the home page (index.html) from it, keeping the site-level head
  3. adds the edition to the top of editions/index.html
  4. adds it to sitemap.xml
  5. removes the queue folder
Safe to run repeatedly; it does nothing when nothing is due.
"""
import json, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://footnote.report/"
MARKER = "<!-- Add each new edition at the top of this list -->"


def publish(qdir: Path) -> None:
    meta = json.loads((qdir / "meta.json").read_text())
    n = f"{meta['number']:03d}"
    day = meta["publish_at"][:10]
    edition = (qdir / "edition.html").read_text()

    # 1. edition page
    out = ROOT / "editions" / n
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(edition)

    # 2. home page: site head from current index.html + edition from fonts on
    home_old = (ROOT / "index.html").read_text()
    split = '<link rel="preconnect"'
    home = home_old[: home_old.index(split)] + edition[edition.index(split):]
    home = home.replace('<a class="word" href="../../">', '<a class="word" href="./">')
    home = re.sub(r'<nav class="foot-nav" aria-label="Archive">.*?</nav>',
                  '<nav class="foot-nav" aria-label="Archive"><a href="editions/">Past editions</a></nav>',
                  home, flags=re.S)
    home = home.replace('href="../../assets/', 'href="assets/')
    (ROOT / "index.html").write_text(home)

    # 3. archive list
    arch_path = ROOT / "editions" / "index.html"
    arch = arch_path.read_text()
    if f'href="{n}/"' not in arch:
        entry = (
            f'{MARKER}\n'
            f'    <article class="ed">\n'
            f'      <span class="num">No. {meta["number"]}</span>\n'
            f'      <div>\n'
            f'        <h2><a href="{n}/">{meta["archive_title"]}</a></h2>\n'
            f'        <div class="date">{meta["archive_date"]}</div>\n'
            f'        <p>{meta["archive_blurb"]}</p>\n'
            f'      </div>\n'
            f'    </article>'
        )
        arch = arch.replace(MARKER, entry, 1)
        arch_path.write_text(arch)

    # 4. sitemap
    sm_path = ROOT / "sitemap.xml"
    sm = sm_path.read_text()
    loc = f"{SITE}editions/{n}/"
    if loc not in sm:
        block = (
            f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{day}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n    <priority>0.9</priority>\n  </url>\n"
        )
        anchor = f"<loc>{SITE}editions/</loc>"
        i = sm.index("</url>", sm.index(anchor)) + len("</url>\n")
        sm = sm[:i] + block + sm[i:]
    for page in (SITE, f"{SITE}editions/"):
        sm = re.sub(rf"(<loc>{re.escape(page)}</loc>\s*<lastmod>)[^<]*", rf"\g<1>{day}", sm)
    sm_path.write_text(sm)

    # 5. dequeue
    shutil.rmtree(qdir)
    print(f"Published No. {meta['number']} ({day})")


def main() -> int:
    now = datetime.now(timezone.utc)
    force = "--force" in sys.argv
    due = []
    for q in sorted((ROOT / "_queue").glob("*/meta.json")):
        at = datetime.fromisoformat(json.loads(q.read_text())["publish_at"])
        if force or at <= now:
            due.append(q.parent)
        else:
            print(f"Waiting: {q.parent.name} goes live {at.isoformat()}")
    for q in due:  # oldest first, so the home page ends on the newest
        publish(q)
    return 0


if __name__ == "__main__":
    sys.exit(main())
