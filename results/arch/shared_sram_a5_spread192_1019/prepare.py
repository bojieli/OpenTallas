import json,gzip,hashlib,math,copy
from pathlib import Path
from collections import Counter
P=Path(__file__).resolve().parent
m=json.loads((P/'input/owned_model.json').read_text());a=json.loads(gzip.decompress((P/'input/a3_inventory.json.gz').read_bytes()));tr=json.loads((P/'input/trunk_model.json').read_text())
inv={'scope':'A5 entire enumerated source-owned actual metal, not core reservation occupancy','sources':{'owned_contract':'73b118546 Spread192 (corrected f25d1e4d2)' ,'A3':'3f468 (exact c634 unchanged)'},'families':{},'original_controls':a['original_controls']}
for fam,f in m['families'].items():
 old=a['families'][fam]
 sig=[dict(s,source_identity=s['identity']) for s in old['shapes'] if s['role'] not in ['via_cut','via_enclosure'] and s['net'] not in ['VDD','VSS']]
 sv=[dict(v) for v in old['vias']]
 assert len({s['net'] for s in sig})==({'qwen':206,'sc2':437}[fam])
 assert len(sv)==({'qwen':408,'sc2':870}[fam])
 supply=[dict(s,identity=s['id'],source_identity=s['id']) for s in f['new_actual_supply_metal'] if not s['role'].startswith('native_VIA')]
 pv=[]
 for c in f['contact_ledger']:
  for v in c['via_stacks']:
   boxes={o['layer']:o['rect_nm'] for o in v['objects']}
   pv.append({'identity':v['id'],'net':c['net'],'name':v['type'],'center_nm':v['center_nm'],'boxes_nm':boxes,'bottom_layer':next(k for k in boxes if k.startswith('M'))})
 ports=[]
 for t in tr['families'][fam]['trunks']:
  for side in ['north','south']:ports.append({'identity':t['id']+':'+side.upper()+'_PORT','net':t['net'],'layer':'M5','rect_nm':t[side+'_port_nm'],'role':'external_supply_interface_subset_of_trunk'})
 shapes=sig+supply
 boxes=[{'identity':s.get('identity'), 'net':s['net'],'layer':s['layer'],'rect_nm':s['rect_nm'],'role':s['role']} for s in shapes]
 for v in sv:
  for lay,key in [('M4','m4_rect_nm'),('M5','m5_rect_nm'),('V4','cut_rect_nm')]:boxes.append({'identity':v['identity']+':'+lay,'net':v['net'],'layer':lay,'rect_nm':v[key],'role':'signal_via'})
 for v in pv:
  for lay,r in v['boxes_nm'].items():boxes.append({'identity':v['identity']+':'+lay,'net':v['net'],'layer':lay,'rect_nm':r,'role':'supply_via'})
 # Source-owned exact supply multiset, including all native enclosures/cuts.
 expected=[(s['net'],s['layer'],tuple(s['rect_nm'])) for s in f['new_actual_supply_metal']+f['new_actual_supply_cuts']]
 actual=[(s['net'],s['layer'],tuple(s['rect_nm'])) for s in boxes if s['net'] in ['VDD','VSS']]
 assert Counter(expected)==Counter(actual)
 d={'outline_nm':f['outline_nm'],'shapes':shapes,'vias':sv+pv,'ports':ports,'actual_boxes':boxes,'conditional_OBS':f['original_OBS_reservations_retained'],'core_exclusions':f['lower_core_exclusions'],'core_bbox':f['original_bitcore_bbox_nm'],'attachment_bbox':f['new_attachment_core_bbox_nm'],'scope':'all known signal access and all owned supply metal/cuts; conditional core interiors are explicit reservations, not fabricated metal'}
 d['counts']={'signal_nets':len({s['net'] for s in sig}),'signal_vias':len(sv),'supply_rails_and_M1_ports':f['contact_count'],'supply_vias':len(pv),'wire_shapes':len(shapes),'actual_decoded_boxes_expected':len(boxes),'external_supply_port_subsets':len(ports),'OBS_reservations':len(d['conditional_OBS']),'lower_exclusions':len(d['core_exclusions']),'layer_boxes':dict(Counter(s['layer'] for s in boxes))}
 inv['families'][fam]=d
 out=P/fam;out.mkdir(exist_ok=True)
 (out/'coupon.json').write_text(json.dumps({'cases':[dict(d,name=fam,wire_status='ROUTED',score_roi_nm=[0,0,*f['outline_nm']])]},indent=2)+'\n')
 w,h=f['outline_nm'];(out/'empty.def').write_text(f'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN a5_{fam} ;\nUNITS DISTANCE MICRONS 1000 ;\nDIEAREA ( 0 0 ) ( {w} {h} ) ;\nTRACKS Y 18 DO {math.ceil(h/36)} STEP 36 LAYER M2 ;\nTRACKS X 0 DO {math.ceil(w/36)} STEP 36 LAYER M1 M3 ;\nTRACKS Y 3 DO {math.ceil(h/48)} STEP 48 LAYER M4 ;\nTRACKS X 0 DO {math.ceil(w/48)} STEP 48 LAYER M5 ;\nGCELLGRID X 0 DO {math.ceil(w/1000)+1} STEP 1000 ;\nGCELLGRID Y 0 DO {math.ceil(h/1000)+1} STEP 1000 ;\nEND DESIGN\n')
(P/'inventory.json.gz').write_bytes(gzip.compress(json.dumps(inv).encode(),mtime=0))
(P/'source_comparison.json').write_text(json.dumps({'inputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (P/'input').iterdir()},'families':{k:{'signal_geometry_unchanged':True,'all_owned_supply_box_multiset_exact':True,'counts':v['counts']} for k,v in inv['families'].items()},'A3_input_immutable':True,'repairs_or_translations':False,'no_engine_run':True},indent=2)+'\n')
print(json.dumps({k:v['counts'] for k,v in inv['families'].items()},indent=2))
