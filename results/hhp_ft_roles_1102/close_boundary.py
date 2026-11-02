#!/usr/bin/env python3
"""Read-only normal producer/source join. Disabled by default; rejects current mismatch."""
from pathlib import Path
import argparse,gzip,hashlib,importlib.util,json,re,sys
R=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def capture(p):
    return p.read_text() if p.is_file() else gzip.decompress(Path(str(p)+'.gz').read_bytes()).decode()
def coverage(clock_text, manifest, part):
    rows=[r for r in manifest['arcs'] if r['part']==part]
    expected=sorted(set([r['input_net'] for r in rows]+[r['output_net'] for r in rows]))
    nodes=sorted(set([r['input_driver'] for r in rows]+[c['mesh_cell'] for r in rows for c in r['parallel_cells']]))
    names=set(re.findall(r'\b[A-Za-z_]\w*\b',clock_text))
    return {'part':part,'expected_boundary_nets':expected,'missing_boundary_nets':[n for n in expected if n not in names],'expected_source_cells':nodes,'missing_source_cells':[n for n in nodes if n not in names]}
def prepare(*, enabled=False, clock_text='', manifest=None, part=''):
    if not enabled:return {'status':'DISABLED','qualified':False}
    c=coverage(clock_text,manifest,part)
    if c['missing_boundary_nets'] or c['missing_source_cells']:
        raise ValueError('CURRENT_CLOCK_GRAPH_MISMATCH: '+json.dumps(c,sort_keys=True))
    # Connectivity validation is additionally required before any implementation;
    # names alone never authorize an infrastructure rewrite.
    raise ValueError('HOLD: exact pin-level source connectivity join required; no name-only adoption')
def main():
    m=json.loads((R/'inputs/historical_ft_manifest.json').read_text());c=R/'current_clock'
    t=json.loads(capture(c/'tree.json'));old=json.loads(gzip.decompress((R/'inputs/canonical_place.json.gz').read_bytes()))
    reports=[]
    for name in ('tree_ctree.v','loaded_ctree.v'):
        text=capture(c/name);rows=[coverage(text,m,p) for p in m['parts']]
        reports.append({'file':name,'sha256':sha(text.encode()),'ck_mesh_references':len(re.findall(r'\bck_mesh\b',text)),'old_premesh_nodes':len(re.findall(r'\bckm_n10_\w+',text)),'output_taps':len(re.findall(r'\boutput\s+t_',text)),'part_cuts':rows})
        for part in m['parts']:
            try:prepare(enabled=True,clock_text=text,manifest=m,part=part)
            except ValueError as e:assert str(e).startswith('CURRENT_CLOCK_GRAPH_MISMATCH')
            else:raise AssertionError('must fail closed on actual current graph')
    nearest=[]
    sites=t['sites']
    for r in m['arcs']:
        for cell in r['parallel_cells']:
            x,y=cell['die_bbox_ll_um'];n,xy=min(sites.items(),key=lambda q:abs(q[1][0]-x)+abs(q[1][1]-y))
            nearest.append({'part':r['part'],'child':r['child'],'historical_cell':cell['mesh_cell'],'historical_origin':[x,y],'nearest_current_cell':n,'nearest_current_origin':xy,'manhattan_um':round(abs(xy[0]-x)+abs(xy[1]-y),6)})
    # Use the normal generator on a genuine HEAD model, not a BASE alias or invented cells.
    repo=Path(__file__).resolve().parents[2];h=repo/'physical/die_plan/qwen_kvsys/cores/harden';sys.path.insert(0,str(h))
    import gen_core_kit_kv as G
    p=R/'head_producer';doc=json.loads((p/'genuine_head_pins.json').read_text());raw=(p/'genuine_head_raw.sv').read_text()
    arcs,names=G.island_ft_arcs(doc,397.44,362.88);assert len(arcs)==2 and len(names)==4
    result=G.island_ft_rtl(raw,'qkd_kvs_pc_h_head_p',arcs)
    # Removing only the exact normal generated text yields the original whole module.
    st=result.index('    // KV-CORES-PV2 (12.2a1)');en=result.index('endmodule',st)
    restored=result[:st]+result[en:]
    for a in arcs:restored=restored.replace(f"input wire {a['source']},\n    output wire {a['sink']},\n    ",'',1)
    assert restored==raw
    assert result.count('BUFx24_ASAP7_75t_R mp_isl')==4
    (p/'genuine_head_NORMAL_FT_PREP.sv').write_text(result)
    (p/'normal_HEAD_island_ft_PREP.tcl').write_text(G.island_ft_tcl(arcs,'genuine_head_PREP_ONLY'))
    d={'status':'CURRENT_CLOCK_GRAPH_MISMATCH','qualified':False,'whole_boundary_applied':False,'default_off':prepare(),'current_clock_form':t['meta']['tree_form'],'current_clock_cell':t['meta']['clock_cell'],'current_taps':t['meta']['taps'],'current_physical_cells':t['meta']['site_legal']['cells'],'current_meta':t['meta'],'graphs':reports,'old_island_nearest_current_cells':nearest,'HEAD_normal_producer':{'module':'qkd_kvs_pc_h_head_p','fixture':'BEFORE_FULL_SOURCE_OVERLAY','producer':'gen_core_kit_kv.island_ft_arcs/island_ft_rtl/island_ft_tcl','producer_sha256':sha(Path(G.__file__).read_bytes()),'raw_body_exact_after_removing_only_normal_FT_text':True,'cells':4,'arcs':arcs,'source_default_changed':False,'active_implementation':False,'physical_hook_scope':'Normal Tcl is child-top: mp_isl* names and top BTerms; not a hierarchical soft-child parent hook. No fabricated prefixed variant emitted.'},'minimal_repair':'Canonical infrastructure event must either provide actual current network membership for the existing BUFx24 islands OR create a separately qualified PC/HEAD physical ABI variant removing obsolete mesh-only FT infrastructure. Neither can be inferred by renaming INV tree nodes, tying to clk/clk_tN, or treating historical m25 as current. No existing producer option maps these legacy islands into current link_htree.', 'no_CAD_or_GEN':True}
    (R/'CURRENT_BOUNDARY_JOIN.json').write_text(json.dumps(d,indent=2)+'\n');print('CURRENT_CLOCK_GRAPH_MISMATCH confirmed for both actual current netlists; genuine HEAD normal producer emits exact4cells/body unchanged, inactive PREP only')
if __name__=='__main__':main()
