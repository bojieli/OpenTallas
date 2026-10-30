#!/usr/bin/env python3
"""S81 pin-contract event PINEV (DIE-S81-32/PINEV, 2026-10-29; COORD ruling loop-gap 19:4x on the S81-CORES-KITS ASK 19:29).

Fix-only delta on frozen plan_s13r2 in the H0 330ee0e6e50 / S81-028 (delta_clkpin_m5_1029b.py) form: each core's OWN plan
pin table (inputs/core_pins/<module>.json), its plan LEF and its legacy-kit macro sites change; no outline, neighbour,
partition or die-level datum changes.  kit_preflight failed on these plan data (no kit variant can fix them):

(a) GEOM-21 clock pins (kit_contract CLOCK_PIN_MIN 0.048 x 0.48, M5, centre on the M5 track x = 0.012 + 0.048 k).
    Same face, nearest legal site, EDGE rectangle (S81-028 rule; no core gets an interior/face-C clock, so the die
    clock tree is not asked to move -- early-tapped cores dsdv_gunit_l0/l4, dsdv_bk_g, ot_v41_bf_col keep their tap):
      W face M4 (0.042|0.096, y) -> M5 0.120x0.48 centre (0.06, y)   [narrowest W-edge rect centred on track 1]
      dsdv_gunit_l1c E face M4 (86.358, y) -> M5 0.072x0.48 centre (86.364, y)  [track 1799; 0.048 cannot be centred]
      dsdv_bk_g S face M3 multiPORT (104.985, 0.0685) -> M5 0.048x0.48 centre (104.988, 0.24)  [track 2187]
      ot_v41_bf_col N face M5 multiPORT 0.024 wide (227.148, 198.6265) -> M5 0.048x0.48 centre (227.148, 198.48)
      ot_s81_sstn_base566 ck W face M4 multiPORT (0.096, 15.132) -> M5 0.120x0.48 centre (0.06, 15.132)
    The multiPORT clocks (bk_g, bf_col, sstn) were emitted by the generator as native dbBox pins, which is also why
    kit_preflight found "no static placement" for them; a single GEOM-21 rect makes them plain place_pin pins.
    Plan LEFs: dsfd_qbank_N/S, dsdv_gunit_* and dsdv_bk_g point at closed ref_tile views and sstn/bf_col at
    s81_die_views that other (legacy frame) ref_tiles also read, so -- as S81-028 did for vsw -- the plan pin
    contract moves to plan-owned copies cores/legacy/lef/<module>.lef (only the clock PIN differs) and the
    hard_cores rows of these modules are repointed (plan_s13r2.json + die_plan.json, textual swap of the lef path).
(b) pins_canonical: the remaining kit != plan mismatches are native multiPORT signal pins (gunit_l0 hp_av, bk_g
    fault[0]/rst_n[0], sstn cc[2]/nf/rs/so[0]/so[1]); kit and plan pin file agree, but kit_contract.placed_pins read
    only place_pin lines.  Fixed in the checker (H0-style minimal: placed_pins reads native multiPORT blocks), not here.
(c) ot_s81c_attn_hcore: the generator refused ld_v "0.042 um off its declared W edge rectangle"; the cause is the
    whole table: all 1214 plan pins sit on the boundary at the outer edge midpoint of their 0.192-deep LEF edge rects
    (590 W, 580 N, 42 E, 2 S).  Every pin -> its rect centre (0.096 um inward, e.g. ld_v (0.0, 4.524) -> (0.096,
    4.524)); clk S-face M5 0.024x0.192 (78.828, 0.0) -> GEOM-21 M5 0.048x0.48 centre (78.828, 0.24) in the plan-owned
    stub LEF (edited in place, its full-outline M5 OBS notched at 0.024 um around the pin).  hcore is not an early tap.
(d) macro channels >= 10.8 um (kit_contract MIN_CHANNEL_UM) inside the unchanged outlines, legacy recipe macro_sites
    (y moves are whole 0.048 M4-track steps, x unchanged):
      dsdv_bk_g  2x ot_sram_1r1w_128x256_m1_r2c2 (94.824x41.064) at x 60.48: y 45.36 / 86.448 (gap 0.024)
                 -> 39.984 / 91.872 (gap 10.824); top 132.936 <= 172.8.
      ot_v41_bf_col 2x ot_rom_4096x274_m8 (125.304x62.952) at x 42.12: y 32.064 R180 / 103.68 MY (gap 8.664)
                 -> 31.008 / 104.784 (gap 10.824, centre row 99.372); top 167.736 <= 198.72.

Every edit asserts the exact old form; a second run refuses (idempotence).  usage: python3 delta_pinev_1029.py
"""
import hashlib
import json
import re
from pathlib import Path

