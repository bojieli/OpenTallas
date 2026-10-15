#!/usr/bin/env python3
"""Actual frozen LEF/Liberty costs on source-identified semantic endpoints."""
import argparse,gzip,hashlib,json
from pathlib import Path
from screen_compressed_tile import xy

def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_text())
def screen(inv,pairs,bundle):
 objects=inv['children']+inv.get('banks',inv.get('data_banks',[]))+inv['reset_nodes'];by={b['inst']:b for b in objects};views=bundle['actual_views'];results=[];excluded=[]
 for r in pairs:
  (sn,sp),(tn,tp)=r['source'],r['sink'];source=by[sn];sink=by[tn];sv=views[source['master']];tv=views[sink['master']];sa=sv['TT_boundary'];ta=tv['TT_boundary'];o=sa['pins'].get(sp,{}).get('O_minus_R_ps');s=ta['pins'].get(tp,{}).get('S_plus_R_ps')
  if o is None or s is None:excluded.append(dict(group=r['group'],bit=r['bit'],source=r['source'],sink=r['sink'],reason='actual frozen Liberty endpoint arc absent/pruned; source classification required'));continue
  x=xy(source,sv['actual_LEF_pins'][sp]);y=xy(sink,tv['actual_LEF_pins'][tp]);L=sum(abs(k-l)for k,l in zip(x,y));margin=833.333-60-(150 if max(sa['R_ps'],ta['R_ps'])>300 else 90)-o-s-sa['clock_extrema_packet_ps']['launch']-ta['clock_extrema_packet_ps']['capture']-.76*L
  results.append(dict(group=r['group'],bit=r['bit'],source=r['source'],sink=r['sink'],source_master=source['master'],sink_master=sink['master'],source_xy=x,sink_xy=y,distance_um=round(L,6),margin_ps=round(margin,6)))
 worst={}
 for r in results:
  if r['group']not in worst or r['margin_ps']<worst[r['group']]['margin_ps']:worst[r['group']]=r
 return dict(screened_payload_pairs=len(results),excluded_payload_pairs=len(excluded),excluded=excluded,min_margin_ps=min(r['margin_ps']for r in results),failing_groups=[r for r in worst.values()if r['margin_ps']<15],worst_by_group=list(worst.values()),qualification=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('inventory',type=Path);p.add_argument('pairs',type=Path);p.add_argument('bundle',type=Path);p.add_argument('out',type=Path);a=p.parse_args();out=screen(read(a.inventory),read(a.pairs),read(a.bundle));out.update(schema='opentallas.qwen.semantic-tile-pin-screen.v1',input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in (a.inventory,a.pairs,a.bundle)},remaining=['Original unmatched source endpoints, parentouterpins/reset/metadata/control','Source/semantic packing equivalence and exact compiler ages','Residual core home and real parent clocks/route TTFFDRC','Complete actual die hardware fit, DVM/SU/IO/KV criticalcuts']);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ('screened_payload_pairs','excluded_payload_pairs','min_margin_ps','failing_groups')}))
if __name__=='__main__':main()
