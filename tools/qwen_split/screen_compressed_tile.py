#!/usr/bin/env python3
"""Independently re-identify exact original LEF pins and screen moved endpoints."""
import argparse,collections,json,re,gzip
from pathlib import Path


def load_pins(path,w,h):
 out={}
 for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1\n',path.read_text(),re.S):
  if name in ('VDD','VSS'):continue
  rects=re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body)
  if rects:
   r=min(rects,key=lambda r:min(float(r[0]),float(r[1]),abs(w-float(r[2])),abs(h-float(r[3]))));x,y,X,Y=map(float,r);out[name]=[(x+X)/2,(y+Y)/2]
 return out

def xy(b,p):
 x,y=p
 if b.get('orient')in ('MY','R180'):x=b['w']-x
 if b.get('orient')in ('MX','R180'):y=b['h']-y
 return [round(b['x']+x,6),round(b['y']+y,6)]

def main():
 p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--pairs',type=Path,required=True);p.add_argument('--views',type=Path,required=True);p.add_argument('--parent-repo',type=Path,required=True);p.add_argument('--boundaries',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 c=json.loads(a.candidate.read_text());d=json.loads(a.inventory.read_text());old={b['inst']:b for b in d['children']+d['data_banks']+d['reset_nodes']};new={b['inst']:b for b in c['children']+c['banks']+c['reset_nodes']};pins={};refs={};point=collections.defaultdict(list)
 for b in list(old.values())+list(new.values()):
  master=b['master']
  if master not in pins:
   path=a.parent_repo/b['view']/(master+'.lef')if b.get('kind')=='child'else a.views/master/'views'/master/(master+'.lef');pins[master]=load_pins(path,b['w'],b['h']);refs[master]=str(path)
 for b in old.values():
  for name,v in pins[b['master']].items():point[tuple(xy(b,v))].append((b['inst'],name))
 costs={p.stem:json.loads(p.read_text())['corners']['tt']for p in a.boundaries.glob('*.json')}
 missing=collections.Counter();results=[];constraints=[]
 def cost(b,pin,role):
  entry=costs[b['master']];v=entry['pins'].get(pin,{}).get('O_minus_R_ps'if role=='o'else'S_plus_R_ps')
  return None if v is None else(v,entry['R_ps'],entry['clock_extrema_packet_ps']['launch'if role=='o'else'capture'])
 for z in json.loads(gzip.decompress(a.pairs.read_bytes())if a.pairs.suffix=='.gz'else a.pairs.read_text()):
  matches=[point.get(tuple(round(x,6)for x in z[k]),[])for k in ('source_xy','sink_xy')]
  if any(len(q)!=1 for q in matches):missing[z['leg']]+=1;continue
  (sn,sp),(tn,tp)=[q[0]for q in matches];source=new[sn];sink=new[tn]
  so=cost(source,sp,'o');si=cost(sink,tp,'s')
  if so is None or si is None:missing['actual_lib_pruned_or_absent_arc']+=1;continue
  x=xy(source,pins[source['master']][sp]);y=xy(sink,pins[sink['master']][tp]);L=sum(abs(k-l)for k,l in zip(x,y));budget=833.333-60-(150 if max(so[1],si[1])>300 else 90);margin=budget-so[0]-si[0]-so[2]-si[2]-.76*L
  results.append(dict(group=z['leg'],bit=z['bit'],source=[sn,sp],sink=[tn,tp],source_master=source['master'],sink_master=sink['master'],distance_um=round(L,6),margin_ps=round(margin,6)))
  constraints.append(dict(group=z['leg'],bit=z['bit'],source=[sn,sp],sink=[tn,tp],reference_source_xy=z['source_xy'],reference_sink_xy=z['sink_xy']))
 worst={}
 for z in results:
  if z['group']not in worst or z['margin_ps']<worst[z['group']]['margin_ps']:worst[z['group']]=z
 out=dict(schema='opentallas.qwen.compressed-pin-screen.v1',scope='Exact uniquely matched actual LEF pin pairs only; unresolved endpoints forbid full qualification',candidate=str(a.candidate),screened_pairs=len(results),unresolved_by_leg=dict(missing),min_margin_ps=min(z['margin_ps']for z in results),failing_groups=[z for z in worst.values()if z['margin_ps']<15],worst_by_group=list(worst.values()),qualification=False,remaining=['Unmatched original assigned-pin vs actual LEF points must be resolved without aliases','Parent external pin ABI and all reset sources/targets need newmanifest','Control/combinational delay and residual glue are unplaced','Actual full source, compiler stages, clockdelivery/route/TT/FF/DRC'])
 a.out.write_text(json.dumps(out,indent=2)+'\n');a.out.with_name('matched_payload_endpoints.json').write_text(json.dumps(constraints,separators=(',',':'))+'\n');print(json.dumps({k:out[k]for k in ('screened_pairs','min_margin_ps','failing_groups')}))
if __name__=='__main__':main()
