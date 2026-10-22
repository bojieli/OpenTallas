"""Preparation checks only. No synthetic source/GEN packet can qualify a run."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('parent',Path(__file__).with_name('s6c_parent_minimum.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)

class ParentPreparation(unittest.TestCase):
    def test_current_source_external_ports_and_original_connection(self):
        rev='16a35bc82'
        name='rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj_ds_rl_sr_gs2_g6c_rope_ovl.sv'
        ports=P.module_ports(P.source(rev,name).decode(),'qkd_kvs_pc')
        self.assertEqual(ports['pc__land_es'],('output',288))
        self.assertEqual(ports['i_next'],('input',780))
        ctx=P.source(rev,'rtl/qwen_sys/d2d_static_20261015/qkd_kvn_ctx_ovl_rope.sv').decode()
        self.assertEqual(P.module_ports(ctx,'qkd_kvn_ctx_ovl_rope')['rst_n'],('input',1))
        statement,conns=P.parent_instance('qkd_kvs_pc pc0 (.ck(root), .i_next({a[3:0],b}), .o_next(out));','pc0','qkd_kvs_pc')
        self.assertEqual(conns['i_next'],'{a[3:0],b}')
        self.assertIn('.i_next({a[3:0],b})',statement)

    def test_incomplete_or_synthetic_input_packet_refused_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'inputs.json'
            for status in ('INCOMPLETE_NO_ACTUAL_GEN','SYNTHETIC_TEST',None):
                p.write_text(json.dumps(dict(schema=P.SCHEMA,status=status)))
                with self.subTest(status=status),self.assertRaisesRegex(ValueError,'current qualified'):
                    P.load_inputs(p)

if __name__=='__main__':unittest.main()
