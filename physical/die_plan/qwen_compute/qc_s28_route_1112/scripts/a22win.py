import sys, json
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/qc-s28-route/tools/die_plan")
import schema as S
raw = json.load(open(sys.argv[1])); P = S.Plan(raw)
res = {}
for lid in P.lanes:
    for part, slot, a, b in P.lane_crossings(lid):
        tn = P.parts[part]["type"]
        if slot != "a22" or not tn.startswith("cbx_q10"): continue
        pr = P.ports[a]; p = P.parts[part]; w, h = P.types[tn]["outline_um"]; o = p.get("orient", "R0")
        tf = P.type_face(part, P.die_face(part, "W"))
        lo, hi = sorted(pr["window_um"]); oy = p["origin_um"][1]; flip = o in ("MX", "R180")
        tw = [round(h - (hi - oy), 4), round(h - (lo - oy), 4)] if flip else [round(lo - oy, 4), round(hi - oy, 4)]
        # type-frame pin table (bit -> layer, coord)
        pins = sorted((bit, ln, round((h - (c - oy)) if flip else (c - oy), 4)) for bit, ln, c in P.port_pins(a))
        order = "lsb_low" if pins[0][2] < pins[-1][2] else "lsb_high"
        key = (tuple(tw), tuple(pr["layers"]), order, P.die_face(part, "W"), pr["face"])
        res.setdefault(tn, {}).setdefault(key, []).append((part, o, lid))
for tn, d in sorted(res.items()):
    for k, v in d.items():
        print(tn, k, len(v), v[:2])
