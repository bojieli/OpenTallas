"""Correct four status rectangles to canonical PLANNED core IO shapes.

Actual selected endpoint abstracts are absent. This is a planning pin-access
component diagnostic only; it preserves the inherited4104FF sites and5130nets,
performs no GRT/STA, and grants no real-IP access or G2 closure.
"""
import hashlib,json,re,shutil,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
for n in ['macros.lib','probe.v','make_tracks.tcl']:shutil.copy2(base/n,out/n)
s=(base/'macros.lef').read_text();changes=[]
for master,ports,oy,by,top in [('PHY_SPB_PROBE',['st[0]','st[1]'],0.,34.56,600.48),('EP_SPB_PROBE',['sd_st[0]','sd_st[1]'],1088.64,0.,397.44)]:
 a=s.index('MACRO '+master);b=s.index('END '+master,a);body=s[a:b]
 for pin in ports:
  match=re.search(r'( PIN '+re.escape(pin)+r'\n.*?RECT )([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)( ;.*? END '+re.escape(pin)+r')',body,re.S)
  if not match:raise ValueError('missing inherited status pin')
  old=list(map(float,match.group(2,3,4,5)));x=(old[0]+old[2])/2;y=(old[1]+old[3])/2
  if master=='PHY_SPB_PROBE':new=[x-.012,by+top-.192,x+.012,by+top]
  else:new=[x-.012,0.,x+.012,.192]
  assert abs(y-(new[1]+new[3])/2)<1e-6
  newtext=match[1]+' '.join(f'{v:.6f}'for v in new)+match[6]
  body=body[:match.start()]+newtext+body[match.end():]
  changes.append(dict(master=master,pin=pin,old_rect_um=old,new_rect_um=new,origin_y_um=oy,global_center_um=[x+(103.68 if master=='PHY_SPB_PROBE'else 181.44),y+oy],authority='canonical gen_core_kit_hbm.io_tcl unsized M5 edge pin: .024 across, .192 depth; PLANNED only'))
 s=s[:a]+body+s[b:]
(out/'macros.lef').write_text(s)
t=(base/'probe.tcl').read_text();t=t[:t.index('global_route -congestion_iterations')]
t+='write_db /work/pin_access_before.odb\npin_access\nwrite_db /work/pin_access_after.odb\nputs SPB_PLANNED_STATUS_ACCESS_DONE\n';(out/'probe.tcl').write_text(t)
(out/'run.sh').write_text('''#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")"
docker run --rm --name codex-spb-access-$$ --cpus=2 --memory=8g --memory-swap=8g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null2>&1; openroad -no_init -exit /work/probe.tcl > /work/access.log2>&1'
rc=$?
echo "$rc" >access.exit
exit "$rc"
'''.replace('>/dev/null2>&1','>/dev/null 2>&1').replace('access.log2>&1','access.log 2>&1'))
(out/'pin_changes.json').write_text(json.dumps(dict(status='PLANNED_RECTANGLE_ACCESS_DIAGNOSTIC_NO_REAL_IP_ABSTRACT',changes=changes,baseline=dict(path=str(base),lef_sha256=hashlib.sha256((base/'macros.lef').read_bytes()).hexdigest(),grt_overflow=193,overflow_layer='M6',wire_um=2021045,nets=5130,flops=4104),unchanged=['all native FF sites and nets','all other pin rectangles','all fullM1-M5OBS','all signal layers/trackgrid/capacity/PHYPG placement keepout'],missing_authority=['EP plan241.92x397.44 vsattachedLEF434.72x371.52','PHY no current selected LEF;1050envelope assumption'],scope='pin_access only; no global_route/STA/PGsolve'),indent=1)+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,axs=plt.subplots(1,2,figsize=(11,5))
for ax,c in zip(axs,[changes[0],changes[2]]):
 ox=103.68 if c['master']=='PHY_SPB_PROBE'else 181.44;oy=c['origin_y_um'];cx,cy=c['global_center_um']
 for name in ['M5','M6','M4']:
  off,pitch,color=(.024,.048,'purple')if name=='M5'else(.032,.064,'orange')if name=='M6'else(.024,.048,'green')
  q=cx if name=='M5'else cy
  for k in range(round((q-off)/pitch)-4,round((q-off)/pitch)+5):
   v=off+k*pitch
   if name=='M5':ax.axvline(v,color=color,alpha=.4,linewidth=.8)
   else:ax.axhline(v,color=color,alpha=.4,linewidth=.8,linestyle='-'if name=='M6'else':')
 for key,color in [('old_rect_um','red'),('new_rect_um','blue')]:
  a,b,d,e=c[key];ax.add_patch(Rectangle((a+ox,b+oy),d-a,e-b,fill=False,color=color,linewidth=2,label=key))
 ax.set_xlim(cx-.13,cx+.13);ax.set_ylim(cy-.15,cy+.15);ax.set_title(c['master']+' '+c['pin']);ax.set_aspect('equal');ax.ticklabel_format(useOffset=False);ax.legend(fontsize=7)
fig.suptitle('Status pin access: inherited .032square versus canonical PLANNED .024x.192 M5 edge rectangle\nPurple M5 x tracks;orange M6 y;green dotted M4 y. No actual endpoint abstract qualification.');fig.tight_layout();fig.savefig(out/'status_access.png',dpi=160)
