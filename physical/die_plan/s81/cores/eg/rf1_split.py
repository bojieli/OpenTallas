#!/usr/bin/env python3
"""S81-RF1 RE-FORM of ot_s81sl_eg (DIE-S81-51/RF-B 2026-11-03, OWNER TWO-STRIKES; CLOSURE-LIST S81-045).

The flat eg (267k cells, 33.4k flops, 259.2 x 259.2) failed twice (synth LEC NOT EQ 4 on merged rsqrt sign pipes, FF hold
-174 structural, ioref TT -3.1).  RE-FORM = three hard blocks, every I/O registered at the face (RTL
rtl/dsrom_sys/s81_dv/eng/ot_s81sl_eg.sv: the eg wrapper is wires only, parents unchanged, +1 cycle i_v -> g_v = 222):
  ot_s81sl_egn x2 (u_eg.u_nh / u_eg.u_nk, ONE template, R0 both): pin flops -> ot_s81_engram_norm -> output face flops.
  ot_s81sl_egg x1 (u_eg.u_gg): pin flops + egn faces -> products -> gate -> pin flops.
Plan side written here: per block the plan pin table (inputs/core_pins/<module>.json), the stub abstract LEF
(cores/eg/rf1/lef/<module>.lef: pins + OBS M1-M7 + PG ports), and (--stub-plan OUT) a kit-only plan = the given base
plan + one partition type 'eg_rf1__stub' listing the two blocks (never instantiated; the real slice placement is the
DIE-S81-51/PLAN batch event S81-RF1).
Proposed slot (inside / just above the old eg slot at (768.96, 414.72) of the c1x slice types, lattice 8.64):
  u_nh (0, 0) 129.6 x 146.88, u_nk (129.6, 0) 129.6 x 146.88, u_gg (0, 146.88) 259.2 x 155.52 (relative to the old
  eg origin; total 259.2 x 302.4 = old slot + 43.2 um north).  egn N face (o_*) abuts egg S face (n_*): face-to-face.
Faces: egn S = i_v, i_x[32], eps[32] (+ clk/rst_n mid); egn N = o_v, o_r[32], o_f.  egg S = the two egn faces (h left,
k right), egg W = i_v, i_c, i_dd, scale, g_v, g_c, g, fault (same W side as the old eg outputs/scale); clk/rst_n at the S-face
middle of both blocks, clk = GEOM-21 M5 edge rectangle 0.048 x 0.48.
usage (repo root): python3 physical/die_plan/s81/cores/eg/rf1_split.py [--stub-plan OUT --base-plan PLAN]"""
import argparse, hashlib, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "leaf"))
import repin as R  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "leaf"))
from split import P  # noqa: E402

D = "physical/die_plan/s81"
BLOCKS = {
    "ot_s81sl_egn": dict(size=(129.6, 146.88), faces=dict(
        S=P("i_v,i_x[32],eps[32]"), N=P("o_v,o_r[32],o_f")), mid="S", dirs=dict(out="o_v,o_r,o_f")),
    "ot_s81sl_egg": dict(size=(259.2, 155.52), faces=dict(
        S=P("n_v[2],n_f[2],n_rh[32],n_rk[32]"), W=P("g_v,g_c[2],g[32],fault,i_v,i_c[2],i_dd[32],scale[32]")),
        mid="S", dirs=dict(out="g_v,g_c,g,fault")),
}
# measured / estimated (flat eg ccA 1_2_yosys.v: 267327 cells, 30108 um2, 33432 DFF; per-leaf flops u_nh 8.2k, rest 16.9k)
CELLS_EST = {"ot_s81sl_egn": 66000, "ot_s81sl_egg": 135000}
SLOT = {"u_nh": ("ot_s81sl_egn", (0.0, 0.0)), "u_nk": ("ot_s81sl_egn", (129.6, 0.0)), "u_gg": ("ot_s81sl_egg", (0.0, 146.88))}


def seq_of(mod, sp, face):
    g = sp["faces"][face]
    if mod == "ot_s81sl_egg" and face == "S":       # h half left, k half right (over u_nh / u_nk N faces)
        s = ["n_v[0]", "n_f[0]"] + ["n_rh[%d]" % i for i in range(32)] + ["n_rk[%d]" % i for i in range(32)] + \
            ["n_f[1]", "n_v[1]"]
    else:
        s = [(n if w == 1 else "%s[%d]" % (n, i)) for n, w in g for i in range(w)]
    if face == sp["mid"]:
        k = len(s) // 2
        s[k:k] = ["clk", "rst_n"]
    return s


