from pathlib import Path
import json
P=Path('/srv/opentallas-scratch/claude/codex-hbm-rebal-0310/final_grt');O=Path(__file__).parent

def inst(p):
 return{r[1]:r[2:]for l in p.read_text().splitlines()if(r:=l.split('\t'))[0]=='INST'}
a,b=map(inst,(P/'clock_pre.tsv',P/'clock_post.tsv'));assert set(a)==set(b)
# Placement status changes aren't a geometry change. Preserve original master,
# DB integer location and actual orientation, not rounded TSV bounding boxes.
names=[n for n in a if a[n][:4]!=b[n][:4]];assert len(names)==35
rows=[dict(name=n,master=a[n][0],x_db=int(a[n][1]),y_db=int(a[n][2]),orient=a[n][3],old_status=a[n][4])for n in names]
(O/'restore35.json').write_text(json.dumps(dict(status='PREPARED_NO_RUN',instances=rows),indent=2)+'\n')
tcl=['set restore35 {']
for r in rows:tcl.append(' {'+' '.join(['{'+r['name']+'}',r['master'],str(r['x_db']),str(r['y_db']),r['orient']])+'}')
tcl+=['}', 'set block [ord::get_db_block]','foreach rec $restore35 {',' lassign $rec name master x y orient',' set i [$block findInst $name]',' if {$i eq "NULL" || $i eq ""} {error "RESTORE missing $name"}',' if {[[$i getMaster] getName] ne $master} {error "RESTORE master change $name"}',' $i setOrient $orient',' $i setLocation $x $y',' if {[$i getLocation] ne [list $x $y] || [$i getOrient] ne $orient} {error "RESTORE failed $name"}','}','puts "HNX_RESTORE35 ORIGINAL_HOMES_DONE"']
(O/'restore35.tcl').write_text('\n'.join(tcl)+'\n')
