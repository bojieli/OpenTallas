#!/usr/bin/env python3
"""Opt-in PRIVATE historical d25/fullm25 source preparation; no GEN/CAD/adoption.

Inputs must be the exact immutable source-event/readset and recovered clock graph.
The output is a source capsule, not a generated/signed kit or production selection.
"""
import argparse,copy,hashlib,json,re,shutil
from pathlib import Path
import kv_core_rtl as K
import kvspc_model_projection as P
import gen_core_kit_kv as G
COHORT='PRIVATE_HISTORICAL_D25_FULLM25'
TYPE='kv3_pc__cl5a95b461'
MANIFEST_SHA='6204f0d885ba697ceb261a6d9cfb9e99b757ff56d4b16d90d3c2ab4ff966307b'
SITES_SHA='7e0c26f5ca69990206118fb508836e3e492223ff8e08b54fee5c1debc25fdf1e'

def require(v,s):
    if not v:raise ValueError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ports(text,module):
    m=re.search(r'^module\s+'+re.escape(module)+r'\s*(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?\(',text,re.M);require(m,'expected ANSI module')
    end=text.index(');',m.end());return text[m.end():end]
def inject_header(text,module,inputs):
    hdr=ports(text,module);require('ck_mesh' not in hdr and not any(n in hdr for n in inputs),'boundary already present')
    m=re.search(r'^module\s+'+re.escape(module)+r'\s*(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?\(',text,re.M)
    new='\n'+''.join('    input wire '+n+',\n' for n in inputs)+'    output wire ck_mesh,\n'
    return text[:m.end()]+new+text[m.end():]
def append_ft(model,arcs):
    m=copy.deepcopy(model)
    for a in arcs:
        for p,d,net,cls in ((a['input_port'],'input',a['input_net'],'in'),(a['output_port'],'output',a['output_net'],'out')):
            require(p not in m['pdecl'],'duplicate FT declaration')
            m['pdecl'][p]={'dir':d,'hi':None,'lo':None,'gaps':[]}
            m['part_conn'][(p,None)]=(net,0);m['pin_class'][(p,None)]=cls
    return m

def head_physical_hook(head_arcs,rows,hc):
    """Normal producer + exact contextual net inventory, including real BASE pins.

No master/geometry/parallel-short semantics change. Reject every undeclared net.
"""
    arcs=copy.deepcopy(head_arcs);byk={r['arc_k']:r for r in rows if r['child']=='kvpc0'};allow={};w=hc['outline_um'][0]
    for a in arcs:
        r=byk[a['k']];a['source']=r['input_net'];a['sink']='ck_mesh'
        for j,c in enumerate(a['cells']):
            original=c['name'];c['name']='u_core_kvpc0.'+original
            # Real MY body lower-left, not a point reflection.
            require(hc['orient']=='MY','unsupported genuine HEAD orient')
            c['x_um']=round(hc['origin_um'][0]+hc['track_offset_um'][0]+w-c['x_um']-1.62,6)
            c['y_um']=round(hc['origin_um'][1]+hc['track_offset_um'][1]+c['y_um'],6)
            if j:allow[c['name']]='u_core_kvpc0.'+r['output_port']+'__p'+str(j)
    text=G.island_ft_tcl(arcs,'PRIVATE_HISTORICAL_SOFT_HEAD')
    # Extend normal exact endpoint census for the actual three real macro pins.
    extra=[]
    for r in rows:
        if r['child']=='kvpc0':continue
        require(r['module']=='qkd_kvs_pc','non-BASE hard child')
        extra.extend([f'  dict lappend want {r["input_net"]} "u_core_{r["child"]}/{r["input_port"]}"',f'  dict lappend want ck_mesh "u_core_{r["child"]}/{r["output_port"]}"'])
    marker='  foreach a $::ot_ft_nets {\n    foreach p [lrange $a 0 1] {'
    require(text.count(marker)==1,'normal FT endpoint-check template changed')
    text=text.replace(marker,'\n'.join(extra)+'\n'+marker)
    old='if {$n ne "NULL" && ![string match "${dst}__p*" [$n getName]]} { error "OT_ISLAND_FT_SHORT $name Y on [$n getName]" }'
    require(text.count(old)==1,'normal FT private-net template changed')
    exact='if {$n ne "NULL" && (![dict exists $::hhp_ft_private $name] || [$n getName] ne [dict get $::hhp_ft_private $name])} { error "OT_ISLAND_FT_SHORT_UNDECLARED $name Y on [$n getName]" }'
    text=text.replace(old,exact)
    # The normal physical check now visits every real cut input, even inputs
    # feeding only BASE macros. The shared mesh remains one real BTerm.
    nets=' '.join('{'+n+' ck_mesh 0}' for n in sorted({r['input_net'] for r in rows}))
    text=re.sub(r'^set ::ot_ft_nets .*$',lambda _: 'set ::ot_ft_nets {'+nets+'}',text,flags=re.M)
    private=' '.join('{'+n+'} {'+v+'}' for n,v in allow.items())
    text='# PRIVATE HISTORICAL ONLY; canonical cohort remains HOLD. Exact normal-producer contextual adapter.\nset ::hhp_ft_private [dict create '+private+']\n'+text
    return text,arcs,allow

