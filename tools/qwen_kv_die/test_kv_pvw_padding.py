from pathlib import Path
import tempfile
import unittest
import kv_pvw_padding as V


class PVPaddingTests(unittest.TestCase):
    def test_bootage_frame_requires_every_exact_source(self):
        from unittest.mock import patch
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'variant').write_text('exact replica rows')
            pins={'variant':hashlib.sha256((root/'variant').read_bytes()).hexdigest()}
            with patch.object(V,'BOOTAGE_SOURCES',pins):
                self.assertEqual(V.qualify_frame('qkd_pvw_die_tb',root),pins)
                (root/'variant').write_text('modified replica rows')
                with self.assertRaisesRegex(ValueError,'boot-age source changed'):V.qualify_frame('qkd_pvw_die_tb',root)
            with self.assertRaisesRegex(ValueError,'not pinned'):V.qualify_frame('qkd_pvw_die_tb_forged',root)
            self.assertEqual(V.qualify_frame('qkd_pvw_die_t',root),{})
    def fixture(self,root,expr="{35'b0,live}",extra=''):
        p=root/'die.v';p.write_text("module die();\nwire live,other;\nwire [35:0] n_pvw_0__w_X;\nqkd_rlys_36 pvw_0__u_X_r0(.a("+expr+"),.b(n_pvw_0__w_X));\n"+extra+'\nendmodule\n')
        rows=[dict(master='qkd_rlys_36',instance='u_X_r0',width=36,pad=set(range(1,36)),output=[('w_X',b)for b in reversed(range(36))])]
        return p,rows
    def test_source_rows_parse_generated_packed_wire_without_space(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.sv';p.write_text("module qkd_pvw_die_t(input wire[4:0] v);\nwire[35:0] w_X;\nqkd_rlys_36 u_X_r0(.ck(v[0]),.a({31'b0,v}),.b(w_X));\nendmodule\n")
            rows=V.source_rows(p);self.assertEqual(rows[0]['pad'],set(range(5,36)))
    def test_live_unread_low_bit_is_not_exempted(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d));doc,c=V.apply_roles(die,rows,{'pvw_0':'qkd_pvw_s'},dict(pads={},instances={}))
            ports=doc['instances']['pvw_0__u_X_r0']['ports'];self.assertEqual(ports,dict(a=[[1,35]],b=[[1,35]]));self.assertEqual(c['new_unused_output_bits'],35)
    def test_same_bit_zero_provenance_through_inserted_repair(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d));text=die.read_text().replace('wire live,other;','wire live,other;\nwire[35:0] repair_o;')
            text=text.replace(".a({35'b0,live})",'.a(repair_o)')
            text=text.replace('endmodule',"qkd_rlys_36 repair(.a({35'b0,live}),.b(repair_o));\nendmodule")
            # The flat generated die format has a space before packed ranges.
            die.write_text(text.replace('wire[35:0]','wire [35:0]'));doc,c=V.apply_roles(die,rows,['pvw_0'],{})
            self.assertEqual(doc['instances']['pvw_0__u_X_r0']['ports']['b'],[[1,35]])
    def test_live_output_alias_does_not_create_unused_permission(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d));die.write_text(die.read_text().replace('.b(n_pvw_0__w_X)','.b({n_pvw_0__w_X[35:1],other})'))
            doc,c=V.apply_roles(die,rows,['pvw_0'],{})
            self.assertEqual(doc['instances']['pvw_0__u_X_r0']['ports']['b'],[[1,35]])
    def test_padding_output_slice_change_refused(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d));die.write_text(die.read_text().replace('.b(n_pvw_0__w_X)','.b({other,n_pvw_0__w_X[34:0]})'))
            with self.assertRaisesRegex(ValueError,'output slice changed'):V.apply_roles(die,rows,['pvw_0'],{})
    def test_zero_bit_with_real_consumer_is_not_unused(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d),extra='consumer real(.a(n_pvw_0__w_X[35]));');doc,c=V.apply_roles(die,rows,['pvw_0'],{})
            self.assertEqual(doc['instances']['pvw_0__u_X_r0']['ports']['b'],[[1,34]])
    def test_unknown_expression_blocks_unused_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d),extra='consumer real(.a(n_pvw_0__w_X ^ 36\'b0));');doc,c=V.apply_roles(die,rows,['pvw_0'],{})
            self.assertEqual(doc['instances']['pvw_0__u_X_r0']['ports']['b'],[])
    def test_live_input_cannot_be_tied_under_old_global_minimum(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d),expr="36'b0")
            with self.assertRaisesRegex(ValueError,'differs from exact source'):V.apply_roles(die,rows,['pvw_0'],{})
    def test_dynamic_pad_position_refused(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d),expr="{other,34'b0,live}")
            with self.assertRaisesRegex(ValueError,'differs from exact source'):V.apply_roles(die,rows,['pvw_0'],{})
    def test_ambiguous_literal_refused(self):
        for expr in ("{35'bx,live}","{35'b0,'1}"):
            with self.subTest(expr=expr),tempfile.TemporaryDirectory() as d:
                die,rows=self.fixture(Path(d),expr=expr)
                with self.assertRaisesRegex(ValueError,'ambiguous'):V.apply_roles(die,rows,['pvw_0'],{})
    def test_existing_permission_cannot_cover_live_field(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d));old=dict(instances={'pvw_0__u_X_r0':dict(master='qkd_rlys_36',ports=dict(b=[[0,35]]))})
            with self.assertRaisesRegex(ValueError,'covers a live field'):V.apply_roles(die,rows,['pvw_0'],old)
    def test_global_output_allowance_is_not_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d))
            with self.assertRaisesRegex(ValueError,'global relay output'):V.apply_roles(die,rows,['pvw_0'],dict(pads=dict(qkd_rlys_36=dict(b=[[0,35]]))))
    def test_stale_pad_receipt_refused(self):
        with tempfile.TemporaryDirectory() as d:
            die,rows=self.fixture(Path(d))
            with self.assertRaisesRegex(ValueError,'different die'):V.apply_roles(die,rows,['pvw_0'],dict(source_contract=dict(die_sha256='0'*64)))


if __name__=='__main__':unittest.main()
