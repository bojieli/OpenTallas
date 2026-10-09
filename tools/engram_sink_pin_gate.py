#!/usr/bin/env python3
"""Remote full eight-slot pin queue exact/overflow-mutant gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[R/'rtl/dsrom_sys/engram/ot_dsrom_engram_rowsink.sv',R/'rtl/dsrom_sys/engram/dsfd_engram_sink.sv',R/'rtl/hdc/engram/ot_hdc_engram_e4m3_bf16.sv',R/'rtl/test/tb_dsrom_engram_sink_pin.sv']
# Locate inherited arithmetic implementation without changing it.
if not paths[2].exists():paths[2]=next(R.glob('rtl/**/ot_hdc_engram_e4m3_bf16.sv'))
out=R/'results/rtl/engram_sink_pin_gate_20261009.json'
def main():
    if out.exists():raise FileExistsError(out)
    rec=dict(schema='opentallas.engram-sink-pin-gate.v1',boundary='1536beats, eight slots, four burst sources; no physical qualification',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]},cases={})
    with tempfile.TemporaryDirectory() as tmp:
        for name,mutant in [('control',False),('overflow_reservation_removed',True)]:
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
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
