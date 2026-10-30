from pathlib import Path
import re,json
R=Path('/srv/opentallas-scratch2/claude/codex-qc-kits-2249/macro_probe');res={}
for d in R.iterdir():
 p=d/'macro_dump.rtlil'
 if not p.exists():continue
 cells=[]
 for m in re.finditer(r'^  cell \\(\S+) \\(\S+)\n(.*?)^  end',p.read_text(),re.M|re.S):
  cells.append({'module':m[1],'inst':m[2],'ports':dict(re.findall(r'^    connect \\(\S+) (.*)$',m[3],re.M))})
 res[d.name]=cells
Path('/srv/opentallas-scratch2/claude/codex-qc-kits-2249/macro_exact_map.json').write_text(json.dumps(res,indent=2)+'\n')
print({k:len(v) for k,v in res.items()})
