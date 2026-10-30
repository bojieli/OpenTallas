#!/usr/bin/env python3
"""S81 gunit pin event (DIE-S81-33/GUNIT, 2026-10-29; COORD 21:4x from GEOM-68 19:51 / 20:30 and GEOM-69 19:53).

Fix-only plan pin delta on frozen plan_s13r2 in the PINEV (delta_pinev_1029.py) / ve_s (delta_ves_clkc_1029.py) form:
only the cores' OWN plan pin tables (inputs/core_pins/<module>.json), their plan-owned LEFs and the type-frame xy of
their early core taps change.  No outline, origin, orient, face, layer, slot set, partition, neighbour, RTL or cycle
changes.

(a) PIN ORDER, dsdv_gunit_l0 / dsdv_gunit_l1 (GEOM-68 19:51 FAIL STRUCTURAL: 206 / 177 captures > 405 um).  Every
    register-to-register relay of the core (RTL, CHECKED: dsdv_gunit_pass u_up rs_i[k]->rn_o[k], u_dn rn_i[k]->rs_o[k],
    u_sid / u_ct; cw_d[k]->cwo_d[k] / bw_d[k] via wd; l0 hp_b[52+i]->wr_bd[i], hp_a[52+i]->wr_ad[i] via ab/bb,
    r_d[k]->g_d[k] via rd_q; l1 dl_a[13+i]->sa_d[i], dl_b[13+i]->sb_d[i] via ab/bb (unpack {dl[236:13],2'b0,dl[12:3],
    36'b0,dl[2:0],1'b0}), w_b[k]->ct_b[k] via wb3 (ctlpk(ctlup(p)) == p), gs_d[k]->rw_x[k] via gd) is an ITEM.  Per
    core and face, the slots of all items on that face form one pool (same face, same layer, same coordinates; every
    other pin keeps its slot).  Items are re-assigned to pool slots by a bottleneck matching (exact interval greedy per
    face, alternated over the faces, deterministic) that minimises the worst of: in-pin -> out-pin (the in-core hop:
    input flop at its pin, output flop at its pin) and core pin -> die partner pin (the gunit hard-core partner in the
    placed frame, honouring MX / MY; soft partners L1f are unconstrained).  The die hops are not allowed to grow.
    The plan LEF PIN PORT geometry moves with the slot (each PIN keeps its name and direction).
    dsdv_gunit_l1's plan LEF moves to a plan-owned copy cores/legacy/lef/dsdv_gunit_l1.lef (PINEV form; the ref_tile
    view is closed), the hard_cores lef path is swapped textually in plan_s13r2.json and die_plan.json.
(b) CLOCK ENTRY (GEOM-21 rect 0.048 x 0.48 on M5, centre on the M5 track x = 0.012 + 0.048 k, y on the 0.048 grid):
      dsdv_gunit_l4  W edge (0.06, 35.292)  -> face C centre (172.812, 32.412)   [GEOM-68 20:30 FAIL-PLAN reach 370]
      dsdv_gunit_l0  W edge (0.06, 94.62)   -> face C centre (172.812, 86.412)   [GEOM-68 19:51 fix (3)]
      dsdv_gunit_l1  W edge M4 (0.042, 100.572) -> face C centre (172.812, 108.012)  [GEOM-68 19:51 fix (3)]
      dsdv_gunit_l1c E edge (86.364, 184.284) -> E edge mid (86.364, 108.012), 0.072 x 0.48 [GEOM-69 19:53 reach 185]
    For the face-C pins the plan LEF M4/M5 OBS is clipped out of a 4.32 x 4.32 ck_entry island around the pin (the
    ve_s form; obs_max M5, so the parent drops M6 -> M5 onto the pin).  l0 / l1 / l4 are EARLY die taps
    (gunit__t1.clock.taps kind core): their type-frame xy moves with the pin (origin + orient(pin) + track_offset,
    the rule the existing rows follow, CHECKED on the old rows), so ot_clk regenerates t_gunit__clk_c1/c2/c4.
    insertion_ps budgets are left as declared (the rebuilt kits re-measure them).  The GEOM-68 l4 in-core islands
    (x ~86 / ~259) have no plan field for hard cores (clock.mesh.core_islands is the 12.2a1 die-mesh pushdown, absent
    on S81): they are a KIT-side CTS contract, recorded in delta_gunit_pins_1029.json, not a plan field.

Every edit asserts the exact old form (pinhash, clk rows, tap xy); a second run refuses.
usage: python3 delta_gunit_pins_1029.py [--dry]
"""
import bisect
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

