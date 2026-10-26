from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import pytest

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('endpoint_export',HERE/'endpoint_clock_export.py')
M=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(M)

MOCK=r'''
set ::ot_ps_method tag
proc ot_ps_ckarr {pin clock which} {
 if {$pin eq "clk"} {return 0.0}
 if {$pin eq "f0/CLK"} {return [expr {$which eq "max" ? 250.0 : 245.0}]}
 return [expr {$which eq "max" ? 265.0 : 255.0}]
}
proc get_full_name {x} {return $x}
proc all_clocks {} {return ck}
proc ck {method} {return {0 4.165e-10}}
proc get_property {object prop} {
 if {$prop eq "sources"} {return clk}
 if {$prop eq "period"} {return 833.0}
 if {$prop eq "clocks"} {return ck}
 if {$prop eq "ref_name"} {return DFFHQNx1_ASAP7_75t_R}
 if {$prop eq "direction"} {return [dict get {clk input din input dout output bypass output unused input unknown input rst input} $object]}
 error "unexpected property $object $prop"
}
proc get_ports {pattern} {return {clk din dout bypass unused unknown rst}}
proc get_cells {name} {return $name}
proc all_registers {option} {
 switch $option {
  -clock_pins {return {f0/CLK f1/CLK}}
  -data_pins {return {f0/D f1/D}}
  -output_pins {return {f0/QN f1/QN}}
  -async_pins {return {f1/RESETN}}
 }
 error "unknown registers option"
}
proc get_nets {args} {return shared_clock_net}
proc argument {key args} {return [lindex $args [expr {[lsearch -exact $args $key]+1}]]}
proc get_fanin {args} {
 set object [argument -to {*}$args]
 switch $object {
  f0/CLK - f1/CLK {incr ::source_queries;return clk}
  dout {return f1/QN}
  bypass {return din}
 }
 error "unexpected fanin $object"
}
proc get_fanout {args} {
 set object [argument -from {*}$args]
 switch $object {
  clk {return {f0/CLK f1/CLK}}
  din {return {f0/D f1/D bypass}}
  unused {return {}}
  unknown {return mystery/A}
  rst {return f1/RESETN}
 }
 error "unexpected fanout $object"
}
namespace eval sta {proc worst_slack_cmd {check} {return 0}}
set source_queries 0
'''


def run_export(tmp_path,corner='TT',prefix=''):
    if not shutil.which('tclsh'):pytest.skip('tclsh unavailable')
    path=tmp_path/(corner+'.jsonl')
    script=MOCK+f'\nsource {{{HERE/"endpoint_clock_export.tcl"}}}\n'+prefix+f'\not_ec::export {{{path}}} {corner} {{rst RESET}} {{view_id recovered input_manifest_sha256 digest}}\nputs "SOURCES $source_queries"\n'
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert not result.stderr,result.stderr
    return [json.loads(l) for l in path.read_text().splitlines()],result.stdout


def test_every_actual_ff_and_distinct_clock_arrivals_are_retained(tmp_path):
    rows,text=run_export(tmp_path)
    regs={r['instance']:r for r in rows if r['kind']=='register'}
    assert set(regs)=={'f0','f1'}
    assert regs['f0']['late_ps']==250 and regs['f1']['late_ps']==265
    assert regs['f0']['early_ps']==245 and regs['f1']['early_ps']==255
    assert regs['f0']['source_ports']==['clk']
    assert 'SOURCES 1' in text  # cache topology by leaf net, never average FF clocks


def test_ports_preserve_bypass_unused_async_and_unmapped_cases(tmp_path):
    rows,_=run_export(tmp_path)
    ports={r['name']:r for r in rows if r['kind']=='port'}
    assert len(ports)==7
    assert ports['din']['ff_members']==['f0','f1'] and ports['din']['bypass_ports']==['bypass']
    assert 'COMBINATIONAL_BYPASS' in ports['din']['flags']
    assert ports['dout']['ff_members']==['f1']
    assert ports['unused']['flags']==['NO_STRUCTURAL_ENDPOINTS']
    assert ports['unknown']['unmapped_endpoints']==['mystery/A']
    assert ports['rst']['async_terminals']==['f1/RESETN'] and ports['rst']['ff_members']==['f1']
    assert ports['clk']['class']=='CLOCK' and ports['clk']['ff_members']==['f0','f1']
    assert rows[-1]['qualification']=='NOT_EVALUATED'


def test_ambiguous_ff_clock_is_exported_with_flags_not_dropped(tmp_path):
    prefix='''
rename get_property original_get_property
proc get_property {object prop} {
 if {$object eq "f1/CLK" && $prop eq "clocks"} {return {ck second_clock}}
 return [original_get_property $object $prop]
}
'''
    rows,_=run_export(tmp_path,prefix=prefix)
    reg=next(r for r in rows if r['kind']=='register' and r['instance']=='f1')
    assert reg['early_ps'] is None and reg['late_ps'] is None
    assert reg['flags']==['MULTIPLE_CLOCKS']


def bound_exports(tmp_path):
    files={}
    for name in ('netlist','spef','odb','sdc','config'):
        p=tmp_path/name;p.write_text('immutable '+name);files[name]=p
    manifest=M.make_manifest('recovered',files,'source_sha')
    mp=tmp_path/'manifest.json';mp.write_text(json.dumps(manifest))
    paths={}
    for corner in ('TT','FF'):
        sub=tmp_path/corner;sub.mkdir()
        rows,_=run_export(sub,corner)
        rows[0]['input_manifest_sha256']=M.sha256(mp)
        p=sub/'export.jsonl';p.write_text(''.join(json.dumps(r)+'\n' for r in rows));paths[corner]=p
    return mp,paths,files


def test_pair_pack_keeps_all_members_and_flags_without_signoff_credit(tmp_path):
    mp,paths,_=bound_exports(tmp_path)
    data=M.pack(mp,paths['TT'],paths['FF'])
    assert len(data['registers'])==2 and len(data['ports'])==7
    assert data['ports']['din']['union']['ff_members']==['f0','f1']
    assert data['ports']['unknown']['union']['unmapped_endpoints']==['mystery/A']
    assert data['qualification']=='NOT_EVALUATED' and data['requires_actual_parent_sta']
    assert data['requires_fresh_policy_signoff']


def test_pack_rejects_changed_rc_input(tmp_path):
    mp,paths,files=bound_exports(tmp_path);files['spef'].write_text('changed RC')
    with pytest.raises(ValueError,match='changed immutable input spef'):
        M.pack(mp,paths['TT'],paths['FF'])


def test_pack_retains_union_when_corner_membership_differs(tmp_path):
    mp,paths,_=bound_exports(tmp_path)
    rows=[json.loads(l) for l in paths['FF'].read_text().splitlines()]
    for r in rows:
        if r['kind']=='port' and r['name']=='din':r['ff_members']=['f1']
    paths['FF'].write_text(''.join(json.dumps(r)+'\n' for r in rows))
    data=M.pack(mp,paths['TT'],paths['FF'])
    assert data['ports']['din']['union']['ff_members']==['f0','f1']
    assert 'CORNER_MEMBERSHIP_DIFFERS' in data['ports']['din']['flags']
