#!/usr/bin/env python3
"""tap_window_floor.py IN OUT [--floor 10] : class fix for 0-ps kit contract windows (HEAD-95, COORD 07:4x (3)).
clock.tap_window.per_port_ps was written by DIE-HEAD-68 l48ue as the RAW measured need (ceil 1 ps) with no margin, so a
port whose need was 0 on the old clock got W = 0 (a missing margin, not a design limit).  The HEAD-93/94 rule for
per-port windows is need + 10 ps capped by per_type_ps; this floors every per_port entry at the margin (10 ps), never
above its type's per_type_ps, and prints every change (each changed type's kit SDC changes -> re-sign)."""
import json, sys
a = sys.argv[1:]; fl = float(a[a.index("--floor") + 1]) if "--floor" in a else 10.0
P = json.load(open(a[0])); tw = P["clock"]["tap_window"]; pt = tw.get("per_type_ps", {}); ch = []
for tn, ports in (tw.get("per_port_ps") or {}).items():
    cap = pt.get(tn, 208.0)
    for p, w in ports.items():
        nw = min(max(w, fl), cap)
        if nw != w: ports[p] = nw; ch.append((tn, p, w, nw))
tw["per_port_note"] = tw.get("per_port_note", "") + (f" | HEAD-95 11-12: per_port floor {fl:g} ps (the +10 margin of the"
    " need+10 rule; l48ue wrote raw needs, 0-ps ports were a missing margin), capped by per_type_ps")
json.dump(P, open(a[1], "w"), indent=1)
for c in ch: print("W %s.%s %g -> %g" % c)
print("changed", len(ch), "types", sorted({c[0] for c in ch}))
