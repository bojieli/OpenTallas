#!/usr/bin/env python3
"""Build an isolated, PLACE-only joined RESTJ selector-replica candidate.

Copies a source-only base kit; never copies implementation or verdict files.
Optional M4/M6 E/W pin alternation is a candidate interface, not a POR update.
"""
import argparse,hashlib,importlib.util,json,pathlib,re,shutil

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def name(p):return p['bus'] if p.get('bit') is None else f"{p['bus']}[{p['bit']}]"

def build(a):
    assert not a.out.exists(), 'choose a fresh output; preserve previous results'
    shutil.copytree(a.base,a.out)
    old=a.out/'rtl/ot_hgi_sfu_split3_ctl_rest_core.sv';text=old.read_text()
    first=re.search(r'(?m)^module ot_hgi_sfu_split3_ctl_rest\s*\(',text)
    second=re.search(r'(?m)^module ot_hgi_sfu_split3_ctl_rest_core\s*\(',text)
    assert first and second
    leaf=a.leaf.read_text();assert '__p56_ctl' in leaf
    old.write_text(text[:first.start()]+leaf+'\n'+text[second.start():])
    receipt={'generator_commit':a.commit,'input_source_commit':'08a2a79f6d93b9ee524e7a5fac8b4571c4d3837f',
             'input_leaf_sha256':hashlib.sha256(text.encode()).hexdigest(),'candidate_core_sha256':sha(old),
             'PIN_CYCLES':0,'mode':'OT_REST1C_SCALAR_OPIPE_JOINED','physical_stage':'PLACE_ONLY',
             'signed':False,'countable':False,'pin_delta':[]}
    if a.alternate_ew_m6:
        pins=json.loads((a.out/'pins.json').read_text());moves={}
        for face in ['E','W']:
            rows=sorted((p for p in pins if p.get('face')==face and p.get('layer')=='M4'
                         and p['bus'] not in {'clk','rst_n','rst_lg_n'}),key=lambda p:p['y'])
            for p in rows[1::2]:
                y=round(0.032+round((p['y']-0.032)/0.064)*0.064,6)
                moves[name(p)]={'old_layer':p['layer'],'old_y':p['y'],'layer':'M6','y':y}
                p['layer']='M6';p['y']=y
        assert moves
        (a.out/'pins.json').write_text(json.dumps(pins,indent=1)+'\n')
        doc=json.loads((a.out/'plan_pins.json').read_text())
        for p in doc['pins']:
            if name(p) in moves:p.update(layer='M6',y=moves[name(p)]['y'])
        doc['candidate_pin_delta']='M4/M6 alternating E/W, M6 pitch0.064 offset0.032; not adopted by parent'
        (a.out/'plan_pins.json').write_text(json.dumps(doc,indent=1)+'\n')
        lines=[]
        for line in (a.out/'io.tcl').read_text().splitlines():
            hit=re.match(r'place_pin -pin_name \{([^}]+)\} -layer M4 -location \{([-.0-9]+) ([-.0-9]+)\} -pin_size \{([-.0-9]+) ([-.0-9]+)\}',line)
            if hit and hit[1] in moves:
                line=f'place_pin -pin_name {{{hit[1]}}} -layer M6 -location {{{hit[2]} {moves[hit[1]]["y"]:.4f}}} -pin_size {{{hit[4]} 0.0320}}'
            lines.append(line)
        (a.out/'io.tcl').write_text('\n'.join(lines)+'\n')
        cfg=(a.out/'config.mk').read_text().replace('export MAX_ROUTING_LAYER = M5','export MAX_ROUTING_LAYER = M6')
        (a.out/'config.mk').write_text(cfg)
        spec=importlib.util.spec_from_file_location('KC',a.kit_contract);kc=importlib.util.module_from_spec(spec);spec.loader.exec_module(kc)
        f=json.loads((a.out/'freeze.json').read_text());f['pins_sha256']=sha(a.out/'plan_pins.json');f['pins_canon_sha256']=kc._canon(doc,f['outline_um'])
        f['candidate_pin_delta']='own M4/M6 prototype; parent plan unchanged; do not count'
        (a.out/'freeze.json').write_text(json.dumps(f,indent=1)+'\n')
        receipt['pin_delta']=[{'pin':n,**m}for n,m in sorted(moves.items())]
    (a.out/'DO_NOT_COUNT').write_text('Own source/geometry pilot; no POR adoption or sign-off claim.\n')
    (a.out/'HOLD_ROUTE').write_text('PLACE only; actual placed geometry must be viewed before any CTS/GRT/route.\n')
    (a.out/'candidate.json').write_text(json.dumps(receipt,indent=1)+'\n')
    print('CANDIDATE',a.out,'PIN_CYCLES0','M6_PIN_MOVES',len(receipt['pin_delta']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=pathlib.Path,required=True);p.add_argument('--leaf',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--alternate-ew-m6',action='store_true');p.add_argument('--kit-contract',type=pathlib.Path);a=p.parse_args();build(a)
