import sys,json,re,hashlib,subprocess
from pathlib import Path
cfg=json.load(sys.stdin); root=Path(cfg['root']); out={'die':cfg['die'],'root':str(root),'kits':[]}
rx=re.compile(r'set_(?:multicycle_path|false_path|max_delay|min_delay)|extra_sdc|sdc_extra|clock_entry_constraints|cdc_synchronizers|seam_windows|multicycle',re.I)
for item in cfg['items']:
 kit=item['view'].split('/views/')[0]; rec=dict(item,kit=kit,files=[],hits=[],missing=[])
 if cfg.get('git'):
  ref=item['ref']; names=subprocess.run(['git','-C',str(root),'ls-tree','-r','--name-only',ref,'--',kit],capture_output=True,text=True,check=True).stdout.splitlines()
  read=lambda n:subprocess.run(['git','-C',str(root),'show',ref+':'+n],capture_output=True,check=True).stdout
 else:
  names=[str(p.relative_to(root)) for p in (root/kit).rglob('*') if p.is_file()] if (root/kit).exists() else []
  read=lambda n:(root/n).read_bytes()
 extra=[]
 for n in names:
  if n.endswith('/spec.json'):
   sp=json.loads(read(n))
   for key in ['sdc_extra','boundary_tcl']:
    v=sp.get(key,[])
    extra.extend(v if isinstance(v,list) else [v])
 wanted=[n for n in names if n.endswith(('.sdc','.tcl')) or n.endswith('/spec.json') or n.endswith('/metadata.json') or n.endswith('/closure.json')]
 wanted=list(dict.fromkeys(wanted+extra))
 if not wanted:rec['missing'].append('No kit/spec/SDC found')
 for n in wanted:
  b=read(n);rec['files'].append({'path':n,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
  for i,line in enumerate(b.decode(errors='replace').splitlines(),1):
   if rx.search(line):rec['hits'].append({'path':n,'line':i,'text':line})
 out['kits'].append(rec)
print(json.dumps(out,indent=2))
