"""S81-FRAME4 10-19: landing_reset_forest_children -- child reset pads on their own kept forest leaves + the three-level
forest (ot_pl_land_reset_forest3) for regions with more than 1024 leaves.  Source/record fixtures only (heavy simulation
of a user, e.g. the S81 frame bench, runs on the fleet).  Run: python3 test_reset_forest_children.py"""
import copy
import re
import tempfile
from pathlib import Path

import lp

W, NS = 1100, 39


def fixture(rel):
    d = lp.ROOT / rel
    (d / 'child.sv').write_text('''module rfc_child #(parameter integer W=1100)(input wire clk,rst_n,input wire[W-1:0] i,output reg[W-1:0] o);
reg[3:0] c;
always @(posedge clk or negedge rst_n) if(!rst_n)begin o<=0;c<=0;end else begin o<=i+c;c<=c+1'b1;end
endmodule
module rfc_small(input wire clk,rst_n,input wire i,output reg o);
always @(posedge clk or negedge rst_n) if(!rst_n) o<=1'b0; else o<=i^o;
endmodule
''')
    smalls = '\n'.join(f'rfc_small u_s{k}(.clk(clk),.rst_n(rst_n),.i(i[{k}]),.o(s[{k}]));' for k in range(NS))
    (d / 'top.sv').write_text(f'''module rfc_top #(parameter integer W={W})(input wire clk,rst_n,input wire[W-1:0] i,output wire[W-1:0] o,output wire[{NS-1}:0] s);
wire[W-1:0] hop;
rfc_child #(.W(W)) u0(.clk(clk),.rst_n(rst_n),.i(i),.o(hop));
rfc_child #(.W(W)) u1(.clk(clk),.rst_n(rst_n),.i(hop),.o(o));
{smalls}
endmodule
''')
    core = ['u0'] + [f'u_s{k}' for k in range(NS)]
    s = dict(top='rfc_top', out_dir=str(rel), sources=[str(rel / 'top.sv')], child_sources=[str(rel / 'child.sv')],
             clock_ports=['clk'], clock_pins=['clk'], reset_port='rst_n', reset_pins=['rst_n'],
             landing_chunk_bits=1, landing_reset_forest=True, landing_reset_forest_children=True,
             port_regions=dict(i='core', o='far', s='core'),
             regions=[dict(name='core', insts=core, centre=[0, 0]), dict(name='far', insts=['u1'], centre=[1050, 0])])
    s['_spec_path'] = str(rel / 'spec.json')
    return s


def build(s):
    p = lp.Parent(s)
    plan = p.plan()
    rtl, rt = p.emit(plan, 'rfc_top_lp')
    return p, plan, rtl, p.record(plan, 'rfc_top_lp', rt)


def main():
    with tempfile.TemporaryDirectory(prefix='reset_forest_children_', dir=lp.ROOT / 'tools/landed_parent') as td:
        rel = Path(td).relative_to(lp.ROOT)
        s = fixture(rel)
        p, plan, rtl, r = build(s)
        assert lp.audit(s, rtl)['ok'], lp.audit(s, rtl)
        fp = r['reset']['same_depth_forest']
        assert fp['regional_stages'] == 3, fp['regional_stages']
        core, far = fp['regions']['core'], fp['regions']['far']
        assert core['leaves'] == 1 + W + 1 + NS and far['leaves'] == 1 + W + 1, (core['leaves'], far['leaves'])
        assert core['levels'] == far['levels'] == 3
        assert core['scalar_child_pad_port_uses'] == 0 and far['scalar_child_pad_port_uses'] == 0
        assert fp['root_D_loads'] == core['top_branches'] + far['top_branches'] == 4, fp['root_D_loads']
        assert rtl.count('ot_pl_land_reset_forest3 #(.DEPTH(3)') == 2 and '.ROOT_LOADS(4)' in rtl
        # every child reset pad reads its own leaf (distinct indices), never the regional run end
        pads = re.findall(r'u_lprc_(\w+) \(\.ck\(ck_(\w+)\), \.d\((.*?)\), \.q\(', rtl)
        assert len(pads) == 2 + NS, len(pads)
        assert all('_leaves[' in d for _, _, d in pads), pads[:3]
        assert len({d for _, _, d in pads}) == len(pads)
        # schedule, SDC and compiler record unchanged by the leaf choice (same reset age)
        no = copy.deepcopy(s)
        no.pop('landing_reset_forest_children')
        q = lp.Parent(no)
        qp = q.plan()
        try:
            q.emit(qp, 'rfc_top_lp')
            raise AssertionError('more than 1024 leaves without the children option must refuse')
        except SystemExit as e:
            assert 'exceeds1024' in str(e), e
        assert p.sdc(plan, 'rfc_top_lp') == q.sdc(qp, 'rfc_top_lp')
        two = copy.deepcopy(no)
        two.pop('landing_reset_forest')     # plain regional runs: the compiler record (calendar) must be identical
        tp = lp.Parent(two)
        tpl = tp.plan()
        trtl, trt = tp.emit(tpl, 'rfc_top_lp')
        assert r['compiler'] == tp.record(tpl, 'rfc_top_lp', trt)['compiler']
        for why, mutate in (('not boolean', lambda x: x.update(landing_reset_forest_children=1)),
                            ('without forest', lambda x: x.pop('landing_reset_forest'))):
            m = copy.deepcopy(s)
            mutate(m)
            try:
                build(m)
                raise AssertionError(f'{why}: accepted')
            except SystemExit:
                pass
    print('RESET_FOREST_CHILDREN_THREE_LEVEL_LEAVES_AGE_AND_REFUSALS PASS')


if __name__ == '__main__':
    main()
