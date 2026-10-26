from pathlib import Path
import json,shutil,re,hashlib,sys,collections
kind=sys.argv[1];root=Path('/srv/opentallas-scratch2/claude/codex-qc-sramif-1713');src=Path('/srv/opentallas-scratch2/claude/codex-qc-sramif-1309')/({'btab':'btab_s8','prog':'prog_s8b'}[kind]);d=root/(kind+'_aspect_a1');d.mkdir(parents=True,exist_ok=False)
for x in src.iterdir():
 if x.is_file() and x.suffix in ('.tcl','.mk','.sdc','.py','.sh','.json','.v','.txt') and not x.name.startswith(('run_','postcts_gate_','RESET_','s6_','signoff','bind_','meas_','current_','probe_')):shutil.copy2(x,d/x.name)
for n in ('cf','macros','rtl','so_exact'):
 if (src/n).exists():shutil.copytree(src/n,d/n)
old=json.loads((src/'pins.json').read_text());portmap=collections.defaultdict(list)
for p in old:portmap[p['bus']].append(p['bit'])
W,H=354.24,259.2
# Native M4/M5 track phase .012, .048 pitch; .192 signal pitch limits density to <=6/um.
def tr(x):return round(.012+round((x-.012)/.048)*.048,6)
def pg_bad(x):return any(abs(x-(o+round((x-o)/4.32)*4.32))<.096-1e-6 for o in (2.064,2.256))
def line(bus,bits,face,start):
 out=[];v=tr(start)
 for bit in bits:
  while face=='S' and (pg_bad(v) or (bus!='ck' and abs(v-177.132)<1.0)):v=round(v+.048,6)
  out.append(dict(bus=bus,bit=bit,layer='M5' if face=='S' else 'M4',x=v if face=='S' else W-.042,y=.042 if face=='S' else v,face=face))
  v=round(v+.192,6)
 return out
pins=[]
if kind=='btab':
 pins+=line('tw_data',list(range(512)),'S',64.8)+line('tw_data',list(range(512,1024)),'S',184.32)
 pins+=line('bs_addr',list(range(24)),'E',96.012)+line('bs_re',[None],'E',101.196)+line('bs_q',list(range(256)),'E',104.652)
 for bus,start in (('tw_addr',302.412),('tw_kind',307.596),('tw_we',310.188),('rst_n',327.468),('fault',330.06)):pins+=line(bus,sorted(portmap[bus],key=lambda x:-1 if x is None else x),'S',start)
 macro='ot_sram_1r1w_128x256_m1_r2c2';mx=129.6;mw=94.824
 aports=['bs_addr','tw_addr','tw_kind','tw_data'];outports={'bs_q','fault'}
else:
 pins+=line('tw_d0',list(range(457)),'S',80.012)+line('tw_d1',list(range(457)),'S',184.32)
 pins+=line('p_idx',list(range(9)),'E',81.036)+line('p_re',[None],'E',83.724)+line('p_q',list(range(457)),'E',88.572)
 for bus,start in (('tw_addr',302.412),('tw_kind',307.596),('tw_we',310.188)):pins+=line(bus,sorted(portmap[bus],key=lambda x:-1 if x is None else x),'S',start)
 macro='ot_sram_1r1w_256x256_m2_r2c2';mx=90.72;mw=172.824
 aports=['p_idx','tw_addr','tw_kind','tw_d0','tw_d1'];outports={'p_q'}
pins+=line('ck',[None],'S',177.132)
assert {(x['bus'],x['bit']) for x in pins}=={(x['bus'],x['bit']) for x in old}
assert len(pins)==len(old)
seen=set()
for p in pins:
 k=(p['layer'],p['x'],p['y']);assert k not in seen,k;seen.add(k)
 assert 0<p['x']<W and 0<p['y']<H
(d/'pins.json').write_text(json.dumps(pins,indent=1)+'\n')
def name(p):return p['bus']+(f"[{p['bit']}]" if p['bit'] is not None else '')
io=['# NEW R0 equal-area profile1713: native source ports, explicit new track/PG-safe locations.']
for p in pins:
 size='.024 .084' if p['face']=='S' else '.084 .024'
 io.append(f"place_pin -pin_name {{{name(p)}}} -layer {p['layer']} -location {{{p['x']:.6f} {p['y']:.6f}}} -pin_size {{{size}}}")
(d/'io.tcl').write_text('\n'.join(io)+'\n')
mod='qfd_dv_s8x_'+kind
lef=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {mod}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {W} BY {H} ;',' SYMMETRY X Y ;']
for p in pins:
 n=name(p);x,y=p['x'],p['y'];dx,dy=(.012,.042) if p['face']=='S' else (.042,.012)
 lef += [f' PIN {n}',f'  DIRECTION {"OUTPUT" if p["bus"] in outports else "INPUT"} ;',f'  USE {"CLOCK" if n=="ck" else "SIGNAL"} ;','  PORT',f'   LAYER {p["layer"]} ;',f'   RECT {x-dx:.6f} {y-dy:.6f} {x+dx:.6f} {y+dy:.6f} ;','  END',f' END {n}']
