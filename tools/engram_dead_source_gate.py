#!/usr/bin/env python3
"""Real typedPROMPT store→source scheduler→released-map protected window gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from engram_token_map_image import prepare
R=Path(__file__).resolve().parents[1]
paths=[*[R/'rtl/dsrom_sys/s81_ctrl'/p for p in ['ot_s81_host_cq.sv','ot_s81_pkg_ctrl.sv','ot_s81_secded.sv']],*[R/'rtl/dsrom_sys/engram'/p for p in ['ot_dsrom_engram_lead_producer.sv','ot_dsrom_engram_token_map.sv','ot_dsrom_engram_idwin.sv','ot_dsrom_engram_idwin_protected.sv']],R/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v',R/'rtl/test/tb_dsrom_engram_dead_source.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
def main():
    out=R/'results/rtl/engram_dead_source_gate_20261009.json'
    if out.exists():raise FileExistsError(out)
    work=Path(tempfile.mkdtemp(prefix='engram-dead-source-'));obj=work/'obj';images=work/'images';prepare(images);top='tb_dsrom_engram_dead_source'
    rec=dict(schema='opentallas.engram-dead-source-gate.v1',retained_objects=str(work),qualification='actual full64-user prompt store and source scheduling; hostcommand software producer and VL embedding arithmetic separately unqualified',cases={},input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',Path(__file__)]})
    b=subprocess.run(['verilator','--timing','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
    (work/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:
        rec.update(status='build-fail',build_error=b.stderr[-3000:]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');return 1
    for m in range(3):
        run=subprocess.run([str(obj/f'V{top}'),f'+MODE={m}',f'+OT_ROM_DIR={images}'],capture_output=True,text=True)
        rec['cases'][str(m)]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and ('ENGRAM_DEAD_SOURCE NEG' if m else 'ENGRAM_DEAD_SOURCE PASS') in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
