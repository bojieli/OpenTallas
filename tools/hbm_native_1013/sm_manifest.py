#!/usr/bin/env python3
"""Source-pinned native SM boundary elaboration; hard interiors are explicit blackboxes.
Run under ot-heavy. This proves wiring/census, not hard-block arithmetic or closure.
"""
import argparse, collections, hashlib, json, math, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RTL='rtl/hbm_accel/sm/ot_hbm_accel_smh.sv'
def run(*args): return subprocess.check_output(args,cwd=ROOT,text=True)
def pinned(commit,path): return run('git','show',f'{commit}:{path}')
def dump(path,data): path.write_text(json.dumps(data,indent=2)+'\n')
def clean(s): return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
def header(body):
    body=clean(body); depth=0
    for i,c in enumerate(body):
        if c=='(': depth+=1
        elif c==')': depth-=1
        elif c==';' and depth==0: return body[:i+1]
    raise ValueError('No module header')
def views(commit,module,prefer=None):
    paths=run('git','ls-tree','-r','--name-only',commit,'physical').splitlines()
    candidates=[p for p in paths if p.endswith('/'+module+'.lef')]
    if prefer: candidates.sort(key=lambda p:(prefer not in p,p))
    else: candidates.sort(key=lambda p:('ref_tile/' not in p,p))
    if not candidates: return {'view_lef':None,'view_lib':{},'w_um':None,'h_um':None,'pg_top':None,'closure_status':'UNRESOLVED_NO_VIEW'}
    p=candidates[0]; text=pinned(commit,p)
    size=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text)
    stem=p[:-4]; libs={c:stem+'_'+c+'.lib' for c in ('tt','ff','ss') if stem+'_'+c+'.lib' in paths}
    obs=text.split('OBS',1)[-1] if 'OBS' in text else ''
    pg=[]
    for pin in re.findall(r'PIN\s+(?:VDD|VSS)\b(.*?)END\s+(?:VDD|VSS)',text,re.S): pg+=re.findall(r'LAYER\s+(M\d+)',pin)
    return {'view_lef':p,'view_lib':libs,'w_um':float(size[1]),'h_um':float(size[2]),'pg_top':max(pg,key=lambda x:int(x[1:])) if pg else None,'closure_status':'CANDIDATE_VIEW_REQUIRES_SOURCE_AND_GATE_AUDIT','view_sha256':hashlib.sha256(text.encode()).hexdigest(),'obs_layers':sorted(set(re.findall(r'LAYER\s+(M\d+)',obs))),'child_lint':str(Path(p).parent/'child_lint.json') if str(Path(p).parent/'child_lint.json') in paths else None}
