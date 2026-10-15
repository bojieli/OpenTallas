import pathlib,json,subprocess
r=pathlib.Path('/srv/opentallas-scratch/codex/s81-hc-static-consumer-1015');o=r/'post_gate';o.mkdir(exist_ok=True)
s=json.loads((r/'post_sources.json').read_text())
with (o/'build.log').open('w') as log:
 p=subprocess.run(['verilator','--binary','--timing','-j','4','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_hc_post_tile_static','--Mdir',str(o/'obj')]+s,cwd=r,stdout=log,stderr=subprocess.STDOUT)
if p.returncode:raise SystemExit(p.returncode)
for mode in ['pass','mut']:
 with (o/(mode+'.log')).open('w') as log:
  p=subprocess.run([str(o/'obj/Vtb_s81_hc_post_tile_static')]+(['+MUT_POST'] if mode=='mut' else []),cwd=r,stdout=log,stderr=subprocess.STDOUT)
 print(mode,p.returncode,(o/(mode+'.log')).read_text(),flush=True)
 if mode=='pass' and p.returncode:raise SystemExit(p.returncode)
 if mode=='mut' and not p.returncode:raise SystemExit(1)
