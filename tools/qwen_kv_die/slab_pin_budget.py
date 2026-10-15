#!/usr/bin/env python3
"""Pinned Liberty costs, not physical layout/route acceptance."""
import collections,gzip,hashlib,importlib.util,json,pathlib
p=pathlib.Path.cwd();m=json.loads((p/'manifest.json').read_text());assert hashlib.sha256((p/'pinreg_audit.py').read_bytes()).hexdigest()==m['normalization_tool_sha256']
spec=importlib.util.spec_from_file_location('pinreg',p/'pinreg_audit.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
r={'scope':m['scope'],'manifest_sha256':hashlib.sha256((p/'manifest.json').read_bytes()).hexdigest(),'normalization':'pinreg_audit.pin_metrics exactly once: output first-loadpoint max rise/fall minus per-clock R; capture max setup constraints plus R. Boundary extrema addends separate.','wire_RC_qualified':False,'views':[]};detail=[]
for v in m['views']:
 for f in v['files']:assert hashlib.sha256((p/f['staged']).read_bytes()).hexdigest()==f['sha256']
 ins=json.loads((p/v['name']/'insertion.json').read_text());row={'name':v['name'],'commit':v['commit'],'view':v['view'],'corners':{}}
 for c in ['tt','ff','ss']:
  lib=a.parse_lib(p/v['name']/(v['top']+'_'+c+'.lib'));refs=a.clock_refs(lib,ins,c);assert len(refs)==1,(v['name'],c,refs)
  metrics=a.pin_metrics(lib,refs);outs=[(x['out'],n)for n,x in metrics.items()if x['out']is not None];caps=[(x['inp'],n)for n,x in metrics.items()if x['inp']is not None]
  buses=collections.defaultdict(lambda:{'bits':0,'launch_fail_bits':0,'capture_fail_bits':0,'max_launch':None,'max_capture':None})
  for n,x in metrics.items():
   b=buses[n.split('[')[0]];b['bits']+=1
   if x['out']is not None:b['max_launch']=max(b['max_launch']if b['max_launch']is not None else x['out'],x['out']);b['launch_fail_bits']+=int(x['out']>220)
   if x['inp']is not None:b['max_capture']=max(b['max_capture']if b['max_capture']is not None else x['inp'],x['inp']);b['capture_fail_bits']+=int(x['inp']>190)
  row['corners'][c]={'clock_refs':refs,'launch_bits':len(outs),'capture_bits':len(caps),'launch_fail_bits':sum(x>220 for x,n in outs),'capture_fail_bits':sum(x>190 for x,n in caps),'worst_launch':max(outs)if outs else None,'worst_capture':max(caps)if caps else None,'buses':dict(buses),'clock_boundary_addends':{n:{'launch':ref['bmax']-ref['rise'],'capture':ref['rise']-ref['bmin']}for n,ref in refs.items()}}
  detail.append({'view':v['name'],'corner':c,'pins':metrics})
 r['views'].append(row);t=row['corners']['tt'];print(v['name'],'TT launchfails',t['launch_fail_bits'],'capturefails',t['capture_fail_bits'],'worst',t['worst_launch'],t['worst_capture'],flush=True)
(p/'summary.json').write_text(json.dumps(r,indent=2)+'\n');raw=(json.dumps(detail,indent=2)+'\n').encode()
with (p/'per_pin.json.gz').open('wb')as f:
 with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as g:g.write(raw)
