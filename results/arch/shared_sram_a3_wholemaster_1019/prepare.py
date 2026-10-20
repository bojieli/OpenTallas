import gzip,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;i=json.loads(gzip.decompress((P/'inventory.json.gz').read_bytes()))
for fam,d in i['families'].items():
 out=P/fam;out.mkdir(exist_ok=True)
 shapes=[dict(s,source_identity=s['identity'])for s in d['shapes'] if s['role']not in ['via_cut','via_enclosure']]
 c={'name':fam,'family':fam,'wire_status':'ROUTED','shapes':shapes,'vias':d['vias'],'score_roi_nm':d['full_native_roi_dbu'],'conditional_OBS':d['conditional_OBS']}
 (out/'coupon.json').write_text(json.dumps({'cases':[c]},indent=2)+'\n')
 w,h=d['outline_nm'];(out/'empty.def').write_text(f'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN a3_{fam} ;\nUNITS DISTANCE MICRONS 1000 ;\nDIEAREA ( 0 0 ) ( {w} {h} ) ;\nTRACKS Y 3 DO {math.ceil(h/48)} STEP 48 LAYER M4 ;\nTRACKS X 0 DO {math.ceil(w/48)} STEP 48 LAYER M5 ;\nGCELLGRID X 0 DO {math.ceil(w/1000)+1} STEP 1000 ;\nGCELLGRID Y 0 DO {math.ceil(h/1000)+1} STEP 1000 ;\nEND DESIGN\n')
out=P/'controls';out.mkdir(exist_ok=True);(out/'coupon.json').write_text(json.dumps({'cases':i['original_controls']},indent=2)+'\n');(out/'empty.def').write_text(Path('/home/ubuntu/artifacts/sram-coupon-a2-1019/empty.def').read_text())