S81 = Path(__file__).resolve().parent
REPO = S81.parents[2]
LEFDIR = "physical/die_plan/s81/cores/legacy/lef/"
PLANS = ("plan_s13r2.json", "die_plan.json")
TAG = "S81 pin event DIE-S81-32/PINEV 2026-10-29 (delta_pinev_1029.py)"

# module: clock pin, old plan (layer, x, y), old LEF PORT rects [(layer, x0, y0, x1, y1)], new centre, new M5 rect
CLOCKS = {
    "dsfd_qbank_N": ("ck[0]", ("M4", 0.042, 4.332), [("M4", 0, 4.32, 0.084, 4.344)],
                     (0.06, 4.332), (0.0, 4.092, 0.12, 4.572)),
    "dsfd_qbank_S": ("ck[0]", ("M4", 0.042, 17.292), [("M4", 0, 8.64, 0.084, 8.664)],
                     (0.06, 17.292), (0.0, 17.052, 0.12, 17.532)),
    "dsdv_gunit_l4": ("clk", ("M4", 0.042, 35.292), [("M4", 0, 35.28, 0.084, 35.304)],
                      (0.06, 35.292), (0.0, 35.052, 0.12, 35.532)),
    "dsdv_gunit_l1c": ("clk", ("M4", 86.358, 184.284), [("M4", 86.316, 184.272, 86.4, 184.296)],
                       (86.364, 184.284), (86.328, 184.044, 86.4, 184.524)),
    "dsdv_gunit_l0r": ("clk", ("M4", 0.042, 100.236), [("M4", 0, 64.656, 0.084, 64.68)],
                       (0.06, 100.236), (0.0, 99.996, 0.12, 100.476)),
    "dsdv_gunit_l0": ("clk", ("M4", 0.042, 94.62), [("M4", 0, 94.608, 0.084, 94.632)],
                      (0.06, 94.62), (0.0, 94.38, 0.12, 94.86)),
    "ot_s81_sstn_base566": ("ck", ("M4", 0.096, 15.132), [("M4", 0, 15.12, 0.192, 15.144), ("M4", 0.156, 15.12, 0.275, 15.144)],
                            (0.06, 15.132), (0.0, 14.892, 0.12, 15.372)),
    "dsdv_bk_g": ("clk[0]", ("M3", 104.985, 0.0685), [("M3", 104.976, 0, 104.994, 0.038), ("M3", 104.976, 0.012, 104.994, 0.125)],
                  (104.988, 0.24), (104.964, 0.0, 105.012, 0.48)),
    "ot_v41_bf_col": ("clk", ("M5", 227.148, 198.6265), [("M5", 227.136, 198.636, 227.16, 198.72), ("M5", 227.136, 198.581, 227.16, 198.672)],
                      (227.148, 198.48), (227.124, 198.24, 227.172, 198.72)),
}
HCORE = "ot_s81c_attn_hcore"
HCORE_LEF = "physical/die_plan/s81/cores/svc/ot_s81c_attn_hcore.lef"       # plan-owned stub: edited in place (H0 form)
HCORE_WH = (157.68, 259.2)
HCORE_CLK = ("clk", ("M5", 78.828, 0.0), ("M5", 78.816, 0.0, 78.84, 0.192), (78.828, 0.24), (78.804, 0.0, 78.852, 0.48))
HCORE_OBS_OLD = "    LAYER M5 ;\n      RECT 0.200 0.200 157.480 259.000 ;\n  END\n"
HCORE_OBS_NEW = ("    LAYER M5 ;\n      RECT 0.200 0.200 78.780 259.000 ;\n      RECT 78.876 0.200 157.480 259.000 ;\n"
                 "      RECT 78.780 0.504 78.876 259.000 ;\n  END\n")
