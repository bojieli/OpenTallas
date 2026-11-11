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


class InbandPricing(unittest.TestCase):
    """COORD item (3): a landed schedule's in-band station edges beyond the emission measurement are priced, x / go /
    cfg must move together, the go_tag lead over go stays in the proven window, and a stale schedule is refused."""
    CMP = HERE.parents[1] / 'results/arch/s81_dv_1016/frame_l4_cluster/compiler'

    def sched(self, m):
        return json.loads((self.CMP / f'{m}_schedule.json').read_text())

    def test_committed_schedules_flat_equivalent(self):
        import frame_return_plan as P
        for m in ('col_h9', 'col_h10'):
            s = self.sched(m)
            self.assertEqual(set(P.inband_shift(m, s).values()), {0}, m)
            self.assertEqual({v['go'] - v['go_tag'] for v in P.schedule_paths(s).values()}, {2}, m)

    def bump(self, s, e, pins, n=1):
        st = s['station_inputs'][e]
        if 'x' in pins:
            for v in st['inputs'].values():
                for q in v['paths']:
                    q['flat_link_edges'] += n
        for k in pins:
            if k != 'x':
                st['control'][k]['path_edges'] += n

    def test_extra_station_priced(self):
        # the bs2/bs3 qbank pin cycle form: one relay on x / go / cfg of e2 and e3, not on go_tag
        import frame_return_plan as P
        s = self.sched('col_h9')
        for e in ('e2', 'e3'):
            self.bump(s, e, ('x', 'go', 'cfg_v'))
        got = P.inband_shift('col_h9', s)                 # go_tag lead 3: inside the proven window, priced +1
        self.assertEqual({k: v for k, v in got.items() if v}, {2: 1, 3: 1})
        self.bump(s, 'e2', ('x', 'go', 'cfg_v'))
        with self.assertRaises(AssertionError) as cm:     # a second relay: lead 4 > proven 3, refused until benched
            P.inband_shift('col_h9', s)
        self.assertIn('go_tag lead', str(cm.exception))

    def test_xgo_skew_refused(self):
        import frame_return_plan as P
        s = self.sched('col_h9')
        self.bump(s, 'e5', ('x',))
        with self.assertRaises(AssertionError) as cm:
            P.inband_shift('col_h9', s)
        self.assertIn('skew', str(cm.exception))

    def test_asbuilt_schedule_not_refused(self):
        # TOK-VERIFY-1 11-11: the strict-bind compile uses as-built schedules (no station_depth / path_edges); plan_phase
        # keeps the main behaviour for them (crossing added_edges only), inband_shift itself would refuse them
        import inspect
        import frame_return_plan as P
        src = inspect.getsource(P.plan_phase)
        self.assertIn("for e in schedule['station_inputs']} if 'asbuilt' in schedule", src)

    def test_stale_schedule_refused(self):
        import frame_return_plan as P
        s = self.sched('col_h10')
        s['station_depth'] = {k: {q: 1 for q in v} for k, v in s['station_depth'].items()}
        with self.assertRaises(AssertionError):
            P.inband_shift('col_h10', s)
        s = self.sched('col_h10')
        for st in s['station_inputs'].values():
            for c in st['control'].values():
                c.pop('path_edges', None)
        with self.assertRaises(AssertionError):
            P.inband_shift('col_h10', s)


class PipelineFloor(unittest.TestCase):
    def test_wqb_pipeline_floor_from_table(self):
        # TOK-VERIFY-1 11-11: the wq_b + idx.q pipeline period must come from the measured FLOORS table
        sys.path[:0] = [str(HERE / 'layer_prog'), str(HERE.parents[1])]
        import xs_field_calendar as XF
        import xs_wqb_die as WD
        self.assertEqual(WD.PIPE_FLOOR, max(XF.FLOORS[o][1] for o in WD.PIPE_OPS))
        self.assertGreaterEqual(WD.PIPE_PERIOD, XF.FLOORS['attn.wq_b'][1])


if __name__ == '__main__':
    unittest.main()