def cut_geometry(geometry,part):
    """Actual recovered native shapes only; no via/route/clock credit."""
    row=next(p for p in geometry['parts'] if p['part']==part)
    shapes={r['net']:r['parent_shapes'] for r in row['clock_only_inputs']}
    shapes['ck_mesh']=[{'layer':'M9','rect_um':p['declared_canonical_M9_strap_subset_parent_rect_um']} for p in row['clock_only_output']['native_FT_sources']]
    require(len(shapes)==5 and sum(len(v) for k,v in shapes.items() if k!='ck_mesh')==12 and len(shapes['ck_mesh'])==8,'wrong native cut geometry')
    lines=['# PRIVATE HISTORICAL ONLY: native M1 Y-pin shapes + canonical M9 strap subsets. NO via/route credit.', 'set dc_b [ord::get_db_block]', 'set dc_u [$dc_b getDbUnitsPerMicron]', 'set dc_tech [ord::get_db_tech]']
    for name,ss in shapes.items():
        lines += ['set dc_t [$dc_b findBTerm {'+name+'}]', 'if {$dc_t eq "NULL" || $dc_t eq ""} {error "HHP_CUT missing '+name+'"}', 'set dc_n [$dc_t getNet]', 'if {$dc_n eq "NULL" || $dc_n eq ""} {error "HHP_CUT disconnected '+name+'"}', '$dc_n setSigType CLOCK', '$dc_t setSigType CLOCK', 'foreach dc_p [$dc_t getBPins] {odb::dbBPin_destroy $dc_p}', 'set dc_p [odb::dbBPin_create $dc_t]', '$dc_p setPlacementStatus FIXED']
        for sh in ss:
            r=sh['rect_um'];require(len(r)==4 and r[2]>r[0] and r[3]>r[1],'invalid actual cut box')
            vals=' '.join('[expr {round('+format(v,'.9f')+'*$dc_u)}]' for v in r)
            lines += ['set dc_l [$dc_tech findLayer {'+sh['layer']+'}]', 'if {$dc_l eq "NULL"} {error "HHP_CUT missing layer"}', 'odb::dbBox_create $dc_p $dc_l '+vals]
    return '\n'.join(lines)+'\n',shapes

