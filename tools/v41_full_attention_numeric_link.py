#!/usr/bin/env python3
"""Link an ALREADY BUILT Verilator archive with existing harness; no RTL rebuild."""
import argparse,subprocess,json,hashlib
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--build',type=Path,required=True);p.add_argument('--harness',type=Path,required=True);p.add_argument('--verilator-root',type=Path,required=True);a=p.parse_args();a.build=a.build.resolve();a.harness=a.harness.resolve();a.verilator_root=a.verilator_root.resolve();obj=a.build/'obj'
 for rel,d in json.loads((a.build/'pins.json').read_text()).items():assert hashlib.sha256((a.build/rel).read_bytes()).hexdigest()==d,rel
 lines=(obj/'Vtb_hier.mk').read_text().splitlines();libs=[];active=False
 for line in lines:
  if line.startswith('VM_HIER_LIBS :='):active=True;continue
  if active:
   value=line.strip().rstrip('\\').strip()
   if not value:break
   libs.append(obj/value)
 top=next((obj/n for n in ['Vtb__ALL.a','libVtb.a'] if (obj/n).is_file()),None)
 if not top:raise SystemExit('Archive not ready; do not rebuild duplicate')
 for x in libs:assert x.is_file(),f'Child archive not ready: {x}'
 inc=a.verilator_root/'include';exe=a.build/'Vtb_exact'
 cmd=['g++','-O0','-std=c++17','-pthread',f'-I{obj}',f'-I{inc}',f'-I{inc}/vltstd',str(a.harness),str(inc/'verilated.cpp'),str(inc/'verilated_threads.cpp'),' -Wl,--start-group'.strip(),str(top),*map(str,libs),'-Wl,--end-group','-o',str(exe)]
 subprocess.run(cmd,check=True,timeout=300)
 (a.build/'link_exact.json').write_text(json.dumps({'command':cmd,'executable_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(a.harness.read_bytes()).hexdigest()},indent=2)+'\n')
if __name__=='__main__':main()