def build(mod, sp):
    W, H = sp["size"]
    pins = []
    for face in sp["faces"]:
        seq = seq_of(mod, sp, face)
        vert = face in "NS"
        span = (4.32, (W if vert else H) - 4.32)
        lay = ["M3", "M5"] if vert else ["M4"]
        slots = {L: R.tracks(L, *span, vert)[::2] for L in lay}
        used = {L: set() for L in lay}
        n = len(seq)
        for i, nm in enumerate(seq):
            L = lay[i % len(lay)]
            sl = slots[L]
            want = span[0] + (span[1] - span[0]) * (i + 0.5) / n
            j = min(range(len(sl)), key=lambda k_: (abs(sl[k_] - want) if k_ not in used[L] else 1e9))
            if j in used[L]:
                raise SystemExit("%s: face %s out of tracks" % (mod, face))
            used[L].add(j)
            c, e = sl[j], R.EDGE[L]
            x, y = {"N": (c, H - e), "S": (c, e), "E": (W - e, c), "W": (e, c)}[face]
            pins.append(dict(name=nm, layer=L, x=round(x, 4), y=round(y, 4)))
    # GEOM-21 (kit_contract.clock_pin_geometry): clk = M5 S-edge rectangle 0.048 x 0.48 centred on an M5 track
    # (x = 0.012 + 0.048 k, y 0.24), at least 0.096 um from every other S-face pin centre.
    q = next(p for p in pins if p["name"] == "clk")
    others = [p["x"] for p in pins if p is not q and abs(p["y"] - q["y"]) < 1]
    k0 = round((q["x"] - 0.012) / 0.048)
    k = min((k_ for k_ in range(k0 - 20, k0 + 21) if all(abs(0.012 + 0.048 * k_ - x) >= 0.096 for x in others)),
            key=lambda k_: abs(k_ - k0))
    q.update(layer="M5", x=round(0.012 + 0.048 * k, 4), y=CLK_L / 2)
    pins.sort(key=lambda p: p["name"])
    return pins


CLK_W, CLK_L = 0.048, 0.48


def clk_lef(txt, q):
    """stub LEF: the clk PORT becomes the GEOM-21 rectangle"""
    import re
    pat = re.compile(r"(  PIN clk\n(?:(?!  END clk\n).)*?    PORT\n)(.*?)(    END\n  END clk\n)", re.S)
    m = pat.search(txt)
    assert m, "clk"
    port = "      LAYER M5 ;\n        RECT %.4f 0.0000 %.4f %.4f ;\n" % (q["x"] - CLK_W / 2, q["x"] + CLK_W / 2, CLK_L)
    return txt[:m.start(2)] + port + txt[m.end(2):]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stub-plan", default=None)
    ap.add_argument("--base-plan", default=os.path.join(D, "plan_h2_2249.json"))
    a = ap.parse_args()
    hcs = []
    for mod, sp in BLOCKS.items():
        pins = build(mod, sp)
        W, H = sp["size"]
        outs = set(sp["dirs"]["out"].split(","))
        dirs = {p["name"]: ("OUTPUT" if p["name"].split("[")[0] in outs else "INPUT") for p in pins}
        lp = os.path.join(D, "cores/eg/rf1/lef/%s.lef" % mod)
        os.makedirs(os.path.dirname(lp), exist_ok=True)
        open(lp, "w").write(clk_lef(R.lef(mod, W, H, pins, dirs), next(p for p in pins if p["name"] == "clk")))
        jp = os.path.join(D, "inputs/core_pins/%s.json" % mod)
        j = dict(module=mod, lef=lp, source="S81-RF1 RE-FORM split of ot_s81sl_eg (cores/eg/rf1_split.py): %gx%g, faces %s"
                 % (W, H, {f: sum(w for _, w in g) for f, g in sp["faces"].items()}),
                 pinhash=hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12], pins=pins)
        json.dump(j, open(jp, "w"), indent=0)
        hcs.append(dict(inst="u_eg_rf1_stub.%s" % mod, module=mod, lef=lp, origin_um=[0.0, 0.0], outline_um=[W, H],
                        orient="R0", track_offset_um=[0.108, 0.012], pins_file="inputs/core_pins/%s.json" % mod,
                        obs_max="M7"))
        print("wrote", jp, lp, len(pins))
    if a.stub_plan:
        plan = json.load(open(a.base_plan))
        plan["partition_types"]["eg_rf1__stub"] = dict(
            module="eg_rf1__stub", outline_um=[259.2, 302.4], hard=True, buses=[], ft_slots=[], clock={}, reset={},
            contents=[], sources=[], hard_cores=hcs, internal_stations=[],
            note="S81-RF1 kit-only stub (cores/eg/rf1_split.py): not instantiated; slice placement = DIE-S81-51/PLAN")
        json.dump(plan, open(a.stub_plan, "w"))
        print("wrote", a.stub_plan)


if __name__ == "__main__":
    main()
