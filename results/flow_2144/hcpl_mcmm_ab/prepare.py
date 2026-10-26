from pathlib import Path
import shutil
root=Path('/srv/opentallas-scratch2/claude/codex-hcpl-mcmm-2144')
for mode in ['ff','mm']:
 k=root/mode
 history=k/'inherited_history';history.mkdir(exist_ok=True)
 for name in ['signoff','views']:
  p=k/name
  if p.exists():shutil.move(str(p),str(history/name))
 for p in k.glob('postcts_gate*'):
  if p.suffix in ('.json','.log'):shutil.move(str(p),str(history/p.name))
 for base in ['results','logs','reports','objects']:
  d=k/'run'/base
  if d.exists():
   for p in d.rglob('*'):
    if p.is_file() and p.name[0:1] in ('5','6'):
     p.unlink()
 (k/'ab_mode.txt').write_text(mode+'\n')
