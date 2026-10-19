#!/usr/bin/env python3
"""QXF-SEAMC 10-18: unit tests of the record-bundle rule (tools/qwen_split/record_bundles.py) on the dv2f14bn GEN netlist
seam (results/rtl/qxf_seamc_1018/fixtures/dv2f14bn_seam_die.v, cut from die.v sha a7a9f980) and the dv2f14bhd GEN lanes +
dv2f14bg land plan (Q-COLLCAL results/rtl/q_collcal_1018): the audit FAILS as built (F5, G-C2) and with Q-COLLCAL's
bus-name groups only, and PASSES after the GEN fix.   python3 tools/qwen_split/test_record_bundles.py"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import lane_groups as LG  # noqa: E402
import record_bundles as RB  # noqa: E402

FX = ROOT / 'results/rtl/qxf_seamc_1018/fixtures/dv2f14bn_seam_die.v'
CC = ROOT / 'results/rtl/q_collcal_1018'
# the compiler's compute-side bundles (claude/layerbench-qwen-1018 e016b38e4 tools/qwen_layerbench/layer_compile.py:58-67,
# (src_inst, src_port, dst_inst)); every one must be a bundle here with the same members
COMPILER = {
    'C.tx_slot': [('d2d_rom', p, 'native59') for p in ('native_tx_slot', 'native_tx_slot_kind', 'native_tx_slot_beat')],
    'C.rx_record': [('d2d_rom', p, 'native59') for p in ('native_rx_v', 'native_rx_slot', 'native_rx_slot_kind',
                                                       'native_rx_slot_beat', 'rx_payload')],
    'C.tx_record': [('native59', p, 'd2d_rom') for p in ('native_tx_v', 'native_tx_payload')],
    'C.x3_record': [('native59', p, 'd2d_rom') for p in ('x3', 'x3_identity', 'x3_generation')],
}


def lp_rows():
    fl = json.loads((CC / 'gen_bhd_asbuilt/fwd_lanes.json').read_text())
    lp = json.loads((CC / 'gen_bhd_lp/land_plan_dv2f14bg.json').read_text())
    return RB.lanes_with_plan(fl, lp)


class RecordBundles(unittest.TestCase):
    def test_compiler_bundles_covered(self):
        for b, mem in COMPILER.items():
            self.assertEqual(sorted(mem), sorted((s, sp, d) for s, sp, d, _ in RB.BUNDLES[b]), b)

    def test_asbuilt_dv2f14bn_fails_f5_and_gc2(self):
        rec = RB.audit_netlist(FX)
        self.assertEqual(rec['verdict'], 'FAIL')
        B = rec['bundles']
        c = {k: v['cycles'] for k, v in B['C.rx_record']['members'].items()}
        # F5: rx_payload a 1-frame landing (K 2, +3) beside direct native_rx_v / slot / kind / beat (+0)
        # QK-LANDEN: the as-built one-frame landing (K 2) reads E = K - 1 = 1 under the registered-en RTL -> 2 cycles
        self.assertEqual(c, {'lnk_rx_payload': 2, 'lnk_native_rx_v': 0, 'lnk_native_rx_slot': 0,
                             'lnk_native_rx_slot_kind': 0, 'lnk_native_rx_slot_beat': 0})
        s = {k: v['cycles'] for k, v in B['SF.rx_record']['members'].items()}
        # G-C2 (measured at the face pins by LAYERBENCH-QWEN on the old RTL): prog_auth_slot +5, prog_witness_slot +4, the
        # rest +3.  RLYH0-EN 10-19: under the registered-en rlyh0 RTL every as-built strap reads E = K - 1 -> one less each
        self.assertEqual((s['sf_prog_auth_slot'], s['sf_prog_witness_slot'], s['sf_prog_rx_v'], s['sf_prog_context_slot'],
                          s['lnk_rx_payload__fo1']), (4, 3, 2, 2, 2))
        self.assertTrue(B['C.tx_slot']['consistent'] and B['C.x3_record']['consistent'])
        self.assertFalse(B['SF.status']['consistent'])          # same class: levels +3 vs result_* +4
        # QK-LANDEN 10-19 made SF.tx_record fail (only its one-frame member moved); RLYH0-EN 10-19 moves every forwarded
        # member by the same edge (hop-0 en registered on every lane) -> SF.tx_record is consistent again
        self.assertEqual(sorted(f.split(':')[0] for f in rec['fails']), ['C.rx_record', 'SF.rx_record', 'SF.status'])

    def test_fixed_dv2f14bn_netlist_passes(self):
        bmap, info, rows, probs = RB.rows_from_netlist(FX)
        self.assertEqual(probs, [])
        fixed = RB.fix_lanes(list(rows.values()), bmap)
        rec = RB.audit_rows({r['bid']: r for r in fixed}, bmap)
        self.assertEqual(rec['verdict'], 'PASS', rec['fails'])
        by = {r['bid']: r for r in fixed}
        for b in ('lnk_native_rx_v', 'lnk_native_rx_slot', 'lnk_native_rx_slot_kind', 'lnk_native_rx_slot_beat'):
            self.assertEqual((by[b]['n'], by[b]['E'], by[b]['K']), (1, 2, 3), b)       # landed with the payload (landh0: K = E + 1)
        self.assertEqual({by[b]['K'] for b in bmap if bmap[b] == 'SF.rx_record'}, {4})
        self.assertTrue(all(by[b]['E_sta'] <= 3 for b in bmap if bmap[b] == 'SF.rx_record'))  # inside the D 4 window
        # the fixed lanes emitted in the GEN's instance form re-audit PASS from the netlist (round trip)
        mem, lines, widths = RB.slice_from_lanes(fixed, bundles=tuple(RB.BUNDLES), bits=RB.PORT_BITS)
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'die.v'
            out = ['module qfd_die ();'] + [f'  wire [{w - 1}:0] {n};' for n, w in widths.items()]
            out += [f'  wire [{widths[sn] - 1}:0] {dn};' for bid, b, s, d, sn, dn in mem if dn != sn]
            # sink pins of the seam instances on the emitted landing outputs, source pins on the lane inputs
            pin = {}
            for bid, b, s, d, sn, dn in mem:
                k = next(m for m in RB.BUNDLES[b] if RB._NAME.match(bid).group('port') == m[1] and m[2] == d)
                pin.setdefault(s, []).append((k[1], sn))
                pin.setdefault(d, []).append((k[3], dn))
            for i in ('d2d_rom', 'native59', 'sys_face'):
                out.append(f'  m_{i} {i} (' + ', '.join(f'.{a}({n})' for a, n in pin[i]) + ');')
            out += [l.replace('SRC_CK', 'n_ck_s').replace('SRC_EN', 'n_en_s').replace('DST_CK', 'n_ck_d')
                    .replace('DST_RS', 'n_rs_d') for l in lines] + ['endmodule']
            p.write_text('\n'.join(out) + '\n')
            rec = RB.audit_netlist(p)
            self.assertEqual(rec['verdict'], 'PASS', rec['fails'])
            self.assertEqual(sorted(rec['bundles']), sorted(RB.BUNDLES))

    def test_bhd_land_plan_asbuilt_and_collcal_fail_fix_passes(self):
        rows, cal, h0 = lp_rows()
        bmap = RB.lanes_bundle_map(rows)
        audit = lambda rs: RB.audit_rows({r['bid']: r for r in rs if r['bid'] in bmap}, bmap)
        self.assertEqual(audit(rows)['verdict'], 'FAIL')
        q = copy.deepcopy(rows)                     # Q-COLLCAL 04f8b56c6: bus-name groups only
        LG.equalize([r for r in q if r.get('E') is not None], 4, cal, h0)
        a = audit(q)
        self.assertEqual(sorted(f.split(':')[0] for f in a['fails']), ['C.rx_record', 'SF.cfg', 'SF.rx_record', 'SF.status'])
        # RLYH0-EN 10-19: the multi-frame lane's K carries the hop-0 en register edge (+1; was 1)
        self.assertEqual({k: v['K'] for k, v in a['bundles']['C.rx_record']['members'].items()}['lnk_rx_payload'], 2)
        fixed = RB.fix_lanes(copy.deepcopy(rows), bmap, 4, cal, h0)
        self.assertEqual(audit(fixed)['verdict'], 'PASS')

    def test_gen_closure_and_pads(self):
        bmap, info, rows, _ = RB.rows_from_netlist(FX)
        nfr = {b: (rows[b]['n'] if b in rows else 0) for b in bmap}
        add = RB.close_zero_stage(bmap, nfr)
        # exactly the four direct C.rx_record members (C.tx_record is direct as a WHOLE bundle: consistent, untouched)
        self.assertEqual(sorted(add), ['lnk_native_rx_slot', 'lnk_native_rx_slot_beat', 'lnk_native_rx_slot_kind',
                                       'lnk_native_rx_v'])
        nfr.update({b: 1 for b in add})
        fp = RB.frame_pads(bmap, nfr)
        self.assertEqual(fp.get('sf_prog_rx_v'), 2)                  # n 2 -> 4: E 3 = 4 - (D - 1 - 2)
        self.assertNotIn('sf_prog_auth_slot', fp)
        self.assertEqual(RB.plain_pads({'a': 'X', 'b': 'X', 'c': 'Y'}, {'a': 3, 'b': 1, 'c': 0}), {'b': 2})

    def test_group_of_honours_bundle(self):
        rows = [dict(bid='lnk_native_rx_v', src='d2d_rom', dst='native59', bundle='C.rx_record'),
                dict(bid='lnk_rx_payload', src='d2d_rom', dst='native59', bundle='C.rx_record'),
                dict(bid='sf_prog_rx_v', src='d2d_rom', dst='sys_face'), dict(bid='sf_prog_auth_slot', src='d2d_rom', dst='sys_face')]
        g = LG.group_of(rows)
        self.assertEqual(g['lnk_native_rx_v'], g['lnk_rx_payload'])
        self.assertNotEqual(g['sf_prog_rx_v'], g['sf_prog_auth_slot'])   # the name families alone miss G-C2

    def test_partial_bundle_fails_closed(self):
        bm, probs = RB.bundle_map([('lnk_native_tx_v', [('native59', 'native_tx_v'), ('d2d_rom', 'native_tx_v')])])
        self.assertTrue(probs and 'C.tx_record' in probs[0])


if __name__ == '__main__':
    unittest.main()
