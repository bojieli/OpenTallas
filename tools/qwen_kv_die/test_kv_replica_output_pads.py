"""Instance-exact spare output declarations must not hide a wider replica's live lane."""
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as P
import kv_rly_std as R
import kv_output_pads as O

RTL = '''module qkd_rlys_36(input wire ck,input wire [35:0] a,output reg [35:0] b);
always @(posedge ck) b <= a;
endmodule
'''
DIE = '''module die(ck,a,c,y,z);
input wire ck;
input wire [16:0] a;
input wire [34:0] c;
output wire [16:0] y;
output wire [34:0] z;
wire [18:0] spare0;
wire spare1;
qkd_rlys_36 r0(.ck(ck),.a({19'b0,a}),.b({spare0,y}));
qkd_rlys_36 r1(.ck(ck),.a({1'b0,c}),.b({spare1,z}));
endmodule
'''


class ReplicaPads(unittest.TestCase):
    def test_full_width_repair_stage_preserves_exact_zero_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'die.v'
            text = DIE.replace('spare0','n_r0__spare').replace('spare1','n_r1__spare')
            text = text.replace('wire [18:0] n_r0__spare;', 'wire [18:0] n_r0__spare;\nwire [35:0] mid;')
            text = text.replace("qkd_rlys_36 r0(.ck(ck),.a({19'b0,a})", "qkd_rlys_36 upstream(.ck(ck),.a({19'b0,a}),.b(mid));\nqkd_landsh_36 r0(.ck(ck),.a(mid)")
            path.write_text(text)
            old = dict(pads={'qkd_rlys_36':dict(reason='existing input dimensions',ports={'a':[[17,35]]})})
            doc = O.derive(path,existing=old)
            self.assertEqual(doc['source_contract']['paired_spare_bits'],20)
            self.assertEqual(P.pad_bits(doc['instances']['upstream']['ports']['a'],36),set(range(17,36)))
            self.assertNotIn('b',doc['instances']['upstream']['ports'])
            self.assertNotIn('a',doc['instances']['r0']['ports'])
            self.assertEqual(P.pad_bits(doc['instances']['r0']['ports']['b'],36),set(range(17,36)))
            self.assertEqual(doc['pads'],{})
            path.write_text(text.replace("19'b0,a", "19'b1,a"))
            with self.assertRaisesRegex(ValueError,'dynamic/nonzero'):
                O.derive(path,existing=old)

    def test_recovery_derives_only_paired_private_bits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'die.v'
            text = DIE.replace('spare0', 'n_r0__spare').replace('spare1', 'n_r1__spare')
            path.write_text(text)
            doc = O.derive(path)
            self.assertEqual(doc['source_contract']['paired_spare_bits'], 20)
            self.assertEqual(P.pad_bits(doc['instances']['r1']['ports']['b'],36), {35})
            path.write_text(text.replace("1'b0,c", "1'b1,c"))
            with self.assertRaisesRegex(ValueError, 'dynamic/nonzero'):
                O.derive(path)
            path.write_text(text.replace("1'b0,c", "'1,c"))
            with self.assertRaisesRegex(ValueError, 'ambiguous/unknown'):
                O.derive(path)

    def check(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root/'die.v'
            f.write_text(text)
            idx = {m.name: m for m in P.parse_modules(RTL, 'relay.sv')}
            pads = P.load_pads(dict(pads={}, instances={'r0': R.replica_pads(36,17),
                                                       'r1': R.replica_pads(36,35)}))
            return P.check(str(f), 'die', idx, {}, set(), pads=pads)

    def test_two_different_logical_widths_bind(self):
        rec = self.check(DIE)
        self.assertEqual(rec['verdict'], 'PASS', rec)
        self.assertEqual(rec['summary']['spare_out_bits'], 20)
        self.assertEqual(rec['summary']['pad_bits'], 20)

    def test_lost_live_lane_on_wider_replica_still_fails(self):
        # r1[34] is a live lane even though r0 declares [35:17] spare on the SAME master.
        text = DIE.replace('wire spare1;', 'wire spare1; wire lost;')
        text = text.replace('.b({spare1,z})', '.b({spare1,lost,z[33:0]})')
        rec = self.check(text)
        self.assertEqual(rec['verdict'], 'FAIL')
        self.assertEqual(rec['summary']['unread_net_bits'], 1)
        self.assertEqual(rec['summary']['undriven_net_bits'], 1)

    def test_tied_live_lane_and_tied_high_padding_still_fail(self):
        for before, after in [('19\'b0,a', "19'b0,1'b0,a[15:0]"), ('19\'b0,a', "19'b1,a")]:
            rec = self.check(DIE.replace(before, after))
            self.assertEqual(rec['verdict'], 'FAIL')
            self.assertGreater(rec['summary']['input_tied'], 0)


if __name__ == '__main__':
    unittest.main()
