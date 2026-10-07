#!/usr/bin/env python3
"""CLAUDE S81-PH ctrl v2: pin plans of the ctrl tiles + the slab composition.

dsfd_ctrl (8,500 x 248 um) -> 32 x dsfd_ctrl_pc (one per PHY pseudo-channel column, x0 = p * 265.584 um, R0) + the
centre tile dsfd_ctrl_ctr (in PC 15's channel) + composition tie cells for the unused PHY W port inputs.
Every tile pin sits exactly on its slab pin (PHY S face, svc N face: tools/_s81ph_gen.py r9 patched port record
physical/s81_ph_views/ports_ph/layer/dsfd_ctrl); per-tile clock/reset pins and the status chain are new die nets.
Writes physical/s81_ph_views/ports/contract/{dsfd_ctrl_pc,dsfd_ctrl_ctr}/{ports.json,io_place.tcl,ports.svh} and
physical/s81_ph_views/ctrl/composition.json."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NPC, PITCH = 32, 265.584
TW, TH = 121.068, 248.376             # PC tile (PC pins span 0.96 .. 120.216 of the column; W port pins from 121.34)
CW, CH = 43.2, 43.2                   # centre tile
WID = dict(k_v=1, k_rdy=1, k_addr=30, k_len=4, k_tag=17, k_we=1, k_wdata=256, k_wstrb=32, k_wr_done=1, kr_v=1,
           kr_rdy=1, kr_tag=17, kr_beat=4, kr_data=256)
PHY_IN_TIED = {'w_v', 'w_addr', 'w_len', 'w_tag', 'wr_rdy'}


def r4(v):
    return round(v + 1e-9, 4)


def emit(master, w, h, pins, dirs, note):
    """pins: list of (name, layer, x0, y0, x1, y1); dirs: {port: (dir, bits)}"""
    d = ROOT / 'physical/s81_ph_views/ports/contract' / master
    d.mkdir(parents=True, exist_ok=True)
    ports = {}
    for nm, ly, x0, y0, x1, y1 in pins:
        base = nm.split('[')[0]
        ports.setdefault(base, dict(bits=dirs[base][1], layer=ly, pins=[]))['pins'].append([nm, ly, r4(x0), r4(y0), r4(x1), r4(y1)])
    for b, p in ports.items():
        assert len(p['pins']) == p['bits'], (master, b, len(p['pins']), p['bits'])
    rec = dict(master=master, die='contract', w_um=w, h_um=h, obs_top=7, domain='stream_1p2+hbm', instances=None,
               orients=['R0'], ports=ports, generator=dict(file='tools/s81_ph/s81_ph_ctrl_tiles.py', note=note))
    (d / 'ports.json').write_text(json.dumps(rec, indent=0))
    L = [f'# {master} (contract pin plan, tools/s81_ph/s81_ph_ctrl_tiles.py)']
    for nm, ly, x0, y0, x1, y1 in pins:
        L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                 f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    (d / 'io_place.tcl').write_text('\n'.join(L) + '\n')
    S = [f'    {dirs[b][0]} wire [{dirs[b][1] - 1}:0] {b},' for b in sorted(dirs)]
    (d / 'ports.svh').write_text('\n'.join(S) + '\n')


def main():
    slab = json.loads((ROOT / 'physical/s81_ph_views/ports_ph/layer/dsfd_ctrl/ports.json').read_text())
    P = slab['ports']
    dfi = json.loads((ROOT / 'results/rtl/s81_ph_20261006/ctrl/phy_dfi_order.json').read_text())
    assert abs(slab['h_um'] - TH) < 1e-6
    pins, dirs = [], {}
    phy_in = {'k_v', 'k_addr', 'k_len', 'k_tag', 'k_we', 'k_wdata', 'k_wstrb', 'kr_rdy'}   # PHY inputs = tile outputs
    for b, w in WID.items():
        dirs[b] = ('output' if b in phy_in else 'input', w)
    ties, extra = [], {}
    for nm, pin in zip(dfi, P['phy']['pins']):
        base, idx = re.match(r'^(\w+)(?:\[(\d+)\])?$', nm).groups()
        _, ly, x0, y0, x1, y1 = pin
        if base in WID:
            i = int(idx or 0)
            if i // WID[base] == 0:
                pins.append((f'{base}[{i % WID[base]}]', ly, x0, y0, x1, y1))
        elif base in PHY_IN_TIED:
            ties.append(dict(phy_pin=nm, x=r4((x0 + x1) / 2), y=r4((y0 + y1) / 2), layer=ly, value=0))
        else:
            extra[nm] = [ly, r4((x0 + x1) / 2), r4((y0 + y1) / 2)]
    # N face: rq / rk / wd / rd fields of PC 0
    def north(slab_port, lo, n, name):
        for i in range(n):
            _, ly, x0, y0, x1, y1 = P[slab_port]['pins'][lo + i]
            pins.append((f'{name}[{i}]', ly, x0, y0, x1, y1))
    north('rq', 0, 341, 'rq'); dirs['rq'] = ('input', 341)
    north('rk', 0, 1, 'rk'); dirs['rk'] = ('output', 1)
    north('wd', 0, 1, 'wd'); dirs['wd'] = ('output', 1)
    north('rd', 0, 256, 'r_data'); dirs['r_data'] = ('output', 256)
    north('rd', 8192, 17, 'r_tag'); dirs['r_tag'] = ('output', 17)
    north('rd', 8736, 4, 'r_beat'); dirs['r_beat'] = ('output', 4)
    north('rd', 8864, 1, 'rv'); dirs['rv'] = ('output', 1)
    xmax = max(p[4] for p in pins)
    assert xmax < TW - 0.5, xmax
    for k, nm in enumerate(('cks', 'ckh', 'rst')):
        x = 0.96 + 0.192 * (580 + 5 * k)
        pins.append((f'{nm}[0]', 'M5', x - 0.012, TH - 0.192, x + 0.012, TH)); dirs[nm] = ('input', 1)
    for face, x0, x1 in (('w', 0.0, 0.192), ('e', TW - 0.192, TW)):
        for k, nm in enumerate((f'ci_{face}', f'co_{face}')):
            for b in range(2):
                y = 124.128 + 0.384 * (2 * k + b)
                pins.append((f'{nm}[{b}]', 'M4', x0, y - 0.012, x1, y + 0.012))
            dirs[nm] = ('input' if nm.startswith('ci') else 'output', 2)
    # tile pin x must be the same in every column (relative): checked against PC 31
    p31 = {}
    for nm, pin in zip(dfi, P['phy']['pins']):
        base, idx = re.match(r'^(\w+)(?:\[(\d+)\])?$', nm).groups()
        if base in WID and int(idx or 0) // WID[base] == NPC - 1:
            p31[f'{base}[{int(idx or 0) % WID[base]}]'] = pin[2] - (NPC - 1) * PITCH
    for nm, ly, x0, *_ in pins:
        if nm in p31:
            assert abs(p31[nm] - x0) < 1e-3, nm
    emit('dsfd_ctrl_pc', TW, TH, pins, dirs,
         'one PHY pseudo-channel column of dsfd_ctrl, instance p at (p * 265.584, 0) R0; PHY S face and svc N face '
         'pins exactly on the slab pins; own cks/ckh/rst; status chain ci/co on W and E faces')
    # centre tile: in PC 15's channel, x0 = 15 * PITCH + 121.068 + 11.4 (centred under the slab ckh/cks/rst/st pins)
    cx0 = r4(15 * PITCH + TW + (PITCH - TW - CW) / 2)
    cp, cd = [], {}
    for k, nm in enumerate(('cks', 'ckh', 'rst')):
        x = 4.8 + 1.92 * k; cp.append((f'{nm}[0]', 'M5', x - 0.012, CH - 0.192, x + 0.012, CH)); cd[nm] = ('input', 1)
    for b in range(2):
        x = 12.48 + 0.96 * b; cp.append((f'st[{b}]', 'M5', x - 0.012, CH - 0.192, x + 0.012, CH))
    cd['st'] = ('output', 2)
    for k, nm in enumerate(('k_oor', 'w_oor', 'phy_rst_n')):
        x = 4.8 + 1.92 * k; cp.append((f'{nm}[0]', 'M5', x - 0.012, 0.0, x + 0.012, 0.192))
        cd[nm] = ('output' if nm == 'phy_rst_n' else 'input', 1)
    for face, x0, x1 in (('w', 0.0, 0.192), ('e', CW - 0.192, CW)):
        for b in range(2):
            y = 21.552 + 0.384 * b; cp.append((f'co_{face}[{b}]', 'M4', x0, y - 0.012, x1, y + 0.012))
        cd[f'co_{face}'] = ('input', 2)
    emit('dsfd_ctrl_ctr', CW, CH, cp, cd, 'centre tile of dsfd_ctrl: resets, PHY reset, status merge')
    comp = dict(
        schema='opentallas.s81_ph.composition.v1', slab='dsfd_ctrl', slab_um=[slab['w_um'], slab['h_um']],
        source='rtl/dsrom_sys/s81_ph/dsfd_ctrl.sv (generated by tools/s81_ph/gen_ctrl_top.py: the exact composition '
               'netlist; bench rtl/dsrom_sys/s81_ph/ctrl/run_ctrl_bench.sh)',
        instances=[dict(inst=f'g_pc[{p}].u_pc', master='dsfd_ctrl_pc', xy=[r4(p * PITCH), 0.0], orient='R0') for p in range(NPC)]
        + [dict(inst='u_ctr', master='dsfd_ctrl_ctr', xy=[cx0, r4((TH - CH) / 2)], orient='R0')],
        nets=dict(
            clocks='cks (stream 1.2 GHz) and ckh (HBM, >= 900 ps) to every dsfd_ctrl_pc and to dsfd_ctrl_ctr from the die '
                   'clock trees; ckh also drives the PHY clk pin (phy[12808]) directly; rst (async die reset) to every tile',
            status='g_pc[p].co_w -> g_pc[p+1].ci_w (p = 0..14), g_pc[p].co_w -> g_pc[p-1].ci_e (p = 31..17); '
                   'g_pc[15].co_w -> u_ctr.co_w, g_pc[16].co_w -> u_ctr.co_e; every other ci_w / ci_e tied {1: 0, 0: 1} (tie cells); '
                   'co_e pins of every PC tile unused',
            phy='g_pc[p] S-face pins abut the PHY pins of pseudo-channel p (same x); u_ctr.phy_rst_n -> phy[12809] (PHY rst_n), '
                'PHY k_oor / w_oor -> u_ctr',
            svc='g_pc[p] N-face pins are the slab rq / rk / wd / rd pins of PC p (same x, y = 248.376)'),
        tie_cells=ties, unused_phy_outputs=sorted(extra),
        timing='every tile pin is a flop except PHY k_rdy (PHY valid/ready, abutted face) and the status inputs '
               '(one OR/AND before the flop); inter-tile nets are the status chain only (one flop each end, 265 um hop)')
    (ROOT / 'physical/s81_ph_views/ctrl/composition.json').write_text(json.dumps(comp, indent=1))
    print('pc pins', len(pins), 'ctr pins', len(cp), 'ties', len(ties), 'unused', len(extra), 'ctr x0', cx0)


if __name__ == '__main__':
    main()
