import glob,re,os,time,socket,json
now=time.time();h=socket.gethostname()
for lg in glob.glob("/srv/opentallas-scratch*/claude/kw4*/runs/*/kit-wave/*/*/items/*/attempt_*/gen/*/run/logs/asap7/*/base/5_2_route.log")+glob.glob("/srv/opentallas-scratch*/claude/kw4*/runs/*/kit-wave/*/*/items/*/gen/*/run/logs/asap7/*/base/5_2_route.log"):
    try:
        if now-os.stat(lg).st_mtime>30*3600: continue
        t=open(lg,errors="ignore").read()
        if "DRT-0255" not in t: continue
        m=re.search(r"items/([^/]+)/",lg)
        aps=re.findall(r"\( (\d+) (\d+) (\d+) \) \(Idx\) / \( (\d+) (\d+) \) \(coords\)",t)
        nets=re.findall(r"cannot find path of net (\S+)",t)
        d=lg.split("/run/logs/")[0]
        pg=""
        for f in glob.glob(d+"/*.tcl")+glob.glob(d+"/config.mk"):
            try:
                c=open(f,errors="ignore").read()
                for mm in re.finditer(r"(add_pdn_stripe[^\n]*-layer\s+\{?M[67]\}?[^\n]*)",c): pg+=" | "+os.path.basename(f)+": "+mm.group(1)[:150]
            except Exception: pass
        print(h,m.group(1),"n0255",len(nets),"aps",[(a[2],a[3],a[4]) for a in aps[:4]],pg[:400])
    except Exception as e: print("ERR",lg,e)
