"""Source-derived accounting for each emitted W1 regional reset-vector pad."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import lp

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline-module');args=ap.parse_args()
    before=None
    if args.baseline_module:
        loader=importlib.util.spec_from_file_location('lp_before',args.baseline_module)
        before=importlib.util.module_from_spec(loader);loader.loader.exec_module(before)
        before.ROOT=lp.ROOT
    with tempfile.TemporaryDirectory(prefix='regional_cost_',dir=lp.ROOT/'tools/landed_parent') as td:
        d=Path(td);rel=d.relative_to(lp.ROOT)
        (d/'child.sv').write_text('''module cost_child(input wire clk,rst_n,
input wire [1:0] clocks,resets,d,output wire [1:0] o);assign o=d;endmodule\n''')
        (d/'top.sv').write_text('''module cost_top(input wire clk,rst_n,input wire [1:0] i,output wire [1:0] o);
cost_child u0(.clk(clk),.rst_n(rst_n),.clocks({2{clk}}),.resets({2{rst_n}}),.d(i),.o(o));endmodule\n''')
        s=dict(top='cost_top',sources=[str(rel/'top.sv')],child_sources=[str(rel/'child.sv')],out_dir=str(rel),
            clock_ports=['clk'],clock_pins=['clk','clocks'],reset_port='rst_n',reset_pins=['rst_n','resets'],
            schedule='reference',reset_extra=5,
            regions=[dict(name='core',insts=['u0'],centre=[0,0]),dict(name='a',insts=[],centre=[216,0]),dict(name='b',insts=[],centre=[432,0])],
            regional_child_clocks=[dict(inst='u0',pin='clocks',regions=['a','b'])],
            regional_child_resets=[dict(inst='u0',pin='resets',regions=['a','b'])])
        p=lp.Parent(s);plan=p.plan();rtl,rt=p.emit(plan,'cost_top_lp',mut=False)
        record=p.record(plan,'cost_top_lp',rt)
        # Count actual emitted reset stages, rather than reproducing record's formula.
        stages=[int(x) for x in re.findall(r'ot_pl_pad #\(\.W\(1\), \.N\((\d+)\)\) u_lpr\w* ',rtl)]
        vector_stages=[int(x) for x in re.findall(r'ot_pl_pad #\(\.W\(1\), \.N\((\d+)\)\) u_lprb_\w+ ',rtl)]
        assert vector_stages==[5,5],vector_stages
        assert record['reset']['regional_vector_padding_FFs']==sum(vector_stages)==10
        assert record['flops']['reset']==sum(stages),(record['flops'],stages,rtl)
        if before:
            q=before.Parent(s);qplan=q.plan();oldrtl,oldrt=q.emit(qplan,'cost_top_lp',mut=False)
            assert rtl==oldrtl
            assert p.sdc(plan,'cost_top_lp')==q.sdc(qplan,'cost_top_lp')
            assert record['flops']['reset']==q.record(qplan,'cost_top_lp',oldrt)['flops']['reset']+10
        if before:
            # Always exercise a self-contained default spec. Feature-branch
            # E/W specs are optional and may not exist on canonical main.
            default={k:v for k,v in s.items() if not k.startswith('regional_child_')}
            now,old=lp.Parent(default),before.Parent(default)
            np,op=now.plan(),old.plan();nr,nrt=now.emit(np,'cost_default_lp');orr,ort=old.emit(op,'cost_default_lp')
            assert nr==orr
            assert now.sdc(np,'cost_default_lp')==old.sdc(op,'cost_default_lp')
            assert now.tb(np,'cost_default_lp',nrt)==old.tb(op,'cost_default_lp',ort)
            assert now.record(np,'cost_default_lp',nrt)==old.record(op,'cost_default_lp',ort)
        for name in (['qfd_dv_slice2_e_lpf','qfd_dv_slice2_w_lpf'] if before else []):
            path=lp.ROOT/'tools/landed_parent/specs'/f'{name}.json'
            if not path.exists():continue
            default=json.loads(path.read_text());now=lp.Parent(default);old=before.Parent(default)
            np,op=now.plan(),old.plan();nr,nrt=now.emit(np,name+'_lp');orr,ort=old.emit(op,name+'_lp')
            assert nr==orr
            assert now.sdc(np,name+'_lp')==old.sdc(op,name+'_lp')
            assert now.tb(np,name+'_lp',nrt)==old.tb(op,name+'_lp',ort)
            assert now.record(np,name+'_lp',nrt)==old.record(op,name+'_lp',ort)
        print('REGIONAL_RESET_SOURCE_PAD_COST10_AND_TOTAL_SOURCE_COUNT PASS')
        if before:print('REGIONAL_OPTIN_RTL_SDC_UNCHANGED_AND_DEFAULT_GENERATED_BYTES PASS')
if __name__=='__main__':main()
