import pathlib,subprocess,re,json,hashlib,sys
repo=sys.argv[1];rev='4d6f5439dcee43b97baffaa731aae826fdcb6a66'
def get(p,r=rev):return subprocess.check_output(['git','-C',repo,'show',r+':'+p])
out=pathlib.Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
script=get('rtl/hbm_next/sm/halves/hnx_rp3lp3x_halves_bench.sh').decode();files=re.search(r'SRCS="([^"]+)"',script).group(1).split()
manifest={}
for f in files:
 b=get(f)
 if f=='rtl/hbm_next/sm/hnx_rp4lp4_leaf.sv':
  fixed=get('physical/die_plan/hbm_arch_cores/rtl/hnx_rp4lp4_leaf_selfcontained.sv','4673cf757e');assert fixed.endswith(b);b=fixed
 if f.endswith('tb_hnx_rp3lp3x_halves.sv'):
  b=b.replace(b'`timescale 1ns/1ps',b'`timescale 1ps/1fs').replace(b'always #0.5',b'always #416.5')
 p=out/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);manifest[f]=hashlib.sha256(b).hexdigest()
flags=re.search(r'-DOT_SMH_CG_ENREG (.+?) \$SRCS',script).group(1)
flags='-DOT_SMH_CG_ENREG '+flags
(out/'manifest.json').write_text(json.dumps(dict(source_commit=rev,header_commit='4673cf757e',sources=manifest,period_ps=833,scope='One native pair transport versus pinnedflatP3; does not prove production arithmetic/front integration'),indent=2)+'\n')
(out/'run.sh').write_text('''#!/bin/bash
set -eu
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p logs
for m in 0 1; do
 "$VL" --binary -j 8 -Wno-fatal --top-module tb_hnx_rp3lp3x_halves -GMUT=$m '''+flags+' '+' '.join(files)+''' -Mdir obj$m >logs/build$m.log 2>&1
 ./obj$m/Vtb_hnx_rp3lp3x_halves >logs/mut$m.log 2>&1 || true
 if [ "$m" = 0 ]; then grep -q 'HV_LOCKSTEP PASS' logs/mut$m.log; else grep -Eq 'HV_LOCKSTEP FAIL|LAND_FAULT' logs/mut$m.log; fi
 tail -5 logs/mut$m.log
done
echo PAIR_NATIVE_GATE_PASS
''')
