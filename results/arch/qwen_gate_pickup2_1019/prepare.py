import sys,pathlib,subprocess
sys.path.insert(0,'/home/ubuntu/wt/codex-pgstream-cdc-1019/tools/ref_tile');import cts_native_probe as P
out=pathlib.Path(__file__).parent
for k in ['sf5','sf5w']:
 remote='/srv/opentallas-scratch/claude/ref_gate/qfd_d2d_static_'+k+'-20261019-'+('115442' if k=='sf5' else '115502')
 for corner in ['tt','ff']:
  t=P.probe_tcl();old='foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }'
  new='foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_'+corner.upper()+'* $plat/lib/NLDM/*_LVT_'+corner.upper()+'_* $plat/lib/NLDM/*_SLVT_'+corner.upper()+'_*] { if {![string match *FAKE* $f]} {read_liberty $f} }'
  assert old in t;t=t.replace(old,new).replace('set ::ot_ce_corner tt','set ::ot_ce_corner '+corner)
  old='if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }'
  new='if {[string match *.lib $w]} { set w [string map {_tt.lib _'+corner+'.lib} $w]; if {![file exists $w]} {error "missing exact macro corner $w"}; read_liberty $w; puts "PICKUP_MACRO_CORNER '+corner+' $w" }'
  assert old in t;t=t.replace(old,new)
  t=t.replace('native_probe_tt.lib','pickup_native_'+corner+'.lib')
  t+='\nputs "PICKUP_WNS '+corner+' setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"\nreport_check_types -max_slew -max_capacitance -max_fanout -violators\n'
  if corner=='tt': t+='\n'+(out/'native_dump.tcl').read_text()
  p=out/(k+'_'+corner+'.tcl');p.write_text(t);subprocess.run(['scp',str(p),'ot-epyc5:'+remote+'/pickup_'+corner+'.tcl'],check=True)
 script='''#!/bin/bash
set -euo pipefail
R='''+remote+'''
for C in tt ff; do
 docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/qfd_d2d_static_'''+k+'''/signoff.sdc -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work" -v "$R/pickup_$C.tcl:/probe.tcl:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl > "$R/pickup_native_$C.log" 2>&1
 done
 echo PICKUP_NATIVE_TT_FF_DONE
'''
 p=out/(k+'_run.sh');p.write_text(script);subprocess.run(['scp',str(p),'ot-epyc5:'+remote+'/pickup_native_run.sh'],check=True)