RECIPES = S81 / "cores/legacy/recipes.json"
BKG_OLD = ' "dsdv_bk_g": {\n  "ref_tile": "physical/ref_tile/s81dvbk_g2",\n  "rtl_dirs": true\n },\n'
BKG_NEW = (' "dsdv_bk_g": {\n  "ref_tile": "physical/ref_tile/s81dvbk_g2",\n  "rtl_dirs": true,\n'
           '  "macro_sites": {"ot_sram_1r1w_128x256_m1_r2c2": [[60.48, 39.984, "R0"], [60.48, 91.872, "R0"]]},\n'
           f'  "_pinev": "{TAG}: spec.json at 45.36/86.448 left a 0.024-um stack gap; sites split -5.376/+5.424 um '
           '(whole M4 tracks) for a 10.824-um interior channel (kit_contract macro_channels >= 10.8) inside the 216x172.8 outline"\n },\n')
BFC_OLD = ('  "macro_sites": {\n   "ot_rom_4096x274_m8": [\n    [\n     42.12,\n     32.064,\n     "R180"\n    ],\n'
           '    [\n     42.12,\n     103.68,\n     "MY"\n    ]\n   ]\n  },\n')
BFC_NEW = ('  "macro_sites": {\n   "ot_rom_4096x274_m8": [\n    [\n     42.12,\n     31.008,\n     "R180"\n    ],\n'
           '    [\n     42.12,\n     104.784,\n     "MY"\n    ]\n   ]\n  },\n'
           f'  "_pinev": "{TAG}: ROM pair y 32.064/103.68 -> 31.008/104.784 (-1.056/+1.104 um, whole M4 tracks): '
           'interior channel 8.664 -> 10.824 um (kit_contract macro_channels >= 10.8), same x, orients, outline",\n')


def fmt_of(text, doc):
    """the exact json.dumps form of a pin table (files differ: one-line / indent 0 / indent 1, trailing newline)."""
    for kw in (dict(), dict(indent=0), dict(indent=1), dict(indent=2)):
        for nl in ("", "\n"):
            if json.dumps(doc, **kw) + nl == text:
                return kw, nl
    raise SystemExit("pin table does not round-trip through json.dumps; refusing to rewrite it")


def pinhash(pins):
    return hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12]


def check_rect(c, r, W, H):
    x, y = c
    x0, y0, x1, y1 = r
    assert abs((x0 + x1) / 2 - x) < 1e-6 and abs((y0 + y1) / 2 - y) < 1e-6, ("rect not centred", c, r)
    assert x1 - x0 >= 0.048 - 1e-9 and y1 - y0 >= 0.48 - 1e-9, ("rect < 0.048x0.48 (GEOM-21)", r)
    k = (x - 0.012) / 0.048
    assert abs(k - round(k)) < 1e-6, ("centre off the M5 track", x)
    assert min(x0, y0, W - x1, H - y1) < 1e-6 and min(x0, y0) >= 0 and x1 <= W + 1e-9 and y1 <= H + 1e-9, \
        ("rect must touch its face and stay inside the outline", r)


def pin_block(txt, pin):
    pat = re.compile(r"^  PIN %s\n.*?^  END %s\n" % (re.escape(pin), re.escape(pin)), re.S | re.M)
    m = list(pat.finditer(txt))
    assert len(m) == 1, ("PIN block", pin, len(m))
    return m[0]


def port_rects(block):
    out, layer = [], None
    for ln in block.splitlines():
        t = ln.split()
        if t[:1] == ["LAYER"]:
            layer = t[1]
        elif t[:1] == ["RECT"]:
            out.append((layer, *map(float, t[1:5])))
    return out


