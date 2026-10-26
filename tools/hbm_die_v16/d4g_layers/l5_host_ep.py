#!/usr/bin/env python3
"""H-D4G5/HOSTEP 10-18 (coordinator 0gd, lanes/OWNERS-HBM.md C2): contract post-layer L5 -- the host control-plane
endpoint swap onto the CLOSED static link endpoint.

    l5_host_ep.py IN_contract.json[.gz] OUT_contract.json --report R.json

Retires   host_cp_ep (ot_hbm_lk_ep: on-die credit loop t_cr / r_cr, ot_lkep_sub never closed), host_cp_ep_face
          (hfd_lk_ep_face), host_phy (ot_hbm_host_phy_adapt: 487 <-> 512 framing, redundant) and host_cp_rx
          (ot_hbm_host_cp_rx: endpoint face in_v / pop / f_send / t_cr).
Adds      host_ep      hfd_ep_static (CLOSED hep_static_w5f_1016-w5f-00f041029, native PASS; the COLL SerDes endpoint
                       master, 5 copies already on the die) between host_N and the host tile: sd_tx / sd_rx / sd_st
                       (512 b) straight to host_N (ot_pdie_ucie tx / rx / st).
          host_cp_rxs  ot_hbm_host_cp_rxs (rtl/hbm_accel/host_ep_20261018): link sequencer (slot-calendar TX, one-frame
                       RX pingpong drain), host link reliability (sequence / CRC-32 / 64-deep store / epoch abort =
                       COLL's link, wrapping counters), the unchanged landing256 + the credit-free packet controller.
Edges     host_cp_rxs <-> host_ep COLL face (tx_v / tx_frame 612, rx arm / release / slot, rx_pin 612, block_ready,
          phy_up); the AXI-lite master to host_cp_ingress and irq / die_fault from host_status exactly as host_cp_rx had;
          host_status.h_fault[1..5] = protocol_fault, land_fault, host_ep.fault, link_fault, seq_fault (was protocol,
          land, face fault, phy pad_fault, phy_fault; bit 0 = ingress fault unchanged).
Session   die strap pads host_cp_rxs__session[7:0] (the link epoch both ends agree on) replace host_phy__session_pad[23:0].
Open      host_ep.fault_cause (11 b), as every ep_<link>.
Integration obligations (GEN2 floorplan / relay planner): host_ep and host_cp_rxs take rst_n from the same reset-tree level
(the TX beat mirror starts on the endpoint gearbox's release edge); the tx frame edge (host_cp_rxs -> host_ep) and the
rx slot / rx_pin edges are abutted or their relay stages are added to the tile parameters TXLAT (9 + stages on
tx_v/tx_frame) / RXLAT (6 + stages on rx_slot_* + rx_pin_*).  Pure-python; no tie-off.
"""
import argparse, collections, gzip, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import l3_vm_hc_coll as L3M  # noqa: E402

REGION = 'd4g_gen2_l5_host_ep'
L3M.REGION = REGION
OLD = ['host_cp_ep', 'host_cp_ep_face', 'host_phy', 'host_cp_rx']
OWN = 'H-D4G5/HOSTEP (host control-plane endpoint)'
B = 'HOSTEP 0gd: host_cp endpoint -> hfd_ep_static (lanes/OWNERS-HBM.md C2)'


class L5(L3M.L3):
    def edge(self, src, snk, basis, clock='stream'):
        super().edge(src, snk, basis, clock)
        self.E[-1]['name'] = f'l5_{self.n:05d}'

    def clocks_of(self, n):
        for p, d in self.I[n]['ports'].items():
            if d['direction'] == 'input' and p.startswith('clk'):
                self.clock(n, p)
        self.clock(n, 'rst_n', 'reset')


