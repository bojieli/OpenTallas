#!/usr/bin/env python3
"""Exact full-shaped hist-ring successor in the established rollback campaign vehicle."""
import argparse, hashlib, json
from pathlib import Path
import mtp_rollback_bench as B

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--record',type=Path,required=True)
    ap.add_argument('--sim',default='verilator')
    args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    src=B.ROOT/'rtl/mtp/rollback/ot_mtp_hist_ring_p.sv'
    pinned_tb=B.ROOT/B.TB
    copied_tb=args.out/'tb_mtp_rollback_hist_p.sv'
    copied_tb.write_text(pinned_tb.read_text().replace('ot_mtp_hist_ring #(','ot_mtp_hist_ring_p #('))
    B.ROM_SRC=[str(src) if p.endswith('/ot_mtp_hist_ring.sv') else p for p in B.ROM_SRC]
    B.TB=str(copied_tb.resolve())
    meta=B.gen(args.out,128,24,170,1)
    rows=[B.run(args.out,'rom',None,args.sim,tag='hist_p_good'),
          B.run(args.out,'rom','rom_engram_hist_no_restore',args.sim,tag='hist_p_append_negative')]
    rec=dict(schema='opentallas.mtp_hist_pipeline_exact.v1',shape=dict(TR=16,NG=4,TW=17,PW=32,window=128),
             stimulus=meta,runs=rows,exact=all(r.get('ok') for r in rows),
             source_sha256={str(p.relative_to(B.ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [src,pinned_tb,Path(B.__file__),Path(__file__)]},
             generated_bench_sha256=hashlib.sha256(copied_tb.read_bytes()).hexdigest())
    args.record.parent.mkdir(parents=True,exist_ok=True)
    args.record.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec),flush=True)
    return 0 if rec['exact'] else 1
if __name__=='__main__': raise SystemExit(main())
