#!/usr/bin/env python3
"""Measure real internal paths; never classify an unbound leaf as closed."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HERE='physical/ha2_relay_tx_internal_20261007'
P='/OpenROAD-flow-scripts/flow/platforms/asap7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True)
 # gaps-design 2026-10-08: --here (the 20261008 pin-band fence vehicle) and --corners (OPTION B: TT setup + FF hold)
 ap.add_argument('--here',default=HERE);ap.add_argument('--corners',default='SS,FF');a=ap.parse_args();run=a.run.resolve();here=a.here
 corners=a.corners.split(',')
 out=run/'internal_timing.json'
 if out.exists():raise SystemExit('Immutable internal timing record already exists')
 base=run/'results/asap7/ha2_relay_tx_internal/base'
 rec=dict(scope='INTERNAL_ONLY: real local D1 launch to TX capture plus other internal sequential paths',adopted=False,physical_closed=False,parent_qualified=False,external_constraints='Deliberately unbound and individually enumerated; no virtual-clock arrival and no false-path waivers',corners={})
 for corner in corners:
  script=f'''foreach f [glob {P}/lib/NLDM/*RVT_{corner}*] {{read_liberty $f}}
read_db /work/results/asap7/ha2_relay_tx_internal/base/6_final.odb
read_sdc /work/results/asap7/ha2_relay_tx_internal/base/6_final.sdc
read_spef /work/results/asap7/ha2_relay_tx_internal/base/6_final.spef
set_propagated_clock [all_clocks]
source /src/{here}/check_pins.tcl
source /src/{here}/timing_audit.tcl
exit
'''
  p=run/f'internal_{corner}.tcl';p.write_text(script)
  cmd=['docker','run','--rm','-v',f'{ROOT}:/src:ro','-v',f'{run}:/work','openroad/orfs:asap7lock','bash','-lc',f'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/internal_{corner}.tcl']
  r=subprocess.run(cmd,capture_output=True,text=True);log=r.stdout+r.stderr;(run/f'internal_{corner}.log').write_text(log)
  if r.returncode or re.search(r'(?m)^\[ERROR|^Error:',log):raise SystemExit(f'{corner} STA failed; immutable log retained')
  slacks={f'{name}_{delay}':float(value) for name,delay,value in re.findall(r'^HA2_INTERNAL_SLACK (\S+) (max|min) (\S+)$',log,re.M)}
  assert len(slacks)==6,slacks
  clocks={}
  for role,name,lo,hi in re.findall(r'^HA2_BRANCH_CLOCK (\S+) (\S+) (\S+) (\S+)$',log,re.M):clocks.setdefault(role,[]).append(dict(pin=name,early_ps=float(lo),late_ps=float(hi)))
  rec['corners'][corner]=dict(internal_slack_ps=slacks,branch_clock_arrivals=clocks,
    register_counts=re.findall(r'^HA2_REGISTER_COUNTS (.*)$',log,re.M),coverage=re.findall(r'^HA2_REG2REG_COVERAGE (.*)$',log,re.M),
    unqualified_external_ports=[dict(direction=d,name=n) for d,n in re.findall(r'^HA2_UNQUALIFIED_EXTERNAL (\S+) (\S+)$',log,re.M)],
    unqualified_register_endpoints=[dict(check=d,pin=n) for d,n in re.findall(r'^HA2_UNQUALIFIED_REGISTER_ENDPOINT (\S+) (\S+)$',log,re.M)])
 rec['source_pins']={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/here/'wrapper.sv',ROOT/here/'internal.sdc',ROOT/here/'timing_audit.tcl']}
 rec['artifacts']={p.name:sha(p) for p in [base/'6_final.odb',base/'6_final.sdc',base/'6_final.spef']}
 su='TT' if 'TT' in rec['corners'] else 'SS'
 rec['setup_corner']=su
 rec['internal_margin_pass']=rec['corners'][su]['internal_slack_ps']['all_reg2reg_max']>=(0 if su=='TT' else 15) and rec['corners']['FF']['internal_slack_ps']['all_reg2reg_min']>=(0 if su=='TT' else 15)
 out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(dict(scope='INTERNAL_ONLY',internal_margin_pass=rec['internal_margin_pass'],physical_closed=False)))
if __name__=='__main__':main()