def run(c, rep):
    R = L3M.Rtl()
    l5 = L5(c, R)
    I, E = l5.I, l5.E
    for n in OLD + ['host_N', 'host_status', 'host_cp_ingress']:
        assert n in I, n
    assert I['host_cp_ep']['master'] == 'ot_hbm_lk_ep' and I['host_phy']['master'] == 'ot_hbm_host_phy_adapt'
    assert I['host_N']['master'] == 'ot_pdie_ucie'
    # host_cp_rx edges to keep (AXI-lite to the ingress, irq / fault from host_status): far end survives, port in rxs
    keep = [dict(e) for e in E if (e['source'][0] == 'host_cp_rx' or e['sink'][0] == 'host_cp_rx')
            and not ({e['source'][0], e['sink'][0]} & set(OLD) - {'host_cp_rx'})
            and not (e['sink'][0] == 'host_status' and e['sink'][1] == 'h_fault')]
    hf = {e['sink'][2]: e for e in E if e['sink'][0] == 'host_status' and e['sink'][1] == 'h_fault'}
    assert sorted(hf) == [0, 1, 2, 3, 4, 5], sorted(hf)
    for n in OLD:
        l5.drop_inst(n)
    l5.inst('host_ep', 'hfd_ep_static', {}, 'host_ep',
            'host link endpoint (static): 613-b frame <-> 512-b UCIe beat gearbox (4 slots / 5 beats, marker + IDLE), RX '
            'marker hunt, off-die elastic RX pingpong; = the COLL SerDes endpoint master (CLOSED hep_static_w5f_1016-w5f-00f041029, '
            'native PASS); sd_* straight to host_N', OWN)
    l5.inst('host_cp_rxs', 'ot_hbm_host_cp_rxs', {}, 'host_cp_rxs',
            'host control-plane tile on the static endpoint: slot-calendar TX / one-frame RX pingpong sequencer, host link '
            'sequence / CRC-32 / store / epoch abort, landing256 + credit-free packet controller (no on-die credit loop)', OWN)
    for n in ('host_ep', 'host_cp_rxs'):
        l5.clocks_of(n)
    rp = I['host_cp_rxs']['ports']
    for e in keep:
        me = 'source' if e['source'][0] == 'host_cp_rx' else 'sink'
        p = e[me][1]
        assert p in rp, p
        e[me] = ['host_cp_rxs'] + e[me][1:]
        e['basis'] = (e.get('basis') or '') + f' | {REGION}: host_cp_rx -> host_cp_rxs'
        E.append(e); l5.log['edges_kept'] += 1
    assert l5.log['edges_kept'] == 18, l5.log['edges_kept']
    ep, rx = 'host_ep', 'host_cp_rxs'
    for a, b, w in (('ep_tx_v', 'tx_v', 1), ('ep_tx_frame', 'tx_frame', 612), ('ep_rx_arm_v', 'rx_arm_v', 1),
                    ('ep_rx_arm_bank', 'rx_arm_bank', 1), ('ep_rx_block_words', 'rx_block_words', 7),
                    ('ep_rx_release_v', 'rx_release_v', 1), ('ep_rx_release_bank', 'rx_release_bank', 1),
                    ('ep_rx_slot_v', 'rx_slot_v', 1), ('ep_rx_slot_bank', 'rx_slot_bank', 1),
                    ('ep_rx_slot_index', 'rx_slot_index', 6)):
        l5.edge([rx, a, 0, w], [ep, b, 0, w], B + ': host tile -> endpoint static face (flop Q -> pin flop)')
    for a, b, w in (('rx_pin_v', 'ep_rx_pin_v', 1), ('rx_pin_flit', 'ep_rx_pin_flit', 612),
                    ('rx_block_ready', 'ep_rx_block_ready', 2), ('phy_up', 'ep_phy_up', 1)):
        l5.edge([ep, a, 0, w], [rx, b, 0, w], B + ': endpoint -> host tile (flop Q -> pin flop)')
    l5.edge([ep, 'sd_tx', 0, 512], ['host_N', 'tx', 0, 512], B + ': endpoint beat -> UCIe tx (was host_phy.phy_tx)')
    l5.edge(['host_N', 'rx', 0, 512], [ep, 'sd_rx', 0, 512], B + ': UCIe rx -> endpoint (was host_phy.phy_rx)')
    l5.edge(['host_N', 'st', 0, 2], [ep, 'sd_st', 0, 2], B + ': UCIe {live, fault} -> endpoint (phy_up / fault)')
    for k, (s, p) in {1: (rx, 'protocol_fault'), 2: (rx, 'land_fault'), 3: (ep, 'fault'), 4: (rx, 'link_fault'),
                      5: (rx, 'seq_fault')}.items():
        l5.edge([s, p, 0, 1], ['host_status', 'h_fault', k, k + 1], B + ': sticky fault observation')
    # session strap pads: 24 -> 8 (the link epoch)
    dp = [x for x in c['die_pins'] if x['instance'] != 'host_phy']
    assert len(dp) == len(c['die_pins']) - 1
    dp.append(dict(name='host_cp_rxs__session', direction='input', bits=8, instance='host_cp_rxs', port='session'))
    c['die_pins'] = dp
    for g in c['gaps']:
        if g['id'] == 'G-HOST-SESSION':
            g['affects'] = [['host_cp_rxs', 'session', 0, 8]]
            g['missing_rtl'] = ('die strap pads: host_cp_rxs.session[7:0] = the host link session epoch (off-die sideband, '
                                'agreed by both link ends before any configuration can cross the link); declared as die pin '
                                'host_cp_rxs__session (was host_phy.session_pad[23:0])')
            g['region'] = REGION
            l5.log['gap_session_moved'] += 1
    for g in c['gaps']:
        g['affects'] = [a for a in g.get('affects', []) if a[0] not in OLD]
    notes = c.get('notes'); c['notes'] = {}
    ex, bad = l5.finish()
    nl = c['notes']
    c['notes'] = notes + [dict(region=k, note=v) for k, v in nl.items()] if isinstance(notes, list) else dict(notes or {}, **nl)
    rep.update(log=dict(l5.log), exposed_inputs=ex, unlisted_exposed=bad, summary=c['summary'],
               retired=OLD, added={n: I[n]['master'] for n in ('host_ep', 'host_cp_rxs')},
               h_fault={k: [e['source'] for e in E if e['sink'][0] == 'host_status' and e['sink'][1] == 'h_fault' and e['sink'][2] == k]
                        for k in range(6)},
               open_outputs_host=[o for o in c['open_outputs'] if o[0] in ('host_ep', 'host_cp_rxs')])
    return ex, bad, l5


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = L3M.ld(a.inp)
    rep = dict(schema='opentallas.hbm.d4g.gen2_l5_host_ep.v1', region=REGION, inp=str(a.inp))
    ex, bad, l5 = run(c, rep)
    json.dump(c, open(a.out, 'w'), indent=None)
    Path(a.report).write_text(json.dumps(rep, indent=1, default=str))
    print('L5', json.dumps(dict(l5.log)), 'exposed', len(ex), 'bits', sum(x[2] for x in ex), 'unlisted', len(bad))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
