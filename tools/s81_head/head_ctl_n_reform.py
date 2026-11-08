#!/usr/bin/env python3
"""Private CTL_n conservative source/model/placement preview; never edits POR or freeze."""
from pathlib import Path
import argparse,json,re,math,sys,collections,bisect
p=argparse.ArgumentParser();p.add_argument('--kit',type=Path,required=True);p.add_argument('--layout',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--render-module-dir',type=Path,required=True);a=p.parse_args()
r=a.out;r.mkdir(parents=True,exist_ok=False);(r/'rtl').mkdir()
src=(a.kit/'rtl/ot_s81hd_ctl_nstrip.sv').read_text()
for slot,w,n in [('w3u',514,5),('w3d',512,5),('unit_ft',45,1)]:
 pat=r'ot_dp_st #\(\.W\('+str(w)+r'\)\) u_ft_'+slot+'_s'+str(n-1)+r' .*?;'
 m=re.search(pat,src);assert m,(slot,'last station missing');old=m[0]
 rst=re.search(r'\.rst_n\(([^)]+)\)',old)[1]
 tail=f'{slot}_s{n-1}_q';te=f'{slot}_s{n-1}_eq'
 repl=old.replace(f'.q({slot}_o[{w-1}:0])',f'.q({tail})').replace(f'.eq({slot}_o[{w}])',f'.eq({te})')
 assert repl!=old
 decl=f'wire [{w-1}:0] {tail}; wire {te};\n    '
 ext=f'\n    ot_dp_st #(.W({w})) u_ft_{slot}_s{n} (.clk(clk), .rst_n({rst}), .d({tail}), .ea({te}), .q({slot}_o[{w-1}:0]), .eq({slot}_o[{w}]));'
 src=src[:m.start()]+decl+repl+ext+src[m.end():]
 src=re.sub(r'(ft slot '+slot+r' \([^,\n]+, )'+str(n)+r'( station\(s\)\))',lambda z:z[1]+str(n+1)+z[2],src)
for slot,w in [('w3u',517),('w3d',515)]:
 old=f'ot_dp_clk_landing_cas #(.W({w}), .DEPTH(4)) u_cland_{slot}_i'
 new=f'ot_dp_clk_landing_cas #(.W({w}), .DEPTH(4), .WREG(1), .FREG(1), .WRITE_CHUNK(8), .WRITE_TAIL(1), .READ_CHUNK(32)) u_cland_{slot}_i'
 assert src.count(old)==1;src=src.replace(old,new)
src='// PRIVATE CTL_n vC preview: +1 ring input data/K+2 and +1 FT outputs; NOT POR.\n'+src
(r/'rtl/ot_s81hd_ctl_nstrip.sv').write_text(src)
ft=(a.kit/'ft_stations.txt').read_text()
for slot,n in [('w3u',6),('w3d',6),('unit_ft',2)]:
 ft=re.sub(r'^'+slot+r' \d+ ',slot+' '+str(n)+' ',ft,flags=re.M)
(r/'ft_stations.txt').write_text(ft)
md=[]
for slot in ['w3u','w3d']:
 for key,value in [('write',8),('read',32),('tail',1)]:md.append(f'dict set ::cland_local_chunks u_cland_{slot}_i {key} {value}')
(r/'cland_local_chunks.tcl').write_text('# Insert after generated prefix data and before standard group placement.\n'+'\n'.join(md)+'\n')
d=json.loads(a.layout.read_text());W,H=d['die'][2:];pins={n.replace('\\',''):((x0+x1)/2,(y0+y1)/2,l) for n,l,x0,y0,x1,y1 in d['pins']}
rows=d['rows'];x0=min(x[1] for x in rows);x1=max(x[3] for x in rows);ys=sorted(set(x[2] for x in rows));rh=.27;sw=.054;fw=1.728
native={n.replace('\\',''):((u+x)/2,(v+y)/2) for n,m,st,u,v,x,y in d['std_cells']}
occupied=collections.defaultdict(list)
def site(xx,yy):
 base=bisect.bisect_left(ys,yy-rh/2);base=min(max(base,0),len(ys)-1)
 for rad in range(100):
  for rr in range(max(0,base-rad),min(len(ys),base+rad+1)):
   if abs(rr-base)!=rad and rad:continue
   for dc in [0,1,-1,2,-2,3,-3,4,-4]:
    x=max(x0,min(x1-fw,x0+round((xx-fw/2-x0)/sw)*sw+dc*fw))
    y=ys[rr]
    if all(x+fw<=l or h<=x for l,h in occupied[rr]):
     occupied[rr].append((x,x+fw));return [round(x,6),round(y,6)]
 raise RuntimeError('no local site')
all_sites={};summary={}
for slot,nb,n,face in [('w3u',515,6,'N'),('w3d',513,6,'W'),('unit_ft',46,2,'S')]:
 st=[[] for j in range(n)];hopmax=0;pinmax=0
 for b in range(nb):
  ip=pins[f'{slot}_i[{b}]'];op=pins[f'{slot}_o[{b}]']
  offx=(b%8)*1.8;offy=-(b%8)*rh
  if slot=='unit_ft':
   nm=f'u_ft_{slot}_s0/'+(f'q[{b}]$_DFF_P_' if b<nb-1 else 'eq$_DFF_PN0_')
   aa=native.get(nm,(ip[0],4.455))
   targets=[aa,(4.32+offx,op[1]+offy)]
  else:
   aa=(ip[0],ip[1]-20) if face=='N' else (ip[0]+20,ip[1])
   zz=(4.32,op[1]) if face=='N' else (op[0],H-4.32)
   targets=[(aa[0]+(zz[0]-aa[0])*(j+1)/n+offx,aa[1]+(zz[1]-aa[1])*(j+1)/n+offy) for j in range(n)]
  pp=aa
  for j,(xx,yy) in enumerate(targets):
   s=site(xx,yy);c=(s[0]+fw/2,s[1]+rh/2);st[j].append(s);all_sites[f'{slot},{j+1},{b}']=s
   hopmax=max(hopmax,abs(c[0]-pp[0])+abs(c[1]-pp[1]));pp=c
  pinmax=max(pinmax,abs(pp[0]-op[0])+abs(pp[1]-op[1]))
 summary[slot]=dict(stations=n,word_bits=nb,registered_hop_max_um_estimate=round(hopmax,3),output_pin_reach_um_estimate=round(pinmax,3),stage_bounds=[[min(x[0] for x in s),min(x[1] for x in s),max(x[0]+fw for x in s),max(x[1]+rh for x in s)] for s in st])
(r/'ft_sites_all.json').write_text(json.dumps(all_sites,separators=(',',':'))+'\n')
# Native face_flops site keys are plan stages1..k-1; its last station is the output face register.
t=['set ff_bit_sites {}','set ff_bit_site_cells {}']
for slot,sm in summary.items():
 t.append(f'dict set ff_bit_site_cells {slot} {{{fw} {rh}}}')
 for j in range(1,sm['stations']):
  for b in range(sm['word_bits']):
   # Landed slot stage j maps to model j-1; an unlanded slot skips its input FF.
   si=j+1 if slot=='unit_ft' else j
   t.append(f'dict set ff_bit_sites {slot},{j},{b} {{{" ".join(map(str,all_sites[f"{slot},{si},{b}"]))}}}')
(r/'ft_bit_sites.tcl').write_text('\n'.join(t)+'\n')
m=dict(status='PRIVATE_MODEL_ONLY_NO_KIT_NO_PHYSICAL',baseline_kit=str(a.kit),outline_um=[W,H],source_mode=dict(WREG=1,FREG=1,WRITE_CHUNK=8,WRITE_TAIL=1,READ_CHUNK=32,placement_local_chunks=dict(write=8,read=32,tail=1)),input_PIN_cycles=dict(w3u_i=1,w3d_i=1),receiver_K_delta=dict(w3u_i=2,w3d_i=2),output_PIN_cycles=dict(w3u_o=1,w3d_o=1,unit_ft_o=1),end_to_end_cycle_delta=dict(w3u=2,w3d=2,unit_ft=1),ps_per_cycle=833,throughput_words_per_cycle=1,MACs_per_cycle=0,transport_bits_per_cycle=dict(w3u=515,w3d=513,unit_ft=46),clock_sink_delta=dict(core_FT=1074,core_read_select=128,forwarded_FREG=1034,forwarded_WREG=522,total=2758),baseline_std_area_um2=d['stats']['std_area'],estimated_added_FF_area_um2=2758*1.188*.27,max_repeater_pitch_um=100,stations=summary,slot_reason='Fixed HEAD partition slot and abutted pin coordinates; no outline growth',pin_proposal='Preserve coherent currentUO GPIO coordinates and layers. Native conservative requested M6 body retains M7 pin-access exception in cons_kit.json. M3 repin alternative superseded/unbuilt.',remaining_gates=['authoritative coherent UO prepared source/sidecar via native generator','native unchanged-pin audit and cons_kit access-layer/route-layer reports; no manual signatures','full newkit frontend+LEC','one PLACE then actual reach/clock/density/congestion image review','compiler/token K and cycle event still private/unadopted'])
m['central_crossing_budget']=dict(width_um=100,demand_bits=1028,M3_pitch_um=.036,M4_pitch_um=.048,M5_pitch_um=.048,M6_pitch_um=.064,vertical_tracks=100/.036+100/.048,horizontal_tracks=100/.048+100/.064,horizontal_raw_use_fraction=1028/(100/.048+100/.064),reserve_fraction=.5,note='Fixed alternating boundary bundle order requires a crossing; staged banks separate it, M3/M5 vertical and M4/M6 horizontal provide capacity. Actual GRT overflow still required.')
m['physical_mode']=dict(OT_CONS_KIT=1,OT_CONS_UTIL=.35,OT_CONS_MAX_LAYER='M6',pin_access_layer='M7',pin_access_adjustment=.9,note='M6 is the requested body ceiling, not a claim that every signal shape is below M7. Native audit/report required.')
m['clock']=dict(existing_root_taps=len([n for n in pins if n=='clk' or n.startswith('clk_t')]),reference_TT_ps=450,reference_FF_ps=342,added_core_sinks=1202,added_forwarded_sinks=1556,note='Retain coherent HEAD clock ports. Actual placed sink census/CTS insertion/internal hold must be reviewed before GRT.')
(r/'model.json').write_text(json.dumps(m,indent=2)+'\n')
# Draw the estimate only: all model FF sites and sampled flight lines, never a fabricated placed image.
sys.path.insert(0,str(a.render_module_dir));import layout_png as L
c=L.Canvas(1400,850);sx=1300/W;sy=710/H
def xy(p):return (round(45+p[0]*sx),round(60+(H-p[1])*sy))
c.box(45,60,1345,770,(0,0,0),2)
colors={'w3u':(25,90,200),'w3d':(225,115,20),'unit_ft':(120,30,140)}
for slot,sm in summary.items():
 col=colors[slot];nb=sm['word_bits'];n=sm['stations']
 for b in range(0,nb,64):
  pp=xy(pins[f'{slot}_i[{b}]'])
  for j in range(n):
   s=all_sites[f'{slot},{j+1},{b}'];qq=xy((s[0]+fw/2,s[1]+rh/2));c.line(*pp,*qq,col,1);pp=qq
  c.line(*pp,*xy(pins[f'{slot}_o[{b}]']),col,1)
 for j,bb in enumerate(sm['stage_bounds']):
  for b in range(nb):
   s=all_sites[f'{slot},{j+1},{b}'];xx,yy=xy((s[0],s[1]));c.fill(xx-1,yy-1,xx+1,yy+1,col)
  xx,yy=xy(((bb[0]+bb[2])/2,bb[3]+10));c.text(xx,yy,f'{slot.upper()} S{j}',col)
for name,pin in pins.items():
 if name=='clk' or name.startswith('clk_t'):
  xx,yy=xy(pin);c.fill(xx-4,yy-4,xx+4,yy+4,(15,135,45));c.text(xx+6,yy,name.upper(),(15,135,45))
c.text(12,10,'CTL_N VC PROPOSAL - MODEL ONLY; NO PLACE',scale=2)
c.text(12,32,'BLUE W3U / ORANGE W3D / PURPLE UNIT; SAME OUTLINE, REGISTERED STATIONS, 100UM REPEATER PITCH')
c.text(12,790,'PIN CYCLES: INPUT W3U/W3D +1 WITH K+2; OUTPUT W3U/W3D/UNIT +1. TOTAL W3U/W3D +2, UNIT +1.')
c.text(12,808,'GPIO UNCHANGED; REQUEST M6 BODY + NATIVE M7 PIN-ACCESS EXCEPTION. NATIVE AUDIT/REPORT STILL REQUIRED.')
c.save(r/'planned.png')
print(json.dumps({k:v['registered_hop_max_um_estimate'] for k,v in summary.items()}))
print(r)
