#!/usr/bin/env python3
"""Prepare the exact Q2NF native child family for the existing HBM kit factory.

No plan adoption or route. Raw children add zero face edges; the actual retained
A parent shell owns the original external captures. All native clock bits stay
separate. Generated source is a reversible identifier alpha transform only.
"""
import argparse,gzip,hashlib,importlib.util,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE='rtl/hbm_accel/cores_split/reform_1106/ot_q2nf_linkstores.sv'
PARENT='ot_q2nf_linkstore_parent'
R2='ot_q2nf_native_parent_r2'
MEM={'ot_sram_1r1w_64x512_m1_r2c2':[171.288,77.784],'ot_sram_1r1w_256x256_m2_r2c2':[172.824,41.064],'ot_sram_1rw_256x64_m4_r2c2':[66.312,17.832]}
BOXES={'ot_q2nf_linkstore0':([34.56,172.8],[233.28,414.72]),'ot_q2nf_control':([289.44,8.64],[207.36,606.96]),'ot_q2nf_linkstore1':([518.4,172.8],[233.28,414.72])}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def ports(text):
 out={}
 for mod,body in re.findall(r'(?ms)^module\s+(\w+)\s*\(.*?\);(.*?)^endmodule',text):
  rows=[]
  for d,hi,lo,n in re.findall(r'(?m)^\s*(input|output)\s+(?:(?:wire|reg|signed)\s+)*(?:\[(\d+):(\d+)\]\s+)?(\\\S+|[A-Za-z_$][A-Za-z0-9_$]*)\s*;',body):rows.append((n.lstrip('\\'),d,abs(int(hi)-int(lo))+1 if hi else 1))
  out[mod]=rows
 return out

