"""The proposed physical kernel must meet its bound at every die corner."""
from pathlib import Path
import sys
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
import vms_reach_plan as P

def test_kernel_has_the_claimed_whole_outline_bound():
    D=SimpleNamespace(die=(0,0,270,403.92),extra=dict(core=(4.32,4.32,265.68,399.6)),cells={})
    box,_=P.kernel(D,395)
    for x in [box[0],box[2]]:
        for y in [box[1],box[3]]:
            assert max(abs(x-a)+abs(y-b) for a in [0,270] for b in [0,403.92])<=395+1e-7

def test_unreachable_outline_is_rejected_before_placement():
    D=SimpleNamespace(die=(0,0,1000,1000),extra=dict(core=(4.32,4.32,995.68,995.68)),cells={})
    try:P.kernel(D,395)
    except ValueError as e:assert 'structural' in str(e)
    else:raise AssertionError('impossible kernel accepted')

def test_hook_requires_same_macro_clock_plan_and_safe_internal_anchors():
    import copy
    s=dict(macros=[],clock_moves=[],outline_um=[270,403.92],moves=[dict(inst=r'u_fcore.bank.q\[17\]$_DFF_P_',xy=[130.1,155.25])])
    hook=P.pre_dpl_hook(s)
    assert 'read_db' not in hook and 'write_db' not in hook and 'detailed_placement' not in hook
    assert hook.index('VMS_AFFINITY_ANCHOR_CONFLICT')<hook.index('$inst setLocation')
    assert r'{u_fcore.bank.q\[17\]$_DFF_P_}' in hook
    for bad in [dict(macros=[{}]),dict(clock_moves=[{}]),dict(moves=[dict(inst='u_bin_dq/q',xy=[1,1])]),dict(moves=[dict(inst='bad}name',xy=[1,1])]),dict(moves=[dict(inst='q',xy=[float('nan'),1])])]:
        x=copy.deepcopy(s);x.update(bad)
        try:P.pre_dpl_hook(x)
        except ValueError:pass
        else:raise AssertionError('unsafe hook contract accepted')

def test_hook_validates_every_anchor_before_mutation_and_preserves_escaped_names():
    import subprocess
    setup=r'''
namespace eval ord {proc get_db_block {} {return block}}
set ::applied {}
proc block {method args} {
 switch $method {
  getDbUnitsPerMicron {return 1000}
  getDieArea {return die}
  findInst {if {[lindex $args 0] eq {u_fcore.q\[17\]$_DFF_P_}} {return ff};return NULL}
 }
}
proc die {method} {switch $method {xMin - yMin {return 0} xMax {return 270000} yMax {return 403920}}}
proc ff {method args} {
 switch $method {getMaster {return master} getPlacementStatus {return PLACED} setLocation {lappend ::applied $args} setPlacementStatus {}}
}
proc master {method} {return 0}
'''
    s=dict(macros=[],clock_moves=[],outline_um=[270,403.92],moves=[dict(inst=r'u_fcore.q\[17\]$_DFF_P_',xy=[130.1,155.25])])
    good=setup+P.pre_dpl_hook(s)+'\nif {$::applied ne {{130100 155250}}} {error "wrong coordinates/name"}\n'
    r=subprocess.run(['tclsh'],input=good,text=True,capture_output=True)
    assert r.returncode==0 and not r.stderr,r.stderr
    s['moves'].append(dict(inst='missing',xy=[1,1]))
    # An error on the second name must leave even the valid first anchor untouched.
    bad=setup+'\nset rc [catch {\n'+P.pre_dpl_hook(s)+'\n} why]\nif {!$rc || $::applied ne {}} {error "partial mutation"}\n'
    r=subprocess.run(['tclsh'],input=bad,text=True,capture_output=True)
    assert r.returncode==0 and not r.stderr,r.stderr
