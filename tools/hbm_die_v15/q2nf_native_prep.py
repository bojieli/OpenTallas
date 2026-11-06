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
BOXES={'ot_q2nf_linkstore0':([34.56,172.8],[224.64,414.72]),'ot_q2nf_linkstore1':([527.04,172.8],[224.64,414.72])}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def ports(text):
 out={}
 for mod,header,body in re.findall(r'(?ms)^module\s+(\w+)\s*\((.*?)\);(.*?)^endmodule',text):
  rows=[]
  for d,hi,lo,n in re.findall(r'(?m)^\s*(input|output)\s+(?:(?:wire|reg|signed)\s+)*(?:\[(\d+):(\d+)\]\s+)?(\\\S+|[A-Za-z_$][A-Za-z0-9_$]*)\s*[,;]',header+'\n'+body):rows.append((n.lstrip('\\'),d,abs(int(hi)-int(lo))+1 if hi else 1))
  out[mod]=rows
 return out

def prepare(repo,out):
 repo=repo.resolve();out.mkdir(parents=True,exist_ok=True)
 original=repo/'physical/die_plan/hbm/over_cap_split/reform_1106/q2nf_linkstores'
 family=json.loads((original/'family_profile.json').read_text());assert family['schema']=='q2nf.bankstore_family.v2'
 layout=json.loads((original/'bank_cut/bank_parent_candidate.json').read_text())
 src=repo/SOURCE;text=src.read_text();inv=ports(text);assert set(BOXES)<=set(inv)
 sys.path.insert(0,str(repo/'tools/hbm_b2'));from hc_alpha_names import normalize_names,placement_name,TOKEN
 text,alpha=normalize_names(text,PARENT)
 aliases={n:'q2n_p_'+hashlib.sha256(n.encode()).hexdigest()[:16] for m in BOXES for n,d,w in inv[m] if not re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*',n)}
 assert len(set(aliases.values()))==len(aliases)
 mapped={'\\'+n:v for n,v in aliases.items()};processed=TOKEN.sub(lambda m:mapped.get(m[0],m[0]),text)
 inverse={v:k for k,v in mapped.items()};assert TOKEN.sub(lambda m:inverse.get(m[0],m[0]),processed)==text
 native=out/'q2nf_native_source.sv';native.write_text(processed);native_inv=ports(processed)
 masks=json.loads((original/'bank_cut/split3.json.ports.json').read_text())
 cl=json.loads((original/'bank_cut/boundary_clocks_bank_summary.json').read_text())
 old_layout=json.loads((original/'q2nf_parent_candidate.json').read_text())
 commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 source_file='q2nf_native/q2nf_native_source.sv';views=[];recipes={};profiles={};geometry={};all_macros=[]
 child_inst={m:'ot_q2nf_rest_g_linkstore'+str(i)for i,m in enumerate(BOXES)}
 child_inst['ot_q2nf_control']='ot_q2nf_rest_rest_control'
 for row in old_layout['macros']:
  owner={'link0':'ot_q2nf_linkstore0','link1':'ot_q2nf_linkstore1','rest_control':'ot_q2nf_control'}[row['owner']]
  name=placement_name(row['name'].removeprefix('u_fcore.'),alpha);x,y,X,Y=row['rect_um']
  all_macros.append(dict(owner=owner,inst=name,macro=row['module'],xy_um=[x,y],orient=row['orientation']))
 for i,(m,(origin,size)) in enumerate(BOXES.items()):
  key='link'+str(i);group='g_linkstore'+str(i);W,H=size;rows=[]
  declared={n:(d,w)for n,d,w in inv[m]}
  actual=set()
  for r in layout['raw_bit_pin_candidates']:
   if r['child']!=key:continue
   n=r['net'];assert declared[n]==(r['direction'],1);actual.add(n)
   rows.append(dict(name=aliases.get(n,n),layer='M4',x=round(r['xy_um'][0]-origin[0],6),y=round(r['xy_um'][1]-origin[1],6),face='E'if i==0 else'W'))
  assert actual==set(declared)-{'clk_link'} and declared['clk_link']==('input',4)
  clockmap={f'clk_link[{j}]':f'clk_link[{j+(1 if i==0 else 6)}]'for j in range(4)}
  assert masks['ot_q2nf_rest_'+group]['clk_link']['kept_original_indices_lsb_first']==list(range(1 if i==0 else 6,5 if i==0 else 10))
  for j,cy in enumerate((249.384,327.24,415.896,493.752)):
   rows.append(dict(name=f'clk_link[{j}]',layer='M5',x=W-4.32 if i==0 else 4.32,y=round(cy-origin[1],6),face='I'))
  assert len(rows)==1142 and len({(r['layer'],r['x'],r['y'])for r in rows})==len(rows)
  pf=out/(m+'_pins.json');write(pf,rows)
  macros=[dict(inst=r['inst'],macro=r['macro'],xy_um=[round(r['xy_um'][0]-origin[0],6),round(r['xy_um'][1]-origin[1],6)],orient=r['orient'])for r in all_macros if r['owner']==m]
  assert len(macros)==4
  views.append(dict(view=m+'@'+sha(pf)[:12],module=m,outline_um=size,pins_file=pf.name,pins_sha256=sha(pf),pins=len(rows),recipe_keys=[m],family='Q2NF_BANK_NATIVE_PREP',instances=[R2+'.u_fcore.'+child_inst[m]],blockers=['UNROUTED; native mapped endpoint census/PA and actual PG/OBS pending']))
  recipes[m]=dict(top=m,files=[source_file],params={},defines=[],macros=sorted({r['macro']for r in macros}),macro_placement=macros,source_commit=commit,read_at_commit=False,source='Exact bank-only zero-edge extraction; original SRAM sites/orientations; reversible alpha identifiers')
  profiles[m]=dict(source_commit=commit,family='Q2NF_BANK_NATIVE_PREP',release_eligible=False,qualification='NATIVE_SOURCE_AND_GEN_PREPARATION_ONLY',added_face_cycles=0,endpoint_contract=dict(kind='INTERNAL_CORE',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION',parent_partition='q2nf_native_parent_prep'),clock_ports=['clk_link'],reset_ports=[],pin_placement_policy='DECLARED_CLOCK_RESET_POINTS',diagnostic_inputs=True,port_inventory=dict(top=m,source_file=source_file,source_sha256=sha(native),ports=native_inv[m]),indexed_clock_parent_bindings=clockmap,original_parent_clock_items=cl[group]['clocked_items_by_actual_parent_clock'],actual_parent_shell='retained A external clk_control captures +1in/+1out; controller remains real soft RTL',physical_reset_phase='Bank source has NO reset input; preserve actual unreset datapath, external controller reset qualification remains in parent',source_manifest={SOURCE:sha(src)},alpha_instance_report=alpha,port_aliases={n:v for n,v in aliases.items()if n in declared})
  write(out/(m+'_density.json'),dict(schema='opentallas.hbm_multi_density.v1',module=m,clock_ports=list(clockmap),layout='density',common_alignment=True,merge_roots=False,review=dict(verdict='DRAFT',basis='Exact original indexed bank roots; actual endpoint cluster census pending')))
  geometry[m]=dict(origin_um=origin,outline_um=size,macro_placement=macros,signal_max='M5',clock_max='M5',obs_intent='M5',pg_top='M5',native_roots=clockmap,pins=rows,qualification='M5 candidate only; actual SRAM OBS M1-M4 leaves M5 transit; physical closure not measured')
 parent_source='rtl/hbm_accel/cores_split/reform_1106/ot_q2nf_parent_r2.sv';parent_primitive='rtl/hbm_accel/cores_split/reform_1106/ot_q2nf_parent_face_reg.sv';ctx=original/'parent_context'
 receipt=json.loads((ctx/'face_shell.json').read_text());assert receipt['clock']=='clk_control'
 parent_pins=json.loads(gzip.decompress((ctx/'parent_pins.json.gz').read_bytes()));pf=out/(R2+'_pins.json');write(pf,parent_pins)
 parent_ports=ports((repo/parent_source).read_text())[R2];assert any(n=='clk_control'for n,d,w in parent_ports) and any(n=='rst_n'for n,d,w in parent_ports)
 views.append(dict(view=R2+'@'+sha(pf)[:12],module=R2,outline_um=[786.24,622.08],pins_file=pf.name,pins_sha256=sha(pf),pins=len(parent_pins),recipe_keys=[R2],family='Q2NF_PARENT_SOFT_PREP',instances=['retained A shell'],blockers=['No signed bank child views; no parent route']))
 parent_macros=[dict(inst='u_fcore.'+child_inst[r['owner']]+'.'+r['inst'],macro=r['macro'],xy_um=r['xy_um'],orient=r['orient'])for r in all_macros]
 recipes[R2]=dict(top=R2,files=[source_file,parent_source,parent_primitive],params={},defines=[],macros=sorted(MEM),macro_placement=parent_macros,source_commit=commit,read_at_commit=False,source='Actual A R2 shell and real controller RTL; no fixed-port substitute before signed bank views')
 profiles[R2]=dict(source_commit=commit,family='Q2NF_PARENT_SOFT_PREP',release_eligible=False,qualification='SOFT_NATIVE_PREP_ONLY_NO_FIXED_CHILD_VIEWS',added_face_cycles=0,existing_external_face_cycles=dict(input=1,output=1,clock='clk_control'),clock_ports=[n for n,d,w in parent_ports if n.startswith('clk')],reset_ports=['rst_n'],source_manifest={SOURCE:sha(src),parent_source:sha(repo/parent_source),parent_primitive:sha(repo/parent_primitive)},port_inventory=dict(top=R2,ports=parent_ports),physical_reset_phase='Retained real A reset semantics; physical placement/qualification pending')
 geometry[R2]=dict(outline_um=[786.24,622.08],signal_max='M6',clock_max='M6',pg_top='M6',higher_parent_pg_landing='M7',macro_placement=parent_macros,soft_controller=True,children_keep_real_RTL=True,nominal_controller_free_area_before_halos_um2=layout['controller_free_area_before_halos_um2'])
 base=json.loads((repo/'physical/die_plan/hbm_arch_cores/native128/plan.json').read_text());base['note']='Q2NF bank candidate only; controller remains soft in full R2 parent';base['partition_types']={'q2nf_native_parent_prep':dict(outline_um=[786.24,622.08],hard_cores=[dict(inst=child_inst[m],module=m,origin_um=BOXES[m][0],outline_um=BOXES[m][1],orient='R0',pins_file=m+'_pins.json')for m in BOXES])};base['partitions']=[]
 write(out/'plan.json',base);write(out/'views.json',dict(schema='opentallas.hbm_arch.core_views.v1',plan='plan.json',view_list=views));write(out/'native_profiles.json',dict(recipes=recipes,profiles=profiles,source_override={source_file:str(native.resolve())},geometry=geometry,source_sha256=sha(src)))
 write(out/'port_aliases.json',aliases);write(out/'kit_assembly.json',dict(bindings=[],parent_profile=dict(top=R2,parameters={}),required_instances=[dict(inst='u_fcore.'+child_inst[m],master=m)for m in [*BOXES,'ot_q2nf_control']],qualification='SOFT_PREP: retain all real hierarchy; bind only two bank helpers after actual signed BB/lib/LEF and parameter seals'))
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--prepare',type=Path,required=True);p.add_argument('--gen',choices=[*BOXES,R2]);p.add_argument('--out',type=Path);a,rest=p.parse_known_args();out=a.prepare.resolve()
 if not a.gen or not (out/'native_profiles.json').exists():out=prepare(a.repo,out)
 if not a.gen:return
 raise SystemExit('WIP: GEN disabled pending native mapped endpoint placement, actual pin access and parent PG binding review')
 if a.out is None:raise ValueError('--out required for GEN')
 cfg=json.loads((out/'native_profiles.json').read_text());m=a.gen;v=json.loads((out/'views.json').read_text());view=next(q['view']for q in v['view_list']if q['module']==m)
 factory=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';sys.path.insert(0,str(factory.parent));spec=importlib.util.spec_from_file_location('q2nf_factory',factory);backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
 sys.argv=[str(factory),'--views',str(out/'views.json'),'--view',view,'--out',str(a.out),'--recipe-key',m,'--face-shell','off','--sigmax','M6' if m==R2 else 'M5','--pg-top-layer','M6' if m==R2 else 'M5','--core-insertion','none','--core-macros','off','--clock-pin-entry','on','--clock-taps','density','--clock-density-contract',str(out/(m+'_density.json')),'--util','.45','--single-root-taps','off',*rest]
 backend.main(recipe_overrides=cfg['recipes'],source_overrides=cfg['source_override'],source_profile=cfg['profiles'][m])
if __name__=='__main__':main()
