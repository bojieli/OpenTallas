"""HBM-PGLG2 10-19: UNLOADED input pins of a landed hard child (routed-netlist proof, never by name).

pgslice_lg light kit --cts gate (claude/tw-hbm-pglg-1019 f5d151f2e) stopped in clock_entries.tcl: "OT_HYBRID: CTS source
ck_r0 must reach only standard-cell clock pins" -- the region root reaches KIND0 clk_insert_0..3 / clk_stage_4, input
ports the closed leaf keeps but whose loads synthesis removed (routed 6_final.v: port declaration only; ETM capacitance
0, no arcs).  The multi-root record classified only the measured pins.  Now: tools/ref_tile/unloaded_pins.py proves the
unloaded set from the closed route's netlist (evidence next to the record's signoff.sdc), landed_record_pins carries it as
"unused", cross-checked against the ETMs, and the pre-CTS dict ::ot_ce_landed_unused lets clock_entries.tcl skip them."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE  # noqa: E402
import unloaded_pins as UP  # noqa: E402
import test_landed_cluster_kit as K  # noqa: E402
import test_landed_raw_child_pins as H  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
UNU = '    pin(UNU) { direction : input; capacitance : 0.0000; }\n    pin(D) {'

NETLIST = r'''// routed
module other (a, y); input a; output y; BUFx2 u (.A(a), .Y(y)); endmodule
module hard (CLK, CKP, UNU, D, bus, \esc[0] , Q);
 input CLK;
 input CKP;
 input UNU;
 input D;
 input [3:0] bus;
 input \esc[0] ;
 output Q;
 wire n1;
 /* UNU never read: .X(UNU) */
 DFFHQNx1_ASAP7_75t_R r (.CLK(CLK), .D(n1), .QN(Q));
 BUFx2 b (.A(bus[1]), .Y(n1));
 sram m (.clk(CKP), .d({bus[3:2], \esc[0] }));
 assign x = D;
endmodule
'''


def leaf(root, pins=('UNU',), etm_unu=UNU, ev=None):
    v = H.leaf(root)
    for c in CE.CORNERS:
        lib = v / f'hard_{c}.lib'
        lib.write_text(lib.read_text().replace('    pin(D) {', etm_unu, 1))
    e = dict(schema=1, job=H.JOB, top='hard', netlist='6_final.v', netlist_sha256='0' * 64, inputs=4,
             unloaded=list(pins))
    e.update(ev or {})
    (root / 'results' / 'rtl' / 'ref_tile' / 'leaf' / H.JOB / 'unloaded_pins.json').write_text(json.dumps(e))
    return v


class Netlist(unittest.TestCase):
    def test_unloaded_inputs_from_the_routed_netlist(self):
        inputs, unloaded = UP.unloaded_inputs(NETLIST, 'hard')
        self.assertEqual(len(inputs), 9)
        # the comment naming UNU is no load; bus[1] (instance), bus[3:2] + \esc[0] (concatenation), D (assign) are
        self.assertEqual(unloaded, ['UNU', 'bus[0]'])
        with self.assertRaises(ValueError):
            UP.unloaded_inputs(NETLIST, 'missing')


class UnusedClass(unittest.TestCase):
    def test_record_carries_the_unused_pins_and_pre_cts_dict(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            v = leaf(root)
            rec = CE.landed_record_pins(v, root)
            self.assertEqual(rec['unused'], ['UNU'])
            self.assertEqual(sorted(rec['raw']), ['CKP'])                 # measured classes unchanged
            s = K.load(root, H.spec(root))
            self.assertIn('set ::ot_ce_landed_unused [dict create {hard/UNU} 1]', CE.landed_pre_cts_tcl(s, root))
            self.assertNotIn('UNU', CE.generate(s, root))                 # nothing measured or counted post-CTS

    def test_no_evidence_no_class_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            v = H.leaf(root)
            self.assertEqual(CE.landed_record_pins(v, root)['unused'], [])
            s = K.load(root, H.spec(root))
            self.assertFalse(any('ot_ce_landed_unused' in x for x in CE.landed_pre_cts_tcl(s, root)))
        with tempfile.TemporaryDirectory() as d:                          # plain landed child: no record at all
            root = Path(d)
            (root / 'plain').mkdir()
            self.assertEqual(CE.landed_unused_pins(K.view(root / 'plain'), root), [])

    def test_refusals_fail_closed(self):
        cases = {
            'loaded in the ETM': dict(etm_unu=UNU.replace('0.0000', '0.5')),
            'has a timing arc': dict(etm_unu=UNU.replace('capacitance : 0.0000;', 'capacitance : 0.0000; timing() { timing_type : min_clock_tree_path; }')),
            'a clock pin': dict(etm_unu=UNU.replace('direction : input;', 'direction : input; clock : true;')),
            'absent from the ETM': dict(pins=('NOPE',)),
            'a bound clock pin of the record': dict(pins=('UNU', 'CKP')),
            'evidence of another job': dict(ev=dict(job='x-r1-0')),
            'evidence of another top': dict(ev=dict(top='other')),
            'evidence without netlist hash': dict(ev=dict(netlist_sha256='')),
        }
        for why, kw in cases.items():
            with tempfile.TemporaryDirectory() as d, self.subTest(why=why):
                root = Path(d)
                v = leaf(root, **kw)
                with self.assertRaises(ValueError):
                    CE.landed_record_pins(v, root)

    def test_clock_entries_skips_only_listed_pins_of_bound_children(self):
        tcl = (REPO / 'physical' / 'common_flow' / 'clock_entries.tcl').read_text()
        self.assertIn('[dict exists $::ot_ce_landed_unused "[[$inst getMaster] getName]/[get_property $pin lib_pin_name]"]', tcl)
        self.assertIn('[dict exists $::ot_ce_counts [[$inst getMaster] getName]]\n                && [info exists ::ot_ce_landed_unused]', tcl)


class RealKind0(unittest.TestCase):
    VIEW = 'physical/ref_tile/hbm_su_static_kind0_l4_leaf1_1015/views/ot_hbm_su_static_kind0_lat4_leaf1_physical'

    def test_kind0_unloaded_clock_ports(self):
        if not (REPO / self.VIEW / 'port_latency.json').is_file():
            self.skipTest('KIND0 view not checked out')
        rec = CE.landed_record_pins(REPO / self.VIEW, REPO)
        for p in ('clk_insert_0', 'clk_insert_1', 'clk_insert_2', 'clk_insert_3', 'clk_stage_4'):
            self.assertIn(p, rec['unused'])
        self.assertFalse(set(rec['unused']) & (set(rec['R']) | set(rec['raw']) | set(rec['cotimed'])))
        self.assertEqual(rec['anchor'], 'clk_stage_0')


if __name__ == '__main__':
    unittest.main()
