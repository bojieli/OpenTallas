#!/usr/bin/env python3
"""CLAUDE S81-PH svc: pin plans of the scan-service rd group (dsfd_svc_pc) and link station (dsfd_svc_stn) tiles and
the svc slab composition (IO hub + 32 PC tiles + 4 quadrant regions + station chains).

dsfd_svc_pc  121.068 x 43.2, instance p at (p * 265.584, 0): S face = exactly the ctrl tile dsfd_ctrl_pc's N face
             pins (the svc S face abuts the ctrl N face: tools/_s81ph_gen.py ports_ph), N face = the same signals to the
             quadrant at the same x.
dsfd_svc_stn 43.2 x 216.0: E face (hub side) and W face (quadrant side) at identical y; chained every <= 430 um.
Writes physical/s81_ph_views/ports/contract/{dsfd_svc_pc, dsfd_svc_stn}/ and physical/s81_ph_views/svc/composition.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s81_ph_coll_tiles import Plan, ROOT, r4, P   # noqa: E402

PITCH, NPC = 265.584, 32
SW, SH = 8500.032, 1576.776
PW_, PH_ = 121.068, 43.2
TW, TH = 43.2, 216.0
HW, HH = 1080.0, 129.6
REACH = 430.0


def main():
    ctrl = json.loads((ROOT / 'physical/s81_ph_views/ports/contract/dsfd_ctrl_pc/ports.json').read_text())['ports']
    pl = Plan('dsfd_svc_pc', PW_, PH_)
    pairs = [('rq', 'qrq', 'output', 'input'), ('rk', 'qrk', 'input', 'output'), ('wd', 'qwd', 'input', 'output'),
             ('rv', 'qrv', 'input', 'output'), ('r_data', 'qr_data', 'input', 'output'), ('r_tag', 'qr_tag', 'input', 'output'),
             ('r_beat', 'qr_beat', 'input', 'output')]
    for s_n, n_n, s_d, n_d in pairs:
        pins = ctrl[s_n]['pins']
        pl.dirs[s_n] = (s_d, len(pins)); pl.dirs[n_n] = (n_d, len(pins))
        for nm, ly, x0, y0, x1, y1 in pins:
            b = int(nm.split('[')[1][:-1])
            pl.put(s_n, b, 'S', 'M5', (x0 + x1) / 2)
            pl.put(n_n, b, 'N', 'M5', (x0 + x1) / 2)
    for i, p in enumerate(('ck', 'rst')):
        pl.bus(p, 1, 'input', 'N', 'M5', 0.96 + 0.192 * (580 + 5 * i))
    pl.emit('scan-service per-PC HBM interface tile: S face = the ctrl tile N face (abutted), N face = the quadrant; '
            'one register per direction')
    st = Plan('dsfd_svc_stn', TW, TH)
    y = 12.0
    for e_n, w_n, b, e_d, w_d in (('q_e', 'q_w', 515, 'input', 'output'),
                                  ('od_ev', 'od_wv', 1, 'output', 'input'), ('od_ed', 'od_wd', 512, 'output', 'input'),
                                  ('od_er', 'od_wr', 1, 'input', 'output'),
                                  ('a0_ev', 'a0_wv', 1, 'output', 'input'), ('a0_ed', 'a0_wd', 512, 'output', 'input'),
                                  ('a0_er', 'a0_wr', 1, 'input', 'output')):
        st.bus(e_n, b, e_d, 'E', 'M4', y)
        y = st.bus(w_n, b, w_d, 'W', 'M4', y)
    assert y < TH - 2, y
    for i, p in enumerate(('ck', 'rst')):
        st.bus(p, 1, 'input', 'N', 'M5', TW / 2 + 2.4 * i)
    st.emit('scan-service quadrant <-> IO hub link station (q register, od / a0 2-slot skids); E = hub side, W = quadrant side')
    # composition
    io = json.loads((ROOT / 'physical/s81_ph_views/ports/contract/dsfd_svc_io/ports.json').read_text())
    slab = json.loads((ROOT / 'physical/s81_ph_views/ports_ph/layer/dsfd_svc/ports.json').read_text())['ports']
    hx = r4(slab['od']['pins'][0][2] - io['ports']['od']['pins'][0][2])
    hy = r4(SH - HH)
    QW = SW / 4
    band_y = [r4(hy - TH * (k + 1)) for k in range(3)]       # one station row per far quadrant (Q0 lowest .. Q2)
    inst = [dict(inst=f'u_pc[{p}]', master='dsfd_svc_pc', xy=[r4(p * PITCH), 0.0], orient='R0', quadrant=p // 8) for p in range(NPC)]
    inst.append(dict(inst='u_io', master='dsfd_svc_io', xy=[hx, hy], orient='R0'))
    chains = []
    for q in range(3):                                        # Q3 (x 6375 .. 8500) contains the hub: direct
        x_end = r4((q + 0.5) * QW)                            # link entry at the quadrant's centre column
        x_hub = hx
        n = 0; x = x_hub - TW
        xs = []
        while x - x_end > 1e-6:
            xs.append(r4(x)); x -= REACH
        xs.append(r4(max(x, x_end)))
        chains.append(dict(quadrant=q, row_y=band_y[2 - q] if q < 3 else None, stations=len(xs),
                           xy=[[xx, band_y[2 - q]] for xx in xs], cycles_each_way=len(xs)))
        for i, xx in enumerate(xs):
            inst.append(dict(inst=f'u_stn_q{q}[{i}]', master='dsfd_svc_stn', xy=[xx, band_y[2 - q]], orient='R0'))
    comp = dict(
        schema='opentallas.s81_ph.composition.v1', slab='dsfd_svc', slab_um=[SW, SH],
        instances=inst, station_chains=chains,
        quadrants=[dict(quadrant=q, region_um=[r4(q * QW), PH_, r4((q + 1) * QW), band_y[2] if True else hy],
                        content='4 attention tiles + index reader share + WINDOW share (owners\' hardened views)',
                        interface=dict(S='qrq / qrk / qwd / qr_* of u_pc[8q .. 8q+7] (abutted: the PC tiles\' N face x)',
                                       N='q (515, valid-only), od (512 valid / ready), a0 (512 valid / ready)' +
                                         (' + a1 / x (index reader, single source) to u_io directly' if q == 3 else '') +
                                         ('; via the station chain u_stn_q%d' % q if q < 3 else '; direct to u_io (same quadrant)')),
                        timing='every quadrant pin a flop / 2-slot skid (DESIGN SIMPLIFICATION RULES)') for q in range(4)],
        nets=dict(hub='u_io q_q[515 q +: 515] -> quadrant q q; quadrant q od / a0 -> u_io od_* / a0_* [q] (stations for q < 3: '
                      'u_io -> u_stn_q<q>[0] E face ... W face of the last station -> quadrant q)',
                  pc='u_pc[p] S face = ctrl tile g_pc[p] N face (rq / rk / wd / rd), u_pc[p] N face = quadrant p // 8',
                  clocks='ck (stream 1.2 GHz) to every tile; rst async',
                  status='hs (ctrl st) -> die (unchanged)'),
        cost='rd / rq +1 cks each way (credit round trip +2); quadrant link +1 cks per station each way (Q0 / Q1 / Q2 chains '
             + '/'.join(str(c['stations']) for c in chains) + ' stations)')
    (ROOT / 'physical/s81_ph_views/svc').mkdir(parents=True, exist_ok=True)
    (ROOT / 'physical/s81_ph_views/svc/composition.json').write_text(json.dumps(comp, indent=1) + '\n')
    print('hub at', hx, hy, 'chains', [c['stations'] for c in chains])


if __name__ == '__main__':
    main()
