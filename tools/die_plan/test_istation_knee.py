"""Internal stations must use shared, axis-aligned banks and keep the priced depth."""
from pathlib import Path
import subprocess,sys
sys.path.insert(0,str(Path(__file__).parent))
import kit_istations as I
PROC=I.TCL_HEAD[I.TCL_HEAD.index('proc is_knee_site'):I.TCL_HEAD.index('proc is_bits')]

def call(body):
    p=subprocess.run(['tclsh'],input=PROC+'\n'+body,text=True,capture_output=True)
    assert p.returncode==0,p.stderr
    return p.stdout.strip()

def test_all_bits_use_same_leg_and_fixed_normal_coordinate():
    out=call('''
for {set edge 1} {$edge <= 3} {incr edge} {
 foreach py {1390 1500 1700} {
  puts "$edge [is_knee_site 0 $py 785.966 1883.6 W $edge 4 out {0 1390 0 1700}]"
 }
}
''')
    rows=[list(map(float,l.split())) for l in out.splitlines()]
    for k in (1,2,3):
        pts=[r[1:] for r in rows if r[0]==k]
        assert max(p[0] for p in pts)-min(p[0] for p in pts)<1e-6
    assert rows[3][1]==785.966  # stage 2 is the shared knee column
    assert rows[3][2]==1390.0

def test_rejects_insufficient_plan_depth_without_inserting_cycles():
    assert call('''
if {[catch {is_knee_site 0 0 1200 1500 W 1 2 out {0 0 0 100}} msg]} { puts $msg } else {error "missing depth guard"}
''').startswith('internal station knee needs a plan depth change:')

def test_input_chain_reverses_output_chain_with_identical_depth():
    out=call('''
for {set k 1} {$k < 8} {incr k} {
 set a [is_knee_site 0 1450 935.49 1883.6 W $k 8 in {0 1390 0 1700}]
 set b [is_knee_site 0 1450 935.49 1883.6 W [expr {8-$k}] 8 out {0 1390 0 1700}]
 puts "[expr {abs([lindex $a 0]-[lindex $b 0])}] [expr {abs([lindex $a 1]-[lindex $b 1])}]"
}
''')
    assert all(max(map(float,l.split()))<1e-6 for l in out.splitlines())
