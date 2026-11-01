"""gen_signed_parent_source.py (FLOW-19 10-31, COORD 15:4x, S81 ot_s81sl_capc5r): any released child sign-off policy at the
die period, child outline checked against its slot in the current parent (plan outline, no sibling overlap), opt-in
--enable-signed-physical drops the exit-78 guard.
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_gen_signed_parent_source.py"""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_signed_parent_source as S  # noqa: E402

VIEWS = HERE.parent / "views"
CAPTR = VIEWS / "captr_signed_1030" / "ot_s81sl_cap_tr"


def _copy(tmp_path, **policy):
    d = tmp_path / "ot_s81sl_cap_tr"
    shutil.copytree(CAPTR, d)
    so = json.loads((d / "signoff.json").read_text())
    so["policy"].update(policy)
    (d / "signoff.json").write_text(json.dumps(so))
    return d


def test_released_policy_other_than_60_25_is_accepted(tmp_path):
    # 12.24c nominal setup policy (uncertainty_setup 0, hold 25) is a released sign-off policy
    v = S.signed_view(_copy(tmp_path, uncertainty_setup_ps=0.0), 833)
    assert v["signoff"] == "SIGNED" and v["policy"]["uncertainty_setup_ps"] == 0.0
    assert v["outline_um"] == [90.72, 86.4]


def test_child_signed_at_another_period_is_refused(tmp_path):
    with pytest.raises(ValueError, match="period"):
        S.signed_view(_copy(tmp_path, period_ps=900.0), 833)


def _kids():
    return [dict(view="rt", inst="u_rt", at=[43.2, 43.2]), dict(view="tr", inst="u_tw", at=[43.2, 302.4]),
            dict(view="tr", inst="u_te", at=[216, 302.4])]


def test_slot_check_uses_the_current_parent_outline():
    views = {"rt": dict(outline_um=[259.2, 116.64]), "tr": dict(outline_um=[90.72, 86.4])}
    r = dict(S.slot_check(_kids(), views, [336.96, 414.72]))
    assert r["u_te"] == pytest.approx((216, 302.4, 306.72, 388.8))
    # a re-signed child may change its outline as long as it still fits its slot (was: must equal the old view)
    views["rt"] = dict(outline_um=[280.8, 120.96])
    S.slot_check(_kids(), views, [336.96, 414.72])


def test_slot_check_refuses_outside_and_overlap_and_rotates():
    views = {"rt": dict(outline_um=[300.0, 116.64]), "tr": dict(outline_um=[90.72, 86.4])}
    with pytest.raises(SystemExit, match="u_rt .* outside"):
        S.slot_check(_kids(), views, [336.96, 414.72])
    views = {"rt": dict(outline_um=[259.2, 270.0]), "tr": dict(outline_um=[90.72, 86.4])}
    with pytest.raises(SystemExit, match="overlaps u_rt"):
        S.slot_check(_kids(), views, [336.96, 414.72])
    k = [dict(view="tr", inst="u_r", at=[0, 0], orient="R90")]
    assert dict(S.slot_check(k, {"tr": dict(outline_um=[90.72, 86.4])}, [86.4, 90.72]))["u_r"] == (0, 0, 86.4, 90.72)
    with pytest.raises(SystemExit):
        S.slot_check(k, {"tr": dict(outline_um=[90.72, 86.4])}, [90.72, 86.4])


def test_capc5r_allowed_and_physical_opt_in():
    src = (HERE / "gen_signed_parent_source.py").read_text()
    assert "'ot_s81sl_capc5r'" in src and "--enable-signed-physical" in src
    assert "if not a.enable_signed_physical:" in src


def test_fixed_parameter_child_preserves_helpers_and_exact_parent_bind(tmp_path):
    view = 'physical/ref_tile/child/views/child'
    d = tmp_path / 'physical/ref_tile/child'; d.mkdir(parents=True)
    (d / 'spec.json').write_text(json.dumps(dict(params=dict(NV=80, K=5, P=3, LA=6))))
    source = tmp_path / 'mixed.sv'
    source.write_text('''module helper(input x,output y); assign y=x; endmodule
module child #(parameter NV=80,K=5,P=3,LA=6)(input clk); endmodule
module top #(parameter integer NS=16, parameter integer NVL=5, parameter integer LA=6)(input clk);
 child #(.NV(NS * NVL), .K(NVL), .P(3), .LA(LA)) u_e (.clk(clk));
endmodule
''')
    spec = dict(top='top', sources=['mixed.sv'], params=dict(NS=16,NVL=5))
    sources, report = S.fixed_child_sources(spec,tmp_path,{view:dict(master='child')},tmp_path/'stage')
    text = Path(sources[0]).read_text()
    assert 'module helper' in text and 'module top' in text and 'module child' not in text
    assert 'child  u_e' in text and report[0]['parameter_bindings'][0]['parameters']==dict(NV=80,K=5,P=3,LA=6)
    spec['params']['NS']=32
    with pytest.raises(ValueError,match='differ from signed child'):
        S.fixed_child_sources(spec,tmp_path,{view:dict(master='child')},tmp_path/'bad')


