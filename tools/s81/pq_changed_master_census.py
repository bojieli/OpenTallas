#!/usr/bin/env python3
"""Source-exact generic FF census for changed canonical PQ masters, not physical timing."""
from pathlib import Path
import argparse,json,subprocess,hashlib
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2]
sets={
 'ot_s81_pq_ctl_static_native':(['rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_static_native.sv','physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv','physical/s81_pq_hier/pinned/rtl/hdc/ot_hdc_delay.sv','physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv','rtl/v41rom/ot_v41_kreg.sv','rtl/common/ot_prefix.sv'],''),
 'ot_s81_pq_command_endpoint':(['rtl/dsrom_sys/s81_static_control/ot_s81_pq_command_endpoint.sv'],'chparam -set PHW 10 ot_s81_pq_command_endpoint;'),
 'ot_s81_pq_calendar_reader':(['rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv'],'chparam -set ACTION_BITS 75 ot_s81_pq_calendar_reader;')}
results={}
for top,(sources,params) in sets.items():
 output=(a.out/(top+'.json')).resolve();script='read_verilog -sv '+' '.join(str(root/f) for f in sources)+'; '+params+' hierarchy -check -top '+top+'; synth -top '+top+' -flatten -noabc; write_json '+str(output)+'; stat;'
 with (a.out/(top+'.log')).open('w') as log:subprocess.run(['yosys','-p',script],stdout=log,stderr=subprocess.STDOUT,check=True)
 cells=json.loads(output.read_text())['modules'][top]['cells'];types={}
 for cell in cells.values():types[cell['type']]=types.get(cell['type'],0)+1
 ff=sum(n for name,n in types.items() if 'DFF' in name)
 results[top]=dict(actual_generic_ff=ff,cells=len(cells),cell_types=types,source_sha256={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in sources},parameter_command=params)
(a.out/'receipt.json').write_text(json.dumps(dict(scope='Generic synthesis census only. No mapped area, clock insertion/spread or TT/FF/DRC qualification.',masters=results),indent=2)+'\n')
print(json.dumps({top:r['actual_generic_ff'] for top,r in results.items()}))
