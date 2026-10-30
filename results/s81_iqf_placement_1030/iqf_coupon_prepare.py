from pathlib import Path
import json
root=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030')
out=root/'iqf_coupon';out.mkdir(exist_ok=True)
rows=sum([json.load(open(root/f))['targets'] for f in ['iqf_ft0_targets.json','iqf_ft1_read_targets.json']],[])
assert len(rows)==8095 and len(set(r['name'] for r in rows))==8095
lines=['read_db /work/original.odb','set b [ord::get_db_block]','set dbu [[ord::get_db_tech] getDbUnitsPerMicron]','set n 0']
for r in rows:
 name=r['name'];x,y=r['xy'];lines += [f'set i [$b findInst {{{name}}}]',f'if {{$i eq "NULL"}} {{error "Missing intended existing FF"}}','$i setPlacementStatus PLACED',f'$i setLocation [expr {{round({x}*$dbu)}}] [expr {{round({y}*$dbu)}}]','$i setPlacementStatus FIRM','incr n']
lines += ['puts "IQF_EXISTING_FF_TARGETS $n"','detailed_placement','check_placement -verbose','write_db /work/legal.odb','source /work/geom_dump.tcl']
(out/'place.tcl').write_text('\n'.join(lines)+'\n')
