import sys,re,gzip
from pathlib import Path
texts=[gzip.open(p,'rt').read() if p.endswith('.gz') else Path(p).read_text() for p in sys.argv[2:]]
header=texts[0][:re.search(r'\bcell\s*\(',texts[0]).start()]; cells=[]
for s in texts:
 for m in re.finditer(r'\bcell\s*\(',s):
  a=s.index('{',m.start()); depth=1;i=a+1
  while depth:
   depth+=(s[i]=='{')-(s[i]=='}');i+=1
  cells.append(s[m.start():i])
Path(sys.argv[1]).write_text(header+'\n'.join(cells)+'\n}\n')
