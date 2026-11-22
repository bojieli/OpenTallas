#!/usr/bin/env python3
"""utf8_guard.py: refuse invalid UTF-8 in coord text (FLOW-FLEET-R2 S1, FABLE-FLOW-0350).  A stray 0x94 byte in lanes/posts/COORD.md made every
autopilot tick skip hold recompile, tree switch, UNBLOCK and LOOP-GAPS for about 1 h.
  utf8_guard.py --text              < stdin : the post text must decode as UTF-8
  utf8_guard.py --files REPO f ...  : the lines a commit would ADD to each named text file (diff vs HEAD; whole file when untracked) must decode
Exit 0 ok, 1 refused (message on stderr naming the file, line and byte), 2 usage.  Env COORD_UTF8_GUARD=off skips (emergency).  Stdlib only."""
import os
import subprocess
import sys

TEXT_EXT = (".md", ".tsv", ".txt", ".json", ".csv", ".log", ".sh", ".py", ".yaml", ".yml", ".conf", ".cfg", ".tcl", ".sv", ".v")


def bad_in(data, label):
    try:
        data.decode("utf-8")
        return ""
    except UnicodeDecodeError as e:
        line = data.count(b"\n", 0, e.start) + 1
        ctx = data[max(0, e.start - 20):e.start + 20].decode("utf-8", errors="replace").replace("\n", " ")
        return f"REFUSED invalid UTF-8 in {label}: byte {data[e.start]:#04x} at line {line} (near: {ctx!r}). Replace it with plain ASCII and retry."


def check_files(repo, files):
    errs = []
    for f in files:
        if not f.lower().endswith(TEXT_EXT):
            continue
        p = os.path.join(repo, f)
        tracked = subprocess.run(["git", "-C", repo, "ls-files", "--error-unmatch", "--", f], capture_output=True).returncode == 0
        if tracked:
            d = subprocess.run(["git", "-C", repo, "diff", "HEAD", "--no-color", "--no-ext-diff", "-U0", "--", f], capture_output=True).stdout
            added = b"\n".join(l[1:] for l in d.split(b"\n") if l.startswith(b"+") and not l.startswith(b"+++"))
        else:
            try:
                added = open(p, "rb").read()
            except OSError:
                continue
        m = bad_in(added, f)
        if m:
            errs.append(m)
    return errs


def main(argv):
    if os.environ.get("COORD_UTF8_GUARD") == "off":
        return 0
    if argv[:1] == ["--text"]:
        m = bad_in(sys.stdin.buffer.read(), "the post text")
    elif argv[:1] == ["--files"] and len(argv) >= 2:
        m = "\n".join(check_files(argv[1], argv[2:]))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    if m:
        print(m, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
