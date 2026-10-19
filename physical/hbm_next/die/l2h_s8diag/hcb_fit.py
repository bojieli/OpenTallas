import json,sys
m=json.load(open(sys.argv[1])); pl=m["placement"]; W,H=m["die_um"]
P=json.load(open(sys.argv[2]))
def hits(x0,y0,x1,y1, skip=('rf','hcb_','hcx_','hc_eng')):
    return [(k,round(v["x"]),round(v["y"]),round(v["w"]),round(v["h"])) for k,v in pl.items() if not k.startswith(skip) and v["x"]<x1 and v["x"]+v["w"]>x0 and v["y"]<y1 and v["y"]+v["h"]>y0]
pitch=572.4
for q in ('SW','SE','NW','NE'):
    b=P['hce_'+q]; cx=b['x']+b['w']/2; cy=b['y']+b['h']/2
    print(q,'hce',b, 'hits_in_hce', hits(b['x'],b['y'],b['x']+b['w'],b['y']+b['h']))
    for name,(w,h) in (('2x4v',(2*pitch,4*pitch)),('4x2h',(4*pitch,2*pitch))):
        x0=cx-w/2; y0=cy-h/2
        print('  ',name,(round(x0),round(y0),round(w),round(h)), hits(x0,y0,x0+w,y0+h))