S81 = Path(__file__).resolve().parent
REPO = S81.parents[2]
RTL = REPO / "rtl/dsrom_sys/s81_dv/unit/dsdv_gunit.sv"
PLAN = S81 / "plan_s13r2.json"
PLANS = ("plan_s13r2.json", "die_plan.json")
TAG = "S81 gunit pin event DIE-S81-33/GUNIT 2026-10-29 (delta_gunit_pins_1029.py)"
OLDHASH = {"dsdv_gunit_l0": "d085db527da9", "dsdv_gunit_l1": "d27497b5bc30", "dsdv_gunit_l4": "405b4ff105a8",
           "dsdv_gunit_l1c": "a3f9c3b6c155"}
L1_REF = "physical/ref_tile/dsdv_gunit_l1/views/dsdv_gunit_l1/dsdv_gunit_l1.lef"
L1_OWN = "physical/die_plan/s81/cores/legacy/lef/dsdv_gunit_l1.lef"
ISL = 2.16                                  # island half-size (4.32 x 4.32, the ve_s ck_entry form)
# module: (old (layer, x, y), old LEF PORT body, new (x, y), new M5 rect, face-C island?, tap inst or None)
CLOCKS = {
    "dsdv_gunit_l4": (("M5", 0.06, 35.292), "      LAYER M5 ;\n        RECT 0.000 35.052 0.120 35.532 ;\n",
                      (172.812, 32.412), (172.788, 32.172, 172.836, 32.652), True, "u_gunit.u_l4.clk"),
    "dsdv_gunit_l0": (("M5", 0.06, 94.62), "      LAYER M5 ;\n        RECT 0.000 94.380 0.120 94.860 ;\n",
                      (172.812, 86.412), (172.788, 86.172, 172.836, 86.652), True, "u_gunit.u_l0.clk"),
    "dsdv_gunit_l1": (("M4", 0.042, 100.572), "      LAYER M4 ;\n        RECT  0 100.56 0.084 100.584 ;\n",
                      (172.812, 108.012), (172.788, 107.772, 172.836, 108.252), True, "u_gunit.u_l1.clk"),
    "dsdv_gunit_l1c": (("M5", 86.364, 184.284), "      LAYER M5 ;\n        RECT 86.328 184.044 86.400 184.524 ;\n",
                       (86.364, 108.012), (86.328, 107.772, 86.4, 108.252), False, None),
}
OLD_TAPS = {"u_gunit.u_l4.clk": [1270.23, 366.504], "u_gunit.u_l0.clk": [1270.23, 501.576],
            "u_gunit.u_l1.clk": [1114.65, 480.744]}
PAIRS = {
    "u_l0": [("rs_i", "rn_o", 0), ("rn_i", "rs_o", 0), ("sid_i", "sid_o", 0), ("cw_d", "cwo_d", 0), ("cw_a", "cwo_a", 0),
             ("hct4_b", "hct_b", 0), ("hp_b", "wr_bd", 52), ("hp_a", "wr_ad", 52), ("r_d", "g_d", 0)],
    "u_l1": [("rs_i", "rn_o", 0), ("rn_i", "rs_o", 0), ("sid_i", "sid_o", 0), ("dl_a", "sa_d", 13), ("dl_b", "sb_d", 13),
             ("cw_d", "bw_d", 0), ("w_b", "ct_b", 0), ("gs_d", "rw_x", 0)],
}
MOD = {"u_l0": "dsdv_gunit_l0", "u_l1": "dsdv_gunit_l1"}


# ------------------------------------------------------------------ geometry / connectivity
def load():
    d = json.load(open(PLAN)); pt = d["partition_types"]["gunit__t1"]
    cores = {c["inst"].split(".")[-1]: c for c in pt["hard_cores"]}
    src = re.sub(r"//[^\n]*", "", RTL.read_text())
    conn = collections.defaultdict(list)
    for inst in cores:
        m = re.search(r"\b" + inst + r"\s*\((.*?)\);", src, re.S)
        for pm in re.finditer(r"\.(\w+)\s*\(\s*([A-Za-z_]\w*)\s*\)", m.group(1)):
            conn[pm.group(2)].append((inst, pm.group(1)))
    tabs = {}
    for i, c in cores.items():
        r = {}
        for p in json.load(open(S81 / c["pins_file"]))["pins"]:
            m = re.match(r"^(\w+)(?:\[(\d+)\])?$", p["name"])
            r[(m.group(1), int(m.group(2)) if m.group(2) else None)] = (p["x"], p["y"], p["layer"])
        tabs[i] = r
    return d, cores, conn, tabs


