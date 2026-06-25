"""
add_jtd_frontmatter.py — Add Just-the-Docs front matter to all pages.

Title rules:
  - Part titles: kept as-is  ("Part I — Language & Data Structures")
  - Chapter titles: "Chapter N: Name" → "Name"  (strip "Chapter N: " prefix)
  - Section titles: derived from filename  ("01-language-basics.md" → "Language Basics")

Hierarchy:
  index.md                          → nav_order: 1 (Home, no parent)
  part-N-*/index.md                 → has_children: true, nav_order: N
  part-N-*/chapter-N-*/index.md     → parent: <part title>, has_children: true, nav_order: N
  part-N-*/chapter-N-*/N-section.md → parent: <clean chapter title>, nav_order: N
  appendices/*/...                  → parent: "Appendices", nav_order: N
"""

import os
import re
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))


def read_front_matter(path):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    if not lines or lines[0].strip() != "---":
        return {}, lines
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}, lines
    fm = {}
    for line in lines[1:end]:
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"')
    return fm, lines[end + 1:]


def write_file(path, fm, body_lines):
    fm_keys = ["layout", "title", "parent", "nav_order", "has_children"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        for k in fm_keys:
            if k in fm:
                v = fm[k]
                if k in ("title", "parent") and any(c in str(v) for c in [":", "&", "—"]):
                    f.write(f'{k}: "{v}"\n')
                else:
                    f.write(f"{k}: {v}\n")
        f.write("---\n")
        f.writelines(body_lines)


def clean_chapter_title(title):
    """Strip 'Chapter N: ' prefix → keep only the name."""
    return re.sub(r"^Chapter\s+\d+:\s*", "", title).strip()


def title_from_filename(filename):
    """01-language-basics.md → Language Basics"""
    name = filename.replace(".md", "")
    name = re.sub(r"^\d+-", "", name)          # strip leading number-dash
    return name.replace("-", " ").title()


def get_raw_title(path):
    fm, _ = read_front_matter(path)
    return fm.get("title", "")


def process():
    # ── collect part titles (kept as-is) ────────────────────────────────────
    part_dirs = sorted(
        d for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d)) and re.match(r"part-\d+", d)
    )
    part_titles = {}  # dirname → title (raw)
    for pd in part_dirs:
        idx = os.path.join(ROOT, pd, "index.md")
        if os.path.exists(idx):
            part_titles[pd] = get_raw_title(idx)

    # ── collect CLEAN chapter titles (used as parent: for section pages) ────
    chapter_clean_titles = {}  # (part_dir, chapter_dir) → clean title
    for pd in part_dirs:
        chapter_dirs = sorted(
            d for d in os.listdir(os.path.join(ROOT, pd))
            if os.path.isdir(os.path.join(ROOT, pd, d)) and re.match(r"chapter-", d)
        )
        for cd in chapter_dirs:
            idx = os.path.join(ROOT, pd, cd, "index.md")
            if os.path.exists(idx):
                raw = get_raw_title(idx)
                chapter_clean_titles[(pd, cd)] = clean_chapter_title(raw)

    # ── root index.md ───────────────────────────────────────────────────────
    root_idx = os.path.join(ROOT, "index.md")
    if os.path.exists(root_idx):
        fm, body = read_front_matter(root_idx)
        fm["layout"] = "home"
        fm["nav_order"] = "1"
        fm.pop("parent", None)
        fm.pop("has_children", None)
        write_file(root_idx, fm, body)
        print(f"✅ index.md")

    # ── part index pages ────────────────────────────────────────────────────
    for i, pd in enumerate(part_dirs, 1):
        idx = os.path.join(ROOT, pd, "index.md")
        if not os.path.exists(idx):
            continue
        fm, body = read_front_matter(idx)
        fm["layout"] = "default"
        fm["nav_order"] = str(i + 1)
        fm["has_children"] = "true"
        fm.pop("parent", None)
        write_file(idx, fm, body)
        print(f"✅ {pd}/index.md")

    # ── chapter index pages — clean title ───────────────────────────────────
    for pd in part_dirs:
        chapter_dirs = sorted(
            d for d in os.listdir(os.path.join(ROOT, pd))
            if os.path.isdir(os.path.join(ROOT, pd, d)) and re.match(r"chapter-", d)
        )
        parent_title = part_titles.get(pd, "")
        for j, cd in enumerate(chapter_dirs, 1):
            idx = os.path.join(ROOT, pd, cd, "index.md")
            if not os.path.exists(idx):
                continue
            fm, body = read_front_matter(idx)
            fm["layout"] = "default"
            fm["title"] = chapter_clean_titles.get((pd, cd), fm.get("title", ""))
            fm["parent"] = parent_title
            fm["nav_order"] = str(j)
            fm["has_children"] = "true"
            write_file(idx, fm, body)
            print(f"✅ {pd}/{cd}/index.md  title={fm['title']!r}")

    # ── section pages — title from filename ─────────────────────────────────
    for pd in part_dirs:
        chapter_dirs = sorted(
            d for d in os.listdir(os.path.join(ROOT, pd))
            if os.path.isdir(os.path.join(ROOT, pd, d)) and re.match(r"chapter-", d)
        )
        for cd in chapter_dirs:
            chapter_path = os.path.join(ROOT, pd, cd)
            parent_title = chapter_clean_titles.get((pd, cd), "")

            # Flat .md files
            section_files = sorted(
                f for f in os.listdir(chapter_path)
                if f.endswith(".md") and f != "index.md"
            )
            for k, sf in enumerate(section_files, 1):
                path = os.path.join(chapter_path, sf)
                if os.path.isdir(path.replace(".md", "")):
                    continue
                fm, body = read_front_matter(path)
                fm["layout"] = "default"
                fm["title"] = title_from_filename(sf)
                fm["parent"] = parent_title
                fm["nav_order"] = str(k)
                fm.pop("has_children", None)
                write_file(path, fm, body)
                print(f"  ✅ {sf}  →  {fm['title']!r}")

            # Section subdirectories
            section_dirs = sorted(
                d for d in os.listdir(chapter_path)
                if os.path.isdir(os.path.join(chapter_path, d))
            )
            for k, sd in enumerate(section_dirs, 1):
                idx = os.path.join(chapter_path, sd, "index.md")
                if not os.path.exists(idx):
                    candidates = glob.glob(os.path.join(chapter_path, sd, "*.md"))
                    if not candidates:
                        continue
                    idx = candidates[0]
                fm, body = read_front_matter(idx)
                fm["layout"] = "default"
                fm["title"] = title_from_filename(sd)
                fm["parent"] = parent_title
                fm["nav_order"] = str(k)
                write_file(idx, fm, body)
                print(f"  ✅ {sd}/  →  {fm['title']!r}")

    # ── appendices ───────────────────────────────────────────────────────────
    app_root = os.path.join(ROOT, "appendices")
    if os.path.isdir(app_root):
        entries = sorted(os.listdir(app_root))
        for k, entry in enumerate(entries, 1):
            entry_path = os.path.join(app_root, entry)
            if os.path.isdir(entry_path):
                for path in glob.glob(os.path.join(entry_path, "*.md")):
                    fm, body = read_front_matter(path)
                    fm["layout"] = "default"
                    fm["parent"] = "Appendices"
                    fm["nav_order"] = str(k)
                    write_file(path, fm, body)
                    print(f"  ✅ appendices/{entry}/")
            elif entry.endswith(".md"):
                fm, body = read_front_matter(entry_path)
                fm["layout"] = "default"
                fm["parent"] = "Appendices"
                fm["nav_order"] = str(k)
                write_file(entry_path, fm, body)
                print(f"  ✅ appendices/{entry}")

    print("\nDone.")


if __name__ == "__main__":
    process()
