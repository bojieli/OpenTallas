"""Exact opt-in vector connectivity; no inference of hidden timing coverage."""
import copy
import json
from pathlib import Path
import tempfile
import lp


def main():
    with tempfile.TemporaryDirectory(prefix='regional_bind_',dir=lp.ROOT/'tools/landed_parent') as td:
        d=Path(td);rel=d.relative_to(lp.ROOT)
        child='''module regional_child(input wire clk, rst_n,
input wire [1:0] clocks, resets, d, output wire [1:0] o);
assign o=d; endmodule\n'''
        top='''module regional_top(input wire clk,rst_n,input wire [1:0] i,output wire [1:0] o);
regional_child u0(.clk(clk),.rst_n(rst_n),.clocks({2{clk}}),.resets({2{rst_n}}),.d(i),.o(o));
endmodule\n'''
        (d/'child.sv').write_text(child);(d/'top.sv').write_text(top)
        spec=dict(top='regional_top',out_dir=str(rel),sources=[str(rel/'top.sv')],child_sources=[str(rel/'child.sv')],
                  clock_ports=['clk'],clock_pins=['clk','clocks'],reset_port='rst_n',reset_pins=['rst_n','resets'],
                  regions=[dict(name='core',insts=['u0'],centre=[0,0]),
                           dict(name='lane0',insts=[],centre=[216,0]),
                           dict(name='lane1',insts=[],centre=[432,0])],
                  regional_child_clocks=[dict(inst='u0',pin='clocks',regions=['lane0','lane1'])],
                  regional_child_resets=[dict(inst='u0',pin='resets',regions=['lane0','lane1'])])
        p=lp.Parent(spec);plan=p.plan();rtl,rt=p.emit(plan,'regional_top_lp')
        assert '.clocks({ck_lane1, ck_lane0})' in rtl
        assert '.resets({lpr_b_u0_resets_1, lpr_b_u0_resets_0})' in rtl
        rec=p.record(plan,'regional_top_lp',rt)
        b=rec['regional_child_bindings']
        assert b[0]['bits'][0]['bit']==0 and b[0]['bits'][0]['clock_port']=='ck_lane0'
        assert 'no internal datapath coverage is implied' in rec['internal_crossing_obligation']
        assert lp.audit(spec,rtl)['ok']
        for old,new in [('{ck_lane1, ck_lane0}','{ck_lane0, ck_lane1}'),
                        ('{lpr_b_u0_resets_1, lpr_b_u0_resets_0}','{lpr_b_u0_resets_0, lpr_b_u0_resets_1}')]:
            assert not lp.audit(spec,rtl.replace(old,new))['ok']
        bads=[]
        for field,val in [('inst','absent'),('pin','d'),('pin','o'),
                          ('regions',['lane0','lane0']),('regions',['lane0','missing']),
                          ('regions',['core','lane0','lane1'])]:
            q=copy.deepcopy(spec);q['regional_child_clocks'][0][field]=val;bads.append(q)
        q=copy.deepcopy(spec);q['regional_child_resets'][0]['regions'].reverse();bads.append(q)
        q=copy.deepcopy(spec);q.pop('regional_child_resets');bads.append(q)
        q=copy.deepcopy(spec);q['regional_child_resets']=[];bads.append(q)
        q=copy.deepcopy(spec);q.pop('regional_child_clocks');bads.append(q)
        # Partial matching: a second clock vector cannot borrow the first
        # vector's reset epochs on different roots.
        q=copy.deepcopy(spec);q['regional_child_resets'][0]['regions']=['core','lane1'];bads.append(q)
        q=copy.deepcopy(spec);q['regions'].append(dict(name='unused',insts=[],centre=[0,216]));bads.append(q)
        for q in bads:
            try:lp.Parent(q)
            except SystemExit:pass
            else:raise AssertionError('invalid vector binding accepted: '+json.dumps(q))
        for old,new in [('{2{clk}}','{clk,clk}'),('{2{rst_n}}','{rst_n,rst_n}')]:
            (d/'top.sv').write_text(top.replace(old,new))
            try:lp.Parent(spec)
            except SystemExit:pass
            else:raise AssertionError('vector aliases accepted')
        (d/'top.sv').write_text(top)
        for rng in ('[0:1]','[2:0]','[WIDTH-1:0]'):
            (d/'child.sv').write_text(child.replace('[1:0] clocks',rng+' clocks'))
            try:lp.Parent(spec)
            except SystemExit:pass
            else:raise AssertionError('nonliteral/mismatched/ascending vector accepted')
        print('REGIONAL_BINDINGS EXACT_LSB_MAP_AND_RESET_EPOCH PASS')
        print('REGIONAL_BINDINGS INVALID_SHAPES_ALIASES_ROOTS_AND_AUDIT_MUTANTS PASS')


if __name__=='__main__':main()
