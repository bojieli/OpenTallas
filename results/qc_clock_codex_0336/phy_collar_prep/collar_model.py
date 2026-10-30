import sys,json,math,gzip,re
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan')
import die_clock_128 as D
L=Path('/home/ubuntu/.cache/opentallas/asap7_nldm')
NAMES=['BUFx8_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx24_ASAP7_75t_R']
libs={}
for c in ['TT','FF']:
 txt=gzip.open(L/f'asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib.gz','rt').read(); libs[c]={}
 for n in NAMES:
  i=txt.index('cell ('+n+')');j=txt.find('cell (',i+10);b=txt[i:j if j>0 else len(txt)]
  libs[c][n]={'cap':float(re.search(r'rise_capacitance : ([\d.]+)',b).group(1)), 'area':float(re.search(r'area\s*:\s*([\d.]+)',b).group(1)),'rise':(D._table(b,'cell_rise'),D._table(b,'rise_transition')),'fall':(D._table(b,'cell_fall'),D._table(b,'fall_transition'))}
r=.014812; cap=.154233*1.7

def stage(c,n,s,length,load):
 b=libs[c][n];el=r*length*(cap*length/2+load)
 vals=[(D._bilin(t[0],s,cap*length+load)+el,math.hypot(D._bilin(t[1],s,cap*length+load),2.2*el)) for t in [b['rise'],b['fall']]]
 return {'delay_ps':max(v[0] for v in vals),'slew_ps':max(v[1] for v in vals),'load_ff':cap*length+load,'lib_domain_load_ff':b['rise'][0][1][-1]}
# Repeatable electrical segment at max input bound, both transitions, both corners. Geometry must later place every cell outside native body.
segs={}
for n in NAMES:
 segs[n]={}
 for length in [25,50,75,100,120]:
  segs[n][length]={c:stage(c,n,80,length,libs[c][n]['cap']) for c in libs}
# Clock bank explicit upper-bound geometry: 32 FF leaf group, 8 leaves per intermediate, root<=5 intermediates.
# Leaf wire 40um, intermediate spoke100um, root spoke100um. Shared branches charged once pessimistically as full wirelength per sink.
ff=json.load(open('/tmp/qcclock0336/collar_cell_pins.json')); logic=json.load(open('/tmp/qcclock0336/collar_logic_lib.json'))
clock={}
for pad in [0,255]:
 sinks=1208+pad; leaves=math.ceil(sinks/32); mids=math.ceil(leaves/8); clock[pad]={}
 for c in libs:
  ff_cap=max(float(ff[c]['DFFHQNx1_ASAP7_75t_R']['pins']['CLK']['capacitance']),float(ff[c]['DFFASRHQNx1_ASAP7_75t_R']['pins']['CLK']['capacitance']))
  # Lump actual total branches, not one wire for entire fanout. Evaluate proposed tree and expose failures.
  root=stage(c,NAMES[2],80,mids*100,mids*libs[c][NAMES[1]]['cap'])
  mid=stage(c,NAMES[1],root['slew_ps'],8*100,8*libs[c][NAMES[0]]['cap'])
  leaf=stage(c,NAMES[0],mid['slew_ps'],40,32*ff_cap)
  clock[pad][c]={'sinks':sinks,'leaf_BUF8':leaves,'mid_BUF16':mids,'root_BUF24':1,'root':root,'mid':mid,'leaf':leaf,'verdict':'PASS' if max(x['slew_ps'] for x in [root,mid,leaf])<=80 else 'FAIL_PROPOSED_TREE'}
area={}
for pad in [0,255]:
 count={'DFFHQN':1203+pad,'DFFASRHQN':5,'INVx1':1205,'NAND2x1':4+pad,'TIEHI':5}
 raw=(1203+pad)*.2916+5*.37908+1205*.04374+(4+pad)*.08748+5*.04374
 area[pad]={'master_counts':count,'raw_um2':raw,'reserved_at_40pct_um2':raw/.4,'excludes':'clock/reset trees, datarepeaters, PG, halos, routing; PAD255 is reserve bound only'}
