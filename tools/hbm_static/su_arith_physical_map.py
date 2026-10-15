#!/usr/bin/env python3
"""Map one actual SU master independently; this is no CTS/closure claim."""
import argparse,hashlib,json,math,re,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('kind',choices=['bank','0','1','2','0_lat4_leaf1','1_lat4_leaf1','2_lat4_leaf1'])
parser.add_argument('out',type=Path)
cli=parser.parse_args();kind=cli.kind;variant=kind.endswith('_lat4_leaf1')
lane_kind=kind.split('_',1)[0]
out=cli.out.resolve();out.mkdir(parents=True,exist_ok=True)
args=[sys.executable,'tools/run_abi3_physical.py','--view','asap7','--clock-period-ns','1.111111111','--clock-uncertainty-ns','0.060','--clock-uncertainty-hold-ns','0.025','--stages','synth','--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited','--keep-workdir',str(out/'work'),'--output',str(out/'result.json')]
if kind=='bank':
 args[args.index('synth')]='pnr'
 args+=['--pnr-stop-after','floorplan','--die-area','0','0','364.472','142.08','--core-area','2','2','362.472','140.08','--macro-place-halo','10','10']
 files=['rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_pinned_bank.sv','rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_data_store.sv','rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v']
 args+=['--top','ot_hbm_su_static_pinned_bank','--clock-port','clk','--param','READERS=6','--param','RB=9','--macro-view','ot_sram_1r1w_128x256_m1_r2c2=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2']
else:
 files=re.findall(r'(?:rtl|physical)/[^\s\\]+\.(?:sv|v)',(R/'tools/hbm_static/su_arith_run.sh').read_text());files=[f for f in files if '/data_store/'not in f and '/peers/'not in f and not f.startswith('physical/') and '/tb_'not in f]
 args+=['--top','ot_hbm_su_static_lane','--clock-port','clk_stage[0]']
 for p in ['KIND='+lane_kind,'LN=7','MLAT='+('4' if variant else '3'),'ALAT=3','LEAF='+('1' if variant else '0'),'FETCH_EXTRA_EDGES=2']:args+=['--param',p]
for f in files:args+=['--source',f]
(out/'command.json').write_text(json.dumps(args,indent=2)+'\n')
with (out/'map.log').open('w')as log:r=subprocess.run(args,cwd=R,stdout=log,stderr=subprocess.STDOUT)
if r.returncode==0 and kind!='bank':
 # Count every actual mapped clock pin through the existing structural parser,
 # retaining all roots (the general textbook report shows only its top six).
 sys.path.insert(0,str(R/'tools'))
 import textbook_lint as TL
 netlist=out/'work/mapped.v'
 mapped=netlist.read_text();g,top=TL.flatten(TL.parse_verilog(mapped),'ot_hbm_su_static_lane')
 _,roots=TL.clock_nets(g,TL.build(g,None))
 result=json.loads((out/'result.json').read_text());syn=result['synthesis']
 population=sum(v['ff'] for v in roots.values())
 if population!=syn['sequential_cell_count']:
  raise RuntimeError(f'mapped clock census {population} != actual synthesis sequential cells {syn["sequential_cell_count"]}')
 area=syn['cell_area_um2'];side=math.ceil((math.sqrt(area/0.5)+4.32)/0.216)*0.216
 census=dict(qualified=False,scope='source-current synthesis area and actual mapped clock population only; no CTS/route qualification',
  profile=dict(KIND=int(lane_kind),LN=7,MLAT=4 if variant else 3,ALAT=3,LEAF=1 if variant else 0,FETCH_EXTRA_EDGES=2),
  period_ps=1111.111111,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
  std_area_um2=area,sequential_area_um2=syn['sequential_area_um2'],sequential_cells=syn['sequential_cell_count'],
  mapped_netlist_sha256=hashlib.sha256(netlist.read_bytes()).hexdigest(),
  roots=[dict(root=f'{k[0]}:{k[1]}',**v) for k,v in sorted(roots.items())],
  maximum_root_sinks=max((v['ff']+v['macro_pins'] for v in roots.values()),default=0),
  provisional_square_outline_um=[round(side,6),round(side,6)],
  outline_basis='mapped std area /0.5 plus4.32um total core margin, rounded up0.216um. Area-only provisional square; no pin/clock/cut/slot legality claim.')
 (out/'mapped_clock_census.json').write_text(json.dumps(census,indent=2)+'\n')
print('SU_PHYSICAL_MAP',kind,'exit',r.returncode,flush=True);sys.exit(r.returncode)
