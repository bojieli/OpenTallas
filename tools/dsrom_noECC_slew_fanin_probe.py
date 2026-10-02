#!/usr/bin/env python3
"""Report the previously omitted enable arcs in the unchanged full q context."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prior_path(prior,key):
    if key.endswith('_prepared'):return prior/(key.removesuffix('_prepared')+'.lib')
    if key.startswith('macro_'):return prior/(key.removesuffix('_lib')+'.lib')
    if key.endswith('_mapped_verilog'):return prior/key.removesuffix('_mapped_verilog')/'mapped.v'
    return None
def run(prior,out):
    if out.exists():raise ValueError('Preserve every probe; no overwrite')
    root=Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git','status','--porcelain'],cwd=root).strip():raise ValueError('Pinned clean source required')
    r=json.loads((prior/'record.json').read_text())
    if r['status']!='MEASURED_INTRINSIC_CAPTURE_ONLY_CONTEXT_OPEN':raise ValueError('Completed retained campaign required')
    for key,digest in r['inputs'].items():
        p=prior_path(prior,key)
        if p is None:continue
        if sha(p)!=digest:raise ValueError('Retained campaign changed: '+key)
    out.mkdir(parents=True)
    prefix=(prior/'q/ss.tcl').read_text().split('report_checks',1)[0]
    # No driving-cell overrides, input slew annotations, case analysis or delay
    # calculator selection. All original clocks/uncertainties/exceptions retained.
    extra='''
report_dcalc -from [get_pins _233706_/A] -to [get_pins _233706_/Y] -max -digits 6
report_dcalc -from [get_pins _233706_/B] -to [get_pins _233706_/Y] -max -digits 6
report_dcalc -from [get_pins _232078_/A] -to [get_pins _232078_/Y] -max -digits 6
report_dcalc -from [get_pins _232078_/B] -to [get_pins _232078_/Y] -max -digits 6
report_checks -through [get_pins _232078_/Y] -to $caps -path_delay max -group_count 4 -endpoint_count 1 -format full_clock_expanded -digits 6 -fields {slew capacitance input_pin net}
exit
'''
    tcl=out/'probe.tcl';tcl.write_text(prefix+extra)
    receipt=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        previous_record_sha256=sha(prior/'record.json'),previous_source_pin=r['source_commit'],
        previous_netlist_sha256=r['inputs']['q_mapped_verilog'],probe_sha256=sha(tcl),
        no_engine_RTL_or_synthesis=True,no_delay_calculator_tuning=True,
        no_clock_or_uncertainty_change=True,no_driving_cell_override=True,scope='Existing full q map: NAND data vs enable arcs, NOR source-enable driver and one-cycle control-to-capture path',status='PREPARED')
    start=time.monotonic()
    with (out/'probe.log').open('w') as log:
        p=subprocess.Popen(['sta','-exit',str(tcl)],stdout=log,stderr=subprocess.STDOUT)
        receipt.update(pid=p.pid,status='LIVE');(out/'record.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        print(p.pid,flush=True);code=p.wait()
    receipt.update(status='TERMINAL',returncode=code,elapsed_s=time.monotonic()-start,log_sha256=sha(out/'probe.log'))
    (out/'record.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.prior,a.output)
