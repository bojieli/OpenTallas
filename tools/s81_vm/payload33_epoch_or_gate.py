#!/usr/bin/env python3
"""Actual 16 payload leaves + four unchanged controls/FJs, independent OR oracle."""
import argparse,pathlib,subprocess,tempfile,sys
R=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--mutant',action='store_true');a=p.parse_args()
with tempfile.TemporaryDirectory() as d:
 exe=str(pathlib.Path(d)/'tb');cmd=['iverilog','-g2012','-s','tb','-o',exe]
 if a.mutant:cmd+=['-DS81_PAY33_MUT_OMIT_EPOCH']
 files=['tools/s81_vm/payload33_epoch_or_bench.sv','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_a2f_payload33.sv','tools/s81_vm/area_a2_controlled.sv','tools/s81_vm/area_a2f.sv','tools/s81_vm/area_a2f_control_resetlocal.sv']
 subprocess.run(cmd+[str(R/f) for f in files],check=True)
 r=subprocess.run(['vvp',exe],text=True,capture_output=True);print(r.stdout+r.stderr,end='');sys.exit(0 if r.returncode==0 and 'PAY33_OR PASS' in r.stdout else 1)
