#!/usr/bin/env python3
"""Extract the immutable minimum production component into a NEW directory."""
from pathlib import Path
import sys,tarfile
o=Path(sys.argv[1]);o.mkdir(parents=True,exist_ok=False)
with tarfile.open(Path(__file__).with_name("sources.tar.gz")) as t:
 for m in t.getmembers():
  if not m.isfile() or Path(m.name).name!=m.name:raise ValueError(m.name)
  with t.extractfile(m) as src,open(o/m.name,"wb") as dst:dst.write(src.read())
print("cd",o,"&& bash run.sh")
