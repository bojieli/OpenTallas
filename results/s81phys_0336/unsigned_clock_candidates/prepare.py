import sys,json,re,hashlib,subprocess
from pathlib import Path
W=Path('/srv/opentallas-scratch2/claude/wt/codex-s81phys-0336'); O=W/'results/s81phys_0336/unsigned_clock_candidates';O.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(W/'tools/die_plan'),str(W/'physical/die_plan/s81/cores/legacy')]
import gen_core_kit_legacy as G
import master_slice as MS
base=W/'physical/die_plan/s81'
report={'scope':'PRIVATE CANDIDATE; NOT ADOPTED; NO PHYSICAL LAUNCH','rtl_changes':0,'added_cycles':0,'external_die_ports_changed':0,'neighbors_changed':0,'outline_changed':0,'cores':{}}
for key,new,kit in [('ot_s81sl_eg_c',('M5',127.116,.24),'ot_s81sl_eg_k1'),('dsdv_gunit_l3',('M5',345.564,98.46),'dsdv_gunit_l3_edgeht')]:
 d=json.load(open(base/'inputs/core_pins'/f'{key}.json'));old=next(p.copy() for p in d['pins'] if p['name']=='clk')
 lp=W/d['lef'];src=lp.read_text(); wh=tuple(map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',src).groups()))
 p=next(p for p in d['pins'] if p['name']=='clk');p.update(layer=new[0],x=new[1],y=new[2]);
 rect=[new[1]-.024,new[2]-.24,new[1]+.024,new[2]+.24]
 assert min(rect)>=0 and rect[2]<=wh[0] and rect[3]<=wh[1]
 pattern=r'(  PIN clk\n)(.*?)(  END clk)'
 block=re.search(pattern,src,re.S).group(2);block=re.sub(r'USE\s+SIGNAL\s*;', 'USE CLOCK ;',block);block=re.sub(r'LAYER\s+M\d\s*;', 'LAYER M5 ;',block);block=re.sub(r'RECT\s+[-\d. ]+;', 'RECT '+' '.join(f'{v:.4f}' for v in rect)+' ;',block)
 dst=O/(key+'.lef'); dst.write_text(re.sub(pattern,lambda m:m.group(1)+block+m.group(3),src,count=1,flags=re.S))
 d['source']+=' | PRIVATE unsigned GEOM-21 clock-entry shape candidate; requires coordinator adoption'
 d['pinhash']=hashlib.sha256(json.dumps(d['pins'],sort_keys=True).encode()).hexdigest()[:12];d['lef']=str(dst.relative_to(W));(O/(key+'.pins.json')).write_text(json.dumps(d,indent=2)+'\n')
 original=json.load(open(base/'inputs/core_pins'/f'{key}.json'))
 changed=[(a,b) for a,b in zip(original['pins'],d['pins']) if a!=b];assert len(changed)==1
 sites=G.plan_pin_sites(d['pins'],wh,{'clock_port':'clk'})
 # Native track table: use existing exact L3 kit; EG emitted kit uses same pinned ASAP7 tracks.
 kd=Path('/srv/opentallas-scratch2/claude/codex-s81phys-0336/kits/dsdv_gunit_l3_edgeht')
 track=MS.on_track(kd,new[0],new[1],new[2]);assert track
 report['cores'][key]=dict(module=d['module'],outline_um=wh,native_clock=old,candidate_clock=p,clock_shape_um=[.048,.48],clock_rect_um=rect,native_track_validator='master_slice.on_track(existing pinned ASAP7 kit)',native_track_pass=track,pin_sites=sites,unchanged_other_pins=len(d['pins'])-1,source_lef=str(lp.relative_to(W)),candidate_lef=str(dst.relative_to(W)),g0c_parent_fit='NOT RUN; candidate not adopted',rtl_eq='EG fresh proof running separately; L3 existing source unchanged')
(O/'impact.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
