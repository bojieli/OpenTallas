#!/usr/bin/env python3
"""Finite all-class actual FF site/clock inventory, without skeletons, RTL edits, DPL or route."""
import argparse,concurrent.futures,json,subprocess,sys
from pathlib import Path
import cb16_physical_pads as C

def one(task):
 plan,bound,inventory,out,tn,mod=map(str,task);plan,bound,inventory,out=map(Path,[plan,bound,inventory,out]);dest=out/tn;dest.mkdir(parents=True);physical=dest/'physical';physical.mkdir();raw=json.loads(plan.read_text());txt=(bound/'rtl'/(mod+'.sv')).read_text()
 try:
  banks,r=C.build(raw,tn,txt,plan.parent,include_clock_inventory=False);(physical/'banks.json').write_text(json.dumps(banks)+'\n');(physical/'report.json').write_text(json.dumps(r)+'\n')
  inv=inventory/tn/'inventory_cells.json'
  if not inv.exists():inv=inventory/tn/'inventory.json'
  args=[sys.executable,str(Path(__file__).with_name('cb16_mapped_sites.py')),str(plan),'--type',tn,'--inventory',str(inv),'--physical',str(physical),'--rtl',str(bound/'rtl'/(mod+'.sv')),'--out',str(dest/'mapped_sites')]
  native=bound/'native_internal_stations'/tn/'plan.json'
  if native.exists():args+=['--native-plan',str(native)]
  with (dest/'mapped_sites.log').open('w') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
  x=json.loads((dest/'mapped_sites/summary.json').read_text());over=[c for c in r['chains'] if c['centre_max_hop_um']>405+1e-6];result=dict(type=tn,status='CANDIDATE' if not x['missing_soft_ff'] and not over and not r['unplaced_delay_ff'] else 'FAIL',actual_soft_ff=x['actual_soft_ff'],located_ff=x['located_soft_ff'],missing_ff=x['missing_soft_ff'],unplaced_source_delay_ff=r['unplaced_delay_ff'],source_chains_over405=over,soft_clock_ports=x['clock_port_count'],max_sinks=x['max_clock_sinks'],max_radius_um=x['max_clock_radius_um'],g2='NOT_RUN; actual native hard views/provider contracts required')
 except Exception as e:result=dict(type=tn,status='FAIL',error=str(e))
 (dest/'result.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result),flush=True);return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--bound',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=4);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True);r=json.loads((a.bound/'bind_report.json').read_text());tasks=[(a.plan,a.bound,a.inventory,a.out,tn,x['module']) for tn,x in r['types'].items() if tn.startswith(('cbf_','cbn_','cbx_'))]
 with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as ex:results=list(ex.map(one,tasks))
 (a.out/'summary.json').write_text(json.dumps(results,indent=1)+'\n');print(json.dumps(dict(types=len(results),failed=sum(x['status']=='FAIL' for x in results))),flush=True)
 if any(x['status']=='FAIL' for x in results):raise SystemExit(1)
if __name__=='__main__':main()
