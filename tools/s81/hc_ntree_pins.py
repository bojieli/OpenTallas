#!/usr/bin/env python3
"""S81 die lead (r5 2026-10-14): top-down subslots + assigned pin files for the HC NORM-TREE variant (default-off,
owner 10-14 ~06:55; request el1011-s81die.log 12:01, branch claude/s81-norm-tree-1014 7d904baa4).

  hc_ntree_pins.py OUT_DIR      -> OUT_DIR/<master>[_C<c>].json (opentallas.s81.assigned_pins.v1, per_bit) + .tcl
                                   OUT_DIR/layout.json (cth_nt sub-layout + sp_hc_t bottom region subslots, hop estimates)

Rules: (1) ports the CLOSED predecessor already has (ctfx -> ctfx_nt, ctfs -> ctfs_nt) keep its exact rectangles
(face / layer / along-face centre), so the closed neighbours stay straight across; (2) the new NORM lanes run on fixed
column lanes common to every cth row (dl 275 b, ul 33 b, cs 64 b) left of the fd runs, N pin straight above S pin, so
ctfx_nt -> ctfs_nt -> next-row ctfx_nt hops are straight vertical wires (parent routes them on M7 over the rows,
never through a tile); (3) the collectors' N inputs sit on the face part that is open toward their far tile, the S
outputs on the side toward the cntree face they feed; 2 tracks (0.096 um) a bit on M5 (N/S), M4 (W/E), depth 0.192.
Port widths: the RTL at the kit parameters (ot_s81_hc_ntree.sv: FXW 1128, FDW 2920, DLW 275, NEX 6 / 8 / 6, O_D 104).
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = 0.096
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)


def lef_pins(path):
    import re
    t = (ROOT / path).read_text()
    w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', t).groups())
    d = {}
    for mm in re.finditer(r'PIN (\S+)\n(.*?)END \1', t, re.S):
        if 'USE POWER' in mm[2] or 'USE GROUND' in mm[2]:
            continue
        r = re.search(r'LAYER (\S+) ;\s+RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', mm[2])
        x0, y0, x1, y1 = map(float, r.groups()[1:])
        face = 'S' if y0 < 0.3 else 'N' if y1 > h - 0.3 else 'W' if x0 < 0.3 else 'E'
        c = (x0 + x1) / 2 if face in 'NS' else (y0 + y1) / 2
        dep = (y1 - y0) if face in 'NS' else (x1 - x0)
        nm = re.match(r'(.*?)(?:\[(\d+)\])?$', mm[1])
        d.setdefault(nm[1], {})[int(nm[2] or 0)] = [face, r[1], round(c, 3), round(dep, 3)]
    return {p: [v[i] for i in sorted(v)] for p, v in d.items()}


def run(face, start, bits, layer=None):
    ly = layer or ('M5' if face in 'NS' else 'M4')
    return [[face, ly, round(start + i * P, 3), 0.192] for i in range(bits)]


def write(master, tag, outline, ports, clock, note):
    rec = dict(schema='opentallas.s81.assigned_pins.v1', master=master, case='v19_ntree_variant', outline_um=outline,
               clock_entries={'stream': [clock]}, source='tools/s81/hc_ntree_pins.py (die lead r5, top-down)', rule=note,
               ports={p: dict(bits=len(v), uniform=False, per_bit=v) for p, v in ports.items()})
    for p, v in ports.items():
        cs = sorted((b[0], b[2]) for b in v)
        for a, b in zip(cs, cs[1:]):
            assert a[0] != b[0] or b[1] - a[1] >= 0.047, (master, p, a, b)
        for b in v:
            L = outline[0] if b[0] in 'NS' else outline[1]
            assert 0.2 < b[2] < L - 0.2, (master, p, b, L)
    fn = OUT / f'{master}{tag}.json'
    fn.write_text(json.dumps(rec, indent=1) + '\n')
    return fn


def check_disjoint(name, ports):
    occ = []
    for p, v in ports.items():
        for b in v:
            occ.append((b[0], b[1], b[2], p))
    occ.sort()
    for a, b in zip(occ, occ[1:]):
        if a[0] == b[0] and a[1] == b[1] and b[2] - a[2] < 0.047:
            raise SystemExit(f'{name}: pins {a} / {b} overlap')


# ---- cth rows: fixed NORM lanes (x, cth frame) left of every fd run (ctfx fd 227.29.., ctfs fd 138.20..)
LANE = dict(dl=40.032, ul=70.032, cs=80.016)     # starts; dl 275 b -> 40.03..66.43, ul 33 b -> 70.03..73.10, cs 64 b -> 80.02..86.06
cx = lef_pins('physical/ref_tile/s81hc_ctfx_ref/views/ot_s81_hc_ctfx/ot_s81_hc_ctfx.lef')
cs_ = lef_pins('physical/ref_tile/s81hc_ctfs_ref/views/ot_s81_hc_ctfs/ot_s81_hc_ctfs.lef')
H2 = 25.92
fx = {p: v for p, v in cx.items()}                 # closed rectangles kept (W clk / rst_in y kept; N y moves with h)
fx.update(dl_in=run('N', LANE['dl'], 275), dl_out=run('S', LANE['dl'], 275), ul_out=run('N', LANE['ul'], 33),
          ul_in=run('S', LANE['ul'], 33), cs_n=run('N', LANE['cs'], 64), cs_s=run('S', LANE['cs'], 64),
          tid=run('W', 8.016, 8))
check_disjoint('ctfx_nt', fx)
fs = {p: v for p, v in cs_.items()}
fs.update(dl_in=run('N', LANE['dl'], 275), dl_out=run('S', LANE['dl'], 275), ul_out=run('N', LANE['ul'], 33),
          ul_in=run('S', LANE['ul'], 33))
check_disjoint('ctfs_nt', fs)
rule = ('die lead r5 10-14: closed predecessor rectangles kept; NORM lanes dl x 40.03-66.43, ul x 70.03-73.10, cs x '
        '80.02-86.06 (M5, N straight above S) common to every cth row')
files = [write('ot_s81_hc_ctfx_nt', '', [576.72, H2], fx, 'clk', rule),
         write('ot_s81_hc_ctfs_nt', '', [576.72, H2], fs, 'clk', rule)]

# ---- bottom region (ot_s81_hc_cnbot, wires only) in the empty chain-1 tail slot of sp_hc_t: x 619.92..1196.64, y 0..1481.76
W_, H_ = 138.24, 151.2
NEX = {0: 6, 1: 8, 2: 6}
# region-local placement (origin = slot SW corner); top row C0 | C2 pairs at the outer edges (near their chains' columns),
# C1 pair below the 23.76-um centre channel its far tile (ctile_41, same column) feeds through, cntree below C1, cnrsq W.
top = 1481.76
place = {
    'C0': (0.0, top - H_), 'C2': (576.72 - 2 * W_, top - H_),
    'C1': (150.12, 957.96),
}
place_tree = (197.64, 1130.4)
place_rsq = (0.0, place_tree[1])
for c in (0, 1, 2):
    ex = NEX[c] * 32
    x0 = place[f'C{c}'][0]
    # N inputs: toward the far tile -- C0 at its W end, C2 at its E end, C1 at the pair seam under the centre channel
    if c == 0:
        na, nb = 4.032, 4.032
    elif c == 2:
        na, nb = W_ - 4.0 - 162 * P, W_ - 4.0 - 161 * P
    else:
        na, nb = W_ - 4.0 - 162 * P, 4.032
    pa = dict(f_fv=run('N', na, 7), f_nv=run('N', na + 7 * P, 8), dl=run('N', na + 15 * P, 147),
              sk=run('W', 4.032, 1), srs=run('W', 4.128, 1), flt_b=run('E', 75.6, 1))
    pb = dict(f_fv=run('N', nb, 7), f_nv=run('N', nb + 7 * P, 8), dl=run('N', nb + 15 * P, 146),
              sk=run('E', 4.032, 1), srs=run('E', 4.128, 1), flt=run('W', 75.6, 1))
    # S outputs: C0 toward its W end (down the W side to cntree W face), C2 toward its E end, C1 centred (around cntree)
    if c == 0:
        sa, sb = 4.032, 4.032
    elif c == 2:
        sa, sb = W_ - 4.0 - (ex + 11) * P, W_ - 4.0 - ex * P
    else:
        sa, sb = 20.016, 20.016
    pa.update(rvt=run('S', sa, 1), pi=run('S', sa + P, 8), ex=run('S', sa + 9 * P, ex), flt=run('S', sa + (9 + ex) * P, 1))
    pb.update(ex=run('S', sb, ex))
    for nm, pp in (('ot_s81_hc_cncla', pa), ('ot_s81_hc_cnclb', pb)):
        check_disjoint(f'{nm}C{c}', pp)
        files.append(write(nm, f'_C{c}', [W_, H_], pp, 'sk', f'die lead r5: pair C{c} at region ({x0:.2f}, {place[f"C{c}"][1]:.2f}), A W of B abutted (A.E flt_b <- B.W flt)'))
rsq = dict(f_fv=run('N', 20.016, 7), f_fc=run('N', 20.016 + 7 * P, 104), f_eps=run('N', 20.016 + 111 * P, 64),
           ul=run('N', 20.016 + 175 * P, 99), sk=run('W', 4.032, 1), srs=run('W', 4.128, 1),
           ss_v=run('E', 100.032, 1), ss=run('E', 100.128, 32), tflt=run('E', 103.296, 1), cflt=run('E', 103.392, 3),
           flt=run('W', 60.0, 1), ngo=run('E', 137.376, 1))
# Registered epoch start toward the CLOSED tree ngo_i N pin (143.100,181.398).
# Physical hop in the region frame: (138.198,1094.976) -> (340.740,1138.998) =246.564um.
check_disjoint('cnrsq', rsq)
files.append(write('ot_s81_hc_cnrsq', '', [138.24, 138.24], rsq, 'sk', 'die lead r5: W of cntree; ss / tflt / cflt on its E face toward the cntree, flt on W (chain 0 side)'))
layout = dict(
    schema='opentallas.s81.subslots.v1', variant='hc_norm_tree (default-off; serial NORM stays bound)', owner='S81 die lead r5',
    request='el1011-s81die.log 2026-10-14 12:01 (s81-norm-tree NT2), branch claude/s81-norm-tree-1014 7d904baa4',
    cth_nt=dict(base='sub_layouts.ot_s81_hc_cth (v13, 740.88)', outline=[576.72, 749.52],
                change='ctfx row ot_s81_hc_ctfx_nt 576.72 x 25.92 (was ot_s81_hc_ctfx 12.96): every row below it +12.96; '
                       'ctfs row ot_s81_hc_ctfs_nt 576.72 x 25.92 (same outline); spare 2.16 -> 0; region 740.88 -> 749.52',
                rows_shift={'ctfx_nt': 365.04, 'ctfn': 391.0, 'ctpl[half1]': 416.88, 'ctnl[j=2]': 535.68, 'ctnl[j=3]': 630.72,
                            'ctfs_nt': 725.76},
                slab_growth_um={'sp_hc_s (10 rows)': 86.4, 'sp_hc_t (12 rows)': 103.68},
                lanes=dict(dl=[40.032, 66.432], ul=[70.032, 73.104], cs=[80.016, 86.064],
                           hops_um={'ctfx_nt.dl_out -> ctfs_nt.dl_in': 725.76 - 365.04 - 25.92,
                                    'ctfs_nt.dl_out -> next ctfx_nt.dl_in': 749.52 - 725.76 - 25.92 + 365.04})),
    cnbot=dict(slot='sp_hc_t chain-1 tail column x 619.92..1196.64, y 0..1481.76 (empty: comb column top-aligned)',
               subslots={f'cncla_C{c}': [round(place[f"C{c}"][0], 3), round(place[f"C{c}"][1], 3), W_, H_] for c in range(3)} |
                        {f'cnclb_C{c}': [round(place[f"C{c}"][0] + W_, 3), round(place[f"C{c}"][1], 3), W_, H_] for c in range(3)} |
                        {'cntree (CLOSED h2 view, R0)': [place_tree[0], round(place_tree[1], 3), 181.44, 181.44],
                         'cnrsq': [place_rsq[0], round(place_rsq[1], 3), 138.24, 138.24]},
               centre_channel_um=[2 * W_, 576.72 - 2 * W_],
               centre_channel_cut=dict(bits=2 * (7 + 8) + 147 + 146, tracks_M5_M7=round(23.76 / 0.048 + 23.76 / 0.064),
                                       ratio=round((2 * 15 + 293) / (23.76 / 0.048 + 23.76 / 0.064), 3)),
               routes=['C0 ex (384) S face W ends -> cntree W face (down the W side, ~200 um)',
                       'C2 ex (384) S face E ends -> cntree E face (down the E side, ~200 um)',
                       'C1 ex (512) S face -> cntree S face around the cntree (~20 + 181 + 60 = ~260 um, W or E side)',
                       'cntree N ss/ss_v/tflt -> cnrsq E face (~200 um)',
                       'far tiles -> collector N inputs and cnrsq N (f_fv/f_fc/f_eps, ul back): parent wiring, <= 500 um to be '
                       'measured on the HC parent placement (relay only if over)']),
    pin_files=[str(f.relative_to(ROOT)) if f.is_absolute() and str(f).startswith(str(ROOT)) else str(f) for f in files])
(OUT / 'layout.json').write_text(json.dumps(layout, indent=1) + '\n')
print(json.dumps(layout['cnbot']['subslots'], indent=1)); print(layout['cnbot']['centre_channel_cut'], len(files), 'pin files')
