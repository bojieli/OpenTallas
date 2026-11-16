import glob,json,os,time,re,socket
now=time.time(); h=socket.gethostname()
pats=["/srv/opentallas-scratch*/claude/kw4*/runs/*/kit-wave/*/*/items/*/attempt_*/gen/*/config.mk",
      "/srv/opentallas-scratch*/claude/kw4*/runs/*/kit-wave/*/*/items/*/gen/*/config.mk"]
seen=set()
for p in pats:
    for cf in glob.glob(p):
        d=os.path.dirname(cf)
        if d in seen: continue
        seen.add(d)
        try:
            m=re.search(r"kit-wave/([^/]+)/([^/]+)/items/([^/]+)/(?:(attempt_\d+)/)?gen",cf)
            if m.group(1)=="hbm": continue
            newest=0
            lg=glob.glob(d+"/run/logs/asap7/*/base/*.log")+glob.glob(d+"/postcts_gate_*.json")
            for x in lg:
                try: newest=max(newest,os.stat(x).st_mtime)
                except Exception: pass
            if not newest or now-newest>30*3600: continue
            tt={};ff={}
            try: tt=json.load(open(d+"/postcts_gate_tt.json"))
            except Exception: pass
            try: ff=json.load(open(d+"/postcts_gate_ff.json"))
            except Exception: pass
            c=open(cf,errors="ignore").read()
            rep=re.search(r"OT_TT_SETUP_REPAIR\s*[:?]?=\s*(\S+)",c)
            rl="";first=""
            for lgf in glob.glob(d+"/run/logs/asap7/*/base/5_2_route.log")+glob.glob(d+"/run/logs/asap7/*/base/5_2_route.tmp.log"):
                t=open(lgf,errors="ignore").read()
                v=re.findall(r"Number of violations = (\d+)",t)
                e=re.findall(r"\[ERROR ([A-Z]+-\d+)\]",t)
                it=re.findall(r"Start (\d+)\w+ optimization",t)
                mm=re.search(r"DRT-0255\] Maze Route cannot find path of net (\S+) in worker of routeBox \( (\d+) (\d+) \)",t)
                if mm: first="%s@%s,%s"%(mm.group(1)[-40:],mm.group(2),mm.group(3))
                rl="it=%s drv=%s err=%s %s"%(it[-1] if it else "", v[-1] if v else "", ",".join(sorted(set(e))), "TMP" if lgf.endswith("tmp.log") else "")
            stages=sorted(os.path.basename(x) for x in glob.glob(d+"/run/logs/asap7/*/base/*.log"))
            last=stages[-1] if stages else ""
            so=""
            try:
                s=json.load(open(d+"/signoff/signoff.json")); so=json.dumps({k:s[k] for k in list(s)[:14] if not isinstance(s[k],(dict,list))})[:260]
            except Exception: pass
            print("\t".join(str(x) for x in [h,m.group(1),m.group(2),m.group(3),m.group(4) or "",round((now-newest)/3600,1),tt.get("setup_wns_est_ps"),tt.get("hold_wns_est_ps"),ff.get("hold_wns_est_ps"),tt.get("parasitics"),rep.group(1) if rep else "-",last,rl,first,so]))
        except Exception as ex:
            print("ERR",cf,ex)
