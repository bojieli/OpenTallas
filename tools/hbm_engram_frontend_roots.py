#!/usr/bin/env python3
"""Synthesize the actual grouped Engram frontend; keep separately-owned common controller/store as explicit blackboxes."""
import argparse,json,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 libs=['rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_pipeline_stack.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_row_store_decode.sv']
 actual=['rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_fetch_grouped.sv']
 js=(out/'frontend.json').resolve()
 script='read_verilog -sv -lib '+' '.join(str(ROOT/p) for p in libs)+'; read_verilog -sv '+' '.join(str(ROOT/p) for p in actual)+'; hierarchy -top ot_hbm_engram_home_fetch_grouped; proc; flatten; opt; memory_map; opt; stat; write_json '+str(js)
 p=subprocess.run(['yosys','-p',script],capture_output=True,text=True);(out/'yosys.log').write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stdout[-2000:]+p.stderr)
 mod=json.loads(js.read_text())['modules']['ot_hbm_engram_home_fetch_grouped']; clocks={}
 for cell in mod['cells'].values():
  if cell['type'].lower().startswith(('$dff','$adff','$sdff')):
   clk=tuple(cell['connections']['CLK']);clocks[clk]=clocks.get(clk,0)+len(cell['connections']['Q'])
 names={tuple(p['bits']):n for n,p in mod['ports'].items()}
 receipt=dict(schema='opentallas.engram.grouped_frontend_roots.v1',logical_ff_bits_by_clock={names.get(k,str(k)):v for k,v in clocks.items()},blackboxes=libs,scope='Frontend only: actual grouped request buffer/arbiters and real CDC flops. Common controller, response SRAMs and staging store are excluded and require separate inventories. Logical root count is not CTS/physical qualification.',source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in libs+actual})
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