def orient(c, xy):
    w, h = c["outline_um"]; x, y = xy
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[c["orient"]]


def todie(c, xy):
    x, y = orient(c, xy); o = c["origin_um"]
    return (o[0] + x, o[1] + y)


def tocore(c, XY):
    o = c["origin_um"]
    return orient(c, (XY[0] - o[0], XY[1] - o[1]))        # every orient used here is an involution


def partner(conn, inst, port):
    for ends in conn.values():
        if (inst, port) in ends:
            return [e for e in ends if e != (inst, port)][0] if len(ends) == 2 else None
    return None


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def face_of(xy, W, H):
    x, y = xy[:2]
    return "W" if x < 0.2 else "E" if x > W - 0.2 else "S" if y < 0.6 else "N" if y > H - 0.6 else "C"


def assign(items, slots, cons, D):
    """exact bottleneck feasibility on one face: item i may take slot s iff md(s, q) <= D for every q in cons[i]."""
    k = 1 if len({s[0] for s in slots}) == 1 else 0
    ss = sorted(slots, key=lambda s: (s[k], s[1 - k])); us = [s[k] for s in ss]; fix = ss[0][1 - k]
    iv = []
    for i in items:
        lo, hi = -1e9, 1e9
        for q in cons[i]:
            r = D - abs(fix - q[1 - k])
            if r < 0:
                return None
            lo, hi = max(lo, q[k] - r), min(hi, q[k] + r)
        if lo > hi + 1e-9:
            return None
        iv.append((hi, lo, i))
    iv.sort()
    nxt = list(range(len(ss) + 1)); out = {}
    def find(j):
        while nxt[j] != j:
            nxt[j] = nxt[nxt[j]]; j = nxt[j]
        return j
    for hi, lo, i in iv:
        j = find(bisect.bisect_left(us, lo - 1e-9))
        if j >= len(ss) or us[j] > hi + 1e-9:
            return None
        out[i] = ss[j]; nxt[j] = j + 1
    return out


def best(items, slots, cons):
    lo, hi = 0.0, 4000.0
    while hi - lo > 0.01:
        m = (lo + hi) / 2
        lo, hi = (lo, m) if assign(items, slots, cons, m) is not None else (m, hi)
    return assign(items, slots, cons, hi)


def optimise(cores, conn, tabs, inst, rounds=8):
    c = cores[inst]; T = tabs[inst]; W, H = c["outline_um"]
    pos0 = {}; mate = {}; part = {}
    for pin, pout, off in PAIRS[inst]:
        pi, po = partner(conn, inst, pin), partner(conn, inst, pout)
        for (n, b) in T:
            if n != pout:
                continue
            i, o = (pin, b + off), (pout, b)
            assert i in T and o not in mate and i not in mate, (inst, i, o)
            pos0[i] = T[i][:2]; pos0[o] = T[o][:2]; mate[i] = o; mate[o] = i
            if pi: part[i] = tocore(c, todie(cores[pi[0]], tabs[pi[0]][(pi[1], b + off)][:2]))
            if po: part[o] = tocore(c, todie(cores[po[0]], tabs[po[0]][(po[1], b)][:2]))
    faces = collections.defaultdict(list)
    for it in sorted(pos0):
        faces[face_of(pos0[it], W, H)].append(it)
    assert "C" not in faces and "W" not in faces, sorted(faces)
    for f, its in faces.items():
        assert len({T[i][2] for i in its}) == 1, (inst, f, "mixed layers")
    pos = dict(pos0)
    for _ in range(rounds):
        for f in sorted(faces):
            its = faces[f]
            a = best(its, [pos0[i] for i in its], {i: [pos[mate[i]]] + ([part[i]] if i in part else []) for i in its})
            pos.update(a)
    def score(p):
        return (round(max(md(p[i], p[mate[i]]) for i in p), 3), round(max(md(p[i], part[i]) for i in part), 3))
    b, a = score(pos0), score(pos)
    assert a[0] < b[0] and a[1] <= b[1] + 1e-9, (inst, b, a)
    per = collections.defaultdict(lambda: [0.0, 0.0])
    for pin, pout, off in PAIRS[inst]:
        for (n, bb) in T:
            if n == pout:
                k = f"{pin}->{pout}"; i, o = (pin, bb + off), (pout, bb)
                per[k][0] = max(per[k][0], md(pos0[i], pos0[o])); per[k][1] = max(per[k][1], md(pos[i], pos[o]))
    return pos0, pos, dict(before=b, after=a, items=len(pos), per={k: [round(v[0], 2), round(v[1], 2)] for k, v in per.items()})


