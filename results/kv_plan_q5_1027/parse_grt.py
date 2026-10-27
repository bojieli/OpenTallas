import re,sys,json,os
out={}
for d in sys.argv[1:]:
    log=open(os.path.join(d,'run.log')).read()
    t=log.split('Final congestion report:')
    lay={}
    if len(t)>1:
        for line in t[-1].splitlines():
            m=re.match(r'\s*(M[1-9])\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)',line)
            if m: lay[m[1]]=dict(res=int(m[2]),dem=int(m[3]),use=float(m[4]),max_h=int(m[5]),max_v=int(m[6]),ovf=int(m[7]))
            m=re.match(r'\s*Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)',line)
            if m: lay['Total']=dict(res=int(m[1]),dem=int(m[2]),use=float(m[3]),ovf=int(m[6]))
    its=re.findall(r"Start extra iteration (\d+)/50",log)
    it_lines=re.findall(r'\[INFO GRT-0103\] Extra Run for hard benchmark',log)
    ovf_hist=re.findall(r'\[INFO GRT-0102\] Overflow report.*?|Total overflow: (\d+)',log)
    nets=re.findall(r'Routed nets:\s+(\d+)',log)
    wl=re.findall(r'Total wirelength:\s+(\d+) um',log)
    out[os.path.basename(d.rstrip('/'))]=dict(done='OT_DONE' in log, exit=re.findall(r'OT_DOCKER_EXIT (\d+)',log), extra_iter_max=max(map(int,its)) if its else 0,
        layers=lay, nets=nets[-1:] , wl=wl[-1:], grt_err=len(re.findall(r'GRT-0113|GRT-0114|GRT-0229|ERROR',log)), maxrss=re.findall(r'Maximum resident set size \(kbytes\): (\d+)',log))
print(json.dumps(out,indent=1))
