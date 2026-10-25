#!/usr/bin/env python3
"""Build ~/coord/CODEX-HANDOFF.md: the coordinator's status narrative + a live snapshot of every lane, the open
release-tree items, fleet load and recent milestones. Used by claude-autocontinue.py at each Claude->Codex handoff;
can also be run by hand."""
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

    parts += ["## Live snapshot", "",
              "### main", "```", sh("git -C ~/OpenTallas fetch -q origin 2>/dev/null; git -C ~/OpenTallas log --format='%h %ci %s' -12 origin/main | cut -c1-160"), "```", "",
              "### Fleet", "```", sh("ssh -o ConnectTimeout=10 epyc1 ~/.local/bin/ot-run --status 2>&1 | head -5"), "```", "",
              "### Open release-tree items (~/coord/RELEASE_TREE.md)", "```",
              sh("grep -E '^\\s*- \\[ \\]' ~/coord/RELEASE_TREE.md | cut -c1-220"), "```", ""]

    parts += ["### Lanes (current step / status / next / OWNER? / review findings from each lane file)", ""]
    lanes = sorted(f for f in os.listdir(os.path.join(COORD, "lanes")) if f.endswith(".md") and f not in SKIP_LANES)
    for f in lanes:
        p = os.path.join(COORD, "lanes", f)
        mt = dt.datetime.fromtimestamp(os.path.getmtime(p), ZoneInfo("America/Los_Angeles"))
        head, body = lane_snapshot(p)
        parts += [f"#### {f[:-3]} (lane file updated {mt:%m-%d %H:%M})"] + head + [""] + body + [""]

    parts += ["### Last 60 milestones (~/coord/HANDOFF.md)", "```", sh("tail -n 60 ~/coord/HANDOFF.md | cut -c1-300"), "```", ""]
    with open(OUT, "w") as fh:
        fh.write("\n".join(parts) + "\n")
    return OUT


if __name__ == "__main__":
    print(main(" ".join(sys.argv[1:])))