# ------------------------------------------------------------------ file edits
def pname(it):
    return it[0] if it[1] is None else f"{it[0]}[{it[1]}]"


def lef_pins(txt):
    """{pin name: (start, end) of its PORT body text}"""
    out = {}
    for m in re.finditer(r"^  PIN (\S+)\n(.*?)^  END \1\n", txt, re.S | re.M):
        body = m.group(2); a = body.index("    PORT\n") + len("    PORT\n"); e = body.rindex("    END\n")
        out[m.group(1)] = (m.start(2) + a, m.start(2) + e)
    return out


def edit_lef_order(txt, moves):
    """moves: {pin name: pin name whose old PORT body it takes}"""
    sp = lef_pins(txt); bodies = {n: txt[a:e] for n, (a, e) in sp.items()}
    parts = []; last = 0
    for n, (a, e) in sorted(sp.items(), key=lambda t: t[1][0]):
        if n in moves:
            parts.append(txt[last:a]); parts.append(bodies[moves[n]]); last = e
    parts.append(txt[last:])
    return "".join(parts)


def clip_obs(txt, layer, isl):
    """remove the island rect from every OBS RECT on layer (rect subtraction, up to 4 pieces)."""
    o0 = txt.index("\n  OBS\n"); o1 = txt.index("\n  END\n", o0)
    obs = txt[o0:o1].split("\n"); out = []; cur = None; cut = 0
    x0, y0, x1, y1 = isl
    for ln in obs:
        s = ln.strip()
        if s.startswith("LAYER "):
            cur = s.split()[1]
        if cur == layer and s.startswith("RECT "):
            a, b, c, d = (float(v) for v in s.split()[1:5])
            if a < x1 and c > x0 and b < y1 and d > y0:
                cut += 1
                for r in ((a, b, c, y0), (a, y1, c, d), (a, max(b, y0), x0, min(d, y1)), (x1, max(b, y0), c, min(d, y1))):
                    if r[2] - r[0] > 1e-6 and r[3] - r[1] > 1e-6:
                        out.append("     RECT  %.3f %.3f %.3f %.3f ;" % r)
                continue
        out.append(ln)
    return txt[:o0] + "\n".join(out) + txt[o1:], cut


