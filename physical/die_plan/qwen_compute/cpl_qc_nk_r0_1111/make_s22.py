"""CPL-QC-NK-R0 11-11 (S2, COORD 17:1x ruling): plan_qc99_s22_nkr0 = plan_qc99_s21_nkout + right-column NK/NL tiles
turned MY -> R0, so their data pins (n_a/n_b/n_y/t_out, core W edge) face the middle channel.

Selection (intent sheet, xscore.py on the bound s21 RTL): a right-column MY tile is ELIGIBLE when no type face bus
(buses[].leaf) lands on it (flipping such a tile turns its face bus away from the face: G0C core_faces, 16 WARNs in
the all-right-column trial); per type the eligible subset with the fewest double macro crossings, then the fewest
crossings, is taken only when it strictly improves.  cbf_q00_s2 (would add 2 crossings) and cbf_q01 (no eligible
tile: t12 carries y_o12 / nb_i12, t13 is already R0) stay unchanged.

Per flipped tile only: hard_cores[].orient MY -> R0 (same origin: R0 and MY fill the same box) and the matching core
clock tap clock.taps[<inst>.ck] (xy = the R0 ck pin centre, orient R0).  Nothing else: no partition / lane / bus /
latency / reset field, no core_out_land_types change (14 types kept).  Pin tracks: every NK/NL pin is M4 (horizontal)
at core x 0.096 or 457.824, so an x mirror (MY <-> R0) leaves every pin y, the only track coordinate, unchanged.
usage: make_s22.py S21.json S22.json DELTA.json"""
import hashlib, json, sys
src, dst, dpath = sys.argv[1:4]
raw = open(src, "rb").read()
assert hashlib.sha256(raw).hexdigest().startswith("cce5cf63a7bd"), "base must be plan_qc99_s21_nkout"
p = json.loads(raw)
assert json.dumps(p, indent=1).encode() == raw
CK = (457.824, 668.076)          # cores/a0_nk_pins.json and a0_nl_pins.json: ck pin centre, core R0 frame
W = 457.92
SEL = {"cbn_q11__cl49ae4555": ["u_t32", "u_t33"], "cbn_q11__cl5cc92dfe": ["u_t32", "u_t33"], "cbf_q11": ["u_t32", "u_t33"],
       "cbx_q10__cl89936551": ["u_t30", "u_t31"], "cbx_q10__cl94a12200": ["u_t30", "u_t31"],
       "cbf_q00__cl1b5a6458": ["u_t10"], "cbf_q00__cl870de686": ["u_t10"], "cbn_q00__cld7bf7197": ["u_t10"],
       "cbn_q00__cl622f65d2": ["u_t10"], "cbn_q00__cldbcda913": ["u_t10"],
       "cbn_q01__clab6e67f2": ["u_t13"], "cbn_q01__cld9ff4c40": ["u_t13"], "cbn_q01__cldd6ea846": ["u_t13"],
       "cbf_q01_s2": ["u_t13"]}
delta = []
for tn, t in sorted(p["partition_types"].items()):
    hcs = t.get("hard_cores") or []
    if not any(h["module"] == "qfd_tile_nk_a0c" for h in hcs):
        continue
    xs = sorted({h["origin_um"][0] for h in hcs if h["module"] in ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c")})
    assert len(xs) == 2, (tn, xs)
    busleaf = {b["leaf"].split(".")[0] for b in t["buses"]}
    for h in hcs:
        if h["inst"] not in SEL.get(tn, ()):
            continue
        assert h["module"] in ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c") and h["origin_um"][0] == xs[1] and h["orient"] == "MY" \
            and h["inst"] not in busleaf, (tn, h["inst"])
        ox, oy = h["origin_um"]; dx, dy = h["track_offset_um"]
        h["orient"] = "R0"
        taps = [tp for tp in t["clock"]["taps"] if tp["name"] == h["inst"] + ".ck"]
        assert len(taps) == 1, (tn, h["inst"])
        tp = taps[0]
        was = dict(xy=tp["xy"], orient=tp.get("orient"))
        tp["xy"] = [round(ox + dx + CK[0], 4), round(oy + dy + CK[1], 4)]
        tp["orient"] = "R0"
        delta.append(dict(type=tn, inst=h["inst"], module=h["module"], origin_um=h["origin_um"], orient=["MY", "R0"],
                          ck_tap=dict(name=tp["name"], was=was, now=dict(xy=tp["xy"], orient="R0"),
                                      my_pin_xy=[round(ox + dx + W - CK[0], 4), round(oy + dy + CK[1], 4)])))
assert sorted((d["type"], d["inst"]) for d in delta) == sorted((t, i) for t, l in SEL.items() for i in l)
p["note"] = p["note"] + (" | s22_nkr0 (CPL-QC-NK-R0 11-11, S2): s21_nkout + %d right-column NK/NL tiles in %d types MY -> R0 "
                         "(data pins face the middle channel, no face-bus tile flipped; core ck taps follow the R0 ck pin)"
                         % (len(delta), len({d["type"] for d in delta})))
out = json.dumps(p, indent=1)
open(dst, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base="plan_qc99_s21_nkout.json", base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha,
               rule="selected right-column MY NK/NL tiles without a type face bus -> R0 (fewest double, then total, macro crossings of the RTL NK links); core ck tap to the R0 pin",
               edits=delta), open(dpath, "w"), indent=1)
print("flipped", len(delta), "tiles in", len({d["type"] for d in delta}), "types; sha256", sha)
for d in delta:
    print(" ", d["type"], d["inst"], d["module"], d["origin_um"], "ck tap", d["ck_tap"]["was"]["xy"], "->", d["ck_tap"]["now"]["xy"],
          "" if d["ck_tap"]["was"]["xy"] == d["ck_tap"]["my_pin_xy"] else "(old tap xy was stale vs the MY pin %s)" % d["ck_tap"]["my_pin_xy"])
