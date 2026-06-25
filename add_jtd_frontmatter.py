"""
add_jtd_frontmatter.py — Add Just-the-Docs front matter to all pages.

Hierarchy:
  index.md                              → nav_order: 1 (Home, no parent)
  part-N-*/index.md                     → has_children: true, nav_order: N
  appendices/*/index.md or *.md         → parent: "Appendices", nav_order: N
  part-N-*/chapter-N-*/index.md         → parent: <part title>, has_children: true, nav_order: N
  part-N-*/chapter-N-*/N-section.md     → parent: <chapter title>, nav_order: N
"""

import os
import re
import glob

ROOT = os.path.dirname(os.path.abspath(__file__))


def read_front_matter(path):
    """Return (front_matter_dict, body_lines) from a markdown file."""
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
    """Write file with updated front matter."""
    fm_keys = ["layout", "title", "parent", "nav_order", "has_children"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        for k in fm_keys:
            if k in fm:
                v = fm[k]
                # Quote titles that contain special chars
                if k in ("title", "parent") and any(c in str(v) for c in [":", "&", "—"]):
                    f.write(f'{k}: "{v}"\n')
                else:
                    f.write(f"{k}: {v}\n")
        f.write("---\n")
        f.writelines(body_lines)


def get_title(path):
    fm, _ = read_front_matter(path)
    return fm.get("title", "")


def nav_order_from_dirname(dirname):
    """Extract leading number from directory/file name."""
    m = re.match(r"(\d+)", dirname)
    return int(m.group(1)) if m else 99


def process():
    # ── collect part titles ─────────────────────────────────────────────────
    part_dirs = sorted(
        d for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d)) and re.match(r"part-\d+", d)
    )
    part_titles = {}  # dirname → title
    for pd in part_dirs:
        idx = os.path.join(ROOT, pd, "index.md")
        if os.path.exists(idx):
            part_titles[pd] = get_title(idx)

    chapter_titles = {}  # (part_dir, chapter_dir) → title
    for pd in part_dirs:
        chapter_dirs = sorted(
            d for d in os.listdir(os.path.join(ROOT, pd))
            if os.path.isdir(os.path.join(ROOT, pd, d)) and re.match(r"chapter-", d)
        )
        for cd in chapter_dirs:
            idx = os.path.join(ROOT, pd, cd, "index.md")
            if os.path.exists(idx):
                chapter_titles[(pd, cd)] = get_title(idx)

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
        fm["nav_order"] = str(i + 1)   # Home=1, Part I=2, Part II=3 …
        fm["has_children"] = "true"
        fm.pop("parent", None)
        write_file(idx, fm, body)
        print(f"✅ {pd}/index.md  (nav_order={i+1})")

    # ── chapter index pages ─────────────────────────────────────────────────
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
            fm["parent"] = parent_title
            fm["nav_order"] = str(j)
            fm["has_children"] = "true"
            write_file(idx, fm, body)
            print(f"✅ {pd}/{cd}/index.md  (parent={parent_title!r})")

    # ── section pages ────────────────────────────────────────────────────────
    for pd in part_dirs:
        chapter_dirs = sorted(
            d for d in os.listdir(os.path.join(ROOT, pd))
            if os.path.isdir(os.path.join(ROOT, pd, d)) and re.match(r"chapter-", d)
        )
        for cd in chapter_dirs:
            chapter_path = os.path.join(ROOT, pd, cd)
            parent_title = chapter_titles.get((pd, cd), "")
            section_files = sorted(
                f for f in os.listdir(chapter_path)
                if f.endswith(".md") and f != "index.md"
            )
            for k, sf in enumerate(section_files, 1):
                path = os.path.join(chapter_path, sf)
                # Handle subdirectories (e.g. section is a folder with index.md)
                if os.path.isdir(os.path.join(chapter_path, sf.replace(".md", ""))):
                    continue
                fm, body = read_front_matter(path)
                fm["layout"] = "default"
                fm["parent"] = parent_title
                fm["nav_order"] = str(k)
                fm.pop("has_children", None)
                write_file(path, fm, body)
                print(f"  ✅ {pd}/{cd}/{sf}")

            # Section subdirs with index.md
            section_dirs = sorted(
                d for d in os.listdir(chapter_path)
                if os.path.isdir(os.path.join(chapter_path, d))
            )
            for k, sd in enumerate(section_dirs, 1):
                idx = os.path.join(chapter_path, sd, "index.md")
                if not os.path.exists(idx):
                    idx_candidates = glob.glob(os.path.join(chapter_path, sd, "*.md"))
                    if not idx_candidates:
                        continue
                    idx = idx_candidates[0]
                fm, body = read_front_matter(idx)
                fm["layout"] = "default"
                fm["parent"] = parent_title
                fm["nav_order"] = str(k)
                write_file(idx, fm, body)
                print(f"  ✅ {pd}/{cd}/{sd}/")

    # ── appendices ───────────────────────────────────────────────────────────
    app_root = os.path.join(ROOT, "appendices")
    if os.path.isdir(app_root):
        entries = sorted(os.listdir(app_root))
        for k, entry in enumerate(entries, 1):
            entry_path = os.path.join(app_root, entry)
            if os.path.isdir(entry_path):
                candidates = glob.glob(os.path.join(entry_path, "*.md"))
                for path in candidates:
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