def plan_row(module):
    p = json.loads((S81 / PLANS[0]).read_text())
    rows = [h for t in p["partition_types"].values() for h in t.get("hard_cores", []) if h["module"] == module]
    assert rows and len({(h["lef"], h["pins_file"], tuple(h["outline_um"])) for h in rows}) == 1, module
    return rows[0], len(rows)


def edit_table(module, fn):
    f = S81 / "inputs/core_pins" / f"{module}.json"
    txt = f.read_text()
    d = json.loads(txt)
    kw, nl = fmt_of(txt, d)
    fn(d)
    f.write_text(json.dumps(d, **kw) + nl)


def edit_clock(module, e, plan_rows):
    pin, old, old_rects, new, rect = e
    row, n = plan_rows[module]
    W, H = row["outline_um"]
    check_rect(new, rect, W, H)
    src = row["lef"]
    assert src != LEFDIR + f"{module}.lef", f"{module}: plan already points at the plan-owned LEF (event applied?)"
    txt = (REPO / src).read_text()
    m = pin_block(txt, pin)
    got = port_rects(m.group(0))
    assert len(got) == len(old_rects) and all(a[0] == b[0] and all(abs(u - v) < 1e-6 for u, v in zip(a[1:], b[1:]))
                                              for a, b in zip(got, old_rects)), (module, "old PORT form", got)
    head = m.group(0).split("    PORT\n", 1)[0]
    blk = (head + "    PORT\n      LAYER M5 ;\n"
           f"        RECT {rect[0]:.3f} {rect[1]:.3f} {rect[2]:.3f} {rect[3]:.3f} ;\n    END\n  END {pin}\n")
    dst = REPO / LEFDIR / f"{module}.lef"
    assert not dst.exists(), f"{dst} exists (event applied?)"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(txt[:m.start()] + blk + txt[m.end():])

    def upd(d):
        assert d["lef"] == src, (module, d["lef"])
        q = [p for p in d["pins"] if p["name"] == pin]
        assert len(q) == 1 and (q[0]["layer"], q[0]["x"], q[0]["y"]) == old, (module, "old plan pin form", q)
        q[0].update(layer="M5", x=new[0], y=new[1])
        d["lef"] = LEFDIR + f"{module}.lef"
        d["pinhash"] = pinhash(d["pins"])
        d["source"] += (f"; {TAG}: clock {pin} {old[0]}({old[1]},{old[2]}) -> M5({new[0]},{new[1]}) "
                        f"{rect[2]-rect[0]:.3f}x{rect[3]-rect[1]:.3f} edge rectangle on the M5 track (GEOM-21); "
                        f"plan LEF = plan-owned copy of {src} (only PIN {pin} differs)")
    edit_table(module, upd)
    return src, n


def edit_plans(swaps):
    out = {}
    for name in PLANS:
        f = S81 / name
        txt = f.read_text()
        for module, (src, n_s13) in swaps.items():
            old = f'"module":"{module}","lef":"{src}"'
            n = txt.count(old)
            assert n > 0 and txt.count(f'"module":"{module}",') == n, (name, module, n)
            if name == PLANS[0]:
                assert n == n_s13, (module, n, n_s13)
            txt = txt.replace(old, f'"module":"{module}","lef":"{LEFDIR}{module}.lef"')
            out[(name, module)] = n
        json.loads(txt)
        f.write_text(txt)
    return out


