#!/usr/bin/env python3
"""Real typedPROMPT store→source scheduler→released-map protected window gate."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from engram_token_map_image import prepare
from engram_source_prompt import commands,REV,TOK_SHA
R=Path(__file__).resolve().parents[1]
paths=[*[R/'rtl/dsrom_sys/s81_ctrl'/p for p in ['ot_s81_source_command_decode.sv','ot_s81_host_cq.sv','ot_s81_pkg_ctrl.sv','ot_s81_secded.sv']],*[R/'rtl/dsrom_sys/engram'/p for p in ['ot_dsrom_engram_lead_producer.sv','ot_dsrom_engram_token_map.sv','ot_dsrom_engram_idwin.sv','ot_dsrom_engram_idwin_protected.sv']],R/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v',R/'rtl/test/tb_dsrom_engram_dead_source.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
def main():
    out=R/'results/rtl/engram_source_word_gate_20261009.json'
    if out.exists():raise FileExistsError(out)
    work=Path(tempfile.mkdtemp(prefix='engram-dead-source-'));obj=work/'obj';images=work/'images';prepare(images);top='tb_dsrom_engram_dead_source'
    prepared=dict(revision=REV,tokenizer_sha256=TOK_SHA,tokens=[[129264 if u%5==0 else 20+u,129264,129264,60+u] for u in range(64)],token_types=[[u%4 if u%5==0 else -1,u%4,(u+1)%4,-1] for u in range(64)])
    cmdpath=work/'commands.hex';cmdpath.write_text(''.join(f'{w:016x}\n' for w in commands(prepared,gen_len=2)))
    rec=dict(schema='opentallas.engram-source-word-gate.v1',retained_objects=str(work),qualification='actual nativeSOURCE word software producer→decoder→full64-user prompt store/source scheduling; VL embedding arithmetic and system software launch separately unqualified',cases={},input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',R/'tools/engram_source_prompt.py',Path(__file__)]})
    rec['prepared_input_sha256']=hashlib.sha256(json.dumps(prepared,sort_keys=True).encode()).hexdigest();rec['commands_sha256']=hashlib.sha256(cmdpath.read_bytes()).hexdigest()
    b=subprocess.run(['verilator','--timing','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
    (work/'build.log').write_text(b.stdout+b.stderr)
    if b.returncode:
        rec.update(status='build-fail',build_error=b.stderr[-3000:]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');return 1
    for m in range(4):
        run=subprocess.run([str(obj/f'V{top}'),f'+MODE={m}',f'+OT_ROM_DIR={images}',f'+COMMANDS={cmdpath}'],capture_output=True,text=True)
        rec['cases'][str(m)]=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and ('ENGRAM_DEAD_SOURCE NEG' if m else 'ENGRAM_DEAD_SOURCE PASS') in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
