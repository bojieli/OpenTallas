"""AM-only alternate-leaf fallback preserves the ordinary affinity guards."""
from pathlib import Path
import shutil,subprocess
import pytest
SRC=Path(__file__).with_name('rck_am_cohort.tcl')
MOCK=r'''
set la_um 30;set la_dbu 1000;set la_maxg @MAXG@;set la_cap @CAP@;set la_ronly @REPORT@
set la_moved 0;set la_blk B;set ::changed 0;set ::same @SAME@
set la_ck {a pa b pb c pc};set la_fo {N1 2 N2 1}
array set ::net {pa N1 pb N1 pc N2}
array set ::pos {a {0 0} b {1000 0} c {2000 0} D1 {100000 0} D2 {@DX@ 0}}
array set ::gate {N1 G N2 @GATE@}
proc la_same_clock {mem} {return $::same}
proc la_leaf {m} {global la_ck;return $::net([dict get $la_ck $m])}
proc la_drv {n} {return [dict get {N1 D1 N2 D2} $n]}
proc la_xy {i} {return $::pos($i)}
proc la_groot {n} {return $::gate($n)}
proc unknown {cmd args} {
 if {$cmd eq "B" && [lindex $args 0] eq "findNet"} {return [lindex $args 1]}
 if {$cmd in {N1 N2}} {
  switch [lindex $args 0] {getName {return $cmd} getSigType {return CLOCK}}
 }
 if {$cmd in {pa pb pc}} {
  switch [lindex $args 0] {
   getInst {return [dict get {pa a pb b pc c} $cmd]}
   getNet {return $::net($cmd)}
   disconnect {set ::net($cmd) {};incr ::changed;return}
   connect {set ::net($cmd) [lindex $args 1];return}
  }
 }
 error "unexpected $cmd $args"
}
@PROC@
puts "RESULT [ot_rck_am_near {a b c}] CHANGED=$::changed MOVED=$la_moved A=$::net(pa) B=$::net(pb) C=$::net(pc)"
'''

def run(**kw):
 s=SRC.read_text();proc=s[s.index('proc ot_rck_am_near'):s.index('set am_hdr')]
 vals=dict(MAXG=24,CAP=4,REPORT=0,SAME=1,DX=10000,GATE='G',PROC=proc);vals.update(kw)
 script=MOCK
 for k,v in vals.items():script=script.replace('@'+k+'@',str(v))
 return subprocess.run(['tclsh'],input=script,text=True,capture_output=True,check=True).stdout

@pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh missing')
def test_alternate_existing_leaf_moves_only_clock_members_within_same_radius():
 out=run();assert 'RESULT moved CHANGED=2 MOVED=2 A=N2 B=N2 C=N2' in out,out

@pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh missing')
@pytest.mark.parametrize('kw,result',[({'CAP':2},'far'),({'DX':100000},'far'),({'GATE':'OTHER'},'far'),({'SAME':0},'clock'),({'MAXG':2},'big')])
def test_guards_refuse_without_rewiring(kw,result):
 out=run(**kw);assert f'RESULT {result} CHANGED=0 MOVED=0 A=N1 B=N1 C=N2' in out,out

@pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh missing')
def test_report_only_never_reconnects():
 out=run(REPORT=1);assert 'RESULT moved CHANGED=0 MOVED=0 A=N1 B=N1 C=N2' in out,out

def test_fallback_stays_inside_existing_optin_and_keeps_ordinary_radius():
 s=SRC.read_text();assert 'OT_S81_RCK_AM_COHORT' in s
 assert 'if {$verdict eq "far"} {set verdict [ot_rck_am_near $members]}' in s
 assert 'set r [expr {$la_um * $la_dbu}]' in s
 assert 'OT_RCK_AM_UM' not in s