def edit_hcore():
    """(c) every one of the 1214 plan pins sits ON the boundary at the outer edge midpoint of its declared 0.192-deep
    edge rect (gen_svc_cores edge-point convention); the generator wants the rect centre (no implicit projection) and
    stopped at the first one (ld_v, 0.042 um vs its default depth).  All pins move to their rect centre, 0.096 um
    inward, parallel coordinate unchanged.  (a') clk: S-face M5 0.024x0.192 -> GEOM-21 0.048x0.48 on the same track
    x 78.828 (track 1642); the stub's full-outline M5 OBS is notched around it at 0.024 um spacing."""
    import sys
    sys.path.insert(0, str(S81 / "cores/legacy"))
    from gen_core_kit_legacy import face_of, lef_pin_rects
    W, H = HCORE_WH
    row, _ = plan_row(HCORE)
    assert row["lef"] == HCORE_LEF and tuple(row["outline_um"]) == HCORE_WH, row["lef"]
    lef = REPO / HCORE_LEF
    txt = lef.read_text()
    pin, old, old_rect, new, rect = HCORE_CLK
    check_rect(new, rect, W, H)
    m = pin_block(txt, pin)
    got = port_rects(m.group(0))
    assert len(got) == 1 and got[0][0] == old_rect[0] and all(abs(u - v) < 1e-6 for u, v in zip(got[0][1:], old_rect[1:])), \
        ("hcore clk old PORT form (event applied?)", got)
    shapes = lef_pin_rects(lef, geometry=True)
    head = m.group(0).split("    PORT\n", 1)[0]
    blk = (head + "    PORT\n      LAYER M5 ;\n"
           f"        RECT {rect[0]:.3f} {rect[1]:.3f} {rect[2]:.3f} {rect[3]:.3f} ;\n    END\n  END {pin}\n")
    txt = txt[:m.start()] + blk + txt[m.end():]
    assert txt.count(HCORE_OBS_OLD) == 1, "hcore M5 OBS not in the expected form"
    lef.write_text(txt.replace(HCORE_OBS_OLD, HCORE_OBS_NEW))
    moved = {}

    def upd(d):
        for q in d["pins"]:
            L, sw, sh, x0, y0, x1, y1 = shapes[q["name"]]
            f = face_of(q["x"], q["y"], W, H)
            cx, cy = round((x0 + x1) / 2, 4), round((y0 + y1) / 2, 4)
            edge = {"W": (0.0, cy), "E": (W, cy), "S": (cx, 0.0), "N": (cx, H)}[f]
            assert L == q["layer"] and abs(q["x"] - edge[0]) < 1e-6 and abs(q["y"] - edge[1]) < 1e-6, \
                ("hcore pin not at its rect's outer edge midpoint (event applied?)", q, shapes[q["name"]])
            if q["name"] == pin:
                assert (q["layer"], q["x"], q["y"]) == old
                cx, cy = new
            moved[f] = moved.get(f, 0) + 1
            q.update(x=cx, y=cy)
        d["pinhash"] = pinhash(d["pins"])
        d["source"] += (f"; {TAG}: all {len(d['pins'])} pins edge-point -> centre of their declared edge rect "
                        f"(0.096 um inward; was refused 'off its declared edge rectangle', first ld_v); clk S M5 "
                        f"0.024x0.192 -> 0.048x0.48 centre ({new[0]},{new[1]}) (GEOM-21), M5 OBS notched")
    edit_table(HCORE, upd)
    return moved


def edit_recipes():
    txt = RECIPES.read_text()
    assert txt.count(BKG_OLD) == 1, "dsdv_bk_g recipe not in the expected form (event applied?)"
    assert txt.count(BFC_OLD) == 1, "ot_v41_bf_col macro_sites not in the expected form (event applied?)"
    i = txt.index(' "ot_v41_bf_col": {\n')
    assert txt.index(BFC_OLD) > i and txt.index(BFC_OLD) < txt.index("\n },\n", i), "bf_col macro_sites outside its recipe"
    txt = txt.replace(BKG_OLD, BKG_NEW).replace(BFC_OLD, BFC_NEW)
    json.loads(txt)
    RECIPES.write_text(txt)


if __name__ == "__main__":
    rows = {m: plan_row(m) for m in CLOCKS}
    swaps = {}
    for mod, e in CLOCKS.items():
        swaps[mod] = edit_clock(mod, e, rows)
        print(mod, e[0], e[1], "->", ("M5",) + e[3], "rect", e[4], "lef", LEFDIR + f"{mod}.lef", "rows", swaps[mod][1])
    for (plan, mod), n in edit_plans(swaps).items():
        print(plan, mod, "hard_cores lef repointed", n)
    print(HCORE, "pins moved to rect centres per face", edit_hcore(), "clk", HCORE_CLK[1], "->", HCORE_CLK[3])
    edit_recipes()
    print("recipes: dsdv_bk_g macro_sites 39.984/91.872, ot_v41_bf_col 31.008/104.784")
