#!/usr/bin/env python3
"""Compare coherent whole-spine arrangements; proposals, never route proofs."""
import argparse, copy, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path
import geometry_search as pins
from placement_repack import validate


def candidates(base):
    yield 'wide27_band1_reference', copy.deepcopy(base), 'Reference: paired collectors west; VM/SU east'
    distributed=copy.deepcopy(base)
    for b in range(3):distributed[f'sp_port_tiles_{b}_f1']['x']=18809.28
    distributed['sp_port_tiles_1_f1']['y']=9499.68
    yield 'distributed_east_collectors', distributed, 'Separate east collectors; paired-slab buses become long'
    swapped=copy.deepcopy(base)
    for name,i in swapped.items():
        if name.startswith(('sp_port_tiles_','sp_band_lanes_','sp_res_ser_')):i['x']+=4838.4
        if name in ('sp_vector_memory','sp_su64_sfu','seq_su','xs_tap','tt_ctlm') or name.startswith(('cbuf_g_','crom_g_')):i['x']-=2371.68
        if name.startswith(('tt_up4_leaf','up4_sel_')):i['x']+=2538.432
        # Move the actual receiver/reset pair together, retaining its adjacency.
        if name in ('clk_rx','rstseq_rom'):i['x']-=2371.68
    yield 'paired_bands_east_vm_su_west', swapped, 'Swap whole paired-band groups and coherent VM/SU group'


def center_metric(graph,model):
    """Coarse complete current geometry graph, including hypernets; no pin claim."""
    total=0.;missing=[];count=0;families=defaultdict(float)
    for name,family,bits,ends in graph:
        if family in ('clock_trunk','reset'):continue
        if any(n not in model for n in ends):missing.append(name);continue
        points=[(model[n]['x']+model[n]['w']/2,model[n]['y']+model[n]['h']/2) for n in ends]
        span=sum(max(p[k]for p in points)-min(p[k]for p in points)for k in (0,1))
        total+=bits*span;families[family]+=bits*span;count+=1
    return dict(resolved_buses=count,missing_buses=missing,weighted_center_hpwl_bit_um=round(total,3),family_bit_um={k:round(v,3)for k,v in families.items()},qualification=False)


def figure(path,rows,die):
    width=1120;panel=350;scale=panel/die['w'];height=die['h']*scale+155
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.1f}" viewBox="0 0 {width} {height:.1f}">','<rect width="100%" height="100%" fill="white"/>','<text x="14" y="22" font-size="16">Qwen whole-spine alternatives: actual child rectangle dimensions, common scale</text>','<text x="14" y="41" font-size="11">Geometry proposals only. No route, pin-access, clock, cut, relay-stage or performance qualification.</text>']
    for index,(name,model,description)in enumerate(rows):
        ox=12+index*370;oy=82
        out.append(f'<text x="{ox}" y="65" font-size="11">{name}</text><rect x="{ox}" y="{oy}" width="{panel}" height="{die["h"]*scale}" fill="#fafafa" stroke="#222"/>')
        for n,i in model.items():
            color='#d1d8de'
            if n.startswith('sp_port_tiles_'):color='#e7a23d'
            elif n.startswith(('sp_band_lanes_','sp_res_ser_')):color='#dc754c'
            elif n in ('sp_vector_memory','sp_su64_sfu'):color='#65a9bd'
            elif n.startswith(('tt_up4_leaf','tt_ctlm','seq_su','cbuf_g_','crom_g_')):color='#9266a3'
            x=ox+i['x']*scale;y=oy+(die['h']-i['y']-i['h'])*scale
            out.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{i["w"]*scale:.3f}" height="{i["h"]*scale:.3f}" fill="{color}" stroke="white" stroke-width="0.2"><title>{n}: {i["w"]} x {i["h"]} um, {i.get("o","R0")}</title></rect>')
            if n in ('sp_vector_memory','sp_su64_sfu'):
                out.append(f'<text x="{x+2:.2f}" y="{y+10:.2f}" font-size="8">{"VM" if n=="sp_vector_memory" else "SU"}</text>')
        out.append(f'<text x="{ox}" y="{oy+die["h"]*scale+17:.2f}" font-size="9">{description}</text>')
    out.append(f'<text x="14" y="{height-15:.2f}" font-size="11">Gray: compute/DVM. Orange: paired collectors. Red: BAND/serializer. Blue: VM/SU. Purple: control/tree/store.</text></svg>')
    path.write_text('\n'.join(out)+'\n')