h=3.888; band=(57.528+2*(30-2.256))*h-h*h
out={'scope':'PREP only. No RTL adoption, no native arrival or routed extraction. Proposed tree failure is preserved.','wire_model':{'r_kohm_um':r,'c_ff_um':.154233,'coupling_guard':1.7,'effective_c_ff_um':cap},'data_segment_trials_input80ps':segs,'clock_proposed_tree':clock,'per_full_serdes_bank_area':area,'current_gap_R2_30um_reachable_reserved_area_um2':band,'current_geometry_verdict':'FAIL: fullbank reserved area exceeds R2 accessible area before clocks/reset','required_followup':'Construct geometry-based branching, sized and placed leaf/repeater cells. Lumped multi-spoke trial deliberately detects unsafe single-driver proposals. Do not use it as qualified clock model.'}
Path('/tmp/qcclock0336/collar_electrical_prep.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'area':area,'clock':clock,'data_BUF24':segs[NAMES[2]]},indent=2))
def branch(c,n,s,length,fanout,capload):
 b=libs[c][n]; cw=cap*length; total=fanout*(cw+capload);el=r*length*(cw/2+capload)
 vals=[(D._bilin(t[0],s,total)+el,math.hypot(D._bilin(t[1],s,total),2.2*el)) for t in [b['rise'],b['fall']]]
 return {'delay_ps':max(v[0] for v in vals),'slew_ps':max(v[1] for v in vals),'total_driver_load_ff':total,'max_spoke_um':length,'spokes':fanout}
qualified={}
for pad in [0,255]:
 n=1208+pad; leaf=math.ceil(n/32); mid=math.ceil(leaf/4); top=math.ceil(mid/4)
 qualified[pad]={'counts':{'BUF8_leaf':leaf,'BUF24_mid':mid,'BUF24_top':top,'BUF24_root':1},'corners':{}}
 for c in libs:
  ff_cap=max(float(ff[c][f]['pins']['CLK']['capacitance']) for f in ['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R'])
  a=branch(c,NAMES[2],80,50,top,libs[c][NAMES[2]]['cap'])
  b=branch(c,NAMES[2],a['slew_ps'],25,4,libs[c][NAMES[2]]['cap'])
  d=branch(c,NAMES[2],b['slew_ps'],15,4,libs[c][NAMES[0]]['cap'])
  e=stage(c,NAMES[0],d['slew_ps'],40,32*ff_cap)
  qualified[pad]['corners'][c]={'root':a,'top':b,'mid':d,'leaf':e,'sum_delay_ps':sum(v['delay_ps'] for v in [a,b,d,e]),'max_slew_ps':max(v['slew_ps'] for v in [a,b,d,e]),'verdict':'PASS_MODEL_ONLY' if max(v['slew_ps'] for v in [a,b,d,e])<=80 else 'FAIL'}
 qualified[pad]['raw_area_um2']=leaf*.17496+(mid+top+1)*.4374
out['clock_correct_spoke_elmore_tree']=qualified
out['clock_proposed_tree']['note']='Historical pessimistic series-chain diagnostic: totalbranchwire used as one serieswire, not a topology prediction. Correct spoke Elmore follows separately.'
Path('/tmp/qcclock0336/collar_electrical_prep.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(qualified,indent=2))
spatial={}
for c in libs:
 a=branch(c,NAMES[2],80,100,3,libs[c][NAMES[2]]['cap']);a2=stage(c,NAMES[2],a['slew_ps'],27.1,libs[c][NAMES[2]]['cap']);b=branch(c,NAMES[2],a2['slew_ps'],25,4,libs[c][NAMES[2]]['cap']);d=branch(c,NAMES[2],b['slew_ps'],15,4,libs[c][NAMES[0]]['cap']);fc=max(float(ff[c][f]['pins']['CLK']['capacitance']) for f in ['DFFHQNx1_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R']);e=stage(c,NAMES[0],d['slew_ps'],40,32*fc)
 spatial[c]={'root':a,'spoke_repeater':a2,'top':b,'mid':d,'leaf':e,'sum_delay_ps':sum(z['delay_ps'] for z in [a,a2,b,d,e]),'max_slew_ps':max(z['slew_ps'] for z in [a,a2,b,d,e])}
out['outerfield_254um_clock_spatial_envelope']={'scope':'Planning envelope only, each of3 rootspokes has aBUF24 at100um then<=27.1um continuation. Must place full nonoverlapping graph before qualified. Alloldclocknodes excluded.','extra_BUF24':3,'raw_extra_area_um2':3*.4374,'corners':spatial}
Path('/tmp/qcclock0336/collar_electrical_prep.json').write_text(json.dumps(out,indent=2)+'\n'); print(json.dumps(spatial,indent=2))
reset={}
for c in libs:
 load=5*float(ff[c]['DFFASRHQNx1_ASAP7_75t_R']['pins']['SETN']['capacitance'])+4*float(logic[c]['NAND2x1_ASAP7_75t_R']['pins']['A']['capacitance'])
 reset[c]={'local_load_ff':load,'local_buffer_BUF8':1,'max_local_wire_um':40,'electrical':stage(c,NAMES[0],80,40,load),'data_flops_reset':False,'ties':'5 local TIEHI for ASR RESETN; async clear via SETN and positive-data INV mapping','scope':'PAD0 local bank only; PAD reset NANDfanout requires sizing usingactualPAD count. Rawreset propagation and nativePHYrst_n arrival/sourcecap remainunbound.'}
out['local_reset_PAD0']=reset
Path('/tmp/qcclock0336/collar_electrical_prep.json').write_text(json.dumps(out,indent=2)+'\n')
