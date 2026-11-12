#!/usr/bin/env python3
"""svc_hrow_conns.py PLAN CORE_CONNS_IN OUT [--types RE]

VL3-S81-SVCSTN (COORD 11-12 00:59 (3)): route_supply core_conns for the svc_rs hrow lanes at their REAL bus windows.
dsdv_svc_sx (rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx.sv): each hrow's face-f lanes (gi_f/si_f in, go_f/so_f out) go
through the relay stations A/B/C to the slice face-f lane ports (gi_d/go_d/si_d/so_d), which are the type's score
exchange buses on face f (attn* / attnh* windows).  The old entry 'face:F' made route_supply draw all of them to the
MIDDLE of face F.  New entry: 'bus:<window>' of the same direction on that face; with several such windows the 8 hrows
are dealt round-robin (route_supply ranks the bits along the window).  A face with no exchange bus of that direction
gets 'glue' (a FM_* = 0 face: the RTL ties the lanes off; a local stub, no route).  All other entries unchanged."""
import argparse, json, re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("conns"); ap.add_argument("out")
    ap.add_argument("--types", default=r"^svc_(hi|lo)_dsdv_svc_rs(_w)?__t\d+$")
    a = ap.parse_args()
    P = json.load(open(a.plan))["partition_types"]; C = json.load(open(a.conns)); rx = re.compile(a.types)
    out = {}; stats = {}
    for tn, t in P.items():
        if not rx.search(tn) or tn not in C:
            continue
        ex = {}
        for b in t.get("buses") or []:
            n = b.get("name", "")
            if re.match(r"attnh?_[io]\d+$", n):
                ex.setdefault((b["face"], "in" if "_i" in n else "out"), []).append(n)
        ent = json.loads(json.dumps(C[tn])); k = 0; ch = 0
        hrows = sorted(i for i in ent if i.endswith("u_hrow"))
        for j, inst in enumerate(hrows):
            for pb, dl in ent[inst].items():
                m = re.match(r"([gs])([io])_([nesw])$", pb)
                if not m or dl != ["face:" + m.group(3).upper()]:
                    continue
                F = m.group(3).upper(); d = "in" if m.group(2) == "i" else "out"
                cand = sorted(ex.get((F, d), []))
                if cand:
                    ent[inst][pb] = ["bus:" + cand[j % len(cand)]]; ch += 1
                else:
                    ent[inst][pb] = ["glue"]          # FM_* = 0 face: tied 0 / unused in the RTL, a local stub only
                k += 1
        out[tn] = ent; stats[tn] = (ch, k, {"%s_%s" % f: v for f, v in ex.items()})
        print(tn, "hrow lane entries -> bus", ch, "of", k, stats[tn][2])
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
