#!/usr/bin/env python3
"""Provisional top-down quant lane-group contacts; not a GRT-derived grant.

Regenerate after spec/RTL adoption, then pin the resulting source commit and
renew the spec digest. Exact candidate IO is intentionally separate from specs.
"""
import argparse, ast, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
COMMIT = '7a67c23d3f2f96f1b92d714feac435d50f282811'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def integer(expr):
    node = ast.parse(expr, mode='eval').body
    def ev(n):
        if isinstance(n, ast.Constant) and type(n.value) is int: return n.value
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult)):
            a,b=ev(n.left),ev(n.right)
            return a+b if isinstance(n.op, ast.Add) else a-b if isinstance(n.op, ast.Sub) else a*b
        raise ValueError('unsupported width expression')
    return ev(node)

def widths(rtl, top):
    header = re.search(r'\bmodule\s+' + top + r'\s*\((.*?)\);', rtl, re.S)[1]
    out = {}
    for match in re.finditer(r'(?:input|output)\s+(?:wire|reg)\s*(?:\[([^:]+):([^\]]+)\])?\s*([^;]+?)(?=,\s*(?:input|output)|$)', header, re.S):
        width = integer(match[1])-integer(match[2])+1 if match[1] else 1
        for name in match[3].split(','): out[name.strip()] = width
    return out

def bits(port, width):
    return [port] if width==1 else [f'{port}[{i}]' for i in range(width)]

