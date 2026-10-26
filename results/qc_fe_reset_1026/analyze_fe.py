import sys,re,json,collections
from pathlib import Path
root=Path(sys.argv[1]);out={}
for typ in ('sle_fe_v1','sle_fe_v2','sle_fe_v3'):
 f=root/f'conn_{typ}.tsv'
 if not f.exists():out[typ]={'status':'NOT BUILT'};continue
 info={};drv=collections.defaultdict(list)
 for l in f.read_text().splitlines():
  n,m,x,y,ins,outs=l.split('\t');n=n.replace('\\','').replace('/','.');info[n]=dict(ref=m,xy=[float(x),float(y)],ins=ins.split(),outs=outs.split())
  for net in outs.split():drv[net].append(n)
 seq=lambda n: info[n]['ref'].startswith('DFF') or info[n]['ref']=='PORT' or 'SRAM' in info[n]['ref'] or 'ROM' in info[n]['ref']
 scopes=[]
 for n,v in info.items():
  m=re.match(r'(.*)\.u_rl\.rs1(?:\[0\])?\$_',n)
  if not m or not v['ref'].startswith('DFF'):continue
  p=m[1];groups={}
  for group,expr in [('agu',r'\.agu_q\[[0-9]\]'),('chu',r'\.chu_q\[(?:547|1094)\]'),('cmd',r'\.cmd_o\[0\]')]:
   targets=[k for k in info if info[k]['ref'].startswith('DFF') and re.match(re.escape(p)+expr+r'\$_',k)]
   groups[group]=dict(cells=targets,count=len(targets),centroid=([sum(info[k]['xy'][i] for k in targets)/len(targets) for i in (0,1)] if targets else None))
  if not any(v['count'] for v in groups.values()):continue
  todo=list(v['ins']);seen=set();roots=set()
  while todo:
   net=todo.pop()
   if net in seen:continue
   seen.add(net)
   for d in drv.get(net,[]):
    if seq(d):roots.add(d)
    elif not info[d]['ref'].startswith(('TIE','LOGIC')):todo.extend(info[d]['ins'])
  scopes.append(dict(prefix=p,rs1=n,rs1_xy=v['xy'],root_drivers=[dict(name=k,**info[k]) for k in sorted(roots)],groups=groups))
 out[typ]=dict(status='ACTUAL READ-ONLY SNAPSHOT',cells=len(info),FUP_scopes=scopes)
out['slw_fe_v2']=dict(status='NOT BUILT: no actual3_place/4_cts in known kits-wave/kits-wave2; prior kit failed anchor origin',sites=None)
print(json.dumps(out,indent=2));(root/'FUP_reset_groups.json').write_text(json.dumps(out,indent=2)+'\n')
