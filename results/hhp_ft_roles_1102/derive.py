#!/usr/bin/env python3
"""Read-only exact historical die-mesh role recovery; no model/source mutation."""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
I=ROOT/'inputs'
sha=lambda b:hashlib.sha256(b).hexdigest()
load=lambda n:json.loads((I/n).read_text())
unzip=lambda n:json.loads(gzip.decompress((I/n).read_bytes()))
def require(ok,msg):
    if not ok:raise ValueError(msg)

def derive():
    manifest=load('historical_ft_manifest.json');plan=load('current_selected_plan.json');pins=load('current_r27_pins.json')
    mesh=unzip('canonical_mesh.json.gz');sites=unzip('canonical_sites.json.gz');placed=unzip('canonical_place.json.gz')
    require(sha(gzip.decompress((I/'canonical_sites.json.gz').read_bytes()))==manifest['mesh_sites_sha256'],'canonical sites hash differs')
    require(plan['type']=='kv3_pc__cl5a95b461','wrong current type')
    require('ft_ck_' not in (I/'current_bound.sv').read_text() and 'ck_mesh' not in (I/'current_bound.sv').read_text(),'raw source already contains FT graph')
    hcs={x['inst']:x for x in plan['hard_cores']};arcs=pins['island_ft']['arcs'];out=[]
    require(len(arcs)==2 and all(a['role']=='mesh_driver' and a['cells']==2 and a['kind']=='clock' and a['master']=='BUFx24_ASAP7_75t_R' for a in arcs),'wrong actual FT contract')
    for part in manifest['parts']:
        rows=[r for r in manifest['arcs'] if r['part']==part];require(len(rows)==8,'incomplete four-PC mapping')
        for r in rows:
            drv=mesh['drivers'][r['mesh_driver_id']]
            require(sorted(drv['cells'])==sorted(r['driver_pair']),'driver pair mismatch')
            require(r['output_net']=='ck_mesh' and r['output_strap']=='M9','not actual mesh output')
            # rec_lg emits a node output, followed by two wire-only legs to this driver.
            tag=r['input_ancestry_leaf_tag'];path=sorted([e for e in mesh['htree'] if tag.startswith(e['tag'])],key=lambda e:e['level'])
            nodes=[e['node'] for e in path if e.get('node')]
            require(nodes[-1]==r['input_driver'] and r['input_net']=='ckm_w_'+nodes[-1],'wrong real pre-mesh source')
            require(all(not e.get('node') and not e['reps'] for e in path if e['level']>10),'post-node topology changed')
            for cell in r['parallel_cells']:
                n=cell['mesh_cell'];require(sites['pushdown_cells'][n]==part+'/'+r['child'],'wrong pushdown owner')
                require([placed[n]['x'],placed[n]['y']]==cell['die_bbox_ll_um'],'canonical cell placement differs')
            if r['module']!='qkd_kvs_pc':continue # genuine HEAD remains separately held
            h=hcs[r['child']];require(h['module']=='qkd_kvs_pc' and r['child'] in ('kvpc1','kvpc2','kvpc3'),'wrong BASE owner')
            a=arcs[r['arc_k']];require((a['source'],a['sink'])==(r['input_port'],r['output_port']),'physical ABI arc mismatch')
            # Match BOTH native fixed cell centres through actual current R0/MY site.
            x0,y0=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);w,_=h['outline_um']
            rect=a['rect_um'];expected=[]
            for j in range(2):
                x=rect[0]+1.62*(j+.5);y=(rect[1]+rect[3])/2
                if h['orient']=='MY':x=w-x
                else:require(h['orient']=='R0','unsupported core orient')
                expected.append((x0+dx+x,y0+dy+y))
            actual=[tuple(c['parent_bbox_center_um']) for c in r['parallel_cells']]
            require(all(min(abs(x-a)+abs(y-b) for a,b in actual)<1e-7 for x,y in expected),'current core sites differ from recovered mapping')
            additions=[]
            for port,direction,net,cls in ((r['input_port'],'input',r['input_net'],'in'),(r['output_port'],'output','ck_mesh','out')):
                additions.append({'key':[port,None],'pdecl':{'dir':direction,'hi':None,'lo':None,'gaps':[]},'part_conn':[net,0],'pin_class':cls})
            out.append({'part':part,'owner':r['child'],'role':'die_owned_mesh_driver','arc':r['arc_k'],'parallel_cells':r['parallel_cells'],'actual_input_driver':r['input_driver'],'actual_input_net':r['input_net'],'actual_output_net':'ck_mesh','proposed_metadata_additions':additions})
    require(len(out)==12,'BASE expected12 arcs across EN/WN')
    boundary=[]
    for part in manifest['parts']:
        rows=[r for r in manifest['arcs'] if r['part']==part]
        ins=sorted(set(r['input_net'] for r in rows));require(len(ins)==4,'wrong four-PC pre-mesh cut')
        boundary.append({'part':part,'required_actual_input_nets':ins,'required_actual_output_net':'ck_mesh','already_in_raw_parent':False,'head_arcs_required_but_not_projected':2,'soft_head_does_not_supply_hardened_FT_cells':True})
    return {'status':'PREP_NOT_ADOPTED','qualified':False,'canonical_adoption':False,'models_mutated':False,'new_CAD':False,'new_aliases':False,'new_FF':0,'added_functional_cycles':0,'source_authority':'12.2a1/CLOCK-KV-R25 exact recovered canonical graph; prior root diagnostic extrusion approval only','scope':'exact current selected sites; BASE only; before-full source graph boundary fixture','interface_additions':out,'parent_boundary_requirements':boundary,'hold':['Raw parent lacks all four real pre-mesh input nets and ck_mesh output; M changes alone produce undeclared/dangling nets.','Normal copied parent/wrapper input closure must expose the exact approved die-network cut, preserving multidriver ck_mesh semantics and all other mesh drivers.','Genuine soft HEAD has no physical FT cells or qualified hard view; its two mesh-driver arcs are not supplied by three BASE projections.','No core ck/clk_tN fallback, fclk ring substitution, source adoption, programme join, STA/PG/routing or parent qualification.'],'input_sha256':{p.name:sha(p.read_bytes()) for p in sorted(I.iterdir())}}
if __name__=='__main__':
    d=derive();(ROOT/'FT_ROLE_PREP.json').write_text(json.dumps(d,indent=2)+'\n');print('PASS:12 actual BASE arcs /24 exact port additions over EN/WN, current sites match; canonical source adoption remains HOLD')
