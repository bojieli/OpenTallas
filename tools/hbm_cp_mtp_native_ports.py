#!/usr/bin/env python3
"""Fresh source-backed CPsouth native MTP collar; preserves every old pin."""
import argparse,copy,hashlib,json
from pathlib import Path
MASTER='hfd_cmdproc_s_mtp_native'
# Exact disjoint S/M5 runs, in micrometres; no historical unbound MTP envelope.
EXTRA={'f_host':(224,'input',100.032),'t_host':(5,'output',330.048),
       'f_provider':(179,'input',150.144),'f_backend':(81,'input',200.064),
       't_backend':(279,'output',240.192),'t_mtp':(179,'output',400.128),
       'f_mtp':(517,'input',450.048),'t_emit':(38,'output',600.192),
       't_provider':(43,'output',610.176),'f_emit_host':(2,'input',625.152),
       't_emit_host':(108,'output',640.128),'t_abort':(1,'output',632.064)}
def make(root,out):
    src=root/'physical/hbm_accel_die_views/cmdproc/split'
    record=copy.deepcopy(json.loads((src/'hfd_cmdproc_s/ports.json').read_text()))
    record.update(master=MASTER,note='fresh CPsouth AR+nativeMTP composite; old closed artifacts unchanged',physical_qualified=False)
    for name,(bits,direction,start) in EXTRA.items():
        pins=[[f'{name}[{b}]','M5',round(start+b*.192,6),0.,round(start+b*.192+.024,6),.192] for b in range(bits)]
        record['ports'][name]=dict(bits=bits,layer='M5',face='S',pins=pins,direction=direction,dir_segments=[[0,bits,'in' if direction=='input' else 'out']])
    flat=[(p[0],p[1],p[2:]) for port in record['ports'].values() for p in port['pins']]
    for i,(name,layer,(x0,y0,x1,y1)) in enumerate(flat):
        if not 0<=x0<x1<=record['w_um'] or not 0<=y0<y1<=record['h_um']:raise ValueError('pin bounds '+name)
        for peer,pl,(a,b,c,d) in flat[i+1:]:
            if layer==pl and max(x0,a)<min(x1,c) and max(y0,b)<min(y1,d):raise ValueError('pin collision '+name+' '+peer)
    split=json.loads((src/'split.json').read_text());south=split['bands'].pop('hfd_cmdproc_s')
    split['bands'][MASTER]=south
    split['bands']['hfd_cmdproc_n']['source_port_record']='physical/hbm_accel_die_views/cmdproc/split/hfd_cmdproc_n/ports.json'
    south['source_port_record']='physical/hbm_cp_mtp_native/collar/'+MASTER+'/ports.json'
    for name,(bits,direction,_) in EXTRA.items():
        if name in ('f_mtp','t_mtp'):south['parent_ports'].append(name)
        else:south['new_ports'][name]=dict(bits=bits,direction=direction,edge='bottom',role='actual native transaction endpoint; external producer binding required')
    for link in split['cross']:
        for key in ('from','to'):
            if link[key].startswith('hfd_cmdproc_s.'):link[key]=MASTER+link[key][len('hfd_cmdproc_s'):]
    out.mkdir(parents=True,exist_ok=False);(out/MASTER).mkdir()
    (out/MASTER/'ports.json').write_text(json.dumps(record,indent=2)+'\n')
    (out/'split.json').write_text(json.dumps(split,indent=2)+'\n')
    lines=['# Fresh native CPsouth collar; exact geometry owned by ports.json.']
    for name,layer,(x0,y0,x1,y1) in flat:
        lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{(x0+x1)/2:.6f} {(y0+y1)/2:.6f}}} -pin_size {{{x1-x0:.6f} {y1-y0:.6f}}}')
    (out/MASTER/'io_place.tcl').write_text('\n'.join(lines)+'\n')
    (out/'endpoint_obligations.json').write_text(json.dumps(dict(master=MASTER,required_endpoints={k:dict(bits=v[0],direction=v[1]) for k,v in EXTRA.items()},source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),old_closed_LEF_unchanged=True,north_unchanged=True,backend_translation_resolved=False,physical_qualified=False),indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();make(a.root,a.out)
if __name__=='__main__':main()
