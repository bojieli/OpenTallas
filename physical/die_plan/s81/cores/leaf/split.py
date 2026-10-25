#!/usr/bin/env python3
"""S81/LEAFPLAN 10-24 (COORD C3 ruling: ve 468k > 400k cap, vn 385k at the cap): structural split of the leaf cores
ot_s81sl_ve and ot_s81sl_vn into two hard cores each.  Plan side only: per new core the plan pin table
(inputs/core_pins/<module>.json), the stub abstract LEF (cores/leaf/lef/<module>.lef: pins + OBS M1-M7) and the port
spec; the RTL split (same arithmetic, every new pin registered on both sides) is the hand-off SPLIT_RTL below.

ve = reduce (r -> mul4 -> pack -> 3 chunk8 -> 3 trees -> p) + add (a -> add8 -> o), all four streams to / from vs.
  ot_s81sl_ve_m  'multiply' : r / a pin flops + order check, mul4 (h*h, k*k, (h*w)*k), add8 (bf16(h + gate*v)) -> o;
                              the 3 x 128-b product quads + mv / mvpre leave through output flops to ve_s.
                              yosys hier synth (generic, not ORFS): mul4 111k + add8 88k + top ~3k of 378k = 53 %.
  ot_s81sl_ve_s  'sum'      : product pin flops, quad pack, chunk8 x 3, beat trees x 3 -> p.  47 %.
  cost: +2 cycles on the reduce stream only (m_* output flop in ve_m + pin flop in ve_s; mv / mvpre / data delayed
  alike, the pack's mvpre-early enable keeps its one-edge lead); the add stream (a -> o) is unchanged.
vn = h store (2 half-row SRAMs, half hf = lanes 4 hf .. 4 hf + 3) + norm group G = 8 (8 lanes: hc_pre mix, square,
  x / w SRAMs, scale x*r*w; the golden chunk-of-8 chain over lanes 0..7) + beat tree.  ot_hbm_norm_grp is 98 % of vn
  (generic hier synth: 8 x norm_mix 40k, 24 lane multipliers 165k, chain 27k).  The cut follows the lane halves the h
  store already has:
  ot_s81sl_vn_a  lanes 0..3: h half 0 macro, its norm lanes 0..3 (mix, square, x / w SRAM half, scale), chain adders
                 1..3 -> the chain partial acc3 (c_s) leaves through an output flop; y lanes 0..3; replicated sequencer.
  ot_s81sl_vn_b  lanes 4..7: h half 1 macro, lanes 4..7, chain adders 4..7 (operand acc3 from c_s through a pin flop,
                 lanes 4..7 squares delayed + 2 to match), beat tree, p; y lanes 4..7 + y_v / y_i; replicated sequencer.
  both take the h write / read ports (hw_* to both, each writes its half; hr_* to both, each answers its half: hq of
  the other half is 0, the leaf ORs the two registered hq words), n_go / n_pre / rb (broadcast), wl_i + their 4-lane
  half of wl_d.  cost: +2 cycles on the norm partial (p) only; y, hq, h writes unchanged.
Faces: as the closed vn / ve (vn: lanes / store / dn bus W, bus N, vq E; ve: everything toward vs below) except the
sibling faces (vn_a N -> vn_b S: c; ve_m W -> ve_s E: m).  clk / rst_n at the middle of the face with the most pins.
Outlines (lattice 8.64): vn_a 356.4 x 164.16 + 17.28 gap + vn_b 356.4 x 172.8 (stacked in vn's 356.4 footprint, both W
faces on the lane field), ve_s 164.16 x 345.6 + 17.28 + ve_m 172.8 x 345.6 (ve_m directly over vs).
usage (repo root): python3 physical/die_plan/s81/cores/leaf/split.py"""
import json, os, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import repin as R

D = "physical/die_plan/s81"


def P(spec):
    """'a,b[8],c[128]' -> [(port, width)]"""
    out = []
    for t in spec.split(","):
        t = t.strip()
        if "[" in t:
            n, w = t[:-1].split("[")
            out.append((n, int(w)))
        else:
            out.append((t, 1))
    return out


