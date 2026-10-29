#!/usr/bin/env python3
"""Reproduce only approved clock_landings block-comment emission on an immutable census snapshot."""
import hashlib,json,re,shutil,sys
from pathlib import Path
src,dst=map(Path,sys.argv[1:3]);assert not dst.exists(),dst
shutil.copytree(src/'rtl',dst/'rtl');shutil.copyfile(src/'sources.f',dst/'sources.f')
doc=json.load(open(src/'sources.json'));changes=[]
pattern=re.compile(r'(?m)^(\s*input wire clk_t[0-9]+\s*)// planned physical tap: forwarded-clock export only(,?)$')
for row in doc['files']:
 f=dst/row['snapshot'];old=f.read_text();new,n=pattern.subn(r'\1/* planned physical tap: forwarded-clock export only */\2',old)
 if n:
  f.write_text(new);changes.append(dict(file=row['snapshot'],ports=n,old_sha256=hashlib.sha256(old.encode()).hexdigest(),new_sha256=hashlib.sha256(new.encode()).hexdigest()))
  # Stripping comments makes the new comma live; all port/connection tokens remain identical.
  row['sha256']=hashlib.sha256(new.encode()).hexdigest();row['bytes']=f.stat().st_size
assert changes,'No affected planned tap inputs found; refuse unrelated snapshot'
doc['syntax_successor']=dict(scope='Clock-port comment emission only, no functional connection or latency changes',source_snapshot=str(src),fix_commit='62c2ae900',changes=changes)
(dst/'sources.json').write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps(doc['syntax_successor']))
