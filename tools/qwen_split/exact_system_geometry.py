#!/usr/bin/env python3
"""Compare full current generated per-bit pins, preserving missing-port evidence."""
import argparse, collections, gzip, hashlib, json, math, re
from pathlib import Path
from system_geometry import candidates, figure
from placement_repack import validate


def analyze(data,model):
    pins={}
    for master,info in data['masters'].items():
        groups=collections.defaultdict(list)
        for p in info['pins']:
            name=p['name'];stem=name.split('[')[0];index=int(name.split('[')[1].split(']')[0])if'['in name else 0
            r=p['rect'];groups[stem].append((index,((r[0]+r[2])/2,(r[1]+r[3])/2)))
        pins[master]={k:[p for _,p in sorted(v)]for k,v in groups.items()}
    def physical(n,p):
        i=model[n];points=[]
        for x,y in pins[i['m']].get(p,[]):
            if i.get('o','R0') in ('MY','R180'):x=i['w']-x
            if i.get('o','R0') in ('MX','R180'):y=i['h']-y
            points.append((i['x']+x,i['y']+y))
        return points
    known=[];missing=[]
    for b in data['buses']:
        if b['c']in ('clock_trunk','reset'):continue
        ends=[physical(n,p)for n,p in b['e']]
        if any(len(e)!=b['n']for e in ends):
            missing.append(dict(bus=b['b'],endpoints=[dict(instance=n,port=p,generated_pins=len(e),bus_bits=b['n'])for (n,p),e in zip(b['e'],ends)if len(e)!=b['n']]));continue
        hpwl=0.;longest=0.
        for bit in range(b['n']):
            xy=[e[bit]for e in ends];hpwl+=sum(max(p[k]for p in xy)-min(p[k]for p in xy)for k in (0,1))
            longest=max(longest,max(x+y for x,y in xy)-min(x+y for x,y in xy),max(x-y for x,y in xy)-min(x-y for x,y in xy))
        known.append(dict(bus=b['b'],family=b['c'],bits=b['n'],endpoints=b['e'],per_bit_hpwl_sum_um=round(hpwl,3),max_manhattan_pin_pair_um=round(longest,3)))
    return known,missing


def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    raw=gzip.decompress(a.input.read_bytes())if a.input.suffix=='.gz'else a.input.read_bytes();d=json.loads(raw);base={i['n']:i for i in d['insts']};rows=[];draw=[];old={}
    for name,model,description in candidates(base):
        known,missing=analyze(d,model)
        if not old:old={x['bus']:x for x in known}
        for x in known:x['delta_bit_um']=round(x['per_bit_hpwl_sum_um']-old[x['bus']]['per_bit_hpwl_sum_um'],3)
        rows.append(dict(name=name,description=description,rectangle_errors=validate(list(model.values()),d['die']),changed_instances=[i for n,i in model.items()if i!=base[n]],resolved_data_buses=len(known),missing=missing,per_bit_hpwl_sum_um=round(sum(x['per_bit_hpwl_sum_um']for x in known),3),worst_pin_pair_um=max(x['max_manhattan_pin_pair_um']for x in known),longest_buses=sorted(known,key=lambda x:-x['max_manhattan_pin_pair_um'])[:15],greatest_regressions=sorted(known,key=lambda x:-x['delta_bit_um'])[:12],greatest_improvements=sorted(known,key=lambda x:x['delta_bit_um'])[:12],qualification=False))
        draw.append((name,model,description))
    out=dict(schema='opentallas.qwen.current-system-pin-geometry.v1',input_sha256=hashlib.sha256(raw).hexdigest(),source_commit=d['source_commit'],source_sha256=d['source_sha256'],coverage=dict(instances=len(base),generated_local_pin_rects=sum(len(m['pins'])for m in d['masters'].values()),total_data_buses=sum(b['c']not in ('clock_trunk','reset')for b in d['buses'])),candidates=rows,qualifications=['Current generated assignment-pin geometry, not routed physical qualification.','Per-bit pin-center HPWL supports fanout but is not an allocated physical route.','Missing ctlm ports are preserved and prohibit full-system qualification.','Actual master pin/obstruction/halo/orientation admission, clocks phi-R, <=0.60 cuts, relay placement, TT/FF/DRC and static cycles remain open.','Current model still carries legacy IO topology; native static IO and full KV/system seam binding remain open.'],qualification=False)
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'current_pin_comparison.json').write_text(json.dumps(out,indent=2)+'\n');figure(a.out/'current_system_candidates.svg',draw,d['die'])
    print(json.dumps([{k:r[k]for k in ('name','rectangle_errors','resolved_data_buses','per_bit_hpwl_sum_um','worst_pin_pair_um')}for r in rows],indent=2))
if __name__=='__main__':main()
