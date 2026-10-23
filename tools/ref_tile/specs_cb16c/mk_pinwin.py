#!/usr/bin/env python3
"""CB16c-COLL2-FB 10-22: flat COLLIO face FALLBACK kits -- the Codex S0 regional7 / P regional5 kits UNCHANGED (RTL, macros,
landing / clock-region hooks, SDC) except that every W/E face port gets a pin_ranges window beside its owning band, so
each clock root's boundary pin flops sit within one ~70-90 um bus window with the root's entry pin beside it.

Cause (measured): route.pin_balance lays a face out alphabetically over the whole 907 um edge, so tx_data (cal_ck pin
flops, 554 sinks) spanned y 457-903 and rx_data / phy_rx / phy_tx (rx_rck / codec0p) each spanned ~450 um:
S0 r7 FB cal_ck boundary pin-flop spread 82.8 ps, S0 r7 MAIN 150.2, P r5 MAIN 263.5 (> 80 ps TT owner rule).
A 546-597 b bus needs >= 0.096 um/pin (M4, 2 tracks): 70-75 um windows give 0.126-0.128 um/pin.

  qfd_coll_face_s0_pinwin    = qfd_coll_face_s0_regional7_main + windows (cts_sink size 12 / 30 um)
  qfd_coll_face_s0_pinwin_f  = qfd_coll_face_s0_regional7_fb   + windows (cts_sink size 20 / 50 um, levels 2)
  qfd_coll_face_p_pinwin     = qfd_coll_face_p_regional5_main  + windows
Usage: mk_pinwin.py <worktree>; then tools/ref_tile/ref_tile.py gen physical/ref_tile/<kit>/spec.json for each.
"""
import json, pathlib, sys

WT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
RT = WT / 'physical/ref_tile'
OWNER = {'owner': 'Claude:CB16c-COLL2-FB', 'branch': 'claude/cb16c-fb-1022'}

# W face (y from the S corner).  Bands (S0 seq_landing / P clock_regions): rx y 54-335 (P 43-346), cal 389-497
# (P 346-518), tx 616-853 (P 605-864).
W_RANGES = {
    # rx_rck root: rx CDC read rank o_data -> rx_data / rx_valid (547 pin flops); entry beside the bus
    'rx_data': [160.0, 230.0], 'rx_rck': [231.12, 231.84], 'rx_valid': [232.92, 233.64],
    'rx_wck': [236.16, 236.88],                       # rx CDC write side, no pins; entry at the rx band
    # cal_ck root (core): tx_data td_q + tx_valid/tx_slot/peer_slot/rst_n/cdc_fault (554 pin flops) over the cal band
    'tx_data': [405.0, 475.0], 'cal_ck': [476.28, 477.0], 'tx_valid': [478.08, 478.8], 'tx_slot': [479.88, 480.6],
    'peer_slot': [481.68, 482.4], 'rst_n': [483.48, 484.2], 'cdc_fault': [485.28, 487.8],
    'cal_lck': [492.48, 493.2],                       # lcal band y 389-497 (no W pins)
    'tx_wck': [733.32, 734.04], 'tx_rck': [736.56, 737.28],   # tx band centre (no pins in either domain)
    'codec2': [740.88, 741.6],                        # bank1 y 616-853
}
# E face.  phy band (codec0p) y 346-605 (P 302-648), centre 475.
E_COMMON = {
    'phy_rx_valid': [384.48, 385.2], 'phy_up': [386.28, 387.0],
    'phy_rx': [395.0, 470.0], 'codec0p': [471.24, 471.96], 'phy_tx': [473.0, 548.0],
    'phy_tx_valid': [549.72, 550.44], 'epoch_abort': [551.52, 552.24], 'fault_cause': [553.32, 557.64],
    'codec3': [210.6, 211.32],                        # bank2 y 97-324
    'codec4': [734.4, 735.12],                        # bank3 y 616-853
}
# cal_lck-owned E outputs: S0 lcal band is W-side y 389-497 -> keep them at that height; P lcal owns an E box y 648-734
E_SLOTS = {'s0': {'phy_tx_slot': [378.72, 379.44], 'phy_rx_slot': [380.88, 381.6]},
           'p': {'phy_tx_slot': [690.12, 690.84], 'phy_rx_slot': [692.28, 693.0]}}