def prepare(repo,out):
 repo=repo.resolve();out.mkdir(parents=True,exist_ok=True)
 src=repo/SOURCE;text=src.read_text();inv=ports(text);assert set(BOXES)<=set(inv)
 sys.path.insert(0,str(repo/'tools/hbm_b2'));from hc_alpha_names import normalize_names,placement_name,TOKEN
 text,alpha=normalize_names(text,PARENT)
 aliases={n:'q2n_p_'+hashlib.sha256(n.encode()).hexdigest()[:16] for m in BOXES for n,d,w in inv[m] if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',n)}
 assert len(set(aliases.values()))==len(aliases)
 mapped={ '\\'+n:v for n,v in aliases.items() }
 processed=TOKEN.sub(lambda m:mapped.get(m[0],m[0]),text)
 inverse={v:k for k,v in mapped.items()};assert TOKEN.sub(lambda m:inverse.get(m[0],m[0]),processed)==text
 native=out/'q2nf_native_source.sv';native.write_text(processed)
 native_inv=ports(processed)
 original=repo/'physical/die_plan/hbm/over_cap_split/reform_1106/q2nf_linkstores';layout=json.loads((original/'q2nf_parent_candidate.json').read_text());raw_clocks=json.loads((original/'boundary_clocks.json').read_text())
 macro_rows=[]
 for r in layout['macros']:
  owner={'link0':'ot_q2nf_linkstore0','link1':'ot_q2nf_linkstore1','rest_control':'ot_q2nf_control'}[r['owner']];origin,size=BOXES[owner];x,y,X,Y=r['rect_um'];inst=r['name'].removeprefix('u_fcore.');orient='MY' if owner.endswith('store0') else 'R0'
  macro_rows.append(dict(owner=owner,inst=placement_name(inst,alpha),macro=r['module'],xy_um=[round(x-origin[0],6),round(y-origin[1],6)],orient=orient,original_global_xy_um=[x,y]))
 mask=json.loads((original/'split3.json.ports.json').read_text());rename={'ot_q2nf_rest_g_linkstore0':'ot_q2nf_linkstore0','ot_q2nf_rest_g_linkstore1':'ot_q2nf_linkstore1','ot_q2nf_rest_rest_control':'ot_q2nf_control'}
 clock_maps={m:{} for m in BOXES}
 for old,table in mask.items():
  m=rename[old]
  for p,q in table.items():
   if p.startswith('clk'):
    keep=q['kept_original_indices_lsb_first'];clock_maps[m].update({p if len(keep)==1 and q['original_width']==1 else f'{p}[{j}]':p if q['original_width']==1 else f'{p}[{i}]' for j,i in enumerate(keep)})
 views=[];recipes={};profiles={};pin_tables={};geometry={}
 for m,(origin,size) in BOXES.items():
  W,H=size;rows=[];occupied=set();alloc={};controller=m=='ot_q2nf_control'
  def add(n,layer,x,y,face):
   assert 0<=x<=W and 0<=y<=H,(m,n,x,y)
   key=(layer,round(x,6),round(y,6));assert key not in occupied,(m,n,key);occupied.add(key);rows.append(dict(name=n,layer=layer,x=round(x,6),y=round(y,6),face=face))
  def field(n,d,w,face,center):
   start=round((center-(w-1)*.048/2-.024)/.048)*.048+.024
   for j in range(w):
    y=start+j*.048;assert 4.32<y<H-4.32,(m,n,w,y,H);add(n if w==1 else f'{n}[{j}]','M4',0 if face=='W' else W,y,face)
   alloc[n]=dict(face=face,first_y_um=start,bits=w,pitch_um=.048)
  clocks=[p for p in native_inv[m] if p[0].startswith('clk')];clockpins=[]
  for n,d,w in clocks:
   for j in range(w):
    name=n if w==1 else f'{n}[{j}]';clockpins.append(name)
    if not controller:
     x=221.4 if m.endswith('store0') else 10.392;y=19.98 if j==0 else [38.472,116.328,204.984,282.84][j-1]
    else:
     k=len(clockpins)-1;x=8.664+(k%3)*.864;y=30.024+(k//3)*50.016
    add(name,'M5',x,y,'I')
  cursor={'W':18.024,'E':18.024}
  for old,d,w in inv[m]:
   if old.startswith('clk'):continue
   n=aliases.get(old,old)
   if old=='rst_n':field(n,d,w,'E' if m.endswith('store0') else 'W',5.016);continue
   if not controller:
    face='E' if m.endswith('store0') else 'W'
    if old=='u_body_q2f_lk_d':center=207.0
    elif old=='rx_pin_flit':center=247.0 if m.endswith('store0') else 347.0
    elif 'codec_rx_flit' in old:center=300.0 if m.endswith('store0') else 395.0
    else:
     # Most scalar outputs are the original codec p_tx_flit bits. Keep all
     # endpoint names distinct; packing follows stable port order.
     center=45.0+cursor[face];cursor[face]+=(w+.5)*.048
    field(n,d,w,face,center)
   else:
    # Both final TX captures already belong to this controller. Their raw
    # producer seams deliberately enter W: parent M6 bridges the right link.
    face='W' if ('g_link' in old or old.startswith('tx_pin_flit')) else 'E'
    center=cursor[face]+(w-1)*.048/2;field(n,d,w,face,center);cursor[face]+=(w+5)*.048
  pf=out/(m+'_pins.json');write(pf,rows);pin_tables[m]=rows
  vid=m+'@'+sha(pf)[:12];views.append(dict(view=vid,module=m,outline_um=size,pins_file=pf.name,pins_sha256=sha(pf),pins=len(rows),recipe_keys=[m],family='Q2NF_NATIVE_PREP',instances=['ot_q2nf_native_parent_r2.u_fcore.'+{'ot_q2nf_control':'ot_q2nf_rest_rest_control','ot_q2nf_linkstore0':'ot_q2nf_rest_g_linkstore0','ot_q2nf_linkstore1':'ot_q2nf_rest_g_linkstore1'}[m]],blockers=['UNROUTED native preparation; actual fixed-child views and parent STA pending']))
  source_file='q2nf_native/q2nf_native_source.sv';commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
  recipes[m]=dict(top=m,files=[source_file],params={},defines=[],macros=sorted({q['macro']for q in macro_rows if q['owner']==m}),macro_placement=[{k:v for k,v in q.items()if k in ('inst','macro','xy_um','orient')}for q in macro_rows if q['owner']==m],source_commit=commit,read_at_commit=False,source='Exact Q2NF source partition; reversible port/instance alpha only; zero child face stages')
  profiles[m]=dict(source_commit=commit,family='Q2NF_NATIVE_PREP',release_eligible=False,qualification='NATIVE_SOURCE_AND_GEN_PREPARATION_ONLY',added_face_cycles=0,endpoint_contract=dict(kind='INTERNAL_CORE',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION',parent_partition='q2nf_native_parent_prep'),clock_ports=[n for n,d,w in clocks],reset_ports=['rst_n'],pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',diagnostic_inputs=True,port_inventory=dict(top=m,source_file=source_file,source_sha256=sha(native),ports=native_inv[m]),indexed_clock_parent_bindings=clock_maps[m],actual_parent_shell='ot_q2nf_native_parent_r2: retained A external clk_control captures, +1in/+1out',physical_reset_phase='PREP_ONLY: original raw reset retained; no inherited native4 or new die receipt',source_manifest={SOURCE:sha(src)},alpha_instance_report=alpha,port_aliases={n:v for n,v in aliases.items()if n in {x[0]for x in inv[m]}})
  dc=dict(schema='opentallas.hbm_multi_density.v1',module=m,clock_ports=clockpins,layout='density',common_alignment=True,merge_roots=False,review=dict(verdict='DRAFT',basis='Actual indexed roots and SRAM-owning fields; per-root native density clusters, no pin merge. Physical timing remains unqualified.'))
  write(out/(m+'_density.json'),dc)
  geometry[m]=dict(origin_um=origin,outline_um=size,pin_fields=alloc,macro_placement=recipes[m]['macro_placement'],signal_max='M5',clock_max='M5',obs_intent='M5',pg_top='M5',native_roots=clock_maps[m])
 # Preserve the real A external shell, not a newly chosen first-clock shell.
 parent_source='rtl/hbm_accel/cores_split/reform_1106/ot_q2nf_parent_r2.sv'
 parent_primitive='rtl/hbm_accel/cores_split/reform_1106/ot_q2nf_parent_face_reg.sv'
 ctx=original/'parent_context';receipt=json.loads((ctx/'face_shell.json').read_text());assert receipt['clock']=='clk_control'
 parent_pins=json.loads(gzip.decompress((ctx/'parent_pins.json.gz').read_bytes()));pf=out/(R2+'_pins.json');write(pf,parent_pins)
 parent_ports=ports((repo/parent_source).read_text())[R2]
 views.append(dict(view=R2+'@'+sha(pf)[:12],module=R2,outline_um=[786.24,622.08],pins_file=pf.name,pins_sha256=sha(pf),pins=len(parent_pins),recipe_keys=[R2],family='Q2NF_PARENT_SOFT_PREP',instances=['retained A shell context'],blockers=['No signed child views: keep actual RTL hierarchy; no parent P&R']))
 child_inst={'ot_q2nf_control':'ot_q2nf_rest_rest_control','ot_q2nf_linkstore0':'ot_q2nf_rest_g_linkstore0','ot_q2nf_linkstore1':'ot_q2nf_rest_g_linkstore1'}
 parent_macros=[dict(inst='u_fcore.'+child_inst[q['owner']]+'.'+q['inst'],macro=q['macro'],xy_um=q['original_global_xy_um'],orient=q['orient'])for q in macro_rows]
 recipes[R2]=dict(top=R2,files=['q2nf_native/q2nf_native_source.sv',parent_source,parent_primitive],params={},defines=[],macros=sorted(MEM),macro_placement=parent_macros,source_commit=commit,read_at_commit=False,source='Actual retained A external R2 shell; only raw callee changes to exact three-child composition')
 parent_clocks=[n for n,d,w in parent_ports if n.startswith('clk')]
 profiles[R2]=dict(source_commit=commit,family='Q2NF_PARENT_SOFT_PREP',release_eligible=False,qualification='SOFT_NATIVE_PARENT_GEN_ONLY_NO_FIXED_CHILD_VIEWS',added_face_cycles=0,existing_external_face_cycles=dict(input=1,output=1,clock='clk_control'),endpoint_contract=dict(kind='EXTERNAL_REGISTERED',partition_rule='RETAIN_ACTUAL_A_PARENT_R2'),clock_ports=parent_clocks,reset_ports=['rst_n'],pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',diagnostic_inputs=True,port_inventory=dict(top=R2,source_file=parent_source,source_sha256=sha(repo/parent_source),ports=parent_ports),source_manifest={SOURCE:sha(src),parent_source:sha(repo/parent_source),parent_primitive:sha(repo/parent_primitive)},physical_reset_phase='Original A shell resets pass through; physical family reset qualification pending owner plan event')
 clock_names=[]
 for n,d,w in parent_ports:
  if n.startswith('clk'):clock_names.extend([n]if w==1 else [f'{n}[{j}]'for j in range(w)])
 write(out/(R2+'_density.json'),dict(schema='opentallas.hbm_multi_density.v1',module=R2,clock_ports=clock_names,layout='density',common_alignment=True,merge_roots=False,review=dict(verdict='DRAFT',basis='Retained A native clock ports, no merge; source preparation only, actual parent STA remains required')))
 geometry[R2]=dict(outline_um=[786.24,622.08],signal_max='M6',clock_max='M6',pg_top='M6',higher_parent_pg_landing='M7',macro_placement=parent_macros,external_capture_clock='clk_control',children_keep_real_RTL=True)
 base=json.loads((repo/'physical/die_plan/hbm_arch_cores/native128/plan.json').read_text());base['note']='Q2NF exact native family GEN preparation only; not adopted die plan';base['partition_types']={'q2nf_native_parent_prep':dict(outline_um=[786.24,622.08],hard_cores=[dict(inst={'ot_q2nf_control':'ot_q2nf_rest_rest_control','ot_q2nf_linkstore0':'ot_q2nf_rest_g_linkstore0','ot_q2nf_linkstore1':'ot_q2nf_rest_g_linkstore1'}[m],module=m,origin_um=BOXES[m][0],outline_um=BOXES[m][1],orient='R0',pins_file=m+'_pins.json')for m in BOXES])};base['partitions']=[]
 write(out/'plan.json',base);write(out/'views.json',dict(schema='opentallas.hbm_arch.core_views.v1',plan='plan.json',view_list=views));write(out/'native_profiles.json',dict(recipes=recipes,profiles=profiles,source_override={ 'q2nf_native/q2nf_native_source.sv':str(native.resolve())},geometry=geometry,source_sha256=sha(src)))
 write(out/'port_aliases.json',aliases);write(out/'kit_assembly.json',dict(bindings=[],parent_profile=dict(top='ot_q2nf_native_parent_r2',parameters={}),required_instances=[dict(inst='u_fcore.'+{'ot_q2nf_control':'ot_q2nf_rest_rest_control','ot_q2nf_linkstore0':'ot_q2nf_rest_g_linkstore0','ot_q2nf_linkstore1':'ot_q2nf_rest_g_linkstore1'}[m],master=m)for m in BOXES],qualification='SOFT_NATIVE_PREP: real RTL children retained; no fixed-port substitution'))
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--prepare',type=Path,required=True);p.add_argument('--gen',choices=[*BOXES,R2]);p.add_argument('--out',type=Path);a,rest=p.parse_known_args();out=a.prepare.resolve()
 if not a.gen or not (out/'native_profiles.json').exists():out=prepare(a.repo,out)
 if not a.gen:return
 raise SystemExit('WIP: GEN disabled pending final emitted-source hierarchy, native face placement and parent PG binding review')
 if a.out is None:raise ValueError('--out required for GEN')
 cfg=json.loads((out/'native_profiles.json').read_text());m=a.gen;v=json.loads((out/'views.json').read_text());view=next(q['view']for q in v['view_list']if q['module']==m)
 factory=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';sys.path.insert(0,str(factory.parent));spec=importlib.util.spec_from_file_location('q2nf_factory',factory);backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
 sys.argv=[str(factory),'--views',str(out/'views.json'),'--view',view,'--out',str(a.out),'--recipe-key',m,'--face-shell','off','--sigmax','M6' if m==R2 else 'M5','--pg-top-layer','M6' if m==R2 else 'M5','--core-insertion','none','--core-macros','off','--clock-pin-entry','on','--clock-taps','density','--clock-density-contract',str(out/(m+'_density.json')),'--util','.45','--single-root-taps','off',*rest]
 backend.main(recipe_overrides=cfg['recipes'],source_overrides=cfg['source_override'],source_profile=cfg['profiles'][m])
if __name__=='__main__':main()
