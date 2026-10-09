"""Literal full native MX1 backend collar; allocation is not timing qualification."""
import argparse,hashlib,json,re
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    text=Path(a.source).read_text();h=text.split('module ot_hbm_native_mtp_operation_backend_mx1',1)[1].split(');',1)[0].split('(\n',1)[1]
    d={};direction=None;width=1
    for piece in h.split(','):
        piece=piece.strip();m=re.match(r'(input|output)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):0\]\s*)?(\w+)$',piece)
        if m:direction=m[1];width=int(m[2])+1 if m[2] else 1;name=m[3]
        else:
            assert re.fullmatch(r'\w+',piece),piece
            name=piece
        assert direction
        face='E' if name in ('sm_done','sm_fault','res_v','res_data') else 'N' if name.startswith('launch_') else 'W' if name.startswith(('cpl_','am_')) or name in ('busy','fault','st_launches','drained_ready') else 'S'
        d[name]=dict(bits=width,face=face,direction=direction)
    counts={f:0 for f in 'NSEW'};ports={};lines=[];W=120.096;H=120.96
    for name,v in d.items():
        f=v['face'];layer='M5' if f in 'NS' else 'M4';pins=[]
        for bit in range(v['bits']):
            z=.012+.096*counts[f];counts[f]+=1
            assert z+.012 <= (W if f in 'NS' else H),(name,counts)
            if f=='N':r=[z-.012,H-.192,z+.012,H]
            elif f=='S':r=[z-.012,0,z+.012,.192]
            elif f=='E':r=[W-.192,z-.012,W,z+.012]
            else:r=[0,z-.012,.192,z+.012]
            pn=name if v['bits']==1 else f'{name}[{bit}]';pins.append([pn,layer,*[round(q,6) for q in r]])
            lines.append(f'place_pin -pin_name {{{pn}}} -layer {layer} -location {{{(r[0]+r[2])/2:.6f} {(r[1]+r[3])/2:.6f}}} -pin_size {{{r[2]-r[0]:.6f} {r[3]-r[1]:.6f}}}')
        ports[name]=dict(bits=v['bits'],layer=layer,face=f,pins=pins,dir_segments=[[0,v['bits'],'in' if v['direction']=='input' else 'out']])
    record=dict(master='ot_hbm_native_mtp_operation_backend_mx1',kind='native_backend',w_um=W,h_um=H,obs_top=7,ports=ports,source_sha256=hashlib.sha256(text.encode()).hexdigest(),face_tracks=counts,qualification='geometry-only; actual clock/reset arrival and32SM transport missing')
    o=Path(a.out);o.mkdir(parents=True,exist_ok=True);(o/'ports.json').write_text(json.dumps(record,indent=2)+'\n');(o/'io_place.tcl').write_text('\n'.join(lines)+'\n');print('full functional pins',sum(counts.values()),'face counts',counts)
if __name__=='__main__':main()
