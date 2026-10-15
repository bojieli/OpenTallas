#!/usr/bin/env python3
"""Collect completed RX native component logs, retaining failed mutant evidence."""
import argparse, datetime, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ROW=re.compile(r'RXDIRECT job=(\d+) d=(\d+) rows=(\d+) first=(\d+) last=(\d+) issue=(\d+) first_latency=(\d+) last_latency=(\d+)')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--scratch',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 records=[]
 for m,d in enumerate(['run','m1','m2','m3']):
  src=a.scratch/d;r=json.loads((src/f'record_m{m}.json').read_text());txt=r['output'];rows=[dict(zip(['job','dut','rows','first','last','issue','first_latency','last_latency'],map(int,x)))for x in ROW.findall(txt)]
  assert len(rows)==6,(m,rows)
  for x in rows:
   assert x['rows']==[6,24,64][x['job']],x
   assert x['last']-x['first']==[5,23,31][x['job']],x
  errors=int(re.search(r'RXDIRECT mut=\d+ errors=(\d+)',txt)[1]);assert errors==[0,6,24,64][m],(m,errors)
  assert r['status']==('pass'if m==0 else'fail')
  assert 'FAULT'not in txt,txt
  r['measured']=rows;r['checked_errors']=errors;r['test_boundary_sha256']={n:sha(src/n)for n in ['inputs.hex','expected.hex','tb_rxh_direct.sv']}
  r['golden_source_sha256']={n:sha(ROOT/n)for n in ['tools/hdc_golden_v41.py','tools/hdc_golden.py','tools/s81_suhc/hc_gate.py','tools/s81_suhc/su_gate.py']}
  (a.out/f'record_m{m}.json').write_text(json.dumps(r,indent=2)+'\n');(a.out/f'run_m{m}.log').write_text(txt);records.append(r)
 rows=records[0]['measured'];delta={}
 for j,n in enumerate(['RA','RB','QR']):
  dut=next(x for x in rows if x['job']==j and x['dut']==0);ref=next(x for x in rows if x['job']==j and x['dut']==1)
  delta[n]=dict(first_output_delta_cycles=dut['first']-ref['first'],last_output_delta_cycles=dut['last']-ref['last'],rxh_first=dut['first_latency'],rxt_first=ref['first_latency'],rows=dut['rows'],output_cycles=dut['last']-dut['first']+1)
 summary=dict(schema='opentallas.s81.rxh_direct.collection.v1',generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='pass',scope='Native arithmetic RX cluster component, not full native layer/token integration.',schedule='Fixed one row/cycle RA; score+bias pair/cycle RB; two rope rows/cycle QR; no credits or ready-driven issue.',latency_definition='First/last output cycle minus first rising-edge operand sample cycle. Relative RXH-vs-RXT deltas use matching cycles.',measurements=delta,mutant_errors=[r['checked_errors']for r in records],source_commit='00185343b',collector_sha256=sha(__file__))
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
