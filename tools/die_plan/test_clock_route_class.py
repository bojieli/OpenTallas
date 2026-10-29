import shutil
import subprocess
import pytest
import clock_route_class as C

TREE='''module ctree(input root, output tap);
  CKINVDCx16_ASAP7_75t_R b0 (.A(root), .Y(n0));
  CKINVDCx16_ASAP7_75t_R b1 (.A(alias), .Y(n1));
  assign alias = n0;
  assign tap = n1;
endmodule
'''


def test_exact_tree_aliases_prefix_and_unrelated_design_data():
    assert C.tree_parents(TREE)=={'b0':None,'b1':'b0'}
    t=C.emit(TREE,'ck_','real_root')
    assert 'findInst {ck_b0}' in t and 'findInst {ck_b1}' in t
    assert 'findNet {real_root}' in t
    assert 'getNets' not in t and 'setNonDefaultRule' not in t


@pytest.mark.parametrize('bad',[
    TREE.replace('.A(root)', '.A(data)'),
    TREE.replace('CKINVDCx16_ASAP7_75t_R b1','AND2x2_ASAP7_75t_R b1'),
    TREE.replace('assign alias = n0;', 'assign alias = alias;'),
    TREE.replace('.A(root)', '.A(n1)'),
    TREE.replace('.Y(n1)', '.Y(n0)'),
])
def test_source_mutants_fail_closed(bad):
    with pytest.raises(ValueError):C.emit(bad)


def run(mutant=False):
    if not shutil.which('tclsh'):pytest.skip('tclsh unavailable')
    stub='''
namespace eval ord {proc get_db_block {} {return block}}
set types [dict create root SIGNAL n0 SIGNAL n1 SIGNAL data SIGNAL]
proc block {method name} {
 if {$method eq "findNet" && $name eq "root"} {return root}
 if {$method eq "findInst" && $name in {ck_b0 ck_b1}} {return $name}
 return NULL
}
foreach name {ck_b0 ck_b1} {
 proc $name {method args} {
  if {$method eq "getMaster"} {return master}
  return [string map {ck_ it_} [lindex [info level 0] 0]]_[lindex $args 0]
 }
}
proc master {method} {return CKINVDCx16_ASAP7_75t_R}
proc it_b0_A {method} {return root}
proc it_b0_Y {method} {return n0}
proc it_b1_A {method} {return n0}
proc it_b1_Y {method} {return n1}
foreach name {root n0 n1 data} {
 proc $name {method args} {
  set name [lindex [info level 0] 0]
  if {$method eq "getName"} {return $name}
  if {$method eq "getSigType"} {return [dict get $::types $name]}
  if {$method eq "setSigType"} {dict set ::types $name [lindex $args 0];return}
  error "unexpected method (including NDR change) $method"
 }
}
'''
    if mutant:stub+='proc it_b1_A {method} {return data}\n'
    text=stub+'set rc [catch {\n'+C.emit(TREE,'ck_')+'} msg]\nputs "RESULT $rc $types"\n'
    return subprocess.run(['tclsh'],input=text,text=True,capture_output=True,check=True).stdout


def test_runtime_marks_only_selected_clock_nets_leaves_data_ndr_untouched():
    assert 'RESULT 0 root CLOCK n0 CLOCK n1 CLOCK data SIGNAL' in run()


def test_actual_connectivity_mutant_is_atomic():
    assert 'RESULT 1 root SIGNAL n0 SIGNAL n1 SIGNAL data SIGNAL' in run(True)
