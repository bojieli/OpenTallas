#!/usr/bin/env python3
"""Build a concise handoff from the maintained current status and recent milestones.
Historical lane journals remain in coord/lanes rather than being copied here.
Used by claude-autocontinue.py at each Claude->Codex handoff; also runnable by hand.
"""
import os, re, subprocess, sys, datetime as dt
from zoneinfo import ZoneInfo

COORD = os.path.expanduser("~/coord")
OUT = os.path.join(COORD, "CODEX-HANDOFF.md")
STATUS = os.path.join(COORD, "CODEX-HANDOFF-STATUS.md")
KEEP = re.compile(r"^#+\s*(current step|status|next|owner\?|state|geom-review findings|codex notes|blocked|open)", re.I)
SKIP_LANES = {"CODEX.md", "TOPDOWN-PLAN.md", "COORD-REVIEW-QUEUE.md"}


def sh(cmd):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return f"({e})"


def lane_snapshot(path, max_lines=30):
    lines = open(path, errors="replace").read().splitlines()
    head = [l for l in lines[:4] if l.strip() and not l.startswith("# ")][:2]   # branch / worktree line
    out, take = [], False
    for l in lines:
        if l.startswith("#"):
            take = bool(KEEP.match(l))
            if take:
                out.append(l)
            continue
        if take:
            out.append(l)
    if not out:                                          # no recognised sections: the last lines of the file
        out = lines[-max_lines:]
    if len(out) > max_lines:
        out = out[:max_lines] + [f"... ({len(out) - max_lines} more lines in the lane file)"]
    return head, out


def main(reason=""):
    now = dt.datetime.now(ZoneInfo("America/Los_Angeles"))
    parts = [f"# Codex handoff document (generated {now:%Y-%m-%d %H:%M %Z})", ""]
    if reason:
        parts += [reason, ""]
    parts += ["Read ~/coord/CODEX-ROLE.md first: your role, the binding rules, and how to cover every task.", ""]
    parts += [open(STATUS).read().rstrip(), ""] if os.path.exists(STATUS) else ["(status narrative missing)", ""]

    # Keep the handoff actionable. Historical lane journals are linked rather
    # than copied: hundreds of old lanes previously expanded this to megabytes.
    parts += ["## Latest handoff milestones", "",
              sh("tail -n 8 ~/coord/HANDOFF.md | cut -c1-300"), "",
              "For live jobs and new results, read the active lane files and "
              "lanes/COORD-REVIEW-QUEUE.md on intel2. Historical lane contents "
              "are intentionally omitted from this handoff.", ""]

    with open(OUT, "w") as fh:
        fh.write("\n".join(parts) + "\n")
    return OUT


if __name__ == "__main__":
    print(main(" ".join(sys.argv[1:])))
