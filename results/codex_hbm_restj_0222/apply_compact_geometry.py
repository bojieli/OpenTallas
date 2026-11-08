#!/usr/bin/env python3
"""Apply reviewed compact B geometry to a fresh own source candidate, never the POR."""
import argparse,hashlib,importlib.util,json,pathlib,re

def sibling(name):
    path=pathlib.Path(__file__).with_name(name+'.py');spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def apply(root):
    assert (root/'candidate.json').is_file() and (root/'DO_NOT_COUNT').is_file()
    assert not (root/'run').exists(),'only a fresh source kit, never a live candidate'
    shape=sibling('compact_geometry');base=sibling('build_form');pins,report=shape.make(json.loads((root/'pins.json').read_text()))
    assert report['geometry_verdict']=='FEASIBLE'
    w,h=report['outline_um'];byname={base.name(p):p for p in pins};doc=json.loads((root/'plan_pins.json').read_text());io=['# Own compact candidate: edge points projected inward0.096um; no POR adoption.']
    widths={'M3':.018,'M4':.024,'M5':.024,'M6':.032}
    for p in doc['pins']:
        q=byname[base.name(p)];x,y=q['x'],q['y'];face=q['face'];layer=q['layer']
        if face in ('E','W'):x+=(.096 if face=='W'else-.096);pw,ph=.192,widths[layer]
        elif face in ('N','S'):y+=(.096 if face=='S'else-.096);pw,ph=widths[layer],.192
        else:pw,ph=q.get('w',.048),q.get('h',.48)
        p.update(x=round(x,6),y=round(y,6),layer=layer)
        for key,value in [('w',pw),('width',pw),('h',ph),('height',ph)]:
            if key in p:p[key]=value
        io.append(f"place_pin -pin_name {{{base.name(p)}}} -layer {layer} -location {{{x:.6f} {y:.6f}}} -pin_size {{{pw:.6f} {ph:.6f}}}")
    doc['candidate_geometry']='181.44x267.84 local-chain/shallow-round B; reviewed model, parent plan unchanged'
    (root/'pins.json').write_text(json.dumps(pins,indent=1)+'\n');(root/'plan_pins.json').write_text(json.dumps(doc,indent=1)+'\n');(root/'io.tcl').write_text('\n'.join(io)+'\n')
    cfg=(root/'config.mk').read_text();cfg=re.sub(r'(?m)^export DIE_AREA =.*',f'export DIE_AREA = 0 0 {w} {h}',cfg);cfg=re.sub(r'(?m)^export CORE_AREA =.*',f'export CORE_AREA = 4.32 4.32 {w-4.32:.2f} {h-4.32:.2f}',cfg);cfg=cfg.replace('export MAX_ROUTING_LAYER = M5','export MAX_ROUTING_LAYER = M6');(root/'config.mk').write_text(cfg)
    freeze=json.loads((root/'freeze.json').read_text());freeze['outline_um']=[w,h];freeze['pins_sha256']=base.sha(root/'plan_pins.json');freeze['pins_canon_sha256']=base.pins_hash(doc,[w,h]);freeze['candidate_geometry']=doc['candidate_geometry'];freeze['clock_entry_source']={'kind':'candidate_model','xy_um':report['clock_xy_um'],'parent_embedding_offset_um':report['clock_anchor_origin_delta_um'],'previous_actual_clock_um':[216.024,224.64],'parent_POR':'UNCHANGED'};(root/'freeze.json').write_text(json.dumps(freeze,indent=1)+'\n')
    receipt=json.loads((root/'candidate.json').read_text());receipt['compact_geometry']=report;receipt['mechanisms']=['full32-bit same-cycle shallow rounding','bounded registered selector and upstreamio copies','bounded reset relay and upstream sync copies'];receipt['boundary_obligations']=['io_word port drives copied io_r FF D pins','rst_n port drives copied sync and relay asyncreset pins; physical locality requires actual placement review'];receipt['routed_kit_lec']='NOT_RUN';(root/'candidate.json').write_text(json.dumps(receipt,indent=1)+'\n');(root/'compact_geometry.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kit',type=pathlib.Path);apply(p.parse_args().kit)
