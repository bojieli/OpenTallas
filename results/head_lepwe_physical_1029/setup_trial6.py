import json,hashlib,re,shutil,sys
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-head-lepwe');K=R/'trial_v6';K.mkdir(exist_ok=True)
p=json.loads((R/'geom/register_plan_v6.json').read_text());assert p['final']['r2r_max']<=405;aa={x['name']:x['xy'] for x in json.loads((R/'geom/macro_face_assignment.json').read_text())}
# Change instance-to-site assignment only; masters/sites, outline and interfaces stay unchanged.
f=K/'macro_placement.tcl';s=f.read_text()
lines=[];n=0
for ln in s.splitlines():
 m=re.match(r'^(\s*)\{(.*?)\} (\S+) ([-\d.]+) ([-\d.]+) (\S+)$',ln)
 if m and m[2] in aa:
  x,y=aa[m[2]];ln=f'{m[1]}{{{m[2]}}} {m[3]} {x:.4f} {y:.4f} {m[6]}';n+=1
 lines.append(ln)
assert n==19,n;f.write_text('\n'.join(lines)+'\n')
body=['# Plan-fixed register field: no RTL/cycle/clock modification.', 'set rp_blk [ord::get_db_block]','set rp_dbu [$rp_blk getDbUnitsPerMicron]','set rp_orient {}','foreach row [$rp_blk getRows] { dict set rp_orient [lindex [$row getOrigin] 1] [$row getOrient] }','set rp_n 0','foreach {name master maxw maxh x y} {']
for r in p["registers"]:body.append("  {"+r["name"]+"} "+r["master"]+" %.6f %.6f %.6f %.6f" % (*r["reserved_size"],*r["xy"]))
body += ['} {','  set i [$rp_blk findInst $name]','  if {$i eq "NULL" || $i eq ""} { error "LEP register plan missing $name" }','  set am [[$i getMaster] getName]', '  regsub {x(p[0-9]+|[0-9]+)_ASAP7} $am {_ASAP7} astem', '  regsub {x(p[0-9]+|[0-9]+)_ASAP7} $master {_ASAP7} estem', '  if {$astem ne $estem} { error "LEP flop function/polarity changed: $name" }', '  if {[[$i getMaster] getWidth] > round($maxw*$rp_dbu) || [[$i getMaster] getHeight] > round($maxh*$rp_dbu)} { error "LEP register exceeds reserved site: $name" }','  set xx [expr {round($x * $rp_dbu)}]; set yy [expr {round($y * $rp_dbu)}]','  if {![dict exists $rp_orient $yy]} { error "LEP register plan not on row: $name y=$y" }','  $i setPlacementStatus PLACED; $i setOrient [dict get $rp_orient $yy]; $i setLocation $xx $yy; $i setPlacementStatus FIRM','  incr rp_n','}',f'if {{$rp_n != {len(p["registers"])}}} {{ error "LEP planned register count changed: $rp_n" }}','puts "LEP_REGISTER_PLAN fixed $rp_n registers (dataflow, unchanged clock/interface/cycles)"']
(K/'register_plan.tcl').write_text('\n'.join(body)+'\n')
for ff in ('face_flops.tcl','face_flops_release.tcl'):
 f=K/ff;f.write_text(f.read_text()+'\n# Same plan at both stages; no post-measurement coordinate changes.\nsource /work/register_plan.tcl\n')
(K/'TRIAL_ONLY').write_text('Placement-only structural trial. Original G1FAIL retained; no signoff/route authorization. Full-kit source LEC remains separate and live.\n')
fz=json.loads((K/'freeze.json').read_text());fz['head_register_plan']=dict(source='codex/head-lepwe-ready-1029@7702c74cf',sha256=hashlib.sha256((R/'geom/register_plan_v6.json').read_bytes()).hexdigest(),macro_assignment_sha256=hashlib.sha256((R/'geom/macro_face_assignment.json').read_bytes()).hexdigest(),cycles_added=0,registers=len(p['registers']))
# Core generator's canonical kit hash, with the same driver that made this kit.
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-head-lepwe/physical/die_plan/hbm_arch_cores')
import gen_core_kit_hbm as G
fz['kit_hash']=G.kit_hash(K);(K/'freeze.json').write_text(json.dumps(fz,indent=1)+'\n')
print('ready',K,'19macro assignments',len(p['registers']),'registers')