def positions(count, layer, height):
    # Two preferred-axis tracks between contacts; evenly distribute full face.
    offset,pitch,half = (12,48,12) if layer=='M4' else (16,64,16)
    tracks=list(range(offset+pitch*2,height-half,pitch*2))
    assert count<=len(tracks), (count,layer,len(tracks))
    return [tracks[round(i*(len(tracks)-1)/(count-1))] for i in range(count)]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--out',type=Path,default=ROOT/'physical/hbm_accel_die_views/pin_assign_1013')
    args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    rtlpath=args.source_root/'rtl/hbm_accel/generic/qw/ot_hgi_qw_lg2.sv'
    rtl=rtlpath.read_text(); manifest={'schema':'opentallas.quant_pinplan_candidate.v1','status':'PROVISIONAL_CONTRACT_NOT_GRT_DERIVED','source_commit':COMMIT,'routing_max_layer':'M5','pg_layer':'M5','guide_dependency':{'host':'ot-agidock128','run':'/srv/opentallas-scratch/claude/hbmdie-v13/grt_r25gqn_v13','observed':'live openroad PID3045759, extra iteration9/12; no guide emitted at preparation','required':'derive/review access against emitted guide and actual neighbor endpoints before final grant'},'parent_dependencies':['Die lead approved relative replica y=[21.504,189.312,357.120,524.928]um; use common absolute y-origin residue0 modulo0.192um. Cluster origin must preserve this residue.','Exclude parent M6 PG from actual contact rectangles and reserve M7 keepout above contacts.','Incorporate IO Tcl into leaf source/spec, commit, then renew source_commit and canonical physical-spec digest; candidate lists are not authorization.'],'cluster_outline_um':[777.6,691.2],'nominal_replica_y_um':[21.6+167.76*k for k in range(4)],'proposed_grid_y_um':[21.504,189.312,357.120,524.928],'placement_approval':'die lead approved 2026-10-13; mandatory source parent placement update','placement_modulo_proof_nm':{'nominal_y_mod64':[32,48,0,16],'approved_y_mod192':[0,0,0,0],'local_M4_y_mod48':12,'local_M6_y_mod64':16},'masters':{}}
    for name,external in [('qw_lgr_ref','W'),('qw_lgw_ref','E')]:
        specpath=args.source_root/'tools/ref_tile/specs_hbmfq'/f'{name}.json'; spec=json.loads(specpath.read_text()); ws=widths(rtl,spec['top'])
        allnames={p for ports in spec['pins'].values() for p in ports}; assert allnames==set(ws), (allnames,set(ws))
        w,h=[round(spec['outline'][k]*1000) for k in ('w','h')]
        rows=[]
        for face,ports in spec['pins'].items():
            if face==external:
                # Adjacent lane payload + request/credit in the contract lane order.
                laneports = [('wrr',257),('wrq',16),('wrq_cr',1)] if external=='W' else [('wwq',280),('wwq_cr',1),('wwq_done',1)]
                names=[f'{p}[{lane*n+i}]' for lane in range(8) for p,n in laneports for i in range(n)]
                assert set(names)=={b for p in ports for b in bits(p,ws[p])}
                layers=['M4' if i%2==0 else 'M6' for i in range(len(names))]
            else:
                names=[b for p in ports for b in bits(p,ws[p])]; layers=['M4']*len(names)
            coords={l:iter(positions(layers.count(l),l,h)) for l in set(layers)}
            for port,layer in zip(names,layers):
                y=next(coords[layer]); half=12 if layer=='M4' else 16; depth=192
                x=depth//2 if face=='W' else w-depth//2
                rect=[0 if face=='W' else w-depth,y-half,depth if face=='W' else w,y+half]
                rows.append({'name':port,'face':face,'layer':layer,'location_um':[x/1000,y/1000],'size_um':[depth/1000,2*half/1000],'rect_um':[v/1000 for v in rect]})
        assert len(rows)==sum(ws.values()); assert len({r['name'] for r in rows})==len(rows)
        for face in spec['pins']:
            for layer in ('M4','M6'):
                spans=sorted((r['rect_um'][1],r['rect_um'][3]) for r in rows if r['face']==face and r['layer']==layer)
                assert all(a[1]<b[0] for a,b in zip(spans,spans[1:]))
        tcl=args.out/f'{name}_io.tcl'; tcl.write_text('# PROVISIONAL contract lane plan; guides and parent track placement remain dependencies.\n# Generated by tools/hbm_quant_pinplan_1013.py; route/PG stay M5.\n'+''.join(f"place_pin -pin_name {{{r['name']}}} -layer {r['layer']} -location {{{r['location_um'][0]:.4f} {r['location_um'][1]:.4f}}} -pin_size {{{r['size_um'][0]:.4f} {r['size_um'][1]:.4f}}}\n" for r in rows))
        grants=[{'name':r['name'],'face':r['face'],'span_um':[r['rect_um'][1],r['rect_um'][3]],'max_depth_um':r['size_um'][0],'max_area_um2':round(r['size_um'][0]*r['size_um'][1],6)} for r in rows if r['layer']=='M6']
        item={'master':spec['top'],'source_spec_path':str(specpath),'source_spec_file_sha256':digest(specpath),'source_spec_canonical_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'rtl_sha256':digest(rtlpath),'outline_um':[w/1000,h/1000],'exact_io_tcl':str(tcl.relative_to(ROOT)),'io_tcl_sha256':digest(tcl),'external_face':external,'external_count':sum(r['face']==external for r in rows),'m6_candidate_count':len(grants),'external_density_per_layer_b_per_um':sum(r['face']==external for r in rows)/2/(h/1000),'m6_grant_status':'CANDIDATE_PORT_BOUNDS_ONLY_RENEW_AFTER_SOURCE_ADOPTION','m6_candidate_ports':grants,'pins':rows}
        (args.out/f'{name}_candidate.json').write_text(json.dumps(item,indent=1)+'\n'); manifest['masters'][name]={k:v for k,v in item.items() if k not in ('pins','m6_candidate_ports')}
    (args.out/'manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
    print(json.dumps({n:{k:v for k,v in d.items() if k in ('external_count','m6_candidate_count','external_density_per_layer_b_per_um')} for n,d in manifest['masters'].items()},indent=1))
if __name__=='__main__': main()
