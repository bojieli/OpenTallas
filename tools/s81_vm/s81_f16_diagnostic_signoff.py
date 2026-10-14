#!/usr/bin/env python3
"""Actual M5 f16 AP/mapped-state diagnostic; parent adoption always remains false."""
import argparse,hashlib,json,os,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',required=True,type=Path);a=p.parse_args();run=a.run.resolve();view=run/'record/views/dsfd_be_f16';lef=view/'dsfd_be_f16.lef';work=run/'record/f16_actual_AP';work.mkdir(parents=True,exist_ok=True)
 station=ROOT/'physical/hbm_accel_die_views/stations/bench/stn_pa_check.sh';generator=work/'generate.sh';generator.write_text(station.read_text().split('docker run --rm',1)[0]);subprocess.run(['bash',str(generator),str(lef),'dsfd_be_f16',str(work)],check=True)
 tcl=work/'pa.tcl';text=tcl.read_text().replace('set_routing_layers -signal M2-M9','set_thread_count 4\nset_routing_layers -signal M2-M5')
 positions=[('R0',10.368,10.368),('MX',64.8,10.392),('MY',10.368,64.8),('R180',64.8,64.824)]
 for k,(ori,x,y) in enumerate(positions):text=re.sub(r'place_inst -name u'+str(k)+r' -location \{[^}]+\} -orientation \S+ -status FIRM',f'place_inst -name u{k} -location {{{x} {y}}} -orientation {ori} -status FIRM',text)
 tcl.write_text(text);image='openroad/orfs:asap7lock';iid=subprocess.check_output(['docker','image','inspect',image,'--format','{{.Id}}'],text=True).strip();command=['docker','run','--rm','-u',f'{os.getuid()}:{os.getgid()}','-v',f'{work}:/work',image,'bash','-c','cd /work && /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit pa.tcl'];start=time.time()
 with (work/'pa.log').open('w') as f:r=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
 log=(work/'pa.log').read_text();ap_pass=r.returncode==0 and 'OT_PA DONE' in log and 'DRT-0073' not in log
 netlists=list((run/'routes').glob('*/work/orfs/results/asap7/*/base/1_*.v'));counts={str(f.relative_to(run)):len(re.findall(r'\b(DFF\S*)\s+(?:\\\S+|\S+)\s*\(',f.read_text())) for f in netlists};mapped_16=bool(counts) and all(n==16 for n in counts.values())
 record=dict(master='dsfd_be_f16',outline_um=[32.4,32.4],actual_cap='M5',actual_AP_pass=ap_pass,AP_returncode=r.returncode,AP_elapsed_s=time.time()-start,AP_image=image,AP_image_id=iid,AP_LEF_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),AP_placements=positions,AP_parent_signal_layers='M2-M5',actual_mapped_FF_counts=counts,mapped_exact16=mapped_16,new_reset_consumer_ACK=False,parent_clock_bound=False,native_parent_adopted=False,diagnostic_checks_pass=ap_pass and mapped_16)
 (run/'record/f16_diagnostic.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));return 0
if __name__=='__main__':raise SystemExit(main())
