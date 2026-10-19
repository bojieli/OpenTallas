import json
from pathlib import Path
import tempfile
import unittest
import kv_fault_plane as F


class InventoryTests(unittest.TestCase):
    def fixture(self,root,extra='',last_a='n_s0[35:0]',first_a="36'b0",kf_pin=False):
        (root/'case_kv').mkdir();(root/'port_bind_v2').mkdir()
        cells="""qkd_rlysh0_36 first(.ck(ckWS),.en(rst),.a(FIRST),.b(n_s0));
qkd_landsh_36 last(.ck(ckc),.ckf(ckWS),.rs(rst),.a(LAST),.b(n_spare),.fault(fault));
qkd_kvs_attn kvs_attn(.ck(ckc),.rst_n(rst),.ufh(hf));
""".replace('FIRST',first_a).replace('LAST',last_a)
        for reg in ('WS','WN','ES','EN'):
            cells+=f'qkd_ctrl_kc kc_{reg}(.ck(ck{reg}),.rsi(rst));\n'
        die='module die();\nwire ckWS,ckWN,ckES,ckEN,ckc,rst,fault,hf;\nwire [35:0] n_s0,n_spare;\n'+cells+extra+'\nendmodule\n'
        for p in ('case_kv/die.v','port_bind_v2/die_bound.v'):(root/p).write_text(die)
        names=['first','last','kvs_attn','kc_WS','kc_WN','kc_ES','kc_EN']
        (root/'case_kv/place.tcl').write_text('\n'.join(f'ot_mts::place [$_blk findInst {n}] {i*50}.0 0.0 R0' for i,n in enumerate(names)))
        def macro(name,pins):
            return 'MACRO '+name+'\n SIZE 21.6 BY 21.6 ;\n'+''.join(' PIN '+p+'\n PORT\n LAYER M4 ;\n RECT 0 1 0.1 1.1 ;\n END\n END '+p+'\n' for p in pins)+'END '+name+'\n'
        lef=macro('qkd_ctrl_kc',['kf[0]'] if kf_pin else [])+macro('qkd_kvs_attn',['ufh[0]'])
        lef+=macro('qkd_rlysh0_36',[f'a[{i}]' for i in range(36)])
        lef+=macro('qkd_landsh_36',['fault[0]']+[f'b[{i}]' for i in range(36)])
        (root/'case_kv/elements.lef').write_text(lef)
        lane=dict(stations=['first','last'],S=36,src_tree='WS',dst_tree='c',en='rst',rs='rst',K=2,landed=4)
        (root/'fwd_lanes.json').write_text(json.dumps(dict(lanes=[lane])))

    def test_exact_inventory_and_missing_physical_source_refused(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r);v=F.inventory(r)
            self.assertEqual(len(v['sources']),6)
            self.assertEqual(len(v['physical_blockers']),4)
            self.assertEqual(v['spare_capacity_by_region']['WS'],36)
            self.assertTrue(all(s['requires_sticky_latch'] for s in v['sources'] if s.get('master')=='qkd_ctrl_kc'))

    def test_live_consumer_is_not_spare(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r,extra='some_consumer real(.a(n_spare[35]));')
            v=F.inventory(r);self.assertEqual(v['spare_transport_candidates'][0]['free_bits'],list(range(35)))

    def test_unknown_expression_is_not_spare(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r,extra='some_consumer real(.a(n_spare ^ n_s0));')
            self.assertEqual(F.inventory(r)['spare_capacity_by_region']['WS'],0)

    def test_dynamic_source_is_not_spare(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r,first_a='{35\'b0,fault}')
            self.assertEqual(F.inventory(r)['spare_transport_candidates'][0]['free_bits'],list(range(1,36)))

    def test_reties_at_intermediate_hop_admitted_only_as_unused(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);self.fixture(r,last_a="36'b0",kf_pin=True)
            v=F.inventory(r);self.assertEqual(v['physical_blockers'],[])
            self.assertEqual(v['spare_capacity_by_region']['WS'],36)
            # The first hop's original payload must remain unconsumed before it is repurposed.
            path=r/'port_bind_v2/die_bound.v';path.write_text(path.read_text().replace('endmodule','some_consumer real(.a(n_s0[5]));\nendmodule'))
            self.assertNotIn(5,F.inventory(r)['spare_transport_candidates'][0]['free_bits'])


if __name__=='__main__':unittest.main()
