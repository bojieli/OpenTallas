from copy import deepcopy
from types import SimpleNamespace
import subprocess
import pytest
from tools.die_plan import landing_place as L


def typ():
    return dict(outline_um=[100,100], contents=[dict(inst='u_core',module='mod',params={'N':2})],
                clock=dict(landing_contract=dict(native_stage_groups=dict(
                    schema='opentallas.native_stage_groups.v1', content='u_core',module='mod',params={'N':2},
                    groups=[dict(prefix=r'u_core\.g_s\[0\]',rect_um=[10,10,30,20],tag='stage:s0')]))))


def test_absent_byte_identical():
    assert L._native_stage_groups({}, [('x',[1,1,2,2],'x')]) == ([('x',[1,1,2,2],'x')],'')


@pytest.mark.parametrize('dataflow',[False,True])
def test_emitted_in_both_paths(dataflow):
    t=typ()
    if dataflow:t['clock']['landing_contract']['monitor']='dataflow'
    text=L.tcl(SimpleNamespace(types={'ty':t},clock={}), 'ty')
    assert '{{u_core\\.g_s\\[0\\]} {10.00000 10.00000 30.00000 20.00000} stage:s0}' in text
    assert 'OT_CLAND missing native stage group' in text


@pytest.mark.parametrize('which,value',[('schema','bad'),('content','wrong'),('module','wrong'),('params',{}),('groups',[])])
def test_contract_fail_closed(which,value):
    t=typ();t['clock']['landing_contract']['native_stage_groups'][which]=value
    with pytest.raises(ValueError):L._native_stage_groups(t,[])


@pytest.mark.parametrize('key,value',[('prefix','u_other'),('prefix','u_core;bad\n'),('prefix','u_core['),
    ('rect_um',[1,1,101,2]),('rect_um',[1,1,1,2]),('rect_um',[True,1,2,3]),('rect_um',[1,1,float('nan'),3]),
    ('tag','raw-copy-optional')])
def test_group_fail_closed(key,value):
    t=typ();t['clock']['landing_contract']['native_stage_groups']['groups'][0][key]=value
    with pytest.raises(ValueError):L._native_stage_groups(t,[])


def test_duplicate_refused():
    t=typ();c=t['clock']['landing_contract']['native_stage_groups'];c['groups'].append(deepcopy(c['groups'][0]))
    with pytest.raises(ValueError,match='duplicate'):L._native_stage_groups(t,[])


@pytest.mark.parametrize('name,passes',[('u_core.g_s[0].q',True),('u_core.g_s[1].q',False),('other',False)])
def test_actual_group_required(tmp_path,name,passes):
    _,check=L._native_stage_groups(typ(),[])
    path=tmp_path/'check.tcl'
    path.write_text('proc blk {cmd} {return cell}\nproc cell {cmd} {return {'+name+'}}\nset ff_blk blk\n'+check)
    p=subprocess.run(['tclsh',str(path)],capture_output=True,text=True)
    assert (p.returncode==0)==passes
    if not passes:assert 'missing native stage group' in p.stderr


@pytest.mark.parametrize('prefix,name',[(r'u_core\.g_s\[0\]', 'u_core.g_s[0]'),
                                        (r'u_core\.u\.g_plw\.g_s\\\[0\\\][/.].*', r'u_core.u.g_plw.g_s\[0\].u_st.q\[9\]$_DFF_PN0_')])
def test_group_word_survives_lassign(tmp_path, prefix, name):
    """HEAD-LEP0N-OPUS 11-17: the prefix the placement loop lassigns from cland_groups must be the very
    ::cland_native_leaf_regex key and match the ODB cell name (hd_lep0N NF15f 'no mapped cells' at GPL)."""
    t=typ();g=t['clock']['landing_contract']['native_stage_groups']['groups'][0];g['prefix']=prefix;g['match']='cell'
    groups,check=L._native_stage_groups(t,[('u_plain',[1,1,2,2],'x')])
    lines='\n'.join(L._group_line(p,r,tag) for p,r,tag in groups)
    init=check.split('foreach cland_native_prefix')[0]
    path=tmp_path/'g.tcl'
    path.write_text(init+'set cland_groups {\n'+lines+'\n}\nforeach s $cland_groups {lassign $s p r tag\n'
        ' if {$p eq "u_plain"} {puts "PLAIN $p"; continue}\n'
        ' puts "KEY [dict exists $::cland_native_leaf_regex $p]"\n'
        ' puts "HIT [regexp [dict get $::cland_native_leaf_regex $p] {'+name+'}]"}\n')
    p=subprocess.run(['tclsh',str(path)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    assert 'PLAIN u_plain' in p.stdout and 'KEY 1' in p.stdout and 'HIT 1' in p.stdout, p.stdout
    assert '  {u_plain {1.00000 1.00000 2.00000 2.00000} x}' in lines
