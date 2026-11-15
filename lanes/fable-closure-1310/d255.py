import re,sys,os,subprocess,time
out=subprocess.run("find /srv/opentallas-scratch*/claude -name 5_2_route.log -mmin -1800 2>/dev/null",shell=True,capture_output=True,text=True).stdout.split()
host=os.uname().nodename
for f in out:
    try: t=open(f,errors='replace').read()
    except Exception: continue
    if 'DRT-0255' not in t: continue
    m=re.search(r'Die area:\s+\( (\d+) (\d+) \) \( (\d+) (\d+) \)',t)
    W,H=(int(m.group(3)),int(m.group(4))) if m else (0,0)
    it0=re.search(r'Number of violations = (\d+)',t)
    kit=f.split('/items/')[-1].split('/')[0] if '/items/' in f else f.split('/')[-6]
    die=f.split('/kit-wave/')[-1].split('/')[0] if '/kit-wave/' in f else '?'
    # blocks: Failed to find ... aps lines ... ERROR
    blocks=re.findall(r'Failed to find a path between pin (\S*) and source aps:\n((?:\( \d+ \d+ \d+ \) \(Idx\) / \( \d+ \d+ \) \(coords\)\n)+)extBBox[^\n]*\n\[ERROR DRT-0255\] Maze Route cannot find path of net (\S+) in worker of routeBox \( (\d+) (\d+) \) \( (\d+) (\d+) \)',t)
    for pin,aps,net,x0,y0,x1,y1 in blocks:
        x0,y0,x1,y1=map(int,(x0,y0,x1,y1))
        A=re.findall(r'\( \d+ \d+ (\d+) \) \(Idx\) / \( (\d+) (\d+) \)',aps)
        zs=sorted(set(int(a[0]) for a in A))
        onb=sum(1 for z,x,y in A if int(x) in (x0,x1) or int(y) in (y0,y1))
        edge=min(x0,y0,W-x1,H-y1)
        print("\t".join(map(str,[host,die,kit,time.strftime('%d_%H:%M',time.localtime(os.path.getmtime(f))),it0.group(1) if it0 else '-',net[:60],repr(pin),x0/1000,y0/1000,len(A),zs,'bnd' if onb==len(A) else ('cell' if onb==0 else 'mix'),edge/1000,W/1000,H/1000])))
