#!/usr/bin/env python3
"""DIE-S81-51/RF-H 2026-11-03: die-local plan delta for the 3-core ot_v41_bf_col (ot_v41_bf_col3).

The bf_col slot (450.168 x 198.72, unchanged) holds three hard cores, rigidly inside the old core frame:
  u_view.u_c  ot_v41_bf_col3_c  old-frame x [241.92, 450.168], full height: all 842 old pins (x - 241.92), the two
              ROMs, FP lanes, chains, pair, segment tree, outputs, BF root adder; W face = the two half interfaces
  u_view.u_ha ot_v41_bf16_half  old-frame [0, 241.92] x [0, 95.04]       (BF lanes 0-7)
  u_view.u_hb ot_v41_bf16_half  old-frame [0, 241.92] x [103.68, 198.72] (BF lanes 8-15; 8.64-um channel between)
Every split coordinate is a multiple of the 8.64-um plan lattice (= a whole number of every M2-M7 pitch), so each pin
keeps the old core's track phase in both orients (R0, MY); the MY half's sub-lattice x (208.248 = 207.36 + 0.888) goes
into track_offset_um.  M4 face pins: the kit default edge rectangle (0.084 x 0.024, centre 0.042 in; the old E pins
move 0.012 um onto it: the contract LEF declares only clk), inter-core pins at 0.192-um pitch,
H east face pin k at y_k and its C west-face partner at y_k (ha) / 103.68 + y_k (hb).  Clock: one M5 N-face edge
entry per core (GEOM-21 0.048 x 0.48, off the M5 straps).
usage: mkplan_rfh3.py <repo root> <base plan json> <out plan json>"""
import gzip, json, sys
from pathlib import Path

R, BASE, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
S81 = R / "physical/die_plan/s81"
W, H = 450.168, 198.72
XS, HH, YB = 241.92, 95.04, 103.68          # split x, half height, half B origin y (all 8.64 multiples)
WC = round(W - XS, 3)                       # 208.248
LAT = 8.64
D = 0.042                                   # M4 edge rectangle 0.084 x 0.024 centre (kit default shape)
PIN_PITCH, M4OFF, M4P = 0.192, 0.012, 0.048

def m4(y):
    return round(M4OFF + round((y - M4OFF) / M4P) * M4P, 3)

# ---- half pin list (port order = face order bottom -> top)
H_IN = [f"t[{i}]" for i in range(13)] + ["v", "rst_c", "ze_c"] + [n for i in range(128) for n in (f"w[{i}]", f"x[{i}]")]
H_OUT = ["ov"] + [f"oval[{i}]" for i in range(32)] + ["oerr"] + [f"otag[{i}]" for i in range(8)] + ["fault"]
HP = H_IN + H_OUT
y0 = m4(HH / 2 - PIN_PITCH * (len(HP) - 1) / 2)
YH = {n: round(y0 + k * PIN_PITCH, 3) for k, n in enumerate(HP)}
assert YH[HP[0]] > 4.32 + 1 and YH[HP[-1]] < HH - 4.32 - 1, (YH[HP[0]], YH[HP[-1]])
CLK_H = (round(M4OFF + 2520 * M4P, 3), round(HH - 0.24, 3))           # 120.972: off the M5 strap pairs
CLK_C = (round(M4OFF + 2169 * M4P, 3), round(H - 0.24, 3))            # 104.124
for x in (CLK_H[0], CLK_C[0]):
    r = (x - 4.32 - 2.064) % 4.32
    assert 0.462 < r < 4.17, (x, r)                                   # reform_shape.on_strap keep-out

hpins = [{"name": "clk", "layer": "M5", "x": CLK_H[0], "y": CLK_H[1]}] + \
        [{"name": n, "layer": "M4", "x": round(XS - D, 3), "y": YH[n]} for n in HP]

# C <-> half signal map (half B: ov / otag unused at the column, no C pin)
def cname(n, s):
    b = n.split("[")[0]; i = n[len(b):]
    m = {"t": f"h_t_{s}", "v": f"h_v_{s}", "rst_c": f"h_rst_{s}", "ze_c": f"h_ze_{s}", "w": f"h_w_{s}", "x": f"h_x_{s}",
         "ov": f"r_v_{s}", "oval": f"r_val_{s}", "oerr": f"r_err_{s}", "otag": f"r_t_{s}", "fault": f"r_f_{s}"}[b]
    if s == "b" and b in ("ov", "otag"):
        return None
    return m + i

old = json.load(open(S81 / "inputs/core_pins/ot_v41_bf_col.json"))
cpins = [{"name": "clk", "layer": "M5", "x": CLK_C[0], "y": CLK_C[1]}]
for q in old["pins"]:
    if q["name"] == "clk":
        continue
    assert q["x"] >= XS + 4.32, q
    x = round(WC - D, 3) if q["x"] > W - 0.5 else round(q["x"] - XS, 3)   # E face: the default edge rectangle centre
    cpins.append(dict(q, x=x))
for s, dy in (("a", 0.0), ("b", YB)):
    for n in HP:
        c = cname(n, s)
        if c:
            cpins.append({"name": c, "layer": "M4", "x": D, "y": round(YH[n] + dy, 3)})
