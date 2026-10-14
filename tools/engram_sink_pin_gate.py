#!/usr/bin/env python3
"""Remote full eight-slot pin queue exact/overflow-mutant gate."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[R/'rtl/dsrom_sys/engram/ot_dsrom_engram_rowsink.sv',R/'rtl/dsrom_sys/engram/dsfd_engram_sink.sv',R/'rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv',R/'rtl/hdc/v41/ot_hdc_engram_gather.sv',R/'rtl/test/tb_dsrom_engram_sink_pin.sv']
out=R/'results/rtl/engram_sink_pin_gate_20261009.json'
def main():
    # el1013-s81-engram: --out (job-local evidence; the default is the immutable 10-09 record) and --only (closure-loop
    # benches: 'control' must PASS, 'mutant' exits 1 with 'ENGRAM_SINK_PIN_NEG FAIL as required' when the mutant is caught).
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=None);ap.add_argument('--only',choices=['control','mutant'])
    a=ap.parse_args()
    global out
    if a.out:out=a.out
    if out.exists():raise FileExistsError(out)
    rec=dict(schema='opentallas.engram-sink-pin-gate.v1',boundary='1536beats, eight slots, four burst sources; no physical qualification',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]},cases={})
    with tempfile.TemporaryDirectory() as tmp:
        for name,mutant in [('control',False),('overflow_reservation_removed',True)]:
            if a.only and (a.only=='mutant')!=mutant:continue
            text=paths[0].read_text()
            if mutant:
                assert text.count("in_ready[gs]<=({1'b0,count}+accepted_q<=2);")==1
                text=text.replace("in_ready[gs]<=({1'b0,count}+accepted_q<=2);","in_ready[gs]<=1'b1;")
            rtl=Path(tmp)/'sink.sv';rtl.write_text(text)
            exe=Path(tmp)/'sim'
            b=subprocess.run(['iverilog','-g2012','-s','tb_dsrom_engram_sink_pin','-o',str(exe),str(rtl),*[str(p) for p in paths[1:]]],capture_output=True,text=True)
            if b.returncode:raise RuntimeError(b.stderr)
            r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
            ok=(r.returncode!=0 and any(x in r.stdout for x in ['duplicate accepted beat','payload mismatch','fullshape acceptance'])) if mutant else r.returncode==0 and 'ENGRAM_SINK_PIN PASS' in r.stdout
            rec['cases'][name]=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,expected_observed=ok)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n')
    if a.only=='mutant':
        caught=rec['status']=='pass'
        print('ENGRAM_SINK_PIN_NEG FAIL as required (overflow reservation removed: caught)' if caught else 'ENGRAM_SINK_PIN_NEG mutant NOT caught');return 1 if caught else 0
    print('ENGRAM_SINK_PIN PASS' if rec['status']=='pass' else 'ENGRAM_SINK_PIN FAIL');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
