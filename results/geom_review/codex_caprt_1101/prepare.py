from pathlib import Path
import shutil,json
src=Path('/srv/opentallas-scratch2/claude/s81ck11cap/kits/ot_s81sl_cap_rt_g2v_ck12LS')
root=Path('/srv/opentallas-scratch2/claude/codex-caprt-1101');root.mkdir(parents=True,exist_ok=True)
for name,dist,size,diam in [('A40',40,16,20),('B25',25,8,12)]:
 k=root/name
 if k.exists(): raise RuntimeError('already exists '+str(k))
 shutil.copytree(src,k,ignore=shutil.ignore_patterns('run','signoff','lec','*.log','*.csv','FAIL*','__pycache__'))
 for section in ('results','logs','reports'):
  for base in (src/'run'/section/'asap7').glob('*/base'):
   dst=k/'run'/section/'asap7'/base.parent.name/'base';dst.mkdir(parents=True,exist_ok=True)
   for p in base.iterdir():
    if p.is_file() and p.name[:1] in ('1','2','3'):
     shutil.copy2(p,dst/p.name)
 cfg=k/'config.mk'; text=cfg.read_text()
 text+='\n# CODEX caprt clock class: short, obstruction-aware CTS trunks and small leaves; no RTL or interface changes\n'
 text+=f'override export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 -obstruction_aware -distance_between_buffers {dist} -sink_clustering_size {size} -sink_clustering_max_diameter {diam}\n'
 cfg.write_text(text)
 (k/'CODEX_REVIEW.json').write_text(json.dumps({'verdict':'PASS-COND CTS-only','picture':'caprt_place.png','looked_at':'2026-11-01 05:52 PST','findings':'Central SRAM has open full-length north/south logic channels, 4.32um macro halo and aligned N/S face-flop rows; PDN and signal geometry inherited unchanged. Failure was 200-300ps clock leaf wire growth. Rebuild with 40/25um repeaters, 16/8-sink clusters, 20/12um leaf diameter, obstruction-aware tree to bound macro detours. Must inspect CTS geometry before detailed route.','added_cycles':0,'rtl_changed':False},indent=2))
 (k/'run_cts.sh').write_text('#!/bin/bash\nset -euo pipefail\nK='+str(k)+'\nbash "$K/run_kit_from_cts.sh" "$K" cts 40 8\n')
print(root)
