"""Run the real chain exporter/comparator on a complete KV bundle fixture."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/qwen_layerbench'),str(ROOT/'tools')]
import netlist_relay_stages as N
import die_relay_stages as D


class RelayChainLanes(unittest.TestCase):
    def fixture(self, path):
        run=path/'run'; case=run/'case_kv'; bound=run/'port_bind_v2'
        case.mkdir(parents=True);bound.mkdir()
        groups=[]
        for port in ('att_rx_v','att_rx_kind','att_rx_beat','rx_payload'):
            groups.append(('d2d_kv',port,'kvs_attn','in_'+port,True))
        for port in ('att_tx_slot','att_tx_kind','att_tx_beat'):
            groups.append(('d2d_kv',port,'kvs_attn','in_'+port,False))
        for port in ('attn__tx_valid','attn__tx_payload'):
            groups.append(('kvs_attn',port,'d2d_kv','in_'+port,False))
        for port in ('rowtx__emb_tx_v','rowtx__emb_tx_payload'):
            groups.append(('kvs_emb',port,'d2d_kv','in_'+port,False))
        for port in ('kvn_word_valid','kvn_word_tag','kvn_word_data','kvn_word_identity','kvn_word_generation'):
            groups.append(('d2d_kv',port,'kvs_ctl','in_'+port,False))
        modules={inst:dict(ck='input') for inst in ('d2d_kv','kvs_attn','kvs_emb','kvs_ctl')}
        conns={inst:dict(ck='n_clk_core_c') for inst in modules}
        wires=['n_clk_core_c'];lines=[];lanes=[]
        for k,(si,sp,di,dp,fwd) in enumerate(groups):
            modules[si][sp]='output';modules[di][dp]='input'
            net=f'n_{si}__{sp}';wires.append(net);conns[si][sp]=net
            if fwd:
                h,m,l=f'h{k}',f'm{k}',f'l{k}'
                wires += [f'a{k}',f'b{k}',f'out{k}',f'hi{k}',f'lo{k}']
                lines += [f'  qkd_rlysh0_1 {h} (.ck(n_clk_core_c), .a({net}), .b(a{k}));',
                          f'  qkd_rlysh_1 {m} (.ck(n_clk_core_c), .a(a{k}), .b(b{k}));',
                          f'  qkd_landsh_1 {l} (.ck(n_clk_core_c), .a(b{k}), .b(out{k}), .k0(hi{k}), .k1(hi{k}), .k2(lo{k}), .tie_hi(hi{k}), .tie_lo(lo{k}));']
                conns[di][dp]=f'out{k}'
                lanes.append(dict(bid=l,landing=l,n=3,E=3,K=3,cal=0,stations=[h,m,l]))
            else:conns[di][dp]=net
        rtl=[]
        for inst,ports in modules.items():
            rtl.append('module '+inst+'_fixture ('+', '.join(f'{d} wire {p}' for p,d in ports.items())+'); endmodule')
            lines.append('  '+inst+'_fixture '+inst+' ('+', '.join(f'.{p}({n})' for p,n in conns[inst].items())+');')
        rtl += ['module qkd_rlysh0_1(input wire ck,a, output wire b); endmodule',
                'module qkd_rlysh_1(input wire ck,a, output wire b); endmodule',
                'module qkd_landsh_1(input wire ck,a,k0,k1,k2, output wire b,tie_hi,tie_lo); endmodule']
        ports=case/'ports.sv';ports.write_text('\n'.join(rtl)+'\n')
        die=bound/'die_bound.v';die.write_text('module die();\n  wire '+', '.join(wires)+';\n'+'\n'.join(lines)+'\nendmodule\n')
        masters=[i+'_fixture' for i in modules]+['qkd_rlysh0_1','qkd_rlysh_1','qkd_landsh_1']
        pb=dict(masters={m:dict(rtl=str(ports),kind='real') for m in masters},defines=[])
        (bound/'port_bind_v2.json').write_text(json.dumps(pb));(case/'SOURCE_COMMIT').write_text('fixture\n')
        (run/'fwd_lanes.json').write_text(json.dumps(dict(lanes=lanes)))
        doc=N.export(str(die),pb,'qwen_kv','fixture',[],[str(case)],'fixture',land_e={r['landing']:r for r in lanes})
        self.assertEqual(doc['problem_count'],0)
        self.assertEqual([b['age_edges'] for b in doc['buses'] if b['src']['port'].startswith('att_rx') or b['src']['port']=='rx_payload'],[4]*4)
        sched=path/'compiled.json';D.write(sched,D.compiled(doc,'complete fixture static schedule'))
        return run,sched,lanes

    def invoke(self,run,sched):
        env=dict(os.environ,OT_RELAY_SCHEDULE=str(sched))
        return subprocess.run(['bash',str(ROOT/'tools/qwen_kv_die/kv_relay_check.sh'),str(run),str(ROOT)],
                              env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    def test_chain_forwards_lane_metadata_and_source_bus_identity(self):
        with tempfile.TemporaryDirectory() as t:
            run,sched,_=self.fixture(Path(t));p=self.invoke(run,sched)
            self.assertEqual(p.returncode,0,p.stdout)
            actual=D.load(run/'relay_stages_netlist.json.gz')
            self.assertEqual(actual['problem_count'],0)
            self.assertTrue(all(b['src_nets'] for b in actual['buses']))
            self.assertIn('RELAY_CHECK PASS',p.stdout)

    def test_missing_lane_metadata_fails_instead_of_qualifying_unknown_ages(self):
        with tempfile.TemporaryDirectory() as t:
            run,sched,_=self.fixture(Path(t));(run/'fwd_lanes.json').unlink();p=self.invoke(run,sched)
            self.assertNotEqual(p.returncode,0,p.stdout)
            self.assertIn('RELAY_CHECK FAIL',p.stdout)

    def test_wrong_calendar_strap_is_rejected_by_real_exporter(self):
        with tempfile.TemporaryDirectory() as t:
            run,sched,lanes=self.fixture(Path(t));lanes[0]['K']=2
            (run/'fwd_lanes.json').write_text(json.dumps(dict(lanes=lanes)));p=self.invoke(run,sched)
            self.assertNotEqual(p.returncode,0,p.stdout)
            self.assertIn('!= (E',p.stdout)


if __name__=='__main__':unittest.main()
