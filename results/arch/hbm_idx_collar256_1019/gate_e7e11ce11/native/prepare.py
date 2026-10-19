import sys,pathlib,subprocess
sys.path.insert(0,'/home/ubuntu/wt/codex-hbm-idx256-physical-1019/tools/ref_tile')
import cts_native_probe as P
out=pathlib.Path(__file__).parent
remote='/srv/opentallas-scratch/claude/ref_gate/hdie_col_idx256_1019-20261019-103656'
for corner in ['tt','ff']:
 t=P.probe_tcl()
 # This kit has no macros/children. Use the same native-corner standard-cell family as ck_insertion.
 old='foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }'
 new='foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_'+corner.upper()+'* $plat/lib/NLDM/*_LVT_'+corner.upper()+'_* $plat/lib/NLDM/*_SLVT_'+corner.upper()+'_*] { if {![string match *FAKE* $f]} {read_liberty $f} }'
 assert old in t;t=t.replace(old,new).replace('set ::ot_ce_corner tt','set ::ot_ce_corner '+corner).replace('native_probe_tt.lib','idx256_native_'+corner+'.lib').replace('native_cts_probe_tt','idx256_native_'+corner)
 if corner=='tt':t+='\nwrite_verilog /work/idx256_postcts.v\nset ::env(OT_LAYOUT_OUT) /work/idx256_postcts_layout.json\nsource /src/tools/ref_tile/layout_dump.tcl\n'
 p=out/('probe_'+corner+'.tcl');p.write_text(t)
 subprocess.run(['scp',str(p),'ot-agidock128:'+remote+'/idx256_probe_'+corner+'.tcl'],check=True)
script='''#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/hdie_col_idx256_1019-20261019-103656
for C in tt ff; do
 docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/hdie_col_idx256_1019/signoff.sdc -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work" -v "$R/idx256_probe_$C.tcl:/probe.tcl:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl > "$R/idx256_native_$C.log" 2>&1
 done
 echo IDX256_NATIVE_TT_FF_DONE
'''
p=out/'run.sh';p.write_text(script);subprocess.run(['scp',str(p),'ot-agidock128:'+remote+'/idx256_native_run.sh'],check=True)
