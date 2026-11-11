"""S81-FRAME-FIX-1 (11-11): the frame compiler takes the pass-through station register depth from the bound RTL.

Fast gate (no simulation): the RTL elaboration reads 2 flops for the dc23a738 stations and 1 for a pre-RTLC rewrite
(negative control on a temporary source root), the recorded return topologies and the emission shift agree with it,
and a stale record is refused."""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1] / 'tools'), str(HERE.parents[1] / 'tools/s81')]
import station_depth as SD  # noqa: E402

ONE_FLOP_RSTG = """`timescale 1ns/1ps
module dsfd_rstg (
    input wire [0:0] ck,
    input wire [65:0] i,
    output wire [65:0] o,
    input wire [0:0] rs
);
    reg [65:1] r; always @(posedge ck[0]) r <= i[65:1];
    reg v; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) v <= 1'b0; else v <= i[0];
    assign o = {r, v};
endmodule
"""


class StationDepth(unittest.TestCase):
    def test_bound_rtl_depths(self):
        fp = SD.fingerprint()
        for m in ('dsfd_qbank_N', 'dsfd_qbank_S', 'dsfd_rstg', 'ot_s81_sstn_payload536', 'ot_s81_sstn_base566'):
            self.assertEqual(set(fp[m].values()), {2}, (m, fp[m]))       # dc23a738f3: 2 flops per station
        self.assertEqual(fp['ot_s81_rly'], {'o': 1})
        self.assertEqual(SD.step('dsfd_rly_63_NS', 'o'), ('i', 1))      # through the ot_s81_rly child instance

    def test_negative_one_flop_root(self):
        """a source root whose dsfd_rstg is the pre-RTLC 1-flop form reads 1 (the depth follows the RTL)"""
        with tempfile.TemporaryDirectory() as td:
            for f in SD.RTL_FILES:
                (Path(td) / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(SD.ROOT / f, Path(td) / f)
            (Path(td) / 'rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv').write_text(ONE_FLOP_RSTG)
            old = os.environ.get('OT_S81_FRAME_SOURCE_ROOT')
            os.environ['OT_S81_FRAME_SOURCE_ROOT'] = td
            try:
                self.assertEqual(SD.step('dsfd_rstg', 'o'), ('i', 1))
                self.assertEqual(SD.step('dsfd_qbank_S', 'o_x0'), ('i_x0', 2))
            finally:
                if old is None:
                    os.environ.pop('OT_S81_FRAME_SOURCE_ROOT')
                else:
                    os.environ['OT_S81_FRAME_SOURCE_ROOT'] = old

    def test_mutant_define_reads_one(self):
        t = (SD.ROOT / 'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv').read_text()
        self.assertIn('hil <= i[535:5]', SD.preprocess(t))
        self.assertNotIn('hil <= i[535:5]', SD.preprocess(t, {'OT_SSTN_PAYLOAD_1FLOP_MUT'}))

    def test_topology_records_current(self):
        import frame_return_plan as P
        for m in ('col_h9', 'col_h10'):
            t = P.load_topology(m)                    # refuses a record whose station depths differ from the RTL
            self.assertEqual(t['station_depth'], SD.fingerprint())
            self.assertEqual(t['root_link'], 13)      # 3 dsfd_rstg x 2 + relays (was 10 with 1-flop rstg)

    def test_stale_record_refused(self):
        import frame_return_plan as P
        rec = json.loads(P.topo_record('col_h10').read_text())
        rec['station_depth']['dsfd_rstg']['o'] = 1
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'topology_col_h10.json'
            p.write_text(json.dumps(rec))
            orig = P.topo_record
            P.topo_record = lambda m: p
            try:
                with self.assertRaises(AssertionError):
                    P.load_topology('col_h10')
            finally:
                P.topo_record = orig

    def test_emission_shift(self):
        """x / go / cfg of every element move together; the shift = stations on the path x (2 - 1)"""
        import frame_return_plan as P
        d = json.loads(P.EMISSION.read_text())
        self.assertEqual(set(d['station_depth_measured']['dsfd_qbank_S'].values()), {1})
        sh = P.station_shift('col_h10', d['station_depth_measured'])
        self.assertEqual(sh, {0: 2, 2: 2, 3: 4, 4: 4, 6: 6, 7: 6, 8: 7, 9: 7, 11: 9, 12: 9, 13: 10, 14: 10})
        off, _ = P.emission('col_h10')
        self.assertEqual({k: off[k] - int(v) for k, v in d['masters']['col_h10']['off'].items() for k in [int(k)]}, sh)


if __name__ == '__main__':
    unittest.main()