assert len({q["name"] for q in cpins}) == len(cpins)

def lef(macro, w, h, clk):
    x, y = clk
    return (f"# DIE-S81-51/RF-H 11-03 {macro} pin-shape contract (3-core bf_col, plan rfh3 delta): only the GEOM-21 clock\n"
            f"# entry rectangle (N face M5 0.048 x 0.48 on the M5 track at x {x:g}); every other pin = the plan pin table\n"
            "# centre with the kit default shape (directions from the kit RTL, recipe rtl_dirs).\n"
            'VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n'
            f"MACRO {macro}\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE {w:g} BY {h:g} ;\n  PIN clk\n    DIRECTION INPUT ;\n"
            f"    USE CLOCK ;\n    PORT\n      LAYER M5 ;\n        RECT {x - 0.024:.3f} {h - 0.48:.3f} {x + 0.024:.3f} {h:g} ;\n"
            f"    END\n  END clk\nEND {macro}\nEND LIBRARY\n")

(S81 / "rfh3").mkdir(exist_ok=True)
LEF = {m: f"physical/die_plan/s81/rfh3/{m}_rfh3_contract.lef" for m in ("ot_v41_bf_col3_c", "ot_v41_bf16_half")}
PF = {m: f"inputs/core_pins/{m}_rfh3.json" for m in LEF}
(R / LEF["ot_v41_bf_col3_c"]).write_text(lef("ot_v41_bf_col3_c", WC, H, CLK_C))
(R / LEF["ot_v41_bf16_half"]).write_text(lef("ot_v41_bf16_half", XS, HH, CLK_H))
SRC = "DIE-S81-51/RF-H 11-03 3-core bf_col (tools: results/rfh_1103/bf_col3/mkplan_rfh3.py)"
for m, pins in (("ot_v41_bf_col3_c", cpins), ("ot_v41_bf16_half", hpins)):
    (S81 / PF[m]).write_text(json.dumps({"module": m, "lef": LEF[m], "source": SRC, "pins": pins}, indent=1) + "\n")

# ---- plan copy
plan = json.load(open(BASE))
notes, n = [], 0
for tn, t in plan["partition_types"].items():
    hcs, new = t.get("hard_cores", []), []
    for hc in hcs:
        if hc["module"] != "ot_v41_bf_col":
            new.append(hc); continue
        n += 1
        o, (dx, dy), ori = hc["origin_um"], hc.get("track_offset_um", [0.0, 0.0]), hc["orient"]
        assert hc["outline_um"] == [W, H] and ori in ("R0", "MY"), hc
        base = {k: v for k, v in hc.items() if k not in ("module", "lef", "lib", "pins_file", "origin_um", "outline_um",
                                                          "track_offset_um", "inst")}
        def core(sfx, mod, x, y, w, h):
            # x, y: the core's lower-left in the OLD core frame -> die-type frame (R0: +x; MY: mirrored x)
            lx = x if ori == "R0" else W - x - w
            gx = o[0] + dx + lx
            ox = LAT * int((gx + 1e-6) // LAT)
            while gx - ox < 0 or gx - ox >= 2.16 - 1e-9:      # keep the old sub-lattice offset form
                ox -= LAT if gx - ox < 0 else -LAT
            assert gx - ox < 2.16, (gx, ox)
            return dict(inst=f"{hc['inst']}.{sfx}", module=mod, lef=LEF[mod], origin_um=[round(ox, 3), round(o[1] + y, 3)],
                        outline_um=[w, h], track_offset_um=[round(gx - ox, 3), dy], pins_file=PF[mod], **base)
        new += [core("u_c", "ot_v41_bf_col3_c", XS, 0.0, WC, H),
                core("u_ha", "ot_v41_bf16_half", 0.0, 0.0, XS, HH),
                core("u_hb", "ot_v41_bf16_half", 0.0, YB, XS, HH)]
        notes.append(f"{tn} {hc['inst']}: RF-H 11-03 3-core bf_col (u_c / u_ha / u_hb, {ori})")
    if len(new) != len(hcs):
        t["hard_cores"] = new
    s = t.get("sources")
    if s and "rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col_kit.sv" in s:
        i = s.index("rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col_kit.sv")
        s[i:i + 1] = ["rtl/v41rom/ot_v41_bf_col3_hw.sv", "rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col3_kit.sv"]
assert n == 56, n
OUT.write_text(json.dumps(plan, separators=(",", ":")))
with open(str(OUT) + ".gz", "wb") as fz, gzip.GzipFile(fileobj=fz, mode="wb", compresslevel=9, mtime=0) as f:
    f.write(OUT.read_bytes())
print(f"replaced {n} bf_col cores; C pins {len(cpins)}, H pins {len(hpins)}, H y {YH[HP[0]]}..{YH[HP[-1]]}")
Path(str(OUT.with_suffix("")) + ".README").write_text(
    "Notes moved out of " + OUT.name + ".gz (schema.validate: unknown keys)\n\n" + "\n".join(notes) + "\n")
