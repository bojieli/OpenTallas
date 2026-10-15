#!/usr/bin/env python3
"""Measure every exactly joined functional hard-leaf bit at actual master pins.
Top inputs/outputs, parent expressions and absent pins remain explicit gaps.
"""
import argparse,collections,gzip,heapq,json,pathlib

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=pathlib.Path,required=True);ap.add_argument('--packing',default='packing.json');ap.add_argument('--select',default='0,4');ap.add_argument('--output',default='reach.json');a=ap.parse_args();r=a.root;inv=json.loads((r/'inventory.json').read_text());pack=json.loads((r/a.packing).read_text());pins=json.load(gzip.open(r/'master_pins.json.gz','rt'));leaves=inv['leaves'];selected=[pack['options'][int(i)]for i in a.select.split(',')];reports=[]
 for option in selected:
  stats=collections.Counter();worst=[];families=collections.defaultdict(lambda:dict(bits=0,sum_um=0,max_um=0,over500=0));ofile=r/('reach_'+option['name']+'.jsonl.gz')
  def xy(ep):
   i,port,bit,d=ep
   if i<0:return None
   leaf=leaves[i];name=port if leaf['ports'][port]['bits']==1 else f'{port}[{bit}]';p=pins[leaf['kit']]['pins'].get(name)
   if p is None:return None
   pos=option['positions'][str(i)];return [pos[k]+p[k]for k in [0,1]]
  with gzip.open(r/'pin_producer_join.jsonl.gz','rt')as f,gzip.open(ofile,'wt')as out:
   for line in f:
    g=json.loads(line)
    if g['status']!='ONE_DRIVER':stats[g['status']]+=len(g['consumers']);continue
    d=g['drivers'][0]
    for c in g['consumers']:
     if any(e[1].startswith(('ck','s_ck','t_ck','rst','rss','s_rst','t_rst'))or e[1]=='rn'for e in [d,c]):stats['clock_reset_endpoints_excluded']+=1;continue
     if d[0]<0 or c[0]<0:stats['external_pin_home_unknown']+=1;continue
     axy,bxy=xy(d),xy(c)
     if axy is None or bxy is None:stats['physical_pin_missing']+=1;continue
     distance=sum(abs(axy[k]-bxy[k])for k in [0,1]);stats['measured_bits']+=1;stats['over500_bits']+=distance>500;stats['sum_L1_um']+=distance;stats['max_L1_um']=max(stats['max_L1_um'],distance)
     fam=leaves[d[0]]['master']+' -> '+leaves[c[0]]['master'];ff=families[fam];ff['bits']+=1;ff['sum_um']+=distance;ff['max_um']=max(ff['max_um'],distance);ff['over500']+=distance>500
     row=dict(source=d,sink=c,source_xy_um=axy,sink_xy_um=bxy,L1_um=distance)
     out.write(json.dumps(row,separators=(',',':'))+'\n');entry=(distance,stats['measured_bits'],row)
     if len(worst)<100:heapq.heappush(worst,entry)
     elif distance>worst[0][0]:heapq.heapreplace(worst,entry)
  reports.append(dict(option=option['name'],outline_um=option['outline_um'],counts=dict(stats),family_pairs=dict(sorted(families.items(),key=lambda x:-x[1]['max_um'])),worst_bits=[x[2]for x in sorted(worst,reverse=True)],all_bits_file=ofile.name,scope='Every pure-wire uniquely joined hardleaf functional bit, at actual LEF/assigned/candidate pin coordinates. Unknown parent-expression/top homes retained; no reach exception, router, timing, clock/PG/cut or static-age proof.'))
 (r/a.output).write_text(json.dumps(dict(source_commit=inv['source_commit'],reports=reports),indent=1)+'\n');print(json.dumps([{k:q[k]for k in ['option','outline_um','counts']}for q in reports],indent=1))
if __name__=='__main__':main()
