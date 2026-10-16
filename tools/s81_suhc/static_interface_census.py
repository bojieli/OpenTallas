#!/usr/bin/env python3
"""Prepare exact native interface-only elaboration for static SU physical partition.

Run the emitted Yosys script through ot-run. Interface blackboxes intentionally
exclude arithmetic from this graph census; they must never qualify simulation.
Generated hardleaf hardware instantiates original actual native RTL instead.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import su_tile_tops as T
R=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);modules={};sources={}
 paths=sorted((R/'rtl/dsrom_sys/s81_suhc').rglob('*.sv'))+[R/'rtl/hdc/ot_hdc_delay.sv']
 for path in paths:
  if '/test/' in str(path):continue
  try:parsed=T.modules(str(path))
  except (ValueError,IndexError,AssertionError):continue
  for name,(params,ports,body) in parsed.items():
   if not(name.startswith('ot_s81_su_') or name=='ot_hdc_delay'):continue
   modules[name]=(params,ports);sources[name]=dict(path=str(path.relative_to(R)),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 stubs=[]
 for name,(params,ports) in modules.items():stubs.append('(* blackbox *) module '+name+(' #(parameter '+', parameter '.join(k+'='+v for k,v in params.items())+')' if params else '')+' ('+ports+'); endmodule\n')
 (out/'stubs.sv').write_text('\n'.join(stubs));source='rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_su_static.sv';raw=(R/source).read_bytes();(out/'dsfd_sp_su_static.sv').write_bytes(raw)
 (out/'source_identity.json').write_text(json.dumps(dict(scope='INTERFACE GRAPH CENSUS ONLY, never functional qualification',top=dict(path=source,sha256=hashlib.sha256(raw).hexdigest(),params={'RXH':2}),native_interfaces=sources),indent=1)+'\n')
 (out/'census.ys').write_text('read_verilog -sv -DSYNTHESIS stubs.sv dsfd_sp_su_static.sv\nhierarchy -top dsfd_sp_su_static -chparam RXH 2\nproc\nopt_clean\nwrite_json census.json\n')
 print(json.dumps(dict(interface_modules=len(modules),out=str(out))))
if __name__=='__main__':main()
