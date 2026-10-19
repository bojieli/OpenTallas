#!/usr/bin/env python3
"""Actual-ODB readonly preflight control for the opt-in fixed clock row helper."""
import argparse,json
from pathlib import Path
import odb
from openroad import Tech,Design
from qwen_clock_power_sites import ClockPowerSites

p=argparse.ArgumentParser(description=__doc__)
for n in ('odb','manifest','policy','out'):p.add_argument('--'+n,required=True)
a=p.parse_args();t=Tech();d=Design(t);d.readDb(a.odb);b=d.getBlock()
model=ClockPowerSites.from_block(b,odb,[d.getDb().findMaster(n) for n in ('BUFx24_ASAP7_75t_R','BUFx12f_ASAP7_75t_R')])
cells=json.loads(Path(a.manifest).read_text())['cells'];good=[];bad=[]
for n,_,x,y in cells:
    (good if model(x,y) else bad).append(n)
if not good or not bad:raise ValueError('actual positive/negative controls absent')
d.evalTclString('source {'+a.policy+'}')
default=d.evalTclString('info default ot_tie_rows preserve_clock_cells value; set value')
if default:raise ValueError('clock preservation is not default off')
d.evalTclString('''
set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]; set obstacles {}
foreach inst [$block getInsts] {
 set m [$inst getMaster]
 if {[$m isBlock] || [$m isPad]} {
  set bb [$inst getBBox]
  lappend obstacles [list [expr {[$bb xMin]-1080}] [expr {[$bb yMin]-1080}] [expr {[$bb xMax]+1080}] [expr {[$bb yMax]+1080}]]
 }
}
set site [[lindex [$block getRows] 0] getSite]
''')
receipts=[]
for name,expected in ((good[0],True),(bad[0],False)):
    obj=b.findInst(name);before=(tuple(obj.getLocation()),str(obj.getOrient()))
    try:
        result=d.evalTclString('ot_clock_rows_prepare $block $dbu $obstacles {'+name+'} 12000 600 8640 .48 $site')
        accepted=True;error=None
    except Exception as e:accepted=False;error=str(e);result=None
    after=(tuple(obj.getLocation()),str(obj.getOrient()))
    if accepted!=expected or before!=after:raise ValueError('actual preflight control failed '+str((name,accepted,error,before,after)))
    receipts.append(dict(clock=name,expected_accept=expected,actual_accept=accepted,error=error,
                         coordinates_unchanged=before==after,result=result))
result=dict(schema='opentallas.qwen.fixed_clock_row_preflight_controls.v1',
            controls=receipts,default_off=True,rows_created=False,power_qualified=False,
            timing_qualified=False,production_admitted=False)
Path(a.out).write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1),flush=True)
