"""Diagnostic census of the actual selected source only; never maps old leaves to HN slots."""
from pathlib import Path
import json,sys,hashlib,collections
P,O=map(Path,sys.argv[1:]);d=json.load(open(P));glue=[];qs=[];unknown=[]
for c in d['cells']:
 if c['kind']=='glue' and c['module']in('$dff','$adff','$sdff','$dffe','$adffe','$sdffe'):
  q=c['ports']['Q'];clk=c['ports'].get('CLK',{});glue.append(dict(path=c['path'],module=c['module'],state_bits=q['width'],clock_sources=clk.get('sources',[]),Q_nets=q['bits']))
 elif c['module']=='ot_smh_qs_reg':
  assert c['ports']['d']['width']==c['ports']['q']['width'];qs.append(dict(path=c['path'],state_bits=c['ports']['q']['width'],clock_sources=c['ports']['clk']['sources'],source_body='rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv:304; one r per qbit, RM chooses reset only',q_nets=c['ports']['q']['bits']))
 elif c['kind']=='leaf':unknown.append(dict(path=c['path'],module=c['module'],reason='Opaque to current selected-part packet; no FF count or HN slot identity invented'))
O.mkdir(parents=True,exist_ok=True);out=dict(status='DIAGNOSTIC_SOURCE_CENSUS_ONLY; HN physical cut mapping FAIL',source_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),source_packet=str(P),actual_cells=len(d['cells']),actual_glue_cells=sum(c['kind']=='glue'for c in d['cells']),actual_glue_sequential_bits=sum(x['state_bits']for x in glue),actual_qs_register_bits=sum(x['state_bits']for x in qs),known_sequential_bits=sum(x['state_bits']for x in glue+qs),QS=qs,glue=glue,other_leafs_unexpanded=unknown,planned_architecture='32 hnx_rp3lp3h n/s hard masters',source_leaf_classes=dict(collections.Counter(c['module']for c in d['cells']if c['kind']=='leaf')),physical_source_compatible=False,FF_homes='NOT BUILT: wait for intended HN exact source composition; no fictional grid',density_requirements='Count all actual selected state bits once, actual reset/START controls and clock aliases, max1500sinks/tap/radius200um; derive legal row/body homes from GEN/RT only',source_changes=0,added_cycles=0)
(O/'selected_source_ff_census.json').write_text(json.dumps(out,indent=1)+'\n');print(out['known_sequential_bits'],out['actual_glue_sequential_bits'],out['actual_qs_register_bits'],out['source_leaf_classes'])