def prepare(native,event_dir,geom,manifest_path,out,*,enabled=False,cohort=None):
    if not enabled:return {'status':'DISABLED','qualified':False}
    require(cohort==COHORT,'explicit PRIVATE historical cohort required')
    native,event_dir,geom,manifest_path,out=map(Path,(native,event_dir,geom,manifest_path,out))
    require(not out.exists(),'output must be fresh; preserve old capsules')
    require(sha(manifest_path)==MANIFEST_SHA,'wrong exact recovered manifest')
    require(sha(geom/'selected_plan.json')==SITES_SHA,'wrong exact current source sites')
    event=event_dir/'event.json';require(sha(event)==P.EVENT_SHA256,'wrong full event')
    e=json.loads(event.read_text());manifest=json.loads(manifest_path.read_text())
    require(manifest['mesh_sites_sha256']=='d25f60c6f22e6921a36d73a850b3bc8a3822f0e5545879ff05e84bd1755513db','wrong historical mesh')
    original=native/'native_rtl';before={p.name:sha(p) for p in original.iterdir() if p.is_file()}
    for row in e['files']:
        if row['before_sha256'] is None:require(row['file'] not in before,'added file already exists')
        else:require(before.get(row['file'])==row['before_sha256'],'wrong native source '+row['file'])
    guard=P.verified_guard(event,event_dir/'rtl_overlay',original/P.BASE_FILE,('kvpc1','kvpc2','kvpc3'))
    out.mkdir(parents=True);common=out/'common_after_full_event';shutil.copytree(original,common)
    for row in e['files']:shutil.copy2(event_dir/'rtl_overlay'/row['file'],common/row['file'])
    plan=json.loads((native/'plan_c.json').read_text());t=plan['partition_types'][TYPE]
    selected=json.loads((geom/'selected_plan.json').read_text())
    require(t['hard_cores']==selected['hard_cores'],'current selected core sites differ')
    basebound=(common/(TYPE+'_bound.sv')).read_text();wrapper=(common/(TYPE+'.sv')).read_text()
    report={'status':'PRIVATE_HISTORICAL_SOURCE_PREP','qualified':False,'canonical_selected_cohort':'HOLD_UNRESOLVED','cohort':COHORT,'enabled_by_default':False,'source_event':P.EVENT_SHA256,'full_event_readset':{p.name:sha(p) for p in common.iterdir() if p.is_file()},'functional_new_cycles_beyond_ea246':0,'new_functional_FF_beyond_ea246':0,'GEN':False,'CAD':False,'parts':{}}
    for part in manifest['parts']:
        rows=[r for r in manifest['arcs'] if r['part']==part];require(len(rows)==8,'incomplete historical graph')
        ins=sorted({r['input_net'] for r in rows});require(len(ins)==4 and {r['output_net'] for r in rows}=={'ck_mesh'},'not exact five-port cut')
        d=out/part;d.mkdir();rtl=d/'rtl';rtl.mkdir()
        bound=inject_header(basebound,TYPE+'_bound',ins);bp=d/(TYPE+'_bound_INPUT.sv');bp.write_text(bound)
        pd={}
        for f in common.iterdir():
            if f.suffix not in ('.sv','.v'):continue
            for n,v in K._regex_ports(f).items():pd.setdefault(n,v)
        # Added cut ports belong to the partition, not arbitrary aliases.
        B=K.Bound(bp,pd);models=[];wrappers={};normal_head=None
        for hc in t['hard_cores']:
            raw=K.build_core(B,t,hc,native/hc['pins_file'],straps=set());text=K.emit_core(B,copy.deepcopy(raw))
            if hc['module']=='qkd_kvs_pc':m,text=P.project_model(raw,text,guard)
            else:
                require(hc['module']=='qkd_kvs_pc_h_head_p' and hc['inst']=='kvpc0','unsupported soft HEAD')
                m=copy.deepcopy(raw) # genuine raw ABI; never BASE/head face projection
            pins=json.loads((native/hc['pins_file']).read_text());arcs,names=G.island_ft_arcs(pins,*hc['outline_um']);require(len(arcs)==2 and len(names)==4,'wrong real FT producer')
            text=G.island_ft_rtl(text,hc['module'],arcs)
            own=[r for r in rows if r['child']==hc['inst']];require(len(own)==2,'missing exact child arcs')
            for a,r in zip(arcs,sorted(own,key=lambda r:r['arc_k'])):
                require(a['k']==r['arc_k'] and a['role']=='mesh_driver' and a['master']=='BUFx24_ASAP7_75t_R' and len(a['cells'])==2,'wrong historical driver role')
                require((a['source'],a['sink'])==(r['input_port'],r['output_port']),'FT source ABI differs')
                centres=[]
                for c in a['cells']:
                    x=c['x_um']+.81;y=c['y_um']+.135
                    if hc['orient']=='MY':x=hc['outline_um'][0]-x
                    else:require(hc['orient']=='R0','unsupported source orientation')
                    centres.append((hc['origin_um'][0]+hc['track_offset_um'][0]+x,hc['origin_um'][1]+hc['track_offset_um'][1]+y))
                require(all(min(abs(x-c['parent_bbox_center_um'][0])+abs(y-c['parent_bbox_center_um'][1]) for c in r['parallel_cells'])<1e-7 for x,y in centres),'real island source placement differs from historical graph')
            m=append_ft(m,own)
            actual=P.declarations(text,hc['module'])
            require({n:(v['dir'],v['hi'],v['lo']) for n,v in m['pdecl'].items()}=={n:(v['dir'],v['hi'],v['lo']) for n,v in actual.items()},'physical model/header disagreement')
            require(set(m['part_conn'])==P.bitkeys(m['pdecl']) and set(m['pin_class'])==P.bitkeys(m['pdecl']),'physical model bit inventory disagreement')
            models.append(m);wrappers[hc['inst']]=text
            if hc['inst']=='kvpc0':normal_head=(arcs,hc)
        split=K.emit_split(B,models);(rtl/(TYPE+'_bound.sv')).write_text(split)
        w=inject_header(wrapper,TYPE,ins);pat=r'(\bu_bound\s*\(\s*)';require(len(re.findall(pat,w))==1,'wrapper bound call mismatch')
        fields=''.join('        .'+n+'('+n+'),\n' for n in ins+['ck_mesh'])
        w=re.sub(pat,lambda m:m[1]+fields,w,count=1);(rtl/(TYPE+'.sv')).write_text(w)
        # Normal leaf rename follows the FULL event; no body transform repeats.
        files=[str(p) for p in common.iterdir() if p.name not in (TYPE+'.sv',TYPE+'_bound.sv')]
        renamed,ledger=K.renamed_leaf_files(files,{'qkd_kvs_pc','qkd_kvs_pc_h_head_p'},rtl)
        for f in renamed:
            p=Path(f)
            if p.parent!=rtl:shutil.copy2(p,rtl/p.name)
        require(len({K.body_key(wrappers[o]) for o in ('kvpc1','kvpc2','kvpc3')})==1,'BASE source masters differ')
        (rtl/'qkd_kvs_pc.sv').write_text(wrappers['kvpc1']);(rtl/'qkd_kvs_pc_h_head_p.sv').write_text(wrappers['kvpc0'])
        (d/'rtl.f').write_text('\n'.join(str(p.resolve()) for p in sorted(rtl.iterdir()) if p.suffix in ('.sv','.v'))+'\n')
        hook,physical,private=head_physical_hook(*normal_head[:1],rows,normal_head[1]);(d/'historical_HEAD_ft.tcl').write_text(hook)
        shutil.copy2(geom/'sram_sites_PREP.tcl',d/'sram_sites_PREP.tcl')
        cut,shapes=cut_geometry(json.loads((geom/'ft_cut_geometry.json').read_text()),part)
        require(set(shapes)==set(ins+['ck_mesh']),'geometry/source exact cut name mismatch')
        (d/'historical_cut_geometry.tcl').write_text(cut)
        bits=lambda m:len(P.bitkeys(m['pdecl']))
        record={'actual_parent_nets':ins+['ck_mesh'],'parent_wrapper_and_bound_extra_ports':5,'full_event_before_leaf_rename':True,'leaf_renames':ledger,'models':{m['hc']['inst']:{'module':m['hc']['module'],'ports':len(m['pdecl']),'bits':bits(m),'FT':[{k:r[k] for k in ('input_port','output_port','input_net','output_net')} for r in rows if r['child']==m['hc']['inst']]} for m in models},'soft_HEAD_normal_cells':physical,'soft_HEAD_private_net_allowlist':private,'actual_cut_shapes':shapes,'source_files_sha256':{p.name:sha(p) for p in rtl.iterdir() if p.is_file()},'holds':['Normal source/kit generation not run; source capsule only.','Actual BASE provisional models are PC_NOT_SIGNED; own final proof/provenance HOLD.','Physical hook exact endpoint inventory requires native post-SYNTH names before use.','Historical clock-only diagnostic; no production selection, fixed programme or source adoption.','Native M5 output to M9 external cut needs real vias/route before connection credit.']}
        (d/'SOURCE_BOUNDARY.json').write_text(json.dumps(record,indent=2)+'\n');report['parts'][part]=record
        bp.unlink()
    (out/'SOURCE_PREP.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
    a=argparse.ArgumentParser();a.add_argument('--enabled',action='store_true');a.add_argument('--cohort');a.add_argument('--native');a.add_argument('--event-dir');a.add_argument('--geom');a.add_argument('--manifest');a.add_argument('--out');x=a.parse_args()
    r=prepare(x.native,x.event_dir,x.geom,x.manifest,x.out,enabled=x.enabled,cohort=x.cohort);print(json.dumps({'status':r['status'],'qualified':r['qualified']}))
if __name__=='__main__':main()
