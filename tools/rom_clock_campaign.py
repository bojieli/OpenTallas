#!/usr/bin/env python3
"""Actual independent-phase/drift RTL campaign. Digital only, no MTBF claim."""
import argparse,json,subprocess,hashlib
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bench',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();rows=[]
    cases=[]
    for phase in range(0,10000,625):
        for mode,n in [('stream',4000000),('wander',1000000),('sparse',500000),('stall',1000000),('reset',10000),('drift',10000),('stop',10000)]:cases.append((phase,mode,n))
    for phase,mode,n in cases:
        p=subprocess.run([str(a.bench),str(phase),mode,str(n)],capture_output=True,text=True)
        if p.returncode:
            row=dict(phase=phase,mode=mode,status='FAIL',stderr=p.stderr,stdout=p.stdout)
            rows.append(row);a.out.write_text(json.dumps(dict(status='FAIL',runs=rows),indent=2)+'\n');raise SystemExit(p.stderr)
        rows.append(json.loads(p.stdout))
        print(f'{phase} {mode} PASS',flush=True)
    d=dict(schema='opentallas.rom.clock.primitive.campaign.v1',status='PASS_DIGITAL_ONLY',metastability_proof=False,
      bench_sha256=hashlib.sha256(a.bench.read_bytes()).hexdigest(),runs=rows,
      accepted_words=sum(r['accepted'] for r in rows),
      steady_sparse_latency_cycles=dict(min=min(r['min_cycles'] for r in rows if r['mode']=='sparse'),max=max(r['max_cycles'] for r in rows if r['mode']=='sparse')),
      wander_sparse_not_measured=True,
      stream_words_per_cycle=dict(min=min(r['words_per_cycle'] for r in rows if r['mode']=='stream'),max=max(r['words_per_cycle'] for r in rows if r['mode']=='stream')),
      clock_stop_scope='Only the running port must deassert acceptance; stopped port can retain valid level, no acceptance edge. Restart requires reset before traffic.',
      reset_scope='Explicit flushed words tracked, both ports quiesced during reset handshake; no atomic cross-clock reset guarantee')
    a.out.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':main()
