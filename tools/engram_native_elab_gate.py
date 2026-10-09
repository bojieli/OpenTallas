#!/usr/bin/env python3
"""Elaborate the opt-in producer/context binding inside the actual native controller."""
import argparse,hashlib,json,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
paths=[*sorted((R/'rtl/dsrom_sys/s81_ctrl').glob('*.sv')),
    *[R/'rtl/dsrom_sys/engram'/p for p in ['ot_dsrom_engram_lead_producer.sv','ot_dsrom_engram_token_map.sv','ot_dsrom_engram_idwin.sv','ot_dsrom_engram_idwin_protected.sv']],
    R/'rtl/dsrom_sys/ot_dsrom_stall_export.sv',R/'physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v']
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--protected',action='store_true');parser.add_argument('--typed',action='store_true');args=parser.parse_args()
    if args.protected:raise ValueError('OwnerV37 rejects protected flop idwin; previous experiment records are historical')
    out=R/'results/rtl'/('engram_native_typed_elab_gate_20261009.json' if args.typed else 'engram_native_elab_gate_20261009.json')
    if out.exists():raise FileExistsError(out)
    work=Path(tempfile.mkdtemp(prefix='engram-native-elab-'))
    rec=dict(schema='opentallas.engram-native-elab.v1',retained_objects=str(work),qualification='actual64user SOURCE/layer/head controller elaboration; no whole-array simulation or numerical/physical adoption claim',cases={},input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[Path(__file__)]})
    for role in [1,0,2]:
        run=subprocess.run(['verilator','--lint-only','-Wno-fatal','--top-module','ot_s81_ctrl','-GWINDOW_CONTEXT=1',f'-GTOKEN_TYPES={int(args.typed)}',f'-GSOURCE_WORD={int(args.typed)}',f'-GROLE={role}','-GMAXU=64',*[str(p) for p in paths]],capture_output=True,text=True)
        (work/f'role{role}.log').write_text(run.stdout+run.stderr)
        rec['cases'][str(role)]=dict(returncode=run.returncode,log_sha256=hashlib.sha256((run.stdout+run.stderr).encode()).hexdigest())
    rec['status']='pass' if all(v['returncode']==0 for v in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
