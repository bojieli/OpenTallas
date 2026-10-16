#!/usr/bin/env python3
"""S81 wide-hub block layout (S-DIE 2026-10-15, coordinator 20:25/20:40: option C5, 5 field columns removed).

Emits a --hub-layout JSON for tools/dsrom_s81_fulldie.py with a 'wide' section, from a canonical wide-hub record
(tools/s81/canonical_capacity.py --remove-columns ...) and the hub block outlines.  Everything is a parameter
(hub interval from the record, road widths, VCH, block outlines), so a calmer or more aggressive column point
reuses it unchanged.

Order W->E (the generator's native orientation, same adjacencies as HC | capture | VM | SU):
  S14W | SU | VM (MIX4 on its N face, W-aligned) | capture column (capture, gather, pq, wfc, sseq, collective,
  host bottom-up; capture faces the VM) | VCH | HC (hc_t, HC corridor, hc_s) | S14E
Returns: E half through the HC corridor + VCH to the gather E face (as today); W half through a W corridor above
MIX4 + the W strip between MIX4 and the capture column to the gather W face.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GX, GY = 0.432, 2.16

# c21h (src22 aa9e7cfae) placed outlines (um) unless overridden; VM = A2-F (S-VM COLLECT 3), MIX4 rotated onto the VM N face
BLOCKS = dict(su_s=(1889.976, 10709.256), vm=(4104.0, 4115.0), mix4=(3229.2, 1321.92),
              capture=(1727.976, 561.576), gather=(1727.976, 1045.416), pq=(1672.248, 449.256), wfc=(1727.976, 328.296),
              sseq=(1727.976, 88.536), collective=(1727.976, 2721.576), host=(1727.976, 129.576),
              hc_t=(1816.536, 9616.296), hc_s=(1816.536, 9130.296),
              bk_selector=(5270.376, 321.816), bk_collector=(5270.376, 881.256))
INST = dict(su_s='sp_su_s', vm='sp_vm', capture='sp_capture', gather='sp_gather', pq='sp_pq', wfc='sp_wfc', sseq='sp_sseq',
            collective='sp_collective', host='sp_host', hc_t='sp_hc_t', hc_s='sp_hc_s', bk_selector='bk_selector',
            bk_collector='bk_collector')


def dn(v, g):
    return round((round(v / g, 6) // 1) * g, 3)


def up(v, g):
    return round(-(-round(v / g, 6) // 1) * g, 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--canonical', required=True, help='canonical wide-hub record (wide_hub.hub_x_um)')
    ap.add_argument('--s14w', type=float, default=661.6, help='S14W road width um (0.50 at its pre-TDM demand)')
    ap.add_argument('--s14e-min', type=float, default=399.0, help='S14E minimum width um (0.50)')
    ap.add_argument('--vch', type=float, default=1296.0, help='VCH width um (capture column | HC)')
    ap.add_argument('--cw', type=float, default=1728.0, help='capture column width um (generator hub column)')
    ap.add_argument('--band-top', type=float, default=3041.256, help='SW PHY/CTRL/SVC band top (um)')
    ap.add_argument('--spine-gap', type=float, default=172.8)
    ap.add_argument('--abut', type=float, default=21.6)
    ap.add_argument('--seam', type=float, default=43.2, help='capture | gather seam (pq-cnt leaves)')
    ap.add_argument('--su-channel', type=float, default=604.8, help='service channel under the SU (VM S-face ends -> SW service)')
    ap.add_argument('--mix4-west', type=float, default=875.0, help='MIX4 overhangs the SU top by this much (widens the W strip)')
    ap.add_argument('--vmhc-seam', type=float, default=345.6, help='capture-column seam reserved for the VM <-> HC buses')
    ap.add_argument('--hc-floor', type=float, default=3216.24)
    ap.add_argument('--hc-corr', type=float, default=799.2)
    ap.add_argument('--w-corr', type=float, default=799.2, help='W return corridor height above MIX4')
    ap.add_argument('--bk', default='13872.384,1464.48,13872.384,23654.16', help='bk_selector x,y,bk_collector x,y')
    ap.add_argument('--phy-sw-x', type=float, default=2884.896)
    ap.add_argument('--block', action='append', default=[], help='override NAME=W,H')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    B = dict(BLOCKS)
    for o in a.block:
        n, wh = o.split('=')
        B[n] = tuple(float(v) for v in wh.split(','))
    cap = json.loads((ROOT / a.canonical if not Path(a.canonical).is_absolute() else Path(a.canonical)).read_text())
    hx0, hx1 = cap['wide_hub']['hub_x_um']
    # ---- x
    su_x = up(hx0 + a.s14w, GX)
    vm_x = up(su_x + B['su_s'][0], GX)
    x_sp = up(vm_x + B['vm'][0], GX)
    x_vch = up(x_sp + a.cw, GX)
    x_spe = up(x_vch + a.vch, GX)
    x_fe = up(x_sp + 2 * a.cw + a.vch, GX)
    hc_x1 = x_spe + B['hc_t'][0]
    s14e = hx1 - max(hc_x1, x_fe)
    assert s14e >= a.s14e_min - 1e-6, ('S14E below its 0.50 width', round(s14e, 1), a.s14e_min)
    # ---- y (VM-centred cluster, coordinator 21:xx): the HC tower is split hc_s LOW | corridor | hc_t HIGH so the VM and
    # the collective face hc_s straight across the capture-column floor and the quiet VCH; the gather is centred on the
    # HC corridor (E returns run straight in); capture + WFC on the VM E face, the gather above the capture, PQ above
    # the gather, the collective on the VM S face (E end, its E face on the capture-column floor), host under it, SU on
    # the VM W face, MIX4 on the VM N face, the W strip (MIX4 E edge .. capture column) opens the gather W face
    su_y = up(a.band_top + a.spine_gap + a.su_channel, GY)   # SU over the SW IO band's x: a service channel under it
    su_top = su_y + B['su_s'][1]
    hc_s = (x_spe, a.hc_floor, *B['hc_s'])
    c0 = a.hc_floor + B['hc_s'][1]
    c1 = c0 + a.hc_corr
    hc_t = (x_spe, up(c1, GY), *B['hc_t'])
    ga_y = up((c0 + c1) / 2 - B['gather'][1] / 2, GY)
    cap_y = dn(ga_y - a.seam - B['capture'][1], GY)     # never shrink the pq-cnt seam
    vm_top = cap_y + B['capture'][1]
    vm_y = up(vm_top - B['vm'][1], GY)
    vm_top = vm_y + B['vm'][1]
    assert vm_y >= su_y and su_top >= vm_top - 1e-6, ('VM outside the SU height', vm_y, su_y, vm_top, su_top)
    mix4 = (vm_x, up(vm_top + a.abut, GY), B['mix4'][0], B['mix4'][1])
    mix4_top = mix4[1] + mix4[3]
    stack = {'capture': (x_sp, cap_y, *B['capture']), 'gather': (x_sp, ga_y, *B['gather'])}
    stack['wfc'] = (x_sp, dn(cap_y - a.abut - B['wfc'][1], GY), *B['wfc'])
    y = up(ga_y + B['gather'][1] + a.spine_gap, GY)
    for n in ['pq', 'sseq']:
        stack[n] = (x_sp, y, B[n][0], B[n][1])
        y = up(y + B[n][1] + a.spine_gap, GY)
    coll = (dn(x_sp - B['collective'][0], GX), dn(vm_y - a.abut - B['collective'][1], GY), *B['collective'])
    stack['collective'] = coll
    stack['host'] = (coll[0], dn(coll[1] - a.spine_gap - B['host'][1], GY), *B['host'])
    seam = None
    wc0 = up(max(su_top, mix4_top) + a.abut, GY)
    wc1 = wc0 + a.w_corr
    bx = [float(v) for v in a.bk.split(',')]
    blocks = {INST['su_s']: [su_x, su_y, *B['su_s'], False], INST['vm']: [vm_x, vm_y, *B['vm'], True],
              INST['hc_t']: [*hc_t, False], INST['hc_s']: [*hc_s, False],
              INST['bk_selector']: [bx[0], bx[1], *B['bk_selector'], True],
              INST['bk_collector']: [bx[2], bx[3], *B['bk_collector'], True]}
    for n, box in stack.items():
        blocks[INST[n]] = [*box, False]
    wfc_y = stack['wfc'][1]
    top = max(b[1] + b[3] for k, b in blocks.items() if k.startswith('sp_'))
    rec = dict(
        schema='opentallas.s81.hub_layout.v2', source='tools/s81/wide_hub_layout.py', canonical=a.canonical,
        order='S14W | SU | VM (+MIX4 N) | capture column | VCH | HC | S14E',
        blocks=blocks,
        corridor=[x_spe, c0, B['hc_t'][0], a.hc_corr],
        mix4_slot=list(mix4),
        wide=dict(x_sp=x_sp, x_fe=x_fe, x_vch=x_vch, vch=a.vch, cw=a.cw,
                  s14w=[hx0, su_x], s14e=[hx1 - s14e, hx1],
                  corr_w=[wc0, wc1], strip_w=[mix4[0] + mix4[2], vm_top, x_sp, wc1], vmhc_seam=seam,
                  hub_w=[su_x, wc0, x_sp, top + a.spine_gap],
                  capfree=[x_sp, a.band_top + a.spine_gap, x_vch, wfc_y - a.abut],
                  **({'seam_rect': [x_sp, seam[0], x_vch, seam[1]]} if seam else {}),
                  above_su=[su_x, su_top + a.abut, vm_x, wc1],
                  vm_s=[vm_x, a.band_top + a.spine_gap, coll[0] - a.abut, vm_y - a.abut],
                  su_under=[hx0, a.band_top + 8.64, x_sp, su_y - 8.64],
                  phy_x=dict(SW=a.phy_sw_x, SE=33000.0 - a.phy_sw_x - 8500.056)),
        checks=dict(hub_um=[hx0, hx1], hub_width_um=round(hx1 - hx0, 3), s14w_um=round(su_x - hx0, 3),
                    s14e_um=round(s14e, 3), vch_um=a.vch, top_um=round(top, 3), su_top=round(su_top, 3),
                    vm_top=round(vm_top, 3), mix4_top=round(mix4_top, 3), hc_corridor=[round(c0, 3), round(c1, 3)],
                    w_corridor=[wc0, round(wc1, 3)]))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['checks']))


if __name__ == '__main__':
    main()
