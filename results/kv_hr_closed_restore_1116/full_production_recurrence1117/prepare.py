#!/usr/bin/env python3
from pathlib import Path
import shutil,sys,tarfile
here=Path(__file__).resolve().parent
o=Path(sys.argv[1]);o.mkdir(parents=True,exist_ok=False)
with tarfile.open(here.parent/'full_production_1116/sources.tar.gz') as t:
 for m in t.getmembers():
  if not m.isfile() or Path(m.name).name!=m.name:raise ValueError(m.name)
  with t.extractfile(m) as src,open(o/m.name,'wb') as dst:dst.write(src.read())
shutil.copy2(here/'tb_full.sv',o/'tb_full.sv')
print('cd',o,'&& bash run.sh')
