import json,re,sys
pts=[];rows=0;active=False;master=None;hidden=0;unplaced=0;unit=1000;die=None
for line in open(sys.argv[1]):
    if line.startswith('UNITS DISTANCE'):unit=int(line.split()[3])
    if line.startswith('DIEAREA'):die=[int(x)/unit for x in re.findall(r'-?\d+',line)]
    if line.startswith('ROW '):rows+=1
    if line.startswith('COMPONENTS '):active=True;continue
    if line.startswith('END COMPONENTS'):break
    if not active:continue
    m=re.match(r'^\s*-\s+(\S+)\s+(\S+)',line)
    if m:master=m.group(2)
    if not master:continue
    q=re.search(r'\+\s+(FIXED|PLACED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)',line)
    if q:
        if master.startswith(('FILLER','DECAP')):hidden+=1
        else:pts.append([int(q[2])/unit,int(q[3])/unit])
        master=None
    elif '+ UNPLACED' in line:unplaced+=1;master=None
assert len(pts)>100000
print(json.dumps(dict(source=sys.argv[1],units=unit,die=die,rows=rows,real_cells=pts,fillers_hidden=hidden,unplaced=unplaced)))
