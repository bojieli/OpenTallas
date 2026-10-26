#!/usr/bin/env python3
"""Admitted minimum actual converter/calendar proof with arithmetic mutant."""
import argparse,base64,gzip,io,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--mutant',choices=['sign','calendar']);a=p.parse_args()
files=['rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv',
       'rtl/hbm_accel/sm/static/ot_smh_static_int8.sv','rtl/test/tb_smh_static_int8.sv']
stream=io.BytesIO()
with tarfile.open(fileobj=stream,mode='w') as archive:
 for f in files:
  data=(ROOT/f).read_bytes();info=tarfile.TarInfo(Path(f).name);info.size=len(data);archive.addfile(info,io.BytesIO(data))
payload=base64.b64encode(gzip.compress(stream.getvalue())).decode()
define={'sign':'-DOT_INT8_MUT_SIGN','calendar':'-DOT_STATIC_INT8_MUT_CALENDAR',None:''}[a.mutant]
script=f'''set -e
work=$(mktemp -d /var/tmp/smh-static-int8.XXXXXX)
trap 'rm -rf "$work"' EXIT
cd "$work"
printf '%s' '{payload}' | base64 -d | gzip -dc | tar xf -
iverilog -g2012 {define} -s tb_smh_static_int8 -o proof *.sv
vvp proof
'''
raise SystemExit(subprocess.call(['/home/ubuntu/bin/ot-run','--mem','2','--threads','1','--','bash','-c',script]))
