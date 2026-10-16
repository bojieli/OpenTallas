import json,sys
d=json.load(open(sys.argv[1])); G=50
for spec in sys.argv[2:]:
    name,rx0,ry0,rx1,ry1=spec.split(':'); rx0,ry0,rx1,ry1=map(float,(rx0,ry0,rx1,ry1))
    nx=int((rx1-rx0)/G); ny=int((ry1-ry0)/G); occ=bytearray(nx*ny)
    for n,m,a,b,c,e in d['blocks']:
        if c<rx0 or a>rx1 or e<ry0 or b>ry1: continue
        if (c-a)*(e-b)<2000: continue  # ignore tiny relays/stations
        for j in range(max(0,int((b-ry0)/G)),min(ny,int((e-ry0)/G)+1)):
            for i in range(max(0,int((a-rx0)/G)),min(nx,int((c-rx0)/G)+1)): occ[j*nx+i]=1
    A=(rx1-rx0)*(ry1-ry0)/1e6; f=sum(occ)/len(occ)
    print(f'{name}: region {rx1-rx0:.0f}x{ry1-ry0:.0f} um = {A:.1f} mm2, block-covered {f:.2f}, empty {A*(1-f):.1f} mm2')
