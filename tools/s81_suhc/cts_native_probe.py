#!/usr/bin/env python3
"""Unqualified placement-RC ETM diagnostics for a completed standalone CTS gate.
Never substitutes for routed views, signoff replay or native die qualification.
"""
import argparse,json,subprocess
from pathlib import Path
PLAT='/OpenROAD-flow-scripts/flow/platforms/asap7'
CELLS=['asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz','asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz','asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz','asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib']
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--gate',required=True);ap.add_argument('--kit',required=True);ap.add_argument('--cell',required=True);a=ap.parse_args()
 gate=Path(a.gate);work=gate/'routes/gate/work/orfs';out=gate/'native_diag';out.mkdir(exist_ok=True)
 out.joinpath('insertion.json').write_text((gate/'ck.json').read_text())
 for corner in ['tt','ff']:
  code=[f'read_lef {PLAT}/lef/asap7_tech_1x_201209.lef',f'read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef']
  code += [f'read_liberty {PLAT}/lib/NLDM/'+x.format(C=corner.upper()) for x in CELLS]
  code += ['set base [lindex [glob /work/results/asap7/*/base] 0]','read_db $base/4_1_cts.odb','read_sdc $base/4_cts.sdc','set_propagated_clock [all_clocks]',f'source {PLAT}/setRC.tcl','estimate_parasitics -placement',f'set ::ot_ce_corner {corner}',f'read_sdc /src/physical/ref_tile/{a.kit}/signoff.sdc',f'write_timing_model -library_name {a.cell}_{corner} /out/{a.cell}_{corner}.lib']
  if corner=='tt':code += [f'write_abstract_lef /out/{a.cell}.lef']
  code += ['puts "PLACEMENT_ONLY_EXPORT_DONE"','exit']
  deck=out/f'probe_{corner}.tcl';deck.write_text('\n'.join(code)+'\n')
  cmd=['docker','run','--rm','--memory','4g','-v',f'{work}:/work:ro','-v',f'{gate / "src"}:/src:ro','-v',f'{out}:/out','openroad/orfs:latest','bash','-lc',f'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init -threads 1 /out/probe_{corner}.tcl']
  with (out/f'probe_{corner}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
  if r.returncode:raise SystemExit(r.returncode)
 out.joinpath('scope.json').write_text(json.dumps({'qualification_status':'UNQUALIFIED_PLACEMENT_ONLY','gate':str(gate),'cell':a.cell,'RC':'placement estimate, no routed SPEF','purpose':'diagnose per-bit native launch/capture/hold before full-route verdict; full signoff and actual die clocks/resets/hops remain required'},indent=2)+'\n')
 print(out)
if __name__=='__main__':main()
