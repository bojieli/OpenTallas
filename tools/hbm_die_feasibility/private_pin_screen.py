#!/usr/bin/env python3
"""Literal private CTS Bterm screen; distances are Manhattan geometry, not measured RC."""
import argparse,hashlib,json,math
from pathlib import Path


def center(shapes):
    if len(shapes)!=1: raise ValueError('single literal signal shape required')
    layer,r=shapes[0]
    if len(r)!=4 or not all(math.isfinite(float(v)) for v in r) or r[2]<r[0] or r[3]<r[1]:
        raise ValueError('nonfinite or invalid literal pin rectangle')
    if not layer.startswith('M') or int(layer[1:])>5: raise ValueError('ungranted above-M5 signal pin')
    return layer,[(r[0]+r[2])/2,(r[1]+r[3])/2]


def screen(report,package,repo):
    demand=json.load(open(package/'physical_pin_demand.json')); pins={}; hashes={}
    for inv in demand['inventory']:
        if inv['master'] not in ['ot_hgi_hc_win_ctl','ot_hgi_hc_win_sector']:continue
        file=repo/inv['actual_pin_coordinates_file']; raw=file.read_bytes();d=json.loads(raw)
        hashes[str(file.relative_to(repo))]=hashlib.sha256(raw).hexdigest()
        pins[inv['master']]={p[0]:center(p[4]) for p in d['bterms'] if p[2]=='SIGNAL'}
    placements=report['hc_scalar_proposals']; bypath={p['source_path']:p for p in placements}; groups={}
    roots=[]
    def actual(path,pin):
        row=bypath[path]; layer,xy=pins[row['master']][pin]
        return {'source_path':path,'pin':pin,'layer':layer,'global_xy_um':[xy[0]+row['xy_um'][0],xy[1]+row['xy_um'][1]],'source_data':'private CTS floorplan Bterm, not final routed abstract'}
    for p in placements:
        prefix=p['source_path'].split('.u_ctl')[0] if p['master'].endswith('_ctl') else p['source_path'].split('.g_sector[')[0]
        groups.setdefault(prefix,[]).append(p)
        roots.append({'clock':actual(p['source_path'],'clk'),'reset':actual(p['source_path'],'rst_n'),'production_source':None,'source_clock_graph_label':p['clock'],'reset_functional_driver':p['reset_driver']})
    edges=[]
    for prefix,rows in groups.items():
        ctl=next(p for p in rows if p['master'].endswith('_ctl'))
        for sec in [p for p in rows if p['master'].endswith('_sector')]:
            index=int(sec['source_path'].split('g_sector[')[1].split(']')[0])
            pairs=[('sector_read','read_v'),('sector_live','live')]+[(f'sector_addr[{b}]',f'read_addr[{b}]') for b in range(7)]
            for a,b in pairs:
                launch=actual(ctl['source_path'],a);capture=actual(sec['source_path'],b)
                edges.append(edge(launch,capture))
            edges.append(edge(actual(sec['source_path'],'fault'),actual(ctl['source_path'],f'sector_fault[{index}]')))
    if len(edges)!=1280 or len(roots)!=160:raise ValueError('incomplete functional seam/root coverage')
    return {'schema':'opentallas.hc_private_pin_screen.v1','qualified':False,'assigned':False,'report_sha256':hashlib.sha256(json.dumps(report,sort_keys=True).encode()).hexdigest(),'input_pin_dump_sha256':hashes,'source_wrapper':'rtl/hbm_accel/generic/peers/ot_hgi_hc_win_partitioned.sv','source_commit':report['hc_source_commit'],'clock_reset_pin_associations':roots,'internal_control_edges':edges,'max_manhattan_um':max(e['manhattan_um'] for e in edges),'uncovered':['bank-to-window source endpoints','window-to-outer-ROM output targets','production root clock/reset launch ports','all final routed views and per-bit setup/hold values'],'geometry_only':True,'wire_delay_measured':False}


def edge(a,b):
    return {'launch':a,'capture':b,'manhattan_um':round(sum(abs(x-y) for x,y in zip(a['global_xy_um'],b['global_xy_um'])),6),'measured_wire_ps':None,'setup_hold_budget_proven':False}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--report',type=Path,required=True);a.add_argument('--package',type=Path,required=True);a.add_argument('--repo',type=Path,required=True);a.add_argument('--output',type=Path,required=True);args=a.parse_args()
    args.output.write_text(json.dumps(screen(json.load(open(args.report)),args.package,args.repo),indent=2)+'\n')
