#!/usr/bin/env python3
"""S81-KVTC-PINS 11-25 (fix B for the kv_leaf T2B GRT overflow): dsfd_su_t_kvtc with POSITION-MAJOR e_d pins.

Same RTL, same top, same port list as the signed kvtch (702 x 25.92, kvtc_h_gen.py); only the pin map and the height
change.  Each tap position p (e_d[128p +: 128] + e_v[p]) leaves in ONE contiguous group of 129 pins (~22 um, <= 6
pins/um over M3 + M5) on the face toward its consumer engine pair (2p, 2p+1) in the T2B seating v11/v12 (bars R0 at
y 933 / 1019; engines of p 0-15 below -> S face, p 16-31 above -> N face), groups ordered along x by consumer engine x.
dn_d / e_cs / e_ob / e_nb / e_eps stay bit-local and monotonic in the bit (8 bits a chunk between groups); the control
band stays at mid width.  The 16 -> 32 rotation transpose now runs inside the tap (about 2k wires over the centre cut,
M4 the only free horizontal layer under the M5 cap), hence the height growth.
usage: kvtcp_gen.py H [suffix]
"""
import json, math, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
root = here / 'kitrepo'
sys.path.insert(0, str(root / 'tools/ref_tile'))
W = 702.0
H = float(sys.argv[1]); SUF = sys.argv[2] if len(sys.argv) > 2 else f"h{int(round(H / 8.64))}"
assert abs(H / 8.64 - round(H / 8.64)) < 1e-6, H
M3_OFF, M3_P, M3_W = 0.009, 0.036, 0.018
M5_OFF, M5_P, M5_W = 0.012, 0.048, 0.024
PIN_L = 0.192
CORE, PG_P, PG_LO, PG_HI = 2.16, 5.4, 0.10, 1.00
X0, XE = 25.416, 676.584          # the signed kvtch pin span (128 bit bands + control band)
CTL = 24.48
XC = (X0 + XE) / 2 - CTL / 2      # control band [XC, XC + CTL)
# consumer engine pair (2p, 2p+1) kve seat x (T2B macro_place v11/v12): quant block b = positions 2b, 2b+1
# measured pair-centre x of the engines (probe_v12 macro_place.tcl, kve seats)
_kx = [140.4, 140.4, 1362.96, 1362.96, 1760.4, 1760.4, 2982.96, 2982.96,
       140.4, 140.4, 1362.96, 1362.96, 1760.4, 1760.4, 2982.96, 2982.96,
       140.4, 140.4, 1362.96, 1362.96, 1760.4, 1760.4, 2982.96, 2982.96,
       140.4, 140.4, 974.16, 974.16, 1408.32, 1408.32, 2388.96, 2388.96]
_ky = [21.6, 172.8, 21.6, 172.8, 21.6, 172.8, 21.6, 172.8, 393.12, 544.32, 393.12, 544.32, 393.12, 544.32, 393.12, 544.32,
       1313.28, 1464.48, 1313.28, 1464.48, 1313.28, 1464.48, 1313.28, 1464.48, 1684.8, 1836.0, 1684.8, 1836.0, 1684.8,
       1831.68, 1684.8, 1831.68]
FACE = {p: ('S' if _ky[p] < 933.12 else 'N') for p in range(32)}
ORDER = {f: sorted((p for p in range(32) if FACE[p] == f), key=lambda p: (_kx[p], abs(_ky[p] - 980), p)) for f in 'NS'}
assert len(ORDER['N']) == 16 and len(ORDER['S']) == 16
rows, used = [], set()
def put(face, layer, x, name):
    off, pch, w = (M3_OFF, M3_P, M3_W) if layer == 'M3' else (M5_OFF, M5_P, M5_W)
    k = round((x - off) / pch); x = off + pch * k
    assert (face, layer, k) not in used, (face, layer, k, name); used.add((face, layer, k))
    y = PIN_L / 2 if face == 'S' else H - PIN_L / 2
    rows.append((face, x, layer, name, f"place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.4f} {y:.4f}}} -pin_size {{{w:.4f} {PIN_L:.4f}}}"))
