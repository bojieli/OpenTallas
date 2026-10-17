#!/usr/bin/env python3
"""Export source-joined raw ABI clock pin homes for a named development placement.
Insertion numbers are reference measurements only; route-source identity remains unqualified.
"""
import argparse,gzip,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);a=ap.parse_args();r=a.root;inv=json.load(open(r/'inventory.json'));pin=json.load(gzip.open(r/'master_pins.json.gz','rt'));packing=json.load(open(r/'packing_producer_local.json'))['options'][0];clock=json.load(open(r/'clock_root_join.json'));rows=[];reference={}
 for e in clock['roots']:
  row=dict(category=e['category'],bit=e['bit'],domain='serial'if e['category'].endswith('_s')else'stream',phase_delivery_status='UNQUALIFIED_NO_PARENT_PHI_WIRE_R_PROOF')
  if e['hard_leaf_pins']:
   assert len(e['hard_leaf_pins'])==1;i,port,bit,d=e['hard_leaf_pins'][0];leaf=inv['leaves'][i];xy=pin[leaf['kit']]['pins'][port];origin=packing['positions'][str(i)];row.update(leaf=i,path=leaf['path'],master=leaf['master'],kit=leaf['kit'],clock_pin=port,xy_um=[xy[k]+origin[k]for k in [0,1]])
   if(leaf['kit'],port)not in reference:
    ins=sorted((ROOT/'physical/ref_tile'/leaf['kit']/'views').glob('*/insertion.json'));data=json.load(open(ins[0]))if ins else{};measure=data.get('clock_measurements',{}).get(port,{}).get('tt',{}).get('boundary');reference[(leaf['kit'],port)]=measure
   row['R_tt_reference_boundary']=reference[(leaf['kit'],port)];row['R_qualification']='REFERENCE_ONLY_ROUTE_CURRENT_SOURCE_IDENTITY_UNVERIFIED';row['explicit_param_mismatches']=leaf.get('explicit_kit_param_mismatches',{})
  else:row.update(xy_um=None,status='LEGACY_NO_NATIVE_HARD_SINK'if e['category']=='ck_core_t'else'INLINE_CONTROL_NO_HARD_OUTLINE_OR_PIN_HOME')
  rows.append(row)
 rec=dict(scope=inv['scope'],source_commit=inv['source_commit'],placement=packing['name'],clock_entries=len(rows),assigned_hard_pin_homes=sum(e['xy_um']is not None for e in rows),entries=rows)
 (r/'clock_candidate_homes.json').write_text(json.dumps(rec,indent=1)+'\n');print('693entries688hardhomes5explicitgaps')
if __name__=='__main__':main()
