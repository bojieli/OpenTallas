#!/usr/bin/env python3
"""Explicit route-guide diagnostic, deduplicating eachchain/window crossing.
Revisiting a roadmap segment can inflate raw polyline crossing demand. Neither
raw nor per-chain unique guide counts establish final routed congestion.
"""
import argparse,gzip,json,math,collections,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();plan=json.loads(gzip.decompress(a.plan.read_bytes()));bins=collections.defaultdict(dict);raw=collections.Counter();nonrect=[]
for c in plan['chain_paths']:
 local=set();bits=sum(c['lanes'])
 for v,w in zip(c['path'],c['path'][1:]):
  x,y=v;X,Y=w
  if abs(x-X)<1e-6:ks=[('Y',k,math.floor(x/260)) for k in range(math.floor(min(y,Y)/260)+1,math.ceil(max(y,Y)/260))]
  elif abs(y-Y)<1e-6:ks=[('X',k,math.floor(y/260)) for k in range(math.floor(min(x,X)/260)+1,math.ceil(max(x,X)/260))]
  else:nonrect.append(dict(chain=c['chain'],source=v,target=w));continue
  for k in ks:raw[k]+=bits;local.add(k)
 for k in local:bins[k][c['chain']]=bits
cap=260*(.75/.080+.75/.064);rank=sorted(bins,key=lambda k:sum(bins[k].values()),reverse=True)
rows=[dict(axis=k[0],cut_um=k[1]*260,span_um=[k[2]*260,(k[2]+1)*260],unique_chain_bits=sum(bins[k].values()),raw_polyline_bits=raw[k],capacity=cap,unique_share=sum(bins[k].values())/cap,contributors=bins[k]) for k in rank[:30]]
r=dict(scope='EXACT_EXPORTED_CHAIN_GUIDE_DIAGNOSTIC_NOT_NATIVE_ROUTE_CUT',plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),top30=rows,excluded_nonrectilinear_segments=nonrect,over060_windows=sum(sum(v.values())/cap>.6 for v in bins.values()),limitations=['Eachchain countedonce/window to suppress ideal-waypoint backtracking inflation','ActualFFhops, pinjogs, clock/PG/reset/directnonchainbuses omitted','Guidewindow allocations can change under realrouting; no globalnecessarycut orDRCclaim','Sourceactivity/serialization separatefromphysicalbittrackdemand']);a.out.write_text(json.dumps(r,indent=1)+'\n');print(rows[0]['unique_share'],r['over060_windows'])