def m5_ok(x):
    return not PG_LO - 0.06 <= (x - CORE) % PG_P <= PG_HI + 0.06
def lay(face, x_lo, x_hi, names):
    """names alternate M5 / M3 over [x_lo, x_hi): M5 on free tracks >= 0.144 apart, M3 >= 0.108 apart, interleaved;
    the order of names is kept along x (M5 and M3 picks merged by x)"""
    xs5 = []; x = M5_OFF + M5_P * math.ceil((x_lo + 0.05 - M5_OFF) / M5_P)
    while x < x_hi - 0.05:
        if m5_ok(x): xs5.append(x); x += 3 * M5_P
        else: x += M5_P
    n5 = min(len(names) // 2, len(xs5)); n3 = len(names) - n5
    step = len(xs5) / n5 if n5 else 1
    pick5 = [xs5[int(i * step)] for i in range(n5)]
    xs3 = []; x = M3_OFF + M3_P * math.ceil((x_lo + 0.05 - M3_OFF) / M3_P)
    while x < x_hi - 0.05:
        if all(abs(x - q) >= 0.06 for q in pick5): xs3.append(x); x += 3 * M3_P
        else: x += M3_P
    assert len(xs3) >= n3, (face, x_lo, x_hi, len(xs3), n3)
    step = len(xs3) / n3 if n3 else 1
    pick3 = [xs3[int(i * step)] for i in range(n3)]
    slots = sorted([(x, 'M5') for x in pick5] + [(x, 'M3') for x in pick3])
    for nm, (x, ly) in zip(names, slots): put(face, ly, x, nm)
def bits(n, k): return [n] if k == 1 else [f"{n}[{i}]" for i in range(k)]
GW = 22.0                          # e_d group width: 129 pins at 5.9 pins/um
# 16 slots a face: 8 left of the control band, 8 right; slot = [group | 8-bit dn_d/e_cs chunk]
span_l = XC - X0; span_r = XE - (XC + CTL)
slot_l = span_l / 8; slot_r = span_r / 8
assert slot_l > 37 and slot_r > 37, (slot_l, slot_r)
def slot_x(i):
    return (X0 + slot_l * i, slot_l) if i < 8 else (XC + CTL + slot_r * (i - 8), slot_r)
for face in 'NS':
    for i in range(16):
        x0, sw = slot_x(i)
        p = ORDER[face][i]
        grp = [f"e_d[{128 * p + b}]" for b in range(128)]
        grp.insert(64, f"e_v[{p}]")
        chunk = []
        for b in range(8 * i, 8 * i + 8):
            if face == 'N':
                chunk += [f"dn_d[{128 * s + b}]" for s in range(8)] + [f"e_cs[{128 * j + b}]" for j in range(2)]
                if b >= 96: chunk.append(f"e_eps[{b - 96}]")
            else:
                chunk += [f"dn_d[{128 * s + b}]" for s in range(8, 16)] + [f"e_cs[{128 * j + b}]" for j in range(2, 4)]
        # the 8 remaining bits of this chunk's 16-bit share (bits 128 / 16 = 8 a slot covers all 128)
        if face == 'N':
            chunk += [f"e_ob[{b}]" for b in range(8 * i, 8 * i + 8) if b < 14]
        else:
            chunk += [f"e_nb[{b}]" for b in range(8 * i, 8 * i + 8) if b < 14]
        # widths in proportion to the pin counts: one uniform density over the slot
        gw = (sw - 0.6) * len(grp) / (len(grp) + len(chunk))
        lay(face, x0 + 0.3, x0 + 0.3 + gw, grp)
        lay(face, x0 + 0.3 + gw, x0 + sw - 0.3, chunk)
cs = ["ck", "rst", "dn_st", *bits("dn_kind", 4), *bits("dn_gsel", 2), *bits("dn_jid", 8), *bits("dn_v", 16), *bits("i_f", 65)]
cn = ["e_gk", *bits("e_gr", 2), *bits("e_gw", 2), "e_go", *bits("e_mode", 2), "o_fu", "o_fo", "o_alive", "o_den", "o_rdy", *bits("o_rjid", 8)]
lay('S', XC + 0.3, XC + CTL - 0.3, cs)
lay('N', XC + 0.3, XC + CTL - 0.3, cn)
# density: every 10-um window of a face <= 6 pins/um
dens = {}
for f in "NS":
    xs = sorted(r[1] for r in rows if r[0] == f); j = 0; best = 0
    for i, x in enumerate(xs):
        while xs[j] < x - 10.0: j += 1
        best = max(best, i - j + 1)
    dens[f] = best / 10.0
    print(f, len(xs), "pins, max", best / 10.0, "pins/um in a 10-um window"); assert best / 10.0 <= 6.0
# group compactness
span = {}
for p in range(32):
    xs = [r[1] for r in rows if r[3].startswith(f"e_d[") and int(r[3][4:-1]) // 128 == p]
    span[p] = (FACE[p], round(min(xs), 3), round(max(xs), 3), round(max(xs) - min(xs), 3))
    assert max(xs) - min(xs) <= 23.5 and all(r[0] == FACE[p] for r in rows if r[3].startswith("e_d[") and int(r[3][4:-1]) // 128 == p)
# same port bits as the signed kvtch map
want = set()
for ln in (here / 'old/s81su_kvtc_m4_io.tcl').read_text().splitlines():
    if ln.startswith("place_pin"): want.add(ln.split("{")[1].split("}")[0])
have = {r[3] for r in rows}
assert want == have and len(rows) == len(have), (len(want), len(have), sorted(want ^ have)[:10])
name = f"s81su_kvleaf_kvtcp_{SUF}"
io = here / f'{name}_io.tcl'
io.write_text(f"# S81-KVTC-PINS kvtc position-major e_d groups ({W} x {H}), N / S faces, M3 + M5 (<= 6 pins/um)\n"
              "# generated by kvtcp_gen.py (do not edit)\n" + "\n".join(r[4] for r in sorted(rows)) + "\n")
print(len(rows), "pins")
spec = json.loads((here / 'old/kvtc.json').read_text())
spec.update(name=name, outline={"w": W, "h": H},
            outline_reason=f"Position-major e_d pin groups (S81-KVTC-PINS): the rotation transpose moves inside the tap; height {H} for the M4 centre cut.")
allp = spec["pins"]["W"] + spec["pins"]["E"]
spec["pins"] = {"S": [p for p in allp if p in ("ck", "rst", "dn_st", "dn_kind", "dn_gsel", "dn_jid", "dn_v", "i_f", "dn_d", "e_cs", "e_nb")],
                "N": [p for p in allp if p not in ("ck", "rst", "dn_st", "dn_kind", "dn_gsel", "dn_jid", "dn_v", "i_f", "dn_d", "e_cs", "e_nb")]}
spec["unregistered_ok"] = {"o_fo": "constant low in the mapped netlist (TIELO via one buffer), as in the signed kvtch (recover_place_1437.sh proof); run_kvtcp.sh re-proves it on 1_2_yosys.v"}
spec["job"]["owner"] = "S81-KVTC-PINS"
spec["job"]["purpose"] = "kvtc position-major e_d pins: kv_leaf T2B GRT overflow fix B (COORD 11-25)"
spec["job"]["views_to"] = f"physical/ref_tile/{name}/views"; spec["job"]["record_to"] = f"results/rtl/ref_tile/{name}"
pk = root / f'physical/ref_tile/{name}/pins_ns.tcl'; pk.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(io, pk)
spec["io_tcl"] = pk.relative_to(root).as_posix()
g = here / f'gen_input/{name}.json'; g.parent.mkdir(exist_ok=True); g.write_text(json.dumps(spec, indent=2) + "\n")
import ref_tile
res = ref_tile.gen(str(g), area_um2=42269 * .102, commit='9deebeb5cf', out_root=root, write=True)
print(res['kit'], res['outline'], res['findings'])
(here / f'{name}_gen_receipt.json').write_text(json.dumps(dict(res, faces=FACE, order=ORDER, group_span=span, density=dens), indent=2) + "\n")
sys.exit(any(f[0] == 'FAIL' for f in res['findings']))
