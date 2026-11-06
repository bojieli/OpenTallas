from pathlib import Path
import json,sys
R=Path('/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106');sys.path.insert(0,str(R/'src/tools/die_plan'))
import taps
rows=json.loads((R/'ev/model.json').read_text())['cbn_q00__cldbcda913']['new_tap_rows'];sinks=[]
for line in Path('/srv/opentallas-scratch3/claude/qc-tapsplit/probe/cbn/sinks.txt').read_text().splitlines():
 a=line.split()
 if a[0]=='SINK' and a[-1]=='0':sinks.append((a[1],float(a[2]),float(a[3])))
load,far,asg=taps.assign(rows,[(x,y,1) for n,x,y in sinks],1200,200,max_distance_um=200)
assert max(load)<=1200 and max(far)<=200
with (R/'proto_assign.tcl').open('w') as f:
 f.write('set ct_taps {};set proto_nets {};set blk [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron]\n')
 for j,(n,x,y,*_) in enumerate(rows):
  f.write(f'set nn [odb::dbNet_create $blk ot_proto_clk_{j}];dict set proto_nets {j} $nn;lappend ct_taps [list ot_proto_clk_{j} $nn [expr {{{x}*$dbu}}] [expr {{{y}*$dbu}}]]\n')
 for (n,x,y),j in zip(sinks,asg):
  f.write('set i [$blk findInst {'+n+'}];if {$i eq "NULL" || $i eq {}} {error "missing actual sink"};set k 0;foreach it [$i getITerms] {if {[$it getNet] eq $proto_root && [$it isInputSignal]} {$it disconnect;$it connect [dict get $proto_nets '+str(j)+'];incr k}};if {$k!=1} {error "actual sink root-clock identity mismatch"}\n')
print('measured prototype',len(rows),len(sinks),max(load),max(far),flush=True)
