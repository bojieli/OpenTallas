#!/usr/bin/env python3
"""Fixed-calendar engine10 transport gate and deliberate tag mutant."""
import sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
import hc_gate as H
out=Path(sys.argv[1]).resolve();mut=int(sys.argv[2]) if len(sys.argv)>2 else 0
out.mkdir(parents=True,exist_ok=True);obj=out/'obj';obj.mkdir(exist_ok=True)
base=ROOT/'rtl/dsrom_sys/engram/mix'
cmd=[H.VERILATOR,'--binary','--timing','-O2','-Wno-fatal','--top-module','tb_s81_engram_dispatch','-Mdir',str(obj),'-j','2',f'-GMUT={mut}',str(base/'ot_s81_engram_mix.sv'),str(base/'ot_s81_engram_dispatch.sv'),str(base/'tb_s81_engram_dispatch.sv')]
r=subprocess.run(cmd,capture_output=True,text=True);(out/'build.log').write_text(r.stdout+r.stderr)
if r.returncode:sys.exit(r.returncode)
r=subprocess.run([str(obj/'Vtb_s81_engram_dispatch')],capture_output=True,text=True);(out/'run.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);sys.exit(r.returncode)