KITS = (('qfd_coll_face_s0_pinwin', 'qfd_coll_face_s0_regional7_main', 's0'),
        ('qfd_coll_face_s0_pinwin_f', 'qfd_coll_face_s0_regional7_fb', 's0'),
        ('qfd_coll_face_p_pinwin', 'qfd_coll_face_p_regional5_main', 'p'))


def check(rng, face):
    iv = sorted(rng.values())
    for (a, b), (c, d) in zip(iv, iv[1:]):
        assert a < b <= c < d, (face, a, b, c, d)
    assert iv[0][0] >= 5 and iv[-1][1] <= 902, face


def build(dst, src, prof):
    s_dir, d_dir = RT / src, RT / dst
    spec = json.loads((s_dir / 'spec.json').read_text())
    hand = sorted({pathlib.Path(p).name for k in ('pin_hook_after_flops', 'pre_dpl_extra', 'pre_cts_extra', 'boundary_tcl',
                                                   'pin_hook_before_flops') for p in spec.get(k, [])
                   if p.startswith(f'physical/ref_tile/{src}/')})
    spec = json.loads((s_dir / 'spec.json').read_text().replace(f'physical/ref_tile/{src}/', f'physical/ref_tile/{dst}/'))
    spec['name'] = dst
    e = dict(E_COMMON, **E_SLOTS[prof])
    assert set(W_RANGES) == set(spec['pins']['W']), set(W_RANGES) ^ set(spec['pins']['W'])
    assert set(e) == set(spec['pins']['E']), set(e) ^ set(spec['pins']['E'])
    check(W_RANGES, 'W')
    check(e, 'E')
    assert not spec.get('pin_ranges'), spec.get('pin_ranges')
    # list each face in window order (documentation only: placement follows pin_ranges)
    spec['pins']['W'] = sorted(W_RANGES, key=lambda n: W_RANGES[n][0])
    spec['pins']['E'] = sorted(e, key=lambda n: e[n][0])
    spec['pin_ranges'] = {**W_RANGES, **e}
    why = (f'CB16c-COLL2-FB 10-22 (FALLBACK, parallel to the CB16c-COLL regional split): {src} unchanged (RTL, 6 macros, '
           f'12 roots, landing / clock-region hooks, SDC, CTS settings) except W/E pin_ranges windows: every bus clustered '
           f'beside its owning band with its clock entry pin adjacent (tx_data 405-475 + cal_ck 476 over the cal band; '
           f'rx_data 160-230 + rx_rck 231 over the rx band; phy_rx 395-470 / codec0p 471 / phy_tx 473-548 on the phy band; '
           f'clock-only entries tx_wck/tx_rck/rx_wck/cal_lck/codec2-4 at their band centres). Cause: route.pin_balance laid '
           f'each face out alphabetically over the 907-um edge, so each root\'s boundary pin flops spanned ~450 um '
           f'(S0 r7 FB cal_ck 82.8 ps, S0 r7 MAIN 150.2, P r5 MAIN 263.5 > 80 ps TT). 546/597-b buses at 0.126-0.128 um/pin '
           f'(>= 0.096 = M4 2 tracks). No RTL change.')
    spec['structural_change'] = why
    spec['job'] = dict(spec.get('job') or {}, **OWNER, tag=dst.replace('qfd_coll_face_', '').replace('_', ''),
                       purpose=why)
    d_dir.mkdir(parents=True, exist_ok=True)
    for f in hand:
        (d_dir / f).write_text((s_dir / f).read_text().replace(src, dst))
    (d_dir / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    print('wrote', d_dir / 'spec.json', 'hand', hand)


if __name__ == '__main__':
    for dst, src, prof in KITS:
        build(dst, src, prof)
