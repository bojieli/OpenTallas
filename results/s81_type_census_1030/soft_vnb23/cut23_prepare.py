from pathlib import Path
import shutil
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030')
for t in [1,3,4,5]:
 s=r/('kv_cut' if t==1 else f'kv_cut_t{t}');d=r/f'kv_cut23_t{t}'
 shutil.copytree(s,d,ignore=shutil.ignore_patterns('run','synth.log'),dirs_exist_ok=False)
 p=d/'config.mk';p.write_text(p.read_text().replace(' *ot_s81sl_vn_b',''))
 sh=(r/'cut_synth.sh').read_text().replace('k=/srv/opentallas-scratch2/claude/codex-s81types-1030/kv_cut',f'k={d}').replace('codex_s81kv_cut1030',f'codex_s81kv_cut23_t{t}_1030').replace('--cpus=8 --memory=48g --memory-swap=48g','--cpus=4 --memory=8g --memory-swap=8g').replace('NUM_CORES=8','NUM_CORES=4').replace('dp_ot_s81sl_kv_leaf__t1',f'dp_ot_s81sl_kv_leaf__t{t}')
 (d/'synth_cut23.sh').write_text(sh)
