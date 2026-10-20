import json
from pathlib import Path
import tempfile
import unittest
import kv_static_head_unused as H


class StaticHeadTests(unittest.TestCase):
    def fixture(self,run):
        (run/'case_kv').mkdir()
        (run/'expand.json').write_text(json.dumps(dict(frames=dict(qkd_rhead=dict(module='ot_qkh_head_native_r4_s',instances=1)))))
        (run/'case_kv/die.v.preexp').write_text('module die();\nwire ck;\nqkd_rhead head(.ck(ck));\nendmodule\n')
        die=run/'bound.v'
        body='module die();\nwire [1023:0] n_head__nb_t;\nwire [63:0] n_other;\n'
        body+=''.join(f'ot_qkh_lane8 head__g_t_{i}__u_l8(.nb(n_head__nb_t[{64*i+63}:{64*i}]));\n'for i in range(16))
        body+='ot_qkh_lane8 dynamic_child(.nb(n_other));\nendmodule\n';die.write_text(body);return die
    def test_only_exact_static_children_are_declared_unused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run);doc=H.derive(run,die)
            self.assertEqual(doc['static_head_unused_contract']['bits'],1024)
            self.assertEqual(len(doc['instances']),16)
            self.assertNotIn('dynamic_child',doc['instances'])
            self.assertEqual(doc['instances']['head__g_t_15__u_l8']['ports'],{'nb':[[0,63]]})
    def test_dynamic_parent_role_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run);p=run/'expand.json';p.write_text(p.read_text().replace('ot_qkh_head_native_r4_s','ot_qkh_head_native_r4'))
            with self.assertRaisesRegex(ValueError,'not the pinned static'):H.derive(run,die)
    def test_real_consumer_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run);die.write_text(die.read_text().replace('endmodule','consumer live(.a(n_head__nb_t[127]));\nendmodule'))
            with self.assertRaisesRegex(ValueError,'another driver/consumer'):H.derive(run,die)
    def test_alias_or_unparsed_expression_refused(self):
        for text in ('assign n_other=n_head__nb_t[63:0];','consumer live(.a(n_head__nb_t ^ 1024\'b0));'):
            with self.subTest(text=text),tempfile.TemporaryDirectory() as d:
                run=Path(d);die=self.fixture(run);die.write_text(die.read_text().replace('endmodule',text+'\nendmodule'))
                with self.assertRaises(ValueError):H.derive(run,die)
    def test_top_face_consumer_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run);die.write_text(die.read_text().replace('wire [1023:0] n_head__nb_t;','output wire [1023:0] n_head__nb_t;'))
            with self.assertRaisesRegex(ValueError,'top face'):H.derive(run,die)
    def test_slice_swap_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run);die.write_text(die.read_text().replace('[63:0]));','[127:64]));',1))
            with self.assertRaisesRegex(ValueError,'identity/role changed'):H.derive(run,die)
    def test_global_permission_removed(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run);doc=H.derive(run,die,existing=dict(pads=dict(ot_qkh_lane8=dict(nb=[[0,63]]))))
            self.assertNotIn('nb',doc['pads']['ot_qkh_lane8'])
    def test_stale_relay_pad_receipt_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run)
            with self.assertRaisesRegex(ValueError,'different die'):H.derive(run,die,existing=dict(source_contract=dict(die_sha256='0'*64)))
    def test_changed_source_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run)
            for name in H.SOURCES:
                p=run/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text((H.ROOT/name).read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'role source changed'):H.derive(run,die,root=run)

    def test_lane8_ledger_row_default_only(self):
        d7="32'sb"+format(7,'032b');d12="32'sb"+format(12,'032b');d8="32'sb"+format(8,'032b')
        self.assertTrue(H.lane8_default_row({}))
        self.assertTrue(H.lane8_default_row(dict(ADD_LAT=d7,LTW=d12)))
        self.assertFalse(H.lane8_default_row(dict(ADD_LAT=d8,LTW=d12)))
        self.assertFalse(H.lane8_default_row(dict(XYZ=d7)))
        self.assertFalse(H.lane8_default_row(dict(ADD_LAT='7')))
    def test_lane8_override_in_ledger_refused(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run)
            pp=run/'case_kv/die.v.params.json';cur=json.loads(pp.read_text()) if pp.exists() else {}
            inst=next(i for i in H.P.parse_die(str(die))[3] if i[0]=='ot_qkh_lane8')[1]
            cur[inst]=dict(ADD_LAT="32'sb"+format(8,'032b'));pp.write_text(json.dumps(cur))
            with self.assertRaisesRegex(ValueError,'identity/role changed'):H.derive(run,die)

    def test_lane8_explicit_default_instance_params_admitted(self):
        d7="32'sb"+format(7,'032b');d12="32'sb"+format(12,'032b')
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run)
            die.write_text(die.read_text().replace('ot_qkh_lane8 head__g_t_',f'ot_qkh_lane8 #(.ADD_LAT({d7}),.LTW({d12})) head__g_t_'))
            doc=H.derive(run,die);self.assertEqual(len(doc['instances']),16)
    def test_lane8_override_instance_params_refused(self):
        d8="32'sb"+format(8,'032b');d12="32'sb"+format(12,'032b')
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);die=self.fixture(run)
            die.write_text(die.read_text().replace('ot_qkh_lane8 head__g_t_3__',f'ot_qkh_lane8 #(.ADD_LAT({d8}),.LTW({d12})) head__g_t_3__'))
            with self.assertRaisesRegex(ValueError,'identity/role changed'):H.derive(run,die)


if __name__=='__main__':unittest.main()