HW = "hw_v,hw_j[3],hw_hf,hw_d[256],hr_v,hr_j[3],hr_hf,hq_v,hq_d[256]"
SPLIT = {
    "ot_s81sl_ve_m": dict(size=(172.8, 345.6), parent="ot_s81sl_ve", faces=dict(
        S=P("r_v,r_c[2],r_h[64],r_k[128],r_w[128],a_v,a_c[2],a_h[128],a_val[256],a_g[32],o_v,o_c[2],o_y[128],fault"),
        W=P("m_v,m_pre,m_hh[128],m_kk[128],m_dd[128]")),
        dirs=dict(out="o_v,o_c,o_y,fault,m_v,m_pre,m_hh,m_kk,m_dd")),
    "ot_s81sl_ve_s": dict(size=(164.16, 345.6), parent="ot_s81sl_ve", faces=dict(
        E=P("m_v,m_pre,m_hh[128],m_kk[128],m_dd[128]"),
        S=P("p_v,p_c[2],p_hh[32],p_kk[32],p_dd[32],fault")),
        dirs=dict(out="p_v,p_c,p_hh,p_kk,p_dd,fault")),
    "ot_s81sl_vn_a": dict(size=(356.4, 164.16), parent="ot_s81sl_vn", faces=dict(
        W=P(HW + ",wl_v,wl_i[3],wl_d[128],n_go,n_pre[128],rb_v,rb_d[32]"),
        E=P("y[64],fault"),
        N=P("c_v,c_s[32]")),
        dirs=dict(out="hq_v,hq_d,y,fault,c_v,c_s")),
    "ot_s81sl_vn_b": dict(size=(356.4, 172.8), parent="ot_s81sl_vn", faces=dict(
        W=P(HW + ",wl_v,wl_i[3],wl_d[128],n_go,n_pre[128]"),
        N=P("rb_v,rb_d[32],p_v,p_d[32]"),
        E=P("y_v,y_i[3],y[64],fault"),
        S=P("c_v,c_s[32]")),
        dirs=dict(out="hq_v,hq_d,y_v,y_i,y,p_v,p_d,fault")),
}
CELLS = {"ot_s81sl_ve_m": round(460279 * 0.53), "ot_s81sl_ve_s": round(460279 * 0.47),
         "ot_s81sl_vn_a": round(375145 * 0.49), "ot_s81sl_vn_b": round(375145 * 0.51)}


def build(mod, sp, xm=False):
    """xm: the x-mirrored pin view (E <-> W, N / S order reversed), built on the tracks directly"""
    W, H = sp["size"]
    sw = dict(E="W", W="E", N="N", S="S") if xm else dict(E="E", W="W", N="N", S="S")
    faces = {sw[f]: [(n, w) for n, w in (g[::-1] if xm and f in "NS" else g)] for f, g in sp["faces"].items()}
    big = max(faces, key=lambda f: sum(w for _, w in faces[f]))
    pins = []
    for face, groups in faces.items():
        seq = [(n if w == 1 else "%s[%d]" % (n, i)) for n, w in groups for i in range(w)]
        if xm and face in "NS":
            seq = [(n if w == 1 else "%s[%d]" % (n, i)) for n, w in groups for i in reversed(range(w))]
        if face == big:
            k = len(seq) // 2
            seq[k:k] = ["clk", "rst_n"]
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
    pins.sort(key=lambda p: p["name"])
    return pins


def main():
    out = {}
    for mod, sp in [(m_, s_) for m_, s_ in SPLIT.items()] + [(m_ + "_xm", dict(s_, xm=True)) for m_, s_ in SPLIT.items()]:
        pins = build(mod, sp, sp.get("xm", False))
        W, H = sp["size"]
        outs = set(sp["dirs"]["out"].split(","))
        dirs = {p["name"]: ("OUTPUT" if p["name"].split("[")[0] in outs else "INPUT") for p in pins}
        lp = os.path.join(D, "cores/leaf/lef/%s.lef" % mod)
        # MACRO = the RTL module (the _xm view is a pin variant of the same module, like cores/leaf/xmirror.py)
        open(lp, "w").write(R.lef(mod.replace("_xm", ""), W, H, pins, dirs))
        j = dict(module=mod, lef=lp, source="S81/LEAFPLAN 10-24 split of %s (cores/leaf/split.py): %gx%g, faces %s; "
                 "stub until the split RTL view closes%s" % (sp["parent"], W, H,
                                                            {f: sum(w for _, w in g) for f, g in sp["faces"].items()},
                                                            "; x-mirrored pin view (E <-> W)" if sp.get("xm") else ""),
                 pinhash=hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()[:12], pins=pins)
        jp = os.path.join(D, "inputs/core_pins/%s.json" % mod)
        json.dump(j, open(jp, "w"), indent=0)
        out[mod] = dict(size=[W, H], pins=len(pins), cells_est=CELLS[mod.replace("_xm", "")],
                        faces={f: sum(w for _, w in g) for f, g in sp["faces"].items()})
        print("wrote", jp, lp, len(pins))
    json.dump(out, open(os.path.join(D, "cores/leaf/split_cores.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
