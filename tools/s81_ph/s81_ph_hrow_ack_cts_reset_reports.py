#!/usr/bin/env python3
"""Actual SS/FF async checks on source-bound CTS with placement RC; diagnostic only."""
from pathlib import Path
import json,re,subprocess,concurrent.futures
R=Path(__file__).resolve().parents[2];O=R/'results/arch/s81_hrow_reset_ack_1014/physical_candidate'
def run(gp,corner):
 g=json.loads(gp.read_text());b=g['source_binding'];host=b['remote_host'];root=b['remote_run'];kit=gp.parent.name;top=json.loads((gp.parent/'spec.json').read_text())['top'];base='/work/results/asap7/opentallas_'+top+'_asap7_ref_gate/base';out=root+'/reset_receipt';local=O/'actual_cts'/top;local.mkdir(parents=True,exist_ok=True);image=re.search(r'GATE_TOOL_IMAGE_ID=(\S+)',b['runtime_tool_provenance'][0])[1]
 tcl=f'''set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $plat/lib/NLDM/*RVT_{corner.upper()}*] {{read_liberty $l}}
foreach l [glob $plat/lib/NLDM/*_LVT_{corner.upper()}_* $plat/lib/NLDM/*_SLVT_{corner.upper()}_*] {{if {{![string match *FAKE* $l]}} {{read_liberty $l}}}}
read_db {base}/4_1_cts.odb
read_sdc {base}/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set ::ot_ce_corner {corner}
read_sdc /src/physical/ref_tile/{kit}/signoff.sdc
set_propagated_clock [all_clocks]
report_checks -to [all_registers -async_pins] -path_delay min_max -format full_clock_expanded -fields {{slew cap fanout input_pin net}} -digits 4 -group_path_count 20000 > /out/reset_{corner}.rpt
if {{[catch {{report_pulse_width_checks -verbose > /out/pulse_{corner}.rpt}} why]}} {{puts "PULSE_WIDTH_OPEN $why"}}
puts "CTS_RESET_DONE {corner} placementRC diagnostic; global source/phase/routed SSFF OPEN"
exit
'''
 subprocess.run(['ssh',host,'mkdir','-p',out],check=True,capture_output=True);subprocess.run(['ssh',host,'tee',out+'/reset_'+corner+'.tcl'],input=tcl.encode(),stdout=subprocess.DEVNULL,check=True)
 cmd=f'docker run --rm -v {root}/src:/src:ro -v {root}/routes/gate/work/orfs:/work:ro -v {out}:/out {image} /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/reset_{corner}.tcl'
 p=subprocess.run(['ssh',host,cmd],capture_output=True);(local/('reset_'+corner+'.log')).write_bytes(p.stdout+p.stderr)
 if not p.returncode:
  for name in ['reset_'+corner+'.rpt','pulse_'+corner+'.rpt','reset_'+corner+'.tcl']:
   r=subprocess.run(['ssh',host,'cat '+out+'/'+name],capture_output=True)
   if r.returncode==0:(local/name).write_bytes(r.stdout)
  report=(local/('reset_'+corner+'.rpt')).read_text();slacks=[float(s) for s in re.findall(r'(-?\d+\.\d+)\s+slack\s+\(',report)];counts={'recovery':len(re.findall(r'^Endpoint:.*\(recovery check',report,re.M)),'removal':len(re.findall(r'^Endpoint:.*\(removal check',report,re.M))}
 else:slacks=[];counts={}
 return dict(master=top,corner=corner,exit=p.returncode,path_counts=counts,worst_slack_ps=min(slacks) if slacks else None,rc='placement estimate, actual CTS ODB',status='Diagnostic candidate checks; no routed or global reset timing qualification')
jobs=[(p,c) for p in sorted((R/'physical/ref_tile').glob('*ack1/gate_result.json')) for c in ['ss','ff']]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:res=list(pool.map(lambda x:run(*x),jobs))
(O/'cts_reset_reports_summary.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
