"""Focused source/record reset-forest fixtures. Heavy simulation runs on fleet."""
import argparse,copy,importlib.util,json
from pathlib import Path
import tempfile
import lp

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline-module');ap.add_argument('--emit-dir');a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='reset_forest_',dir=lp.ROOT/'tools/landed_parent') as td:
        d=Path(a.emit_dir).resolve() if a.emit_dir else Path(td);d.mkdir(parents=True,exist_ok=True)
        rel=d.relative_to(lp.ROOT)
        (d/'child.sv').write_text('''module forest_child #(parameter integer W=1073)(input wire clk,rst_n,input wire[W-1:0] i,output reg[W-1:0] o);
reg[3:0] c;
always @(posedge clk or negedge rst_n) if(!rst_n)begin o<=0;c<=0;end else begin o<=i+c;c<=c+1'b1;end
endmodule\n''')
        (d/'top.sv').write_text('''module forest_top #(parameter integer W=1073)(input wire clk,rst_n,input wire[W-1:0] i,output wire[W-1:0] o);
wire[W-1:0] hop;
forest_child #(.W(W)) u0(.clk(clk),.rst_n(rst_n),.i(i),.o(hop));
forest_child #(.W(W)) u1(.clk(clk),.rst_n(rst_n),.i(hop),.o(o));endmodule\n''')
        s=dict(top='forest_top',out_dir=str(rel),sources=[str(rel/'top.sv')],child_sources=[str(rel/'child.sv')],
            clock_ports=['clk'],clock_pins=['clk'],reset_port='rst_n',reset_pins=['rst_n'],
            landing_chunk_bits=24,landing_direct_timing=True,landing_reset_forest=True,
            port_regions=dict(i='core',o='far'),
            regions=[dict(name='core',insts=['u0'],centre=[0,0]),dict(name='far',insts=['u1'],centre=[1050,0])])
        s['_spec_path']=str(rel/'spec.json')
        p=lp.Parent(s);plan=p.plan();rtl,rt=p.emit(plan,'forest_top_lp');r=p.record(plan,'forest_top_lp',rt)
        assert lp.audit(s,rtl)['ok'],lp.audit(s,rtl)
        fp=r['reset']['same_depth_forest']
        assert fp['regional_stages']==3 and fp['root_D_loads']==2
        assert sum(x['leaves'] for x in fp['regions'].values())==92
        assert fp['incremental_FFs']==92
        assert all(x['scalar_child_pad_port_uses']==1 for x in fp['regions'].values())
        assert 'ot_pl_land_vector_reset_w' in rtl and 'ot_pl_land_vector_reset_r' in rtl
        assert '.ROOT_LOADS(2)' in rtl
        no=copy.deepcopy(s);no.pop('landing_reset_forest');old=lp.Parent(no);op=old.plan();orr,ort=old.emit(op,'forest_top_lp')
        assert r['flops']['reset']==old.record(op,'forest_top_lp',ort)['flops']['reset']+92
        assert r['compiler']==old.record(op,'forest_top_lp',ort)['compiler']
        assert p.sdc(plan,'forest_top_lp')==old.sdc(op,'forest_top_lp')
        for mutate in ('not_boolean','no_chunks','not_enough_paid_depth','too_many_leaves','too_many_root_loads'):
            q=copy.deepcopy(s)
            if mutate=='not_boolean':q['landing_reset_forest']=1
            if mutate=='no_chunks':q.pop('landing_chunk_bits')
            if mutate=='not_enough_paid_depth':q['regions'][1]['centre']=[216,0]
            if mutate=='too_many_leaves':q['params']={'W':24576}
            if mutate=='too_many_root_loads':q['regions'] += [dict(name=f'extra{k}',insts=[],centre=[0,0]) for k in range(31)]
            try:
                x=lp.Parent(q);x.emit(x.plan(),'bad_lp')
            except SystemExit:pass
            else:raise AssertionError('forest accepted '+mutate)
        if a.baseline_module:
            loader=importlib.util.spec_from_file_location('before',a.baseline_module);b=importlib.util.module_from_spec(loader);loader.loader.exec_module(b);b.ROOT=lp.ROOT
            bp=b.Parent(no);bplan=bp.plan();br,brt=bp.emit(bplan,'forest_top_lp')
            assert orr==br
            assert old.sdc(op,'forest_top_lp')==bp.sdc(bplan,'forest_top_lp')
            assert old.tb(op,'forest_top_lp',ort)==bp.tb(bplan,'forest_top_lp',brt)
            assert old.record(op,'forest_top_lp',ort)==bp.record(bplan,'forest_top_lp',brt)
            assert old.bench_sh('forest_top_lp',str(rel),op)==bp.bench_sh('forest_top_lp',str(rel),bplan)
        if a.emit_dir:
            s['_spec_path']=str(rel/'spec.json');(d/'spec.json').write_text(json.dumps(s,indent=2)+'\n');lp.gen(s)
        print('RESET_FOREST_EXACT_LEAVES_FLOPS_AGE_AND_FAILCLOSED_NEGATIVES PASS')
        if a.baseline_module:print('RESET_FOREST_DEFAULT_RTL_SDC_TB_RECORD_BENCH_BYTES PASS')
if __name__=='__main__':main()
