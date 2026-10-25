#!/usr/bin/env python3
"""S81-PLAN3 10-25: hard_cores[].obs_max from each core's abstract (LEF OBS + PIN layers), IN PLACE.

G2 (tools/die_plan/g2.py probe_blockages) obstructs a planned hard core that declares no obs_max up to the partition
signal ceiling (M7).  That is right for an unknown core, wrong for one whose abstract leaves upper layers free: the
svc attention cores (ot_s81c_attn_hcore, dsdv_svc_sx_hrow) obstruct M1-M5 only, ROM macros M1-M4, so the parent may
route feedthrough bundles over them on M6/M7 (industry practice: the macro LEF defines the blockage).  This delta
sets obs_max = highest OBS/PIN layer of the core's LEF: the plan's own hard_cores[].lef (read from git HEAD, so a
sparse worktree works), else a copy under physical/die_plan/s81/cores (the most obstructive copy wins).  Cores with
no LEF keep no obs_max (G2 stays pessimistic, M7).  Edits only hard_cores[].obs_max.

    python3 physical/die_plan/s81/delta_obsmax_1025.py IN.json [OUT.json]
"""
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LAYER_RE = re.compile(r"LAYER\s+M(\d+)\s*;")


def top_of(txt):
    lay = [int(m) for m in LAYER_RE.findall(txt)]
    return f"M{max(lay)}" if lay else None


def lef_index():
    idx = collections.defaultdict(set)
    for p in (HERE / "cores").rglob("*.lef"):
        t = top_of(p.read_text())
        if t:
            idx[p.stem].add(t)
    return idx


_GIT = {}


def git_lef_top(rel):
    if rel not in _GIT:
        r = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{rel}"], capture_output=True, text=True)
        _GIT[rel] = top_of(r.stdout) if r.returncode == 0 else None
    return _GIT[rel]


def apply(raw):
    idx = lef_index()
    rep = collections.Counter()
    for t in raw["partition_types"].values():
        for h in t.get("hard_cores", []):
            m = h.get("module")
            own = git_lef_top(h["lef"]) if h.get("lef") else None
            tops = {own} if own else idx.get(m)
            if not tops:
                rep[(m, "no LEF: stays M7")] += 1
                continue
            top = max(tops, key=lambda s: int(s[1:]))
            if h.get("obs_max") not in (None, top):
                rep[(m, f"kept declared {h['obs_max']} (LEF {top})")] += 1
                continue
            h["obs_max"] = top
            rep[(m, top + (" (plan lef)" if own else " (cores/ copy)"))] += 1
    return rep


if __name__ == "__main__":
    src = Path(sys.argv[1])
    raw = json.loads(src.read_text())
    for (m, how), n in sorted(apply(raw).items(), key=lambda kv: -kv[1]):
        print(f"{n:5d} {m}: {how}")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src
    sys.path.insert(0, str(HERE))
    try:
        import pdump  # compact one-entry-per-line writer (S81-PLAN2)
        out.write_text(pdump.dumps(raw))
    except ImportError:
        sys.path.insert(0, "/srv/opentallas-scratch2/claude/s81-plan2")
        import pdump
        out.write_text(pdump.dumps(raw))
