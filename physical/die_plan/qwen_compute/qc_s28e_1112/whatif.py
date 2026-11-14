import json,sys
# whatif.py PLAN OUT type=W[xH][,type=...]   (outline-only growth to the right/top; content unchanged)
p=json.load(open(sys.argv[1]))
for spec in sys.argv[3].split(','):
    t,v=spec.split('=')
    o=p['partition_types'][t]['outline_um']
    if 'x' in v: w,h=v.split('x'); o[0]=float(w); o[1]=float(h)
    else: o[0]=float(v)
json.dump(p,open(sys.argv[2],'w'))
