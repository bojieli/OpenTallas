"""Supplemental Stage A visibility control only; original candidate ODB untouched."""
import json,os,hashlib
from pathlib import Path
import odb,openroad
P=Path('/work');os.chdir(P)
assert hashlib.sha256(Path('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad').read_bytes()).hexdigest()=='21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846'
tech=openroad.Tech();tech.readLef('/work/input/asap7_tech.lef');design=openroad.Design(tech);design.readDef('/work/empty.def'); db=tech.getDB();block=design.getBlock();t=db.getTech()
# EXACT same relative 9nm step union as original controls, now actual fixed pin figures.
net=odb.dbNet.create(block,'FIXED_PIN_CONTROL');term=odb.dbBTerm.create(net,'FIXED_PIN_CONTROL');term.setIoType('INPUT');pin=odb.dbBPin.create(term);pin.setPlacementStatus('FIRM')
rects=[[744,987,1032,1011],[1008,996,1032,1020]]
for r in rects:odb.dbBox.create(pin,t.findLayer('M4'),*r)
(P/'fixed_pin_geometry.json').write_text(json.dumps(dict(status='FIRM_BPIN',rects_nm=rects,role='visibility negative only; same union as original 9nm step; not production geometry'),indent=2)+'\n')
# Recover every native LEF property string and numeric width-table vector from actual loaded DB.
rule_dump={}
for ln in ['M4','M5']:
 l=t.findLayer(ln);out={}
 for prop in odb.dbProperty.getProperties(l):
  try:out['property:'+prop.getName()]=prop.getValue()
  except Exception as e:out['property:'+prop.getName()]=str(e)
 for j,w in enumerate(l.getTechLayerWidthTableRules()):
  a={'methods':[m for m in dir(w) if not m.startswith('_')]}
  for name in a['methods']:
   if name.startswith('get'):
    try:
     val=getattr(w,name)()
     if not isinstance(val,(str,int,float,bool,list,tuple)):
      try:val=list(val)
      except Exception:val=str(val)
     a[name]=val
    except Exception as e:a[name]={'unavailable':str(e)}
  out['width_table_'+str(j)]=a
 rule_dump[ln]=out
(P/'actual_property_rules.json').write_text(json.dumps(rule_dump,indent=2,default=str)+'\n')
design.evalTclString('write_db /work/fixed_pin.odb');design.evalTclString('write_def /work/fixed_pin.def')
cmd='drt::check_drc -box {808 808 1208 1208} -output_file /work/fixed_pin_markers.rpt -marker_name TRUE_FIXED_PIN'
result=design.evalTclString('if {[catch {'+cmd+'} why]} {puts stderr "CHECKER_ERROR $why"; exit 1} else {puts "CHECKER_OK fixed_pin $why"}')
assert (P/'fixed_pin_markers.rpt').is_file(),result
print('FIXED_PIN_COMPLETE',repr(result),flush=True)
