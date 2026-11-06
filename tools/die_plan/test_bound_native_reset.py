"""Opt-in bound native reset context cannot invent a singleton root or relay topology."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import gen_phys as G
import gen_rtl
import reset_tree as R
from test_sdc_lint import TINY, _errs, _kit


def tree(entry='relayed'):
    return dict(type='t', entry=entry, sync_stages=2, root=[8.64, 8.64], start=False,
                relays=[dict(name='u_rrl_0', d='rst_root_n', q='rst_n_t0', xy=[17.28, 17.28],
                             depth=1, tap=0, kind='tap')], taps=['clk'], own_depth=1, depth=1,
                n_tree=1, n_pad=0, max_hop_um=17.28, reach_um=405, outs=[], core_resets=[], relay_driver=False)


def fixture(tmp_path, entry='relayed', mutate=lambda s:s, start=False):
    t = tree(entry)
    if start:t.update(start=True,start_in=[8.64,10.8],start_role='mission',tap_roles={'0':'mission'},start_tap=None)
    text = ('module top(input clk, arst_n);\n bound u_bound(.clk(clk), .arst_n(arst_n));\nendmodule\n'
            'module bound(input clk, arst_n);\n' + '\n'.join(R.rtl_lines(t)) + '\nendmodule\n' + gen_rtl.CELLS)
    f = tmp_path/'native.sv'; f.write_text(mutate(text))
    p = SimpleNamespace(types={'t':dict(module='top', outline_um=[100,100],
                                      clock=dict(landing_contract=dict(collector_tree=t)))})
    return p, f


def test_receiver_uses_exact_tree_entry_and_coordinates(tmp_path):
    p,f=fixture(tmp_path); c=G.install_bound_native_reset(p,'t',[f])
    assert c['entry_path']=='u_bound.u_rst_in'
    assert not G.root_async_reset(p,'t')
    assert R.for_type(p,'t')==tree()
    assert R.in_pin(p,'t')==(8.64,8.64)
    text=R.tcl_text(R.for_type(p,'t'),native_paths=c['native_paths'])
    assert 'u_bound[./]u_rst_in[./]*' in text and '*u_rst_root[./]*' not in text
    assert len(c['native_paths'])==2


def test_positive_nested_root_has_exact_two_bit_exception(tmp_path):
    p,f=fixture(tmp_path,'sync');G.install_bound_native_reset(p,'t',[f])
    assert G.root_async_reset(p,'t')
    line=G.root_reset_false_path(p,'t')
    assert '^u_bound[./]u_rst_root[./]p\\[[01]\\]' in line
    text,ctx=_kit(TINY);ctx.update(root_async_reset=True,root_reset_hier='u_bound.u_rst_root')
    assert _errs(text+line+'\n',ctx)==[]
    assert _errs(text+line.replace('u_bound','wrong')+'\n',ctx)
    assert _errs(text+line.replace('/RESETN','/D')+'\n',ctx)


def test_default_exception_and_context_unchanged():
    assert G.root_reset_false_path(SimpleNamespace(),'unused')==G.ROOT_RESET_FALSE_PATH
    text,ctx=_kit(TINY);ctx['root_async_reset']=True
    assert _errs(text+G.ROOT_RESET_FALSE_PATH+'\n',ctx)==[]
    assert 'root_reset_hier' not in ctx


def extra_node(text):
    i=text.index('\nendmodule',text.index('module bound'))
    return text[:i]+'\n ot_dp_rrelay u_rrl_999(.clk(clk),.d(rst_root_n),.q(extra));'+text[i:]


@pytest.mark.parametrize('mutation',[
    lambda s:s.replace('u_rrl_0 (','missing_relay ('),
    lambda s:s.replace('ot_dp_rrelay u_rrl_0','ot_dp_rgate u_rrl_0'),
    lambda s:s.replace('.d(rst_root_n), .q(rst_n_t0)','.d(wrong), .q(rst_n_t0)'),
    lambda s:s.replace('bound u_bound(.clk(clk), .arst_n(arst_n));','bound u_bound(.clk(clk), .arst_n(arst_n));\n bound duplicate(.clk(clk), .arst_n(arst_n));'),
    extra_node,
])
def test_missing_wrong_duplicate_or_topology_fail_closed(tmp_path,mutation):
    p,f=fixture(tmp_path,mutate=mutation)
    with pytest.raises(gen_rtl.GenError):
        G.install_bound_native_reset(p,'t',[f])
    assert R.bound_native_contract(p,'t') is None


def test_wrong_entry_and_bad_geometry_fail_closed(tmp_path):
    p,f=fixture(tmp_path);p.types['t']['clock']['landing_contract']['collector_tree']['entry']='sync'
    with pytest.raises(Exception,match='missing/duplicate/wrong-module'):
        G.install_bound_native_reset(p,'t',[f])
    p,f=fixture(tmp_path);p.types['t']['clock']['landing_contract']['collector_tree']['root']=[101,8]
    with pytest.raises(Exception,match='coordinate outside outline'):
        G.install_bound_native_reset(p,'t',[f])


def test_changed_root_cell_cannot_gain_exception(tmp_path):
    p,f=fixture(tmp_path,'sync',lambda s:s.replace("p <= 2'b0", "p <= 2'b1"))
    with pytest.raises(Exception,match='canonical stage/gate behavior'):
        G.install_bound_native_reset(p,'t',[f])


def test_actual_frozen_thirteen_source_receiver():
    path=os.getenv('OT_NATIVE_RESET_FIXTURE')
    if not path:pytest.skip('actual frozen native fixture is supplied explicitly')
    b=Path(path);t=json.loads((b/'type_overlay.json').read_text());p=SimpleNamespace(types={'slw_stm_v3':t})
    files=list(b.glob('*.sv'))+list(b.glob('*.v'));assert len(files)==13
    c=G.install_bound_native_reset(p,'slw_stm_v3',files)
    assert c['entry_path']=='u_bound.u_rst_in' and len(c['tree']['relays'])==167
    assert len(c['native_paths'])==260 and not G.root_async_reset(p,'slw_stm_v3')
    assert R.start_in_pin(p,'slw_stm_v3')==(308.896,369.376)
    text=R.tcl_text(R.for_type(p,'slw_stm_v3'),native_paths=c['native_paths'])
    assert 'u_bound[./]u_rrl_166[./]*' in text and '*u_rst_root[./]*' not in text
    assert c['verified_cell_classes']==['ot_dp_rgate','ot_dp_rrelay']


def test_same_name_receiver_bypass_cannot_gain_native_contract(tmp_path):
    p,f=fixture(tmp_path)
    source=f.read_text();start=source.index('module ot_dp_rrelay ');end=source.index('endmodule',start)
    body=source[start:end];assert 'q <= d' in body
    f.write_text(source[:start]+body.replace('q <= d','q <= ~d')+source[end:])
    with pytest.raises(gen_rtl.GenError,match='canonical stage/gate behavior'):
        G.install_bound_native_reset(p,'t',[f])


def test_same_name_gate_mutant_cannot_gain_native_contract(tmp_path):
    p,f=fixture(tmp_path,start=True)
    source=f.read_text();start=source.index('module ot_dp_rgate ');end=source.index('endmodule',start)
    body=source[start:end];assert 'run' in body
    f.write_text(source[:start]+body.replace('d & run','d | run')+source[end:])
    assert f.read_text()!=source
    with pytest.raises(gen_rtl.GenError,match='canonical stage/gate behavior'):
        G.install_bound_native_reset(p,'t',[f])


def test_same_name_one_stage_root_is_rejected(tmp_path):
    p,f=fixture(tmp_path,'sync')
    source=f.read_text();start=source.index('module ot_dp_rsync_s2 ');end=source.index('endmodule',start)
    body=source[start:end].replace('reg [1:0] p','reg [0:0] p').replace('sync_rst_n = p[1]','sync_rst_n = p[0]')
    f.write_text(source[:start]+body+source[end:])
    assert f.read_text()!=source
    with pytest.raises(gen_rtl.GenError,match='canonical stage/gate behavior'):
        G.install_bound_native_reset(p,'t',[f])


def test_declared_depth_mismatch_fails_closed(tmp_path):
    p,f=fixture(tmp_path);p.types['t']['clock']['landing_contract']['collector_tree']['relays'][0]['depth']=2
    with pytest.raises(gen_rtl.GenError,match='declared depth differs'):
        G.install_bound_native_reset(p,'t',[f])


def test_captured_source_and_staged_identity_fail_closed(tmp_path):
    import bound_reset_contract as B
    p,f=fixture(tmp_path)
    record=B.emitted(f,'t',tree())
    assert B.source(f,'t',tmp_path,tmp_path)['tree_sha256']==B.digest(tree())
    c=G.install_bound_native_reset(p,'t',[f],source_contract=record)
    B.stage(tmp_path,record,c)
    assert B.kit([f],'t')['native_paths']==c['native_paths']
    (tmp_path/'reset_tree.tcl').write_text('wrong placement')
    with pytest.raises(ValueError,match='placement sidecar differs'):B.kit([f],'t')
    f.write_text(f.read_text()+'\n// changed source\n')
    with pytest.raises(ValueError,match='source RTL identity differs'):B.source(f,'t',tmp_path,tmp_path)
    record['tree']['relays'][0]['d']='different'
    with pytest.raises(ValueError,match='tree content differs'):B.validate(record,'t')


def test_wrapper_tied_reset_and_recomputed_tree_rejected(tmp_path):
    import bound_reset_contract as B
    p,f=fixture(tmp_path)
    rec=B.emitted(f,'t',tree())
    p.types['t']['clock']['landing_contract']['collector_tree']['relays'][0]['xy']=[30,30]
    with pytest.raises(gen_rtl.GenError,match='differs from captured'):G.install_bound_native_reset(p,'t',[f],source_contract=rec)
    p,f=fixture(tmp_path,mutate=lambda s:s.replace('.arst_n(arst_n)',".arst_n(1'b1)"))
    with pytest.raises(gen_rtl.GenError,match='exact passthrough'):G.install_bound_native_reset(p,'t',[f])


def test_out_copy_negedge_and_native_core_reset_preserved(tmp_path):
    import bound_reset_contract as B
    t=tree();t.update(relay_lockup='negedge',outs=[[25,25]],n_clock_taps=1,
                     core_resets=[dict(inst='native_core',port='rst_n',tap=0)])
    t['relays'].append(dict(name='u_rrl_1',d='rst_root_n',q='rst_n_t1',xy=[25,25],depth=1,tap=1,kind='tap'))
    t['taps'].append('rst_o_0')
    t.update(depth=2,own_depth=2)
    for relay in t['relays']:relay.update(d='rst_rl_2',depth=2)
    t['relays'].insert(0,dict(name='u_rrl_2',d='rst_root_n',q='rst_rl_2',xy=[12,12],depth=1,tap=None,kind='tree'))
    text=('module top(input clk, arst_n, output rst_o_0);\n'
          'bound u_bound(.clk(clk),.arst_n(arst_n),.rst_o_0(rst_o_0));\nendmodule\n'
          'module bound(input clk, arst_n, output rst_o_0);\n'+'\n'.join(R.rtl_lines(t))+
          '\nendmodule\n'+gen_rtl.CELLS+gen_rtl.LOCKUP_CELLS)
    f=tmp_path/'bound.sv';f.write_text(text)
    p=SimpleNamespace(types={'t':dict(outline_um=[100,100],clock=dict(landing_contract=dict(collector_tree=t)))})
    c=G.install_bound_native_reset(p,'t',[f])
    nodes={n['name']:n for n in c['physical_nodes']}
    assert nodes['u_rrl_1']['q']=='rst_o_0' and nodes['u_rrl_1_t']['q']=='rst_n_t1'
    assert 'ot_dp_rrelay_nl' in c['verified_cell_classes']
    result=R.tcl_text(t,native_paths=c['native_paths'],native_nodes=c['physical_nodes'])
    assert 'disconnect' not in result and 'native_core' not in result
    f.write_text(text.replace('ot_dp_rrelay_nl u_rrl_2','ot_dp_rrelay u_rrl_2'))
    with pytest.raises(gen_rtl.GenError,match='wrong-module'):G.install_bound_native_reset(p,'t',[f])


def test_reviewed_sites_keep_ids_and_bound_hops(tmp_path):
    import bound_reset_contract as B
    p,f=fixture(tmp_path);t=tree()
    image=tmp_path/'review.png';image.write_bytes(b'actual test image')
    overlay=dict(schema='opentallas.bound_reset_placement.v1',source_tree_sha256=B.digest(t),
                 sites={'u_rrl_0':[20,20]},review=dict(verdict='PASS',image=str(image),findings='sites reviewed'))
    landing=p.types['t']['clock']['landing_contract'];landing['bound_reset_placement']=overlay
    c=G.install_bound_native_reset(p,'t',[f]);assert c['physical_nodes'][0]['xy']==[20,20]
    assert c['tree']==t
    rec=B.emitted(f,'t',t);B.stage(tmp_path,rec,c)
    del landing['bound_reset_placement']
    inherited=G.install_bound_native_reset(p,'t',[f])
    assert inherited['physical_nodes'][0]['xy']==[20,20]
    landing['bound_reset_placement']=overlay
    for key,value,match in [('source_tree_sha256','wrong','exact captured tree'),('sites',{'u_rrl_999':[20,20]},'unknown native')]:
        before=overlay[key];overlay[key]=value
        with pytest.raises(gen_rtl.GenError,match=match):G.install_bound_native_reset(p,'t',[f])
        overlay[key]=before
    overlay['review']['verdict']='FAIL'
    with pytest.raises(gen_rtl.GenError,match='PASS image review'):G.install_bound_native_reset(p,'t',[f])
    overlay['review']['verdict']='PASS'
    p.types['t']['outline_um']=[1000,1000];overlay['sites']={'u_rrl_0':[500,500]}
    with pytest.raises(gen_rtl.GenError,match='beyond captured reach'):G.install_bound_native_reset(p,'t',[f])
