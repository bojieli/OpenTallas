#!/usr/bin/env python3
"""Same-age private child reset leaves, including a real dense parent graph."""
import argparse, copy, importlib.util, json, tempfile
from pathlib import Path
import lp

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline-module');a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='child_reset_',dir=lp.ROOT/'tools/landed_parent') as tmp:
        d=Path(tmp);rel=d.relative_to(lp.ROOT)
        (d/'child.sv').write_text('module cr_child(input wire clk,rst_n,input wire[63:0] i,output reg[63:0] o); always @(posedge clk or negedge rst_n) if(!rst_n)o<=0;else o<=i; endmodule\n')
        lines=['module cr_top(input wire clk,rst_n,input wire[63:0] i,output wire[63:0] o);']
        for n in range(36):
            lines.append(f'wire[63:0] x{n}; cr_child u{n}(.clk(clk),.rst_n(rst_n),.i('+('i' if n==0 else f'x{n-1}')+f'),.o(x{n}));')
        lines.append('cr_child u_far(.clk(clk),.rst_n(rst_n),.i(x35),.o(o)); endmodule')
        (d/'top.sv').write_text('\n'.join(lines)+'\n')
        spec=dict(top='cr_top',out_dir=str(rel),sources=[str(rel/'top.sv')],child_sources=[str(rel/'child.sv')],clock_ports=['clk'],clock_pins=['clk'],reset_port='rst_n',reset_pins=['rst_n'],landing_chunk_bits=24,port_regions=dict(i='core',o='far'),regions=[dict(name='core',insts=[f'u{n}' for n in range(36)],centre=[0,0]),dict(name='far',insts=['u_far'],centre=[1050,0])])
        spec['_spec_path']=str(rel/'spec.json')
        base=lp.Parent(spec);bp=base.plan();br,bt=base.emit(bp,'cr_top_lp')
        explicit=lp.Parent(dict(spec,landing_child_reset_forest=False));ep=explicit.plan();er,et=explicit.emit(ep,'cr_top_lp')
        assert (er,explicit.sdc(ep,'cr_top_lp'),explicit.record(ep,'cr_top_lp',et))==(br,base.sdc(bp,'cr_top_lp'),base.record(bp,'cr_top_lp',bt))
        print('CHILD_RESET_DEFAULT_OFF_BYTES PASS')
        oldforest=dict(spec,landing_reset_forest=True)
        try:
            old=lp.Parent(oldforest);old.emit(old.plan(),'bad')
        except SystemExit as e:assert '36 ports' in str(e),str(e)
        else:raise AssertionError('dense scalar reset was accepted without private leaves')
        print('CHILD_RESET_EXISTING_SCALAR_LIMIT_RETAINED PASS')
        safe=dict(oldforest,landing_child_reset_forest=True);p=lp.Parent(safe);plan=p.plan();rtl,rt=p.emit(plan,'cr_top_lp');rec=p.record(plan,'cr_top_lp',rt);forest=p.reset_forest_plan(plan)
        bindings=[(region,b) for region,row in forest['regions'].items() for b in row['child_bindings']]
        assert len(bindings)==37
        assert len({(region,b['leaf']) for region,b in bindings})==37
        assert forest['regional_stages']==3 and forest['root_D_loads']==2
        assert all(row['leaves']<=1024 for row in forest['regions'].values())
        for region,b in bindings:
            assert f'.d(lpr_{region}_leaves[({b["first_expr"]})])' in rtl
        assert rec['compiler']==base.record(bp,'cr_top_lp',bt)['compiler']
        assert p.sdc(plan,'cr_top_lp')==base.sdc(bp,'cr_top_lp')
        assert lp.audit(safe,rtl)['ok'],lp.audit(safe,rtl)
        print('CHILD_RESET_UNIQUE_LEAVES_AGES_COMPILER_SDC_AUDIT PASS')
        for value in [0,1,'yes']:
            try:lp.Parent(dict(spec,landing_child_reset_forest=value))
            except SystemExit:pass
            else:raise AssertionError('nonboolean option accepted')
        print('CHILD_RESET_EXPLICIT_BOOLEAN_NEGATIVES PASS')
        try:lp.Parent(dict(spec,landing_child_reset_forest=True))
        except SystemExit as e:assert 'requires landing_reset_forest' in str(e)
        else:raise AssertionError('private leaves without same-age forest accepted')
        print('CHILD_RESET_REQUIRES_EXISTING_FOREST PASS')
        if a.baseline_module:
            loader=importlib.util.spec_from_file_location('before',a.baseline_module);old=importlib.util.module_from_spec(loader);loader.loader.exec_module(old);old.ROOT=lp.ROOT
            q=old.Parent(spec);qp=q.plan();qr,qt=q.emit(qp,'cr_top_lp')
            assert (br,base.sdc(bp,'cr_top_lp'),base.record(bp,'cr_top_lp',bt),base.tb(bp,'cr_top_lp',bt),base.bench_sh('cr_top_lp',str(rel),bp))==(qr,q.sdc(qp,'cr_top_lp'),q.record(qp,'cr_top_lp',qt),q.tb(qp,'cr_top_lp',qt),q.bench_sh('cr_top_lp',str(rel),qp))
            print('CHILD_RESET_BASELINE_ALL_DEFAULT_ARTIFACTS PASS')
if __name__=='__main__':main()
