"""Add one actual clock pin to the preserved loader source collar, remotely."""
import argparse,json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    d=json.loads(Path(a.source).read_text());d['source_master']=d['master'];d['master']='hfd_loader_cx_local_reset'
    d['qualification']='standalone pathfinding; external core clock producer unbound'
    d['inst_names']=['hb_loader_cx_local_reset'];p=d['ports']['ck'];x0,y0,x1,y1=p['pins'][0][2:]
    dx=.096
    rect=['cx[0]',p['layer'],round(x0+dx,6),y0,round(x1+dx,6),y1]
    assert rect[4]<=d['w_um']
    for port in d['ports'].values():
        for pin in port['pins']:
            if pin[1]==rect[1]:
                assert min(pin[4],rect[4])<=max(pin[2],rect[2]) or min(pin[5],rect[5])<=max(pin[3],rect[3]),pin
    d['ports']['cx']=dict(bits=1,layer=p['layer'],pins=[rect],face=p['face'],dir_segments=[[0,1,'in']])
    o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
    (o/'ports.json').write_text(json.dumps(d,indent=2)+'\n')
    lines=[]
    for port in d['ports'].values():
        for name,layer,x0,y0,x1,y1 in port['pins']:
            lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{(x0+x1)/2:.6f} {(y0+y1)/2:.6f}}} -pin_size {{{x1-x0:.6f} {y1-y0:.6f}}}')
    (o/'io_place.tcl').write_text('\n'.join(lines)+'\n')
    print('PASS preserved loader pins plus one nonoverlapping actual core clock pin')
if __name__=='__main__':main()
