import json,os,sys,time,glob,subprocess
host=sys.argv[1]
out=subprocess.run("find /srv/opentallas-scratch/claude /srv/opentallas-scratch2/claude -maxdepth 10 -name 'signoff*.json' -mmin -4320 2>/dev/null",shell=True,capture_output=True,text=True).stdout.split()
for f in out:
    try: d=json.load(open(f))
    except Exception: continue
    if not isinstance(d,dict) or 'checks' not in d: continue
    c=d.get('checks',{}); r=d.get('route') or {}
    def g(k,f2='wns_ps'):
        v=c.get(k) or {}; return v.get(f2)
    inp=d.get('inputs') or {}
    rec=dict(host=host,f=f,mtime=time.strftime('%m-%d %H:%M',time.localtime(os.path.getmtime(f))),name=d.get('name'),verdict=d.get('verdict'),
      setup=g('setup_tt'),hold=g('hold_ff'),setup_n=g('setup_tt','violators'),hold_n=g('hold_ff','violators'),
      drc=r.get('drc'),drv=(c.get('drv') or {}).get('verdict'),drvf=(c.get('drv') or {}).get('failing'),
      fg=(d.get('face_guard') or {}).get('verdict'),sdc=(d.get('sdc_lint') or {}).get('verdict'),
      clock=(c.get('clock') or {}).get('verdict'),fanout=(c.get('fanout') or {}).get('verdict'),
      reasons=d.get('reasons'),odb=inp.get('odb'),kit=inp.get('kit'),cells=((d.get('corners') or {}).get('tt') or {}).get('cells'))
    print(json.dumps(rec))