def main():
    dry = "--dry" in sys.argv
    plan, cores, conn, tabs = load()
    rec = dict(tag=TAG, order={}, clocks={}, taps={})
    pins_txt = {}; pins = {}
    for m in CLOCKS:
        p = S81 / "inputs/core_pins" / f"{m}.json"; t = p.read_text(); d = json.loads(t)
        if d["pinhash"] != OLDHASH[m] or json.dumps(d, indent=0) != t:
            raise SystemExit(f"{m}: pin table not in the expected old form (pinhash {d['pinhash']}; second run refused)")
        pins_txt[m] = t; pins[m] = d
    # (a) pin order
    lefs = {}
    for inst, m in MOD.items():
        pos0, pos, st = optimise(cores, conn, tabs, inst)
        rec["order"][m] = st
        slot_owner = {tuple(v): k for k, v in pos0.items()}
        by = {pp["name"]: pp for pp in pins[m]["pins"]}
        moves = {}
        for it, xy in pos.items():
            q = by[pname(it)]; src = slot_owner[tuple(xy)]
            assert q["layer"] == by[pname(src)]["layer"]
            q["x"], q["y"] = xy
            if src != it:
                moves[pname(it)] = pname(src)
        rec["order"][m]["moved_pins"] = len(moves)
        lp = REPO / (L1_REF if m == "dsdv_gunit_l1" else f"physical/die_plan/s81/cores/legacy/lef/{m}.lef")
        lefs[m] = edit_lef_order(lp.read_text(), moves)
    # (b) clocks
    for m, (old, oldport, new, rect, island, tap) in CLOCKS.items():
        q = [pp for pp in pins[m]["pins"] if pp["name"] == "clk"]
        assert len(q) == 1 and (q[0]["layer"], q[0]["x"], q[0]["y"]) == old, (m, q)
        k = (new[0] - 0.012) / 0.048; assert abs(k - round(k)) < 1e-6, (m, "off M5 track")
        q[0].update(layer="M5", x=new[0], y=new[1])
        if m not in lefs:
            lefs[m] = (S81 / f"cores/legacy/lef/{m}.lef").read_text()
        lt = lefs[m]
        blk = f"  PIN clk\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n{oldport}    END\n  END clk\n"
        assert lt.count(blk) == 1, (m, "clk PORT not in the expected form")
        lt = lt.replace(blk, blk.replace(oldport, "      LAYER M5 ;\n        RECT %.3f %.3f %.3f %.3f ;\n" % rect))
        cuts = {}
        if island:
            isl = (new[0] - ISL, new[1] - ISL, new[0] + ISL, new[1] + ISL)
            for lay in ("M4", "M5"):
                lt, cuts[lay] = clip_obs(lt, lay, isl)
        lefs[m] = lt
        rec["clocks"][m] = dict(old=old, new=["M5", *new], rect=rect, island=island and [round(v, 3) for v in isl],
                                obs_rects_clipped=cuts)
        if tap:
            c = cores[tap.split(".")[1]]; to = c["track_offset_um"]
            x, y = todie(c, new); xy = [round(x + to[0], 3), round(y + to[1], 3)]
            # the rows were written from the pre-PINEV M4 pin (x 0.042); PINEV moved l0/l4 to x 0.06 without the tap
            ox, oy = todie(c, (0.042, old[2])); assert [round(ox + to[0], 3), round(oy + to[1], 3)] == OLD_TAPS[tap], (tap, "tap rule")
            rec["taps"][tap] = dict(old=OLD_TAPS[tap], new=xy, moved_um=round(md(OLD_TAPS[tap], xy), 3))
    rec["l4_incore_islands_kit_contract"] = dict(
        note="GEOM-68 20:30: 2 pre-placed in-core clock islands (ve_s ce27m form) for dsdv_gunit_l4 12,098 sinks; "
             "no plan field for hard cores -> kit CTS contract only", centres_um=[[86.4, 32.4], [259.2, 32.4]])
    # write pin tables
    for m, d in pins.items():
        d["source"] += f"; {TAG}: " + ("relay pin order (pooled per face, bottleneck) + " if m in ("dsdv_gunit_l0", "dsdv_gunit_l1") else "") + \
                       "clk %s(%g,%g) -> M5(%g,%g)" % (*CLOCKS[m][0], *CLOCKS[m][2])
        if m == "dsdv_gunit_l1":
            assert d["lef"] == L1_REF; d["lef"] = L1_OWN
        d["pinhash"] = hashlib.sha256(json.dumps(d["pins"], sort_keys=True).encode()).hexdigest()[:12]
        rec.setdefault("pinhash", {})[m] = [OLDHASH[m], d["pinhash"]]
    # plan: tap xy (plan_s13r2 only; die_plan.json has no gunit taps) + l1 lef path (both)
    ptxt = {f: (S81 / f).read_text() for f in PLANS}
    for f in PLANS:
        assert ptxt[f].count(f'"lef":"{L1_REF}"') == 1, (f, "l1 lef row")
        ptxt[f] = ptxt[f].replace(f'"lef":"{L1_REF}"', f'"lef":"{L1_OWN}"')
    want = json.loads((S81 / "plan_s13r2.json").read_text())
    for tp in want["partition_types"]["gunit__t1"]["clock"]["taps"]:
        if tp["name"] in rec["taps"]:
            assert tp["xy"] == OLD_TAPS[tp["name"]]; tp["xy"] = rec["taps"][tp["name"]]["new"]
    for h in want["partition_types"]["gunit__t1"]["hard_cores"]:
        if h["lef"] == L1_REF: h["lef"] = L1_OWN
    t = ptxt["plan_s13r2.json"]
    for name, v in rec["taps"].items():
        o = '"name": "%s",\n      "kind": "core",\n      "xy": [\n       %s,\n       %s\n      ]' % (name, *[json.dumps(z) for z in v["old"]])
        assert t.count(o) == 1, (name, "tap text form")
        t = t.replace(o, '"name": "%s",\n      "kind": "core",\n      "xy": [\n       %s,\n       %s\n      ]' % (name, *[json.dumps(z) for z in v["new"]]))
    ptxt["plan_s13r2.json"] = t
    if json.loads(t) != want:
        raise SystemExit("plan text edit != json edit")
    print(json.dumps({k: rec[k] for k in ("order", "clocks", "taps", "pinhash")}, indent=1))
    if dry:
        return
    for m, d in pins.items():
        (S81 / "inputs/core_pins" / f"{m}.json").write_text(json.dumps(d, indent=0))
    for m, lt in lefs.items():
        (S81 / f"cores/legacy/lef/{m}.lef").write_text(lt)
    for f, tx in ptxt.items():
        (S81 / f).write_text(tx)
    (S81 / "delta_gunit_pins_1029.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("OT_GUNIT_PINS written: 4 pin tables, 4 plan LEFs (l1 new plan-owned copy), 3 early-tap xy, l1 lef path in", PLANS)


if __name__ == "__main__":
    main()
