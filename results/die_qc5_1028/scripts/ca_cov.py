#!/usr/bin/env python3
"""DIE-QC-5: landed partition pairs (main build_pairs) vs count-align bind tags.  usage: ca_cov.py TOOLS PROOF PLAN BIND"""
import sys, json
sys.path.insert(0, sys.argv[1])
import die_sta_related as R
from pathlib import Path
meta, taps = R.load_taps(Path(sys.argv[2]), "TT")
plan = json.loads(Path(sys.argv[3]).read_text())
pairs, _ = R.build_pairs(plan, taps)
bind = json.loads(Path(sys.argv[4]).read_text())
bt = {f"{b['src']}->{b['dst']}" for b in bind["ports"].values()}
lt = {}
for a, b, tag in pairs["landed"]:
    lt[tag] = lt.get(tag, 0) + 1
miss = sorted(t for t in lt if t not in bt)
print("landed tags", len(lt), "landed tap pairs", sum(lt.values()), "bind tags", len(bt), "bind ports", len(bind["ports"]),
      "landed tags NOT in bind", len(miss), "tap pairs", sum(lt[t] for t in miss))
print(miss[:20])
print("bind tags not landed", sorted(bt - set(lt))[:10])
