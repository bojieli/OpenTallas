import re,sys,os,subprocess,time
out=subprocess.run("find /srv/opentallas-scratch*/claude -name 5_2_route.log -mmin -1800 2>/dev/null",shell=True,capture_output=True,text=True).stdout.split()
host=os.uname().nodename
for f in out:
    try: t=open(f,errors='replace').read()
    except Exception: continue
    if 'DRT-0255' not in t: continue
    kit=f.split('/items/')[-1].split('/')[0] if '/items/' in f else 'priv'
    die=f.split('/kit-wave/')[-1].split('/')[0] if '/kit-wave/' in f else '?'
    # find kit dir pdn.tcl
    kd=f.split('/run/logs/')[0]
    pdn=''
    try: pdn=open(kd+'/pdn.tcl').read()
    except Exception: pass
    offs={}
    for m in re.finditer(r'add_pdn_stripe .*?-layer \{(M[567])\} -width \{([\d.]+)\}(?: -spacing \{([\d.]+)\})? -pitch \{([\d.]+)\} -offset \{([\d.]+)\}',pdn):
        offs[m.group(1)]=(float(m.group(2)),float(m.group(3) or 0),float(m.group(4)),float(m.group(5)))
    m8obs=len(re.findall(r'findLayer M8',pdn)), pdn.count('dbObstruction_create')
    cfg=''
    try: cfg=open(kd+'/config.mk').read()
    except Exception: pass
    ca=re.search(r'CORE_AREA\s*=\s*([\d.]+) ([\d.]+)',cfg)
    cx,cy=(float(ca.group(1)),float(ca.group(2))) if ca else (4.32,4.32)
    mx=re.search(r'MAX_ROUTING_LAYER\s*=\s*(\S+)',cfg)
    blocks=re.findall(r'Failed to find a path between pin (\S*) and source aps:\n((?:\( \d+ \d+ \d+ \) \(Idx\) / \( \d+ \d+ \) \(coords\)\n)+)extBBox[^\n]*\n\[ERROR DRT-0255\] Maze Route cannot find path of net (\S+) in worker of routeBox \( (\d+) (\d+) \) \( (\d+) (\d+) \)',t)
    for pin,aps,net,x0,y0,x1,y1 in blocks:
        x0,y0,x1,y1=map(int,(x0,y0,x1,y1))
        for z,x,y in re.findall(r'\( \d+ \d+ (\d+) \) \(Idx\) / \( (\d+) (\d+) \)',aps):
            z=int(z);x=int(x)/1000;y=int(y)/1000
            onb=(round(x*1000) in (x0,x1)) or (round(y*1000) in (y0,y1))
            side='x' if round(x*1000) in (x0,x1) else ('y' if round(y*1000) in (y0,y1) else '-')
            ph={}
            for L,(w,s,p,o) in offs.items():
                c=(y-cy) if L=='M6' else (x-cx)
                d=(c-o)%p
                # strap1 centre at 0 (start edge?) report raw phase
                ph[L]=round(d,3)
            print("\t".join(map(str,[host,die,kit,net[:40],z,x,y,'bnd' if onb else 'cell',side,ph.get('M5'),ph.get('M6'),ph.get('M7'),round((y-0.04)/0.08%54,2),round(y%4.32,3),round(x%4.32,3),m8obs[1],mx.group(1) if mx else '?',offs.get('M5'),offs.get('M6'),offs.get('M7')])))
