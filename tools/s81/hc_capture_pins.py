#!/usr/bin/env python3
"""Assign native HC owned capture leaves using closed CPL receiver coordinates.
Preserve the original strip port rectangles. Additional register pins occupy free
S-face M5 tracks nearest the repeated CPL input coordinates. Report exact geometry;
new launch/capture timing remains a required native audit after routing.
"""
import json,re
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_hc_capture';out.mkdir(exist_ok=True)
 base=json.loads((R/'physical/s81_die_pins/v19_ntree/ot_s81_hc_ctfx_nt.json').read_text())
 cplwh,cpl=V.lef_bits('physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl/ot_s81_hc_ctpl.lef')
 rows=[(g,h,144.72*g,751.68-y-118.8) for g in range(4) for h,y in enumerate((203.04,416.88))]
 # One master broadcasts both half rows; x optimum for every bit is midpoint
 # of min/max closed receiver pins across all four columns.
 desired=[]
 for source,port in [('fv_local','fv'),('fdx_local','fdx')]:
  for b,pin in sorted(cpl[port].items()):
   xs=[x+pin[2] for _,_,x,_ in rows]
   desired.append(((min(xs)+max(xs))/2,source,b))
 old={p:v['per_bit'] for p,v in base['ports'].items()}
 used=[b[2] for ps in old.values() for b in ps if b[:2]==['S','M5']]
 free=[round(0.24+.096*i,3) for i in range(6000) if 0.2<=.24+.096*i<=576.52 and all(abs(.24+.096*i-u)>=.0479 for u in used)]
 desired.sort();target=sum(x[0] for x in desired)/len(desired)
 width=len(desired);start=min(range(len(free)-width+1),key=lambda i:abs((free[i]+free[i+width-1])/2-target))
 extra={'fv_local':[None]*7,'fdx_local':[None]*1128}
 for (_,p,b),x in zip(desired,free[start:start+width]):extra[p][b]=['S','M5',x,.084]
 proof=[]
 for p,rp in [('fv_local','fv'),('fdx_local','fdx')]:
  for bit,pin in sorted(cpl[rp].items()):
   sx=extra[p][bit][2];sy=751.68-365.04-25.92+.042
   for g,h,x,y in rows:
    length=abs(sx-x-pin[2])+abs(sy-y-pin[3])
    proof.append({'port':p,'bit':bit,'group':g,'half':h,'length_um':round(length,3)})
 for master in ('ot_s81_hc_ctfx_nt','ot_s81_hc_ctfx_cap'):
  ports={p:list(v) for p,v in old.items() if master.endswith('_nt') or p in ('clk','rst_in','fv_in','fd_in','fv','fdx')}
  ports.update(extra)
  # Custom writer preserves original rectangles; all new S pins have checked
  # spacing from preserved ports rather than nudging accepted rectangles.
  rec=dict(base,master=master,case='v20_hc_owned_capture',ports={p:{'bits':len(v),'uniform':False,'per_bit':v} for p,v in ports.items()},source='tools/s81/hc_capture_pins.py')
  (out/(master+'.json')).write_text(json.dumps(rec,indent=1)+'\n')
  lines=[]
  for p,ps in ports.items():
   for i,(f,ly,c,d) in enumerate(ps):
    x,y={'S':(c,.042),'N':(c,25.878),'W':(.042,c),'E':(576.678,c)}[f]
    nm=p if len(ps)==1 else f'{p}[{i}]'
    lines.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
  (out/(master+'.tcl')).write_text('\n'.join(lines)+'\n')
 report={'scope':'actual CLOSED CPL faces only; CTRA/CTRB have no published LEF and remain unverified','max_um':max(r['length_um'] for r in proof),'over500':[r for r in proof if r['length_um']>500],'hops':proof,'new_sink_timing':'unverified pending routed owned capture leaf'}
 (out/'cpl_geometry.json').write_text(json.dumps(report,indent=1)+'\n')
 # Strip expansion requires 751.68 height: old spare2.16 is consumed. N-face
 # offsets preserve upper rows; all rows below capture move12.96 down.
 contract=json.loads((R/'results/arch/hier_contract_1011/s81.json').read_text())['sub_layouts']['ot_s81_hc_cth']
 contract=json.loads(json.dumps(contract));contract['outline']['h']=751.68;contract['spare_um']=0
 for row in contract['rows']:
  if row['tile']=='ctfx':row.update(cell='ot_s81_hc_ctfx_cap',h=25.92)
  elif row['y']>365.04:row['y']=round(row['y']+12.96,3)
 contract['qualification']='NEW_UNCLOSED_NATIVE_CAPTURE; actual CPL geometry reported, CTRA/CTRB/native timing owed'
 (out/'serial_capture_layout.json').write_text(json.dumps(contract,indent=1)+'\n')
 print('CAPTURE_PIN_ASSIGN',len(proof),'CPL bits',report['max_um'],'max_um',len(report['over500']),'over500')
if __name__=='__main__':main()