def test_parameter_expressions_do_not_execute_code():
    assert S._integer("8'h10 * NVL",dict(NVL=5))==80
    with pytest.raises(ValueError,match='not a resolved integer'):
        S._integer("__import__('os').system('false')",{})


def test_generic_signed_parent_uses_native_views_sites_and_insertion(tmp_path):
    declared='physical/ref_tile/leaf/views/ot_s81sl_cap_tr'
    target=tmp_path/declared;target.parent.mkdir(parents=True);shutil.copytree(CAPTR,target)
    source=tmp_path/'parent.sv';source.write_text('module any_parent(input clk); ot_s81sl_cap_tr u(.clk(clk)); endmodule\n')
    parent=dict(top='any_parent',sources=['parent.sv'],params={},clock_port='clk',children=[dict(view=declared,inst='g_cp[0].u_e',at=[4.32,4.32])])
    staged,rec,ledger=S.prepare(parent,{},tmp_path,tmp_path/'stage',[110,100],833)
    assert 'children' not in staged and staged['macros'][0]['view']==str(target.resolve())
    assert rec['orfs_vars']['SYNTH_BLACKBOXES']=='ot_s81sl_cap_tr'
    kit=tmp_path/'kit';kit.mkdir();(kit/'config.mk').write_text('');(kit/'macro_place.tcl').write_text('')
    S.stage_contract(kit,parent,ledger,'clk')
    assert '{g_cp[0].u_e} {clk} 258.820000 {clk}' in (kit/'core_latency.txt').read_text()
    assert '{g_cp[0].u_e} {clk} 200.380000 {clk}' in (kit/'core_latency_ff.txt').read_text()
    import signoff
    assert signoff.pair_target_file(dict(kit=str(kit)),'tt')==kit/'core_latency.txt'
    assert signoff.pair_target_file(dict(kit=str(kit)),'ff')==kit/'core_latency_ff.txt'
    place=(kit/'macro_place.tcl').read_text()
    assert '{g_cp[0].u_e} eq' in place and 'string match' not in place
    assert 'OT_CORE_LAT = /work/core_latency.txt' in (kit/'config.mk').read_text()
    original_place=(kit/'macro_place.tcl').read_bytes()
    S.stage_contract(kit,parent,ledger,'clk',clock_only=True)
    assert (kit/'macro_place.tcl').read_bytes()==original_place
    assert (kit/'config.mk').read_text().count('export OT_CORE_LAT =')==1
    so=json.loads((target/'signoff.json').read_text());so['verdict']='NOT SIGNED';(target/'signoff.json').write_text(json.dumps(so))
    with pytest.raises(ValueError,match='not SIGNED'):
        S.prepare(parent,{},tmp_path,tmp_path/'unsigned',[110,100],833)


def test_signed_parent_rejects_changed_declared_port_contract(tmp_path):
    declared='physical/ref_tile/leaf/views/ot_s81sl_cap_tr'
    target=tmp_path/declared;target.parent.mkdir(parents=True);shutil.copytree(CAPTR,target)
    native=tmp_path/'native/ot_s81sl_cap_tr';native.parent.mkdir();shutil.copytree(CAPTR,native)
    lf=target/'ot_s81sl_cap_tr.lef';lf.write_text(lf.read_text().replace('PIN fault','PIN wrong_fault').replace('END fault','END wrong_fault'))
    parent=dict(top='p',sources=[],children=[dict(view=declared,inst='u',at=[0,0])])
    with pytest.raises(ValueError,match='interface differs'):
        S.prepare(parent,{},tmp_path,tmp_path/'stage',[110,100],833,{declared:str(native)})


def test_fixed_child_checks_hidden_latency_default_even_without_overrides(tmp_path):
    view='physical/ref_tile/child/views/child'
    d=tmp_path/'physical/ref_tile/child';d.mkdir(parents=True)
    (d/'spec.json').write_text(json.dumps(dict(params=dict(LA=7))))
    (tmp_path/'s.sv').write_text('module child #(parameter LA=6)(input clk); endmodule\nmodule top(input clk); child u(.clk(clk)); endmodule\n')
    with pytest.raises(ValueError,match='differ from signed child'):
        S.fixed_child_sources(dict(top='top',sources=['s.sv']),tmp_path,{view:dict(master='child')},tmp_path/'stage')