def main():
    a=argparse.ArgumentParser();a.add_argument('--historical',type=Path,required=True);a.add_argument('--current',type=Path,required=True);a.add_argument('--projection',type=Path,required=True);a.add_argument('--pin-dir',type=Path,action='append',required=True);a.add_argument('--out',type=Path,required=True);s=a.parse_args()
    raw,base,plans,hashes=pins.load(s.historical,s.projection,s.pin_dir,s.current)
    current=json.loads(s.current.read_text());historical_known,missing,_,oldrow=pins.analyze(raw,base,plans)
    current_by_name={b[0]:b for b in current['buses']}
    known=[b for b in historical_known if b['b'] in current_by_name and b['n']==current_by_name[b['b']][2] and sorted(e[0]for e in b['e'])==sorted(current_by_name[b['b']][3])]
    excluded=[b['b']for b in historical_known if b not in known]
    historical={b['b'] for b in raw['buses'] if b['c']not in ('clock_trunk','reset')};present={b[0]for b in current['buses']if b[1]not in ('clock_trunk','reset')}
    results=[];draw=[]
    for name,model,description in candidates(base):
        errors=validate(list(model.values()),raw['die']);_,_,_,row=pins.analyze(raw,model,plans)
        legs=[dict(row(b),delta_bit_um=round(row(b)['bit_um']-oldrow(b)['bit_um'],3))for b in known]
        results.append(dict(name=name,description=description,rectangle_errors=errors,changed_instances=[i for n,i in model.items()if i!=base[n]],known_historical_pin_bound_bit_um=round(sum(x['bit_um']for x in legs),3),worst_known_pin_bound_um=max(x['pin_bound_um']for x in legs),greatest_regressions=sorted(legs,key=lambda x:-x['delta_bit_um'])[:12],greatest_improvements=sorted(legs,key=lambda x:x['delta_bit_um'])[:12],current_geometry_center_metric=center_metric(current['buses'],model),qualification=False))
        draw.append((name,model,description))
    s.out.mkdir(parents=True,exist_ok=True)
    (s.out/'comparison.json').write_text(json.dumps(dict(schema='opentallas.qwen.system-geometry.v1',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in (s.historical,s.current,s.projection)},pin_plan_sha256=hashes,die=raw['die'],actual_rectangle_instances=len(base),historical_pin_graph_coverage=dict(resolved_current_matching=len(known),historical_resolved=len(historical_known),historical_unresolved=len(missing),excluded_changed_or_retired_resolved_bus_names=excluded,retired_bus_names=sorted(historical-present),new_current_bus_names=sorted(present-historical)),candidates=results,qualification=False,open_gates=['Canonical current production port-level bus graph, including KV/system seam','Actual leaf physical orientation/obstructions/halos','Per-bit pin routes and <=0.60 cut utilization','Real relay site population and per-pair phi-R reach','Clock delivery, TT setup, FF hold and DRC','Full static programme latency and original token-price comparison']),indent=2)+'\n')
    figure(s.out/'system_candidates.svg',draw,raw['die'])
    print(json.dumps([{k:r[k]for k in ('name','rectangle_errors','known_historical_pin_bound_bit_um','worst_known_pin_bound_um')}for r in results],indent=2))
if __name__=='__main__':main()
