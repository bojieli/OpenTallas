#!/usr/bin/env python3
"""Compose actual HEAD ctl/host/LEP/mesh providers into a candidate copy only.
The source frontier can close before production boot, physical infra, die STA
and token gates. Missing compiler boot dates retain the unadmitted defaults.
"""
import argparse,json
from pathlib import Path
import head_control_plan_delta as control
import head_host_plan_delta as host

def apply(base,closure,host_params=None):
 return host.apply(control.apply(base,closure),host_params)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--closure',type=Path,required=True);ap.add_argument('--host-params',type=Path);ap.add_argument('--out',type=Path,required=True)
 a=ap.parse_args()
 if a.base.resolve()==a.out.resolve():raise SystemExit('refusing canonical overwrite')
 p=apply(json.loads(a.base.read_text()),json.loads(a.closure.read_text()),json.loads(a.host_params.read_text()) if a.host_params else None)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(p,indent=2)+'\n')
 print('HEAD_PROVIDERS candidate only; actual boot/START, infra, timing and token remain open')
if __name__=='__main__':main()