lef += [f'END {mod}','END LIBRARY'];(d/'target_profile.lef').write_text('\n'.join(lef)+'\n')
ys=[30.24,86.4,142.56,198.72];sites=' '.join(f'{{{mx} {y} R0}}' for y in ys)
s=(d/'macro_place.tcl').read_text();s=re.sub(r'(foreach \{master sites\} \{)'+re.escape(macro)+r' \{.*?\}\} \{',lambda m:m[1]+macro+' {'+sites+'}} {',s,count=1,flags=re.S);assert sites in s;(d/'macro_place.tcl').write_text(s)
s=(d/'config.mk').read_text();oldnick=re.search(r'(?m)^export DESIGN_NICKNAME = (\S+)',s)[1];newnick='kq_'+mod+'_aspect1713a1'
s=re.sub(r'(?m)^export DESIGN_NICKNAME = .*',f'export DESIGN_NICKNAME = {newnick}',s)
s=re.sub(r'(?m)^export DIE_AREA = .*',f'export DIE_AREA = 0 0 {W} {H}',s);s=re.sub(r'(?m)^export CORE_AREA = .*',f'export CORE_AREA = 4.32 4.32 {W-4.32} {H-4.32}',s)
s=re.sub(r'(?m)^export OT_MSCTS_CORR = .*\n','',s)
s=re.sub(r'(?m)^export CTS_ARGS = .*','export CTS_ARGS = -sink_clustering_enable -sink_clustering_size 16 -sink_clustering_max_diameter 35 -repair_clock_nets -delay_buffer_derate 0.5',s)
s+='\n# NEW1713 profile: no transferred RCX correction from old geometry.\nexport OT_MSCTS_MACRO_EARLY = 20\n';(d/'config.mk').write_text(s)
# Four short south banks + eight local SRAM-edge regions, with planned taps outside macro halos.
rootxy=(177.132,6);spec=['# NEW R0 profile1713; 12 regional banks, max local cluster16/35um. No old RCX corrections.','set ot_ms_port ck',f'set ot_ms_root {{{rootxy[0]} {rootxy[1]}}}','set ot_ms_taps {']
for k in range(4):
 a=k*W/4;b=(k+1)*W/4;x=(a+b)/2
 spec.append(' {S%d {%.6f 6 %.6f 6 %.6f 16} {{%.6f 0 %.6f 25.92}}}' % (k,rootxy[0],x,x,a,b))
limits=[25.92,79.2,135.36,191.52,H]
for k,y in enumerate(ys):
 for side,x,a,b in (('W',mx-12,0,W/2),('E',mx+mw+12,W/2,W)):
  spec.append(' {%s%d {%.6f 6 %.6f 6 %.6f %.6f} {{%.6f %.6f %.6f %.6f}}}' % (side,k,rootxy[0],x,x,y+20.52,a,limits[k],b,limits[k+1]))
spec+=['}','set ot_ms_macros {']
patterns=[f'g_btb*{k}*.u_m' for k in range(4)] if kind=='btab' else ['g_prog*0*.u_hi','g_prog*0*.u_lo','g_prog*1*.u_hi','g_prog*1*.u_lo']
for k,pattern in enumerate(patterns):spec.append(f' {{{pattern} W{k} {{{mx-7} {ys[k]+1}}}}}')
spec+=['}'];(d/'mscts_spec.tcl').write_text('\n'.join(spec)+'\n')
# Same synth netlist and exact source as the prior profile; fresh floorplan/placement, never routed checkpoints.
sbase=next((src/'run/results/asap7').glob('*/base'));base=d/'run/results/asap7'/newnick/'base';base.mkdir(parents=True)
for p in sbase.iterdir():
 if p.name.startswith('1_'):shutil.copy2(p,base/p.name)
meta=dict(profile='NEW_R0_ASPECT1713_A1',module=mod,outline_um=[W,H],old_outline_um=[259.2,354.24],area_um2=W*H,rtl_cycles_added=0,source_kit=str(src),native_port_count=len(pins),macro_sites=[dict(master=macro,x=mx,y=y,w=mw,h=41.064) for y in ys],clock_taps=12,io_hold_proposal=dict(vector_ports=aports,proposed_sender_min_ps=12.5,qualification='NOT_APPLIED_REAL_PARENT_RECEIPT_REQUIRED'),pins_sha256=hashlib.sha256((d/'pins.json').read_bytes()).hexdigest(),source_rtl_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (d/'rtl').iterdir() if p.is_file()})
(d/'profile1713.json').write_text(json.dumps(meta,indent=1)+'\n')
print(d,len(pins),'pins',len(meta['source_rtl_sha256']),'sourcefiles','sameRTL/from1_synth only')
