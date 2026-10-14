#!/usr/bin/env python3
"""Read-only STA replay of CLOSED routed async checks; original constraints preserved."""
from pathlib import Path
import argparse,json,re,subprocess,shlex,concurrent.futures
repo=Path(__file__).resolve().parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=repo/'results/arch/s81_hrow_native_placement_1013/reset_classification');ap.add_argument('--masters',nargs='*');args=ap.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
def run(k,m,c):
 directory=repo/'physical/ref_tile'/k/'views'/m;a=json.load(open(directory/'abstract.json'));cmd=a['corners'][c]['command'][:];work=next(x for x in cmd if x.endswith(':/work:ro'));host='ot-epyc4' if 'scratch2' in work else 'ot-epyc1tb';remote='/tmp/s81_hrow_reset_classify_'+m
 subprocess.run(['ssh',host,'mkdir','-p',remote],check=True)
 tcl=(directory/('export_'+c+'.tcl')).read_text();tcl='\n'.join(x for x in tcl.splitlines() if not x.startswith(('write_timing_model','write_abstract_lef','exit')))
 tcl+='\nreport_checks -to [all_registers -async_pins] -path_delay min_max -format full_clock_expanded -fields {slew cap fanout input_pin net} -digits 4 -group_path_count 1000 > /out/reset_'+c+'.rpt\nputs "RESET_REPORT_DONE"\nexit\n'
 subprocess.run(['ssh',host,'tee',remote+'/run_'+c+'.tcl'],input=tcl.encode(),stdout=subprocess.DEVNULL,check=True)
 cmd=[remote+':/out' if x.endswith(':/out') else x for x in cmd];cmd[-1]='/out/run_'+c+'.tcl'
 result=subprocess.run(['ssh',host,shlex.join(cmd)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (out/(m+'_reset_'+c+'.log')).write_bytes(result.stdout)
 if result.returncode==0:(out/(m+'_reset_'+c+'.rpt')).write_bytes(subprocess.check_output(['ssh',host,'cat',remote+'/reset_'+c+'.rpt']))
 return m,c,result.returncode,result.stdout.decode()[-700:]
jobs=[('dsfd_die_rstsync_m5','dsfd_die_rstsync'),('dsfd_hrow_r15_m5','dsfd_hrow_r15'),('dsfd_hrow_r23_m5','dsfd_hrow_r23'),('hrow5_cbe_cx','dsfd_mtp_hrow_cbe'),('hrow5_cbw_cx','dsfd_mtp_hrow_cbw'),('dsfd_hrow_r1025_m5','dsfd_hrow_r1025'),('dsfd_hrow_r2079_m5','dsfd_hrow_r2079')]
if args.masters:jobs=[(k,m) for k,m in jobs if m in args.masters]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for result in pool.map(lambda x:run(*x),[(k,m,c) for k,m in jobs for c in ['ss','ff']]):print(result,flush=True)
