"""Results-local NLDM/RC START relay feasibility. No source/RTL/plan mutation."""
import json,sys,math
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
from die_clock_128 import _bilin
from clk_aocv import branch_pessimism
from count_align_plan import sync_choice_iv
L=json.load(open(R/'start_lib.json'))['corners'];C=json.load(open(R/'cal_g03b_refit.json'));A=json.load(open(R/'tool_snapshot/tools/die_plan/clk_aocv_table_g021.json'))['clock_aocv']
def data(c,length,inslew,pol):
 lib=L[c]['cells'];slew=inslew;total=0.;mx=0.;components=[]
 n=max(1,math.ceil(length/100));q='fall' if pol=='rise' else 'rise';path=[('DFFHQNx1_ASAP7_75t_R',0.,'INVx8_ASAP7_75t_R',pol)]+[(('INVx8_ASAP7_75t_R' if i==0 else 'BUFx8_ASAP7_75t_R'),length/n,('DFFHQNx1_ASAP7_75t_R' if i==n-1 else 'BUFx8_ASAP7_75t_R'),q) for i in range(n)]
 for cell,wire,nxt,p in path:
  cw=wire*.187*1.7;rw=wire*.0125096;load=lib[nxt]['cap_ff'];el=rw*(cw/2+load)
  d=_bilin(lib[cell]['cell_'+p],slew,cw+load);s=_bilin(lib[cell][p+'_transition'],slew,cw+load)
  total+=d+el;slew=math.hypot(s,2.2*el);mx=max(mx,slew);components.append(d+el)
 return total,mx,components
rows=[]
for length in [0,50,100,150,200,250,297.54,300]:
 corners={}
 for c in ['TT','FF']:
  vals=[data(c,length+20.,s,p) for s in [20,80] for p in ['rise','fall']]
  d0,k1,k2,kf=C['leg' if c=='TT' else 'leg_FF'];clock=2*d0+k1*length+k2*(length*length/2)
  b=dict(cell_ps=2*d0,net_ps=clock-2*d0,stages={'Ainv':2});a=dict(cell_ps=0,net_ps=0,stages={})
  dn=branch_pessimism(A,c,a,b,length,False,'setup');up=branch_pessimism(A,c,a,b,length,False,'hold')
  # Conservative data cell/net envelope: cell +/-5%, wire +/-3%, plus 5.11% late droop.
  low=min(x[0] for x in vals)*.95;high=max(x[0] for x in vals)*1.1011
  corners[c]=dict(clock_ps=clock,clock_ocv_dn_ps=dn,clock_ocv_up_ps=up,data_lo_ps=low,data_hi_ps=high,max_data_slew_ps=max(x[1] for x in vals),phase_lo_ps=clock-dn-high,phase_hi_ps=clock+up-low)
 # Additional relay-isolation clock branch, including real modeled falling-edge INV2.
  lib=L[c]['cells'];cap=5*lib['DFFHQNx1_ASAP7_75t_R']['clock_cap_ff']+lib['INVx2_ASAP7_75t_R']['cap_ff'];buf=[_bilin(lib['BUFx8_ASAP7_75t_R']['cell_'+p],s,cap) for s in [20,80] for p in ['rise','fall']];fall=[_bilin(lib['INVx2_ASAP7_75t_R']['cell_'+p],s,2*lib['DFFHQNx1_ASAP7_75t_R']['clock_cap_ff']) for s in [20,80] for p in ['rise','fall']];ep_lo=.95*(min(buf)+min(fall))-1.1011*max(buf);ep_hi=1.1011*(max(buf)+max(fall))-.95*min(buf)
  corners[c]['phase_lo_ps']+=ep_lo;corners[c]['phase_hi_ps']+=ep_hi+clock*.0552;corners[c]['endpoint_fall_clock_delta_ps']=[ep_lo,ep_hi]
 lo=min(z['phase_lo_ps'] for z in corners.values());hi=max(z['phase_hi_ps'] for z in corners.values());choice=sync_choice_iv(dict(lo=lo,hi=hi,fall_lo=lo,fall_hi=hi,d_ps=(lo+hi)/2),833.,104.125)
 rows.append(dict(pair_wire_um=length,corners=corners,union_phase_ps=[lo,hi],canonical_model_edge=choice[1],sample_values=choice[0],boundary_distance_ps=choice[3],aperture_margin_ps=choice[3]-104.125))
json.dump(dict(scope='ANALYTIC MODEL ONLY. Two co-routed INV clock segments vs DFFQN->INV8-><=100umBUF8->DFF D; M6/7 max stock RC +1.7 coupling; actual TT/FF NLDM 20..80ps launch slew; full clock AOCV and conservative data derates. Fall branch explicitly modeled BUF8 driving5posedgeFF+INV2 driving2negedgeFF, with conservativeendpointclockderates andspiceupper;20umextra datalength reservedforrelaybays. Canonicalfallmodel only; physical receipt required.',rows=rows,build_allowed=False),open(R/'start_hop_model.json','w'),indent=1)
for x in rows:print(x['pair_wire_um'],x['union_phase_ps'],x['canonical_model_edge'],x['aperture_margin_ps'],max(c['max_data_slew_ps'] for c in x['corners'].values()))
