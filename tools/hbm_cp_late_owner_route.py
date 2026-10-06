#!/usr/bin/env python3
"""Route the exact late-owner CP successor in the unchanged accepted parent slot."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--job-root',type=Path,required=True);ap.add_argument('--density',type=float,default=.55)
    args=ap.parse_args();job=args.job_root.resolve();job.mkdir(parents=True,exist_ok=True)
    exact=json.loads((ROOT/'results/rtl/hbm_cp_late_owner_20261006/terminal.json').read_text())
    assert exact['pass_exact']
    for p,digest in exact['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
    record=json.loads((ROOT/'results/physical/hbm_cp_control_tail_parent_context_20261006/r1_terminal/prepared.json').read_text())
    argv=record['argv'];argv=[a.replace('SU_CONTROL_TAIL_CUT=1','SU_CONTROL_TAIL_CUT=2') for a in argv]
    for option,value in [('--keep-workdir',str(job/'work')),('--output',str(job/'physical.json')),('--nickname-tag','item5_cp_late_owner')]:argv[argv.index(option)+1]=value
    for i,v in enumerate(argv):
        if v.startswith('PLACE_DENSITY='):argv[i]='PLACE_DENSITY='+str(args.density)
    case=job/'work/orfs';case.mkdir(parents=True,exist_ok=True);(case/'tmp').mkdir(exist_ok=True)
    (case/'cts_membership.tcl').write_text('source /src/physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl\n')
    patch = '''from pathlib import Path
import hashlib,json
p=Path('/OpenROAD-flow-scripts/flow/scripts/cts.tcl')
s=p.read_text()
needle='set result [catch { log_cmd detailed_placement } msg]'
assert s.count(needle)==2, 'Installed CTS legalization API changed'
print(json.dumps(dict(original_cts_sha256=hashlib.sha256(s.encode()).hexdigest(),membership_calls=2)))
p.write_text(s.replace(needle,'source /work/cts_membership.tcl\\n'+needle))
'''
    if True:
        # Same installed canonical GPL as Noether a0076e760/c3f2e5fb0:
        # initial placement removes an empty top-level component. The earlier
        # automatic-density prequery cannot initialize that empty component.
        # Preserve exact modeled density0.5 and bind newly inserted IO cells
        # after native port buffering, before canonical initial placement.
        patch += '''
p=Path('/OpenROAD-flow-scripts/flow/scripts/global_place.tcl')
s=p.read_text()
needle='proc do_placement { global_placement_args } {'
assert s.count(needle)==1, 'Installed GPL port-buffer/placement API changed'
s=s.replace(needle,'source /src/physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl'+chr(10)+needle)
p.write_text(s)
p=Path('/OpenROAD-flow-scripts/flow/scripts/global_route.tcl')
s=p.read_text()
needle='    log_cmd detailed_placement'
assert s.count(needle)==2, 'Installed GRT repair legalization API changed'
s=s.replace(needle,'    source /src/physical/hbm_cp_parent_context_20261005/fast_frontier_membership.tcl'+chr(10)+needle)
p.write_text(s)
'''
    (case/'bind_cts_membership.py').write_text(patch)
    import run_abi3_physical as driver
    original=driver.run
    def run(command,**kwargs):
        if command[:3]==['docker','run','--rm'] and 'make DESIGN_CONFIG=/work/config.mk' in command[-1]:
            command=list(command);command[-1]='python3 /work/bind_cts_membership.py || exit $?; '+command[-1]
        return original(command,**kwargs)
    driver.run=run
    rc=driver.main(argv)
    if list(case.glob('results/**/6_final.odb')):
        import hbm_cp_parent_context
        hbm_cp_parent_context.corner_sta(case,job/'corner_sta.json')
    (job/'terminal.exit').write_text(str(rc)+'\n')
    return rc
if __name__=='__main__':raise SystemExit(main())