def main():
    a=argparse.ArgumentParser(); a.add_argument('--source',default='49b00f711'); a.add_argument('--out',default='results/arch/hbm_native_1013/sm'); args=a.parse_args()
    commit=run('git','rev-parse',args.source).strip(); out=ROOT/args.out; out.mkdir(parents=True,exist_ok=True)
    source=pinned(commit,RTL)
    bodies={m.group(1):m.group(0) for m in re.finditer(r'\bmodule\s+(\w+)\b.*?\bendmodule\b',source,re.S)}
    top='ot_hbm_accel_smh'; fc='ot_hbm_accel_smh_front_c'
    masters=['ot_hbm_accel_smh_front_n','ot_hbm_accel_smh_front_s','ot_hbm_accel_smh_tile_eg','ot_hbm_accel_smh_tile_wg','ot_hbm_accel_smh_be_eg','ot_hbm_accel_smh_be_wg']+[f'ot_hbm_accel_smh_fc_{n}' for n in ['bc','is','xl','t','xr','b']]
    sv='`define OT_SMH_CG\n`define OT_SMH_FC_HIER\n`define SYNTHESIS\n'+bodies[top]+'\n'+bodies[fc]+'\n'+'\n'.join('(* blackbox *) '+header(bodies[m])+'\nendmodule' for m in masters)+'\n'
    (out/'boundary_elaboration.sv').write_text(sv)
    ys=f'read_verilog -sv {args.out}/boundary_elaboration.sv\nhierarchy -check -top {top}\nproc\nflatten\ncheck\nwrite_json {args.out}/elaborated.json\n'
    (out/'elaborate.ys').write_text(ys)
    proc=subprocess.run(['yosys','-Q','-s',str(out/'elaborate.ys')],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/'elaboration.log').write_text(proc.stdout)
    if proc.returncode: raise SystemExit(proc.returncode)
    design=json.loads((out/'elaborated.json').read_text()); module=design['modules'][top]
    assert len(module['cells'])==35,[(k,v['type']) for k,v in module['cells'].items()]
    ports={k:{'direction':v['direction'],'width':len(v['bits']),'role':'clock' if k=='clk' else 'reset' if k=='rst_n' else 'control' if k=='cg_en' else 'signal'} for k,v in module['ports'].items()}
    nodes=collections.defaultdict(list); constants=[]; children=[]
    for port,data in module['ports'].items():
        for i,bit in enumerate(data['bits']): nodes[bit].append({'instance':'$boundary','port':port,'lsb':i,'width':1,'direction':data['direction']})
    for name,cell in sorted(module['cells'].items()):
        typ=cell['type']; physical=views(commit,typ,prefer='80412d770_np_r2_tc' if '_be_' in typ else None)
        publications=json.loads((out/'publication_evidence.json').read_text())
        if typ in publications:
            evidence=publications[typ]; physical.update({k:evidence[k] for k in ['view_lef','view_lib','w_um','h_um']})
            physical.update(view_source_commit=evidence['source_commit'],view_publication_commit=evidence['publication_commit'],view_job=evidence['job'],module_text_equal=evidence['source_module_text_equal_ignoring_comments_whitespace'],closure_status='INHERITED_CLOSED_VIEW_NATIVE_SEAMS_OPEN',child_lint=None)
            lef=(ROOT/physical['view_lef']).read_text(); pg=[]
            for pin in re.findall(r'PIN\s+(?:VDD|VSS)\b(.*?)END\s+(?:VDD|VSS)',lef,re.S): pg+=re.findall(r'LAYER\s+(M\d+)',pin)
            physical['pg_top']=max(pg,key=lambda x:int(x[1:])) if pg else None
            lint=ROOT/str(Path(physical['view_lef']).parent/'child_lint.json')
            if lint.exists(): physical['child_lint']={'path':str(lint.relative_to(ROOT)), 'verdict':json.loads(lint.read_text())['verdict']}
            if not physical['child_lint'] or 'tt' not in physical['view_lib']: physical['closure_status']='HISTORICAL_CLOSED_VIEW_NATIVE_CHILD_LINT_TT_EXPORT_OPEN'
        fresh_be=out/'be_eg_r2_physical_candidate'
        if typ=='ot_hbm_accel_smh_be_eg' and (fresh_be/'receipt.json').exists():
            receipt=json.loads((fresh_be/'receipt.json').read_text()); physical.update(view_lef=str((fresh_be/(typ+'.lef')).relative_to(ROOT)),view_lib={corner:str((fresh_be/(typ+'_'+corner+'.lib')).relative_to(ROOT)) for corner in ['tt','ff','ss']},view_source_commit=receipt['physical_rtl_snapshot_commit'],view_publication_commit=receipt['publication_commit'],view_job=receipt['job'],pg_top='M5',closure_status='CLOSED_TT_FF_PHYSICAL_NATIVE_ADOPTION_PENDING',child_lint={'path':str((fresh_be/'child_lint.json').relative_to(ROOT)),'verdict':json.loads((fresh_be/'child_lint.json').read_text())['verdict']},physical_receipt=str((fresh_be/'receipt.json').relative_to(ROOT)))
        if '_tile_' in typ:
            variant='eg' if typ.endswith('_eg') else 'wg'; specpath=f'physical/ref_tile_specs/smh/smh_tile_{variant}_ref.json'
            spec=json.loads(pinned(commit,specpath)); snapshot_dir=out/'inherited_tile_manifests'; snapshot_dir.mkdir(exist_ok=True); spec_snapshot=snapshot_dir/f'smh_tile_{variant}_ref.spec.json'; dump(spec_snapshot,spec); fp_original=f'physical/ref_tile/smh_tile_{variant}_ref/floorplan.json'; fp_snapshot=snapshot_dir/f'smh_tile_{variant}_ref.floorplan.json'; dump(fp_snapshot,json.loads(pinned(commit,fp_original))); physical.update(view_lef=None,view_lib={},w_um=spec['outline']['w'],h_um=spec['outline']['h'],pg_top='M7',closure_status='OPEN_NATIVE_TILE_R5',physical_spec=str(spec_snapshot.relative_to(ROOT)),original_physical_spec=specpath,inherited_children=spec['children'],child_manifest=str(fp_snapshot.relative_to(ROOT)),original_child_manifest=fp_original)
        children.append({'instance':name,'logical_module':typ,'source_commit':commit,'parameters':cell.get('parameters',{}),'boundary_ports':{p:{'direction':cell['port_directions'][p],'width':len(b)} for p,b in cell['connections'].items()},'orientation':'R0',**physical})
        for port,bits in cell['connections'].items():
            for i,bit in enumerate(bits):
                endpoint={'instance':name,'port':port,'lsb':i,'width':1,'direction':cell['port_directions'][port]}
                if isinstance(bit,str): constants.append({'value':bit,**endpoint})
                else: nodes[bit].append(endpoint)
    connections=[]; binding=[]
    for bit,endpoints in sorted(nodes.items(),key=lambda x:str(x[0])):
        boundary=[e for e in endpoints if e['instance']=='$boundary']; others=[e for e in endpoints if e['instance']!='$boundary']
        for b in boundary:
            for e in others: binding.append({'parent_port':b['port'],'parent_lsb':b['lsb'],'width':1,'child_instance':e['instance'],'child_port':e['port'],'child_lsb':e['lsb']})
        connections.append({'net':f'n{bit}','endpoints':endpoints,'kind':'clock' if any(e['port']=='clk' for e in endpoints) else 'reset' if any(e['port'] in ('rst_a','rst_n') for e in endpoints) else 'signal'})
    # Exact source census including front_c's nine children; no hard SM or front_c parent.
    counts=collections.Counter(c['logical_module'] for c in children)
    assert sum(n for k,n in counts.items() if '_tile_' in k)==16
    assert sum(n for k,n in counts.items() if '_be_' in k)==8
    assert sum(n for k,n in counts.items() if '_fc_' in k)==9
    # Candidate footprint has real tile dimensions and real front/back views. Open dimensions never imply closure.
    gap=8.64; tw=630.72; th=1252.8
    front=[c for c in children if '_front_' in c['logical_module'] or '_fc_' in c['logical_module']]
    fw=898.56  # prior FC_HIER center-band contract; actual inherited masters retain actual dimensions
    be=[c for c in children if '_be_' in c['logical_module']]; bh=math.ceil(max(c['h_um'] for c in be)/gap)*gap
    fx=4*(tw+gap)
    # Functional front layout from source-pinned FC_POS (not obsolete H3_TILE dimensions).
    fc_xy={'u_bc':(254.88,4.32,'R0'),'u_is':(254.88,494.64,'R0'),'u_xl':(298.08,786.24,'R0'),'u_tw':(4.32,872.64,'R0'),'u_te':(678.24,872.64,'MY'),'u_rw':(4.32,518.4,'R0'),'u_re':(678.24,518.4,'MY'),'u_bw':(4.32,0,'R0'),'u_be':(678.24,0,'MY')}
    fs=next(c for c in front if c['logical_module'].endswith('front_s')); fn=next(c for c in front if c['logical_module'].endswith('front_n'))
    fc_y=fs['h_um']+gap; fc_h=1088.64
    fs['xy_um']=[round(fx+(fw-fs['w_um'])/2,3),0]
    fn['xy_um']=[round(fx+(fw-fn['w_um'])/2,3),round(fc_y+fc_h+gap,3)]
    for c in front:
        if '_fc_' in c['logical_module']:
            x,y,orient=fc_xy[c['instance'].split('.')[-1]]; c['xy_um']=[round(fx+x,3),round(fc_y+y,3)]; c['orientation']=orient
    fy=fn['xy_um'][1]+fn['h_um']
    for c in children:
        match=re.search(r'g_c\[(\d+)\](?:\.g_p\[(\d+)\])?',c['instance'])
        if not match: continue
        col=int(match[1]); x=col*(tw+gap)+(fw+gap if col>=4 else 0)
        row=int(match[2]) if match[2] else None
        y=bh+gap+(1-row)*(th+gap) if row is not None else 0
        c['xy_um']=[round(x,3),round(y,3)]
    width=round(8*(tw+gap)+fw,3); height=round(max(fy, bh+gap+2*(th+gap)),3)
    unresolved=[{'instance':c['instance'],'logical_module':c['logical_module'],'reason':c['closure_status'],'owner':'/root/hbm_sm_cluster' if '_tile_' in c['logical_module'] else '/root/hbm_sm_native_manifest','required':['source equivalence','TT setup and FF hold','DRC zero','child_lint','PG export and native seam timing','throughput qualification']} for c in children]
    manifest={'schema':'opentallas.native_component.v1','component':'sm','logical_module':top,'source_commit':commit,'source_file':RTL,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'boundary_elaboration_defines':['OT_SMH_CG','OT_SMH_FC_HIER','SYNTHESIS'],'defines':['OT_SMH_CG','OT_SMH_FC_HIER','OT_SMH_CG_ENREG','OT_SMH_XLK','OT_FP_DATA_NORST','OT_SMH_DRST0','OT_SMH_RSTRELAY','OT_SMH_HIER','OT_SMH_PTW_OHDLY','SYNTHESIS'],'parameters':{'NC':8,'SUB':4,'RPT':2,'LBS':2,'LSB':16,'IL':8,'RMAX':4096,'LEV':4,'XD':128,'MAX_OUT':512,'TCK':1,'PIO':2,'HAZ':1,'NOUT':4,'ENABLE_INT8':0,'PIPE_INT8':0,'REQCR':1},'outline_um':{'w':width,'h':height},'placement_revision':3,'placement_status':'nonoverlapping_functional_front_candidate_requires_seam_placement','front_placement_reference':{'source_commit':commit,'source_file':'tools/hbm_accel_smh_physical.py','table':'FC_POS','front_c_soft_band_um':[898.56,1088.64],'native_site_grid_um':0.432,'east_my_x_delta_um':0.048,'note':'Actual view widths218.16supersede oldFC_DIM216.024. EastMYx678.192->678.24 snaps oldFC_POS to native0.432sitegrid. No hard front_c master.'},'closed':False,'boundary_ports':ports,'children':children,'connections':connections,'boundary_binding':binding,'constant_binding':constants,'unresolved':unresolved,'preconditions':['Hard tiles placed directly on die; no hardened full-SM master','front_c expands to nine children under OT_SMH_FC_HIER; no hardened front_c parent','FC_HIER adds two cycles to row bundles and tile-row-1 x-write; must price and exactness qualify','Tile R5 closure must publish real M7 PG LEF plus TT/FF/SS libs before placement can qualify','M8 die ties to M7 tile PG, M9 distribution candidate; continuity/IR remain open','Candidate packing requires registered relays for every long seam; no placement-only timing claim','Legacy hfd_sm 3214.08x1131.84 outline is not native coverage']}
    # Coalesce adjacent bits only if every endpoint advances by one; preserve exact permutations.
    compact=[]
    for row in sorted(connections,key=lambda r:int(r['net'][1:])):
        row['endpoints'].sort(key=lambda e:(e['instance'],e['port'],e['lsb']))
        prev=compact[-1] if compact else None
        if prev and prev['kind']==row['kind'] and len(prev['endpoints'])==len(row['endpoints']) and all(a['instance']==b['instance'] and a['port']==b['port'] and a['direction']==b['direction'] and a['lsb']+a['width']==b['lsb'] for a,b in zip(prev['endpoints'],row['endpoints'])):
            prev['elaboration_bits'].append(int(row['net'][1:]))
            for endpoint in prev['endpoints']: endpoint['width']+=1
        else:
            row['elaboration_bits']=[int(row['net'][1:])]; compact.append(row)
    manifest['connections']=compact
    compact_binding=[]
    for row in sorted(binding,key=lambda r:(r['parent_port'],r['child_instance'],r['child_port'],r['parent_lsb'])):
        prev=compact_binding[-1] if compact_binding else None
        if prev and all(prev[k]==row[k] for k in ['parent_port','child_instance','child_port']) and prev['parent_lsb']+prev['width']==row['parent_lsb'] and prev['child_lsb']+prev['width']==row['child_lsb']: prev['width']+=1
        else: compact_binding.append(row.copy())
    manifest['boundary_binding']=compact_binding
    compact_constants=[]
    for row in sorted(constants,key=lambda r:(r['instance'],r['port'],r['lsb'])):
        prev=compact_constants[-1] if compact_constants else None
        if prev and all(prev[k]==row[k] for k in ['instance','port','value','direction']) and prev['lsb']+prev['width']==row['lsb']: prev['width']+=1
        else: compact_constants.append(row.copy())
    manifest['constant_binding']=compact_constants
    overlaps=[]
    for i,c in enumerate(children):
        for d in children[i+1:]:
            x,y=c['xy_um']; xx,yy=d['xy_um']
            if min(x+c['w_um'],xx+d['w_um'])>max(x,xx)+1e-8 and min(y+c['h_um'],yy+d['h_um'])>max(y,yy)+1e-8: overlaps.append([c['instance'],d['instance']])
    assert not overlaps,overlaps
    manifest['placement_check']={'overlaps':overlaps,'all_dimensions_from_real_views_or_tile_specs':True,'seam_routes_closed':False}
    dump(out/'component.json',manifest)
    replication=[{'sm':sm,'cluster':sm//8,'local_sm':sm%8,'owner':'/root/hbm_die_compiler','template':'component.json','instance_prefix':f'sm{sm:02d}','closed':False} for sm in range(32)]
    production_rows=[]
    for sm in range(32):
        for i,c in enumerate(children): production_rows.append({'instance':f'sm{sm:02d}/'+c['instance'],'sm':sm,'cluster':sm//8,'logical_module':c['logical_module'],'component_row':i,'template':'component.json','xy_local_um':c['xy_um'],'w_um':c['w_um'],'h_um':c['h_um'],'orientation':c['orientation'],'closure_status':c['closure_status'],'owner':'/root/hbm_sm_cluster' if '_tile_' in c['logical_module'] else '/root/hbm_sm_native_manifest','die_placement_owner':'/root/hbm_die_compiler','closed':False})
    dump(out/'production_components.json',{'source_commit':commit,'placement_revision':3,'rows':production_rows,'census':{'rows':len(production_rows),'tiles':512},'global_xy_um':None,'precondition':'Die lead translates these local candidates; no full-SM hard macro instantiated'})
    dump(out/'production_instances.json',{'source_commit':commit,'template':'component.json','expansion_rule':'Each child and endpoint instance is prefixed smNN/; boundary becomes smNN/$boundary; local coordinates are translated by die placement. This is an explicit parametrically identical replication, never a hard parent.','instances':replication,'census':{'sms':32,'tile_clusters':512,'backends':256,'front_n':32,'front_s':32,'front_c_children':288,'direct_die_hard_candidates':1120},'aggregate_tile_bbox_area_mm2':512*tw*th/1e6,'full_candidate_bbox_mm2':32*width*height/1e6,'closed':False})
    dump(out/'checks.json',{'yosys_exit_code':proc.returncode,'yosys_version':run('yosys','-V').strip(),'boundary_ports':len(ports),'child_count':len(children),'module_counts':dict(counts),'connected_bit_nets':len(connections),'compressed_net_rows':len(compact),'overlaps':overlaps,'boundary_bit_bindings':len(binding),'constant_bits':len(constants),'tile_boundary_widths':{'rin':1636,'bin':2069,'gin':100,'gout':200},'exactness_scope':'Production source top and hierarchical front_c are parsed and elaborated; hard interiors are blackboxes. No arithmetic bit-exactness, physical closure or throughput claim.','compile_command':['ot-heavy','--mem','8','--','python3','tools/hbm_native_1013/sm_manifest.py','--source',commit],'pass':True})
    print(json.dumps({'source_commit':commit,'counts':dict(counts),'outline_um':[width,height],'connection_bits':len(connections),'boundary_bindings':len(binding)}))
if __name__=='__main__': main()
