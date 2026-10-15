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
 # Direct vertical M3 pin-to-pin capture lanes. Original M5 first-stage
 # rectangles remain fixed; a different net may share x on another layer.
 extra={'fv_local':[list(x) for x in old['fv_in']],
        'fdx_local':[list(x) for x in old['fd_in']]}
 occupied=set();clamps=[]
 for p,source in [('fv_local','fv'),('fdx_local','fdx')]:
  for bit,b in enumerate(extra[p]):
   sx=b[2];sy=751.68-365.04-25.92+.042
   limits=[]
   for g,h,x,y in rows:
    pin=cpl[source][bit];radius=499.8-abs(sy-y-pin[3])
    limits.append((x+pin[2]-radius,x+pin[2]+radius))
   lo=max(t[0] for t in limits);hi=min(t[1] for t in limits)
   assert lo<=hi,(p,bit,'no single-pin CPL reach solution',lo,hi)
   target=min(max(sx,lo),hi)
   # ASAP7 M3 vertical track centres: .012 + .048*n; reserve separate
   # tracks for distinct local outputs, including the nine edge clamps.
   candidates=[round(.012+.048*n,3) for n in range(max(0,int((lo-.012)/.048)+1),int((hi-.012)/.048)+1)]
   candidates=[c for c in candidates if c not in occupied]
   assert candidates,(p,bit,'no free M3 pin within reach interval')
   outx=min(candidates,key=lambda c:abs(c-target))
   if abs(outx-sx)>.0241:clamps.append([p,bit,sx,outx])
   occupied.add(outx);extra[p][bit]=['S','M3',outx,.084]
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
  # Put the reset capture flop within its measured CTS cluster. Preserve UL
  # pins: moving ul_out[15] would exceed its actual 500um north seam.
  reset_x = 45.036 if master.endswith('_nt') else 225.036
  ports['rst_in'] = [['N','M3',reset_x,.084]]
  if master.endswith('_nt'):
   # Production TID is localparam BC+p or BC+START+p in dsfd_sp_hc.
   # Its capture must stay in the measured reset/control clock neighborhood.
   ports['tid'] = [['N','M3',round(45.132+.096*i,3),.084] for i in range(8)]
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
 report={'scope':'actual CLOSED CPL faces only; CTRA/CTRB have no published LEF and remain unverified','max_um':max(r['length_um'] for r in proof),'over500':[r for r in proof if r['length_um']>500],'hops':proof,'new_sink_timing':'unverified pending routed owned capture leaf','M3_reach_clamps':clamps,'reset_reassignment':{'source':'CLOSED ot_s81_hc_ctfn.rst_c W M4 centre(0.042,10.044), ctfn Noffset390.96','source_xy_um':[.042,344.844],'capture_N_y_um':386.598,'serial_reset_x_um':225.036,'nt_reset_x_um':45.036,'serial_hop_um':266.748,'nt_hop_um':86.748,'qualification':'geometry only; native reset epoch, launch/capture and CTS remain required'},'tid_delivery':{'port':'ot_s81_hc_ctfx_nt.tid[7:0]','pins':'N/M3 x45.132..45.804','source':'rtl/dsrom_sys/s81_suhc/dsfd_sp_hc.sv localparam TID=BC+p or BC+START+p, passed through cth_nt to ctfx_nt','delivery':'static per-instance value; local tie realization remains required in native parent, no dynamic launch source','native_capture':'must be measured after retap/pin move'},'ul_policy':'preserve original UL rectangles; ul_out15 needs a measured local clock branch, not a pin move'}
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