def test_nonparameterized_signed_child_inside_wrapper_stays_supported(tmp_path):
    (tmp_path/'s.sv').write_text('module child(input clk);endmodule\nmodule inner(input clk);child u(.clk(clk));endmodule\nmodule top(input clk);inner w(.clk(clk));endmodule\n')
    files,_=S.fixed_child_sources(dict(top='top',sources=['s.sv']),tmp_path,{'v/child':dict(master='child')},tmp_path/'stage')
    assert 'child u(.clk(clk))' in Path(files[0]).read_text()


@pytest.mark.parametrize('pattern',['g_cp[0].u_e','*g_cp?0?.u_e'])
def test_indexed_child_site_executes_as_literal_or_explicit_glob(pattern):
    import subprocess
    if not shutil.which('tclsh'):pytest.skip('tclsh unavailable')
    setup='''namespace eval ord {proc get_db_block {} {return B}}
proc B {m args} {if {$m eq "getDbUnitsPerMicron"} {return 1000};if {$m eq "getInsts"} {return I}}
proc M {m args} {return child}
proc Q {m args} {return 0}
proc I {m args} {
 if {$m eq "getMaster"} {return M}
 if {$m eq "getName"} {return {g_cp[0].u_e}}
 if {$m eq "getBBox"} {return Q}
 if {$m eq "setPlacementStatus"} {puts PLACED}
}
'''
    script=S.placement(dict(children=[dict(view='v/child',inst=pattern,at=[8.64,8.64])]),{})
    run=subprocess.run(['tclsh'],input=setup+script,text=True,capture_output=True)
    assert run.returncode==0 and run.stderr=='' and 'PLACED' in run.stdout


def test_named_memory_macro_keeps_its_legacy_instance_site():
    p=S.placement(dict(macros=[dict(view='v/mem',inst='*u_q.u_mem.g_b?0?.g_w?0?.u_m',at=[4.32,8.64])],children=[]),{})
    assert '[string match {*u_q.u_mem.g_b?0?.g_w?0?.u_m}' in p
    assert 'expected one actual instance' in p


def test_fixed_child_sources_synthesizes_one_native_master(tmp_path):
    import subprocess
    if not shutil.which('yosys'):pytest.skip('yosys unavailable')
    view='physical/ref_tile/child/views/child'
    p=tmp_path/'physical/ref_tile/child';p.mkdir(parents=True)
    (p/'spec.json').write_text(json.dumps(dict(params=dict(W=4,L=6))))
    (tmp_path/'s.sv').write_text('''module child #(parameter W=4,L=6)(input [W-1:0] a,output [W-1:0] b);assign b=a;endmodule
module top #(parameter N=2)(input [3:0] a,output [3:0] b);child #(.W(2*N),.L(6)) u(.a(a),.b(b));endmodule
''')
    src,_=S.fixed_child_sources(dict(top='top',params=dict(N=2),sources=['s.sv']),tmp_path,{view:dict(master='child')},tmp_path/'stage')
    (tmp_path/'bb.v').write_text('(* blackbox *) module child(input [3:0] a,output [3:0] b);endmodule\n')
    run=subprocess.run(['yosys','-Q','-q','-p',f'read_verilog -sv {tmp_path}/bb.v {src[0]}; hierarchy -check -top top; proc; flatten; write_json {tmp_path}/net.json'],text=True,capture_output=True)
    assert run.returncode==0,run.stderr
    net=json.loads((tmp_path/'net.json').read_text())
    assert [c['type'] for c in net['modules']['top']['cells'].values()]==['child']


def test_parameter_literals_keep_declared_width_sign_and_verilog_remainder():
    assert S._integer("8'h1ff",{})==255
    assert S._integer("8'shff",{})==-1
    assert S._integer('-7 % 3',{})==-1
    assert S._integer('-7 / 3',{})==-2
    assert 'module child' not in S._mask('initial $display("module child // endmodule");')


@pytest.mark.parametrize('custom',[False,True])
def test_cli_recipe_override_and_default_preserve_historical_refusal(tmp_path,monkeypatch,custom):
    default=tmp_path/'recipes.json';default.write_text(json.dumps(dict(default_parent=dict(spec_git='old:spec.json'))))
    private=tmp_path/'private.json';private.write_text(json.dumps(dict(private_parent=dict(spec_git='old:private.json'))))
    monkeypatch.setattr(S.G,'HERE',tmp_path)
    argv=['gen_signed_parent_source.py','--enable-signed-source-only','--module',('private_parent' if custom else 'default_parent'),
          '--child-views',str(tmp_path/'views.json'),'--plan',str(tmp_path/'plan.json'),'--out',str(tmp_path/'out')]
    if custom:argv+=['--recipes',str(private)]
    monkeypatch.setattr(sys,'argv',argv)
    with pytest.raises(SystemExit,match='historical parent spec'):
        S.main()
