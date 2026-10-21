from pathlib import Path
import re,json,hashlib,collections
p=Path('.');s=(p/'original.v').read_text();names=sorted(set(re.findall(r'\\[^\s]+\.poison(?=\s)',s)));out=[]
for name in names:
 hits=[]
 for line in s.splitlines():
  if re.search(re.escape(name)+r'(?=\s)',line):
   kind='declaration' if re.match(r'\s*wire\s+'+re.escape(name)+r'\s*;',line) else ('assignment_LHS' if re.match(r'\s*assign\s+'+re.escape(name)+r'\s*=',line) else 'LIVE_OR_UNKNOWN_USE')
   hits.append(dict(kind=kind,line=line.strip()))
 assert len(hits)==2 and {x['kind'] for x in hits}=={'declaration','assignment_LHS'},(name,hits)
 out.append(dict(name=name,driver=hits[1]['line'] if hits[1]['kind']=='assignment_LHS' else hits[0]['line'],live_RHS_or_cell_pin_uses=0,hits=hits))
w=[x for x in (p/'map.log').read_text().splitlines() if x.startswith('Warning:')]
rec=dict(mapped_sha256=hashlib.sha256((p/'original.v').read_bytes()).hexdigest(),audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),poison_aliases=len(names),poison_live_uses=0,aliases=out,warnings=w,scope='exact escaped Verilog token connectivity, each alias appears only declaration and assign LHS; no active fanout inferred from name alone; no whole mapping semantic qualification')
Path('poison_connectivity.json').write_text(json.dumps(rec,indent=2)+'\n');print('POISON_ALIASES',len(names),'LIVE_USES',0,'WARNINGS',len(w))
