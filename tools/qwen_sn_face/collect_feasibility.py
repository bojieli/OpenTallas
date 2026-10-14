#!/usr/bin/env python3
"""Summarize preserved actual floorplan and placement-estimated CTS evidence."""
import hashlib,json,pathlib
root=pathlib.Path(__file__).resolve().parents[2]
r=root/'results/rtl/qwen_sn_face_1013';items={}
for name in ['sn_e0','ns_e0','sn_e1','ns_e1']:
 d=json.loads((r/name/'floorplan_dump.json').read_text());ck=json.loads((r/name/'ck.json').read_text());bad=[]
 signals=[x for x in d['bterms'] if x[3] in ['INPUT','OUTPUT']]
 for pin,_,kind,direction,shapes in signals:
  side=('S' if name.startswith('sn') else 'N') if pin.startswith('d[') else ('N' if name.startswith('sn') else 'S') if pin.startswith('q[') else 'W'
  for layer,(x0,y0,x1,y1) in shapes:
   if layer!=('M4' if side=='W' else 'M5') or (side=='W' and x0!=0) or (side=='S' and y0!=0) or (side=='N' and y1!=12.96):bad.append(pin)
 assert not bad,(name,bad)
 assert len(signals)==(1026 if name.endswith('1') else 1025)
 assert len(d['rows'])==32
 items[name]={'rows':len(d['rows']),'row_height_um':round(d['rows'][0][3]-d['rows'][0][1],3),'die':d['die'],'core':d['core'],'signal_pins':len(signals),'pin_face_layer_errors':bad,'three_corner_boundary':{c:ck[c]['boundary'] for c in ['tt','ff','ss']},'parasitics':ck['parasitics'],'scope':'Prototype actualsite/PG/pin placement/CTS evidence; no routed view or die-slot approval'}
a={'scope':'Four independent candidate face masters; no route job submitted','rtl_sha256':hashlib.sha256((root/'rtl/qwen_sys/vm_plane_20261013/face/ot_qfd_vm_face.sv').read_bytes()).hexdigest(),'masters':items}
(r/'feasibility.json').write_text(json.dumps(a,indent=1)+'\n')
for n,v in items.items():
 t=v['three_corner_boundary']['tt'];print(n,'TT mean/max/spread',t['mean'],t['max'],round(t['max']-t['min'],1),'ps')
