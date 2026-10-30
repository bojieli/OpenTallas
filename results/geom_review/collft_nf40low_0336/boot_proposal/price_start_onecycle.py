from pathlib import Path
import json,math
b=Path('/srv/opentallas-scratch2/claude/codex-collft-0336');c=json.loads((b/'start_impact_census.json').read_text())
P={'s0':[199.206,165.645],'sf':[199.314,169.965],'s1south':[300.024,180.225],'s1north':[199.206,564.975],'s2north':[300.024,865.215],'pdnorth':[350.028,885.195],'rawnorth':[274.05,849.825],'s1northright':[337.932,579.015]}
md=lambda a,z:round(sum(abs(x-y) for x,y in zip(a,z)),3)
rows=[]
for n,v in c.items():
 stage=n.split('/')[-1].split('$')[0];origin='u_cland_origin/' in n;raw='u_cland_rst_crec_rx_s1_i/' in n
 for q in v['captures']:
  cap=q['name'];dst=q['xy'];src=v['xy'];label=n;role='existing'
  # North FSTART FFs remain at their existing physical faces.
  if origin:
   if stage=='sf':src=P['sf'];dst=P['s0'];role='sf→shareds0'
   elif stage=='s0':src=P['s0'];dst=P['s1south'];role='s0→originals1'
   elif stage=='s1':
    if 'u_cland_origin/s2' in cap:src=P['s1south']
    elif dst[1]>500:src=P['s2north'];role='north FSTART one extra boot cycle: start replaces start_d'
    else:src=P['s1south']
   elif stage in ('s2','pd') and dst[1]>500:src=P['pdnorth' if ('u_cland_fstart_' in cap or stage=='pd') else 's2north'];role='north same-state branch or delayed FSTART'
  if raw:
   if 'u_cland_origin/s0' in cap:dst=P['s0']
   elif 'u_cland_origin/s1' in cap:dst=P['s1south']
   elif dst[1]>500:src=P['rawnorth'];role='north same-state rawreset'
  rows.append(dict(source=label,capture=cap,source_xy=src,capture_xy=dst,distance=md(src,dst),role=role))
# New retained stage graph. The original south state chain remains, same shareds0.
r9=next(v['xy'] for n,v in c.items() if 'u_rrl_9/' in n)
for a,z in [('s0','s1north'),('s1north','s2north'),('s2north','pdnorth'),('rawnorth','s1north'),('rawnorth','s2north'),('rawnorth','pdnorth')]:rows.append(dict(source=a,capture=z,source_xy=P[a],capture_xy=P[z],distance=md(P[a],P[z]),role='new same-cycle retained branch'))
rows.append(dict(source='rst_rl_9',capture='rawnorth',source_xy=r9,capture_xy=P['rawnorth'],distance=md(r9,P['rawnorth']),role='same-stage rawreset replica'))
pin=[199.2,165.6];nF=[q['xy'] for n,v in c.items() if 'u_cland_origin/s1' in n for q in v['captures'] if q['xy'][1]>500];d=max(md(pin,q) for q in nF)
pins={'crec_rx_s1_o':[70.176,990.944],'crec_rx_s2_o':[185.248,990.944],'fltk_o':[474.528,990.944],'fltv_o':[478.432,990.944]}
fixed=[]
for n,v in c.items():
 if 'u_cland_origin/s1' not in n:continue
 for q in v['captures']:
  if q['xy'][1]<500:continue
  bus=q['name'].split('u_cland_fstart_')[1].split('/')[0];distance=md(pin,q['xy']);pos=q['xy']
  fixed.append(dict(output=bus,current_face_ff_xy=q['xy'],pin_xy=pins[bus],distance_from_input=distance,min_extra_cycles_fixed_face_ff_and_s0_at_pin=max(0,math.ceil(distance/405)-2),zero_cycle_model_face_ff_xy=pos,zero_cycle_model_output_pin_reach=md(pos,pins[bus])))
out=dict(north_output_price=fixed,schema='codex.collft.boot_impact.v1',scope='analytic source/stage impact only; NOT physical/STA/LEC approval; FF2 kit unchanged',anchors_cell_centres_um=P,additional_flops=4,additional_boot_cycles={'crec_rx_s1_o':1,'crec_rx_s2_o':1,'fltk_o':1,'fltv_o':1,'internal_north_ring_START':0},replicated_stages=['north s1','north s2','north pd','north raw-reset copy from same rst_rl_9'],input_pin_um=pin,input_s0_reach=md(pin,P['s0']),input_sf_reach=md(pin,P['sf']),new_stage_max=max(q['distance'] for q in rows),gt405=[q for q in rows if q['distance']>405],arcs=rows,strict30um_alternative=dict(worst_north_FSTART_pin_distance=d,available_two_serial_r2r_plus30=840,minimum_input_s0_distance_for_zero_cycles=round(d-810,3),minimum_added_serial_cycles_if_all_input_FFs_within30=math.ceil((d-30)/405)-2))
(b/'start_impact_plan_onecycle.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='arcs'},indent=2))
