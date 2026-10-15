#!/usr/bin/env python3
"""Actual rank-local producer clocks/storage, with sole common PC owner explicit."""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out,rank):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 macro='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v';common='rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_owned_stack.sv'
 paths=['rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_gather.sv','rtl/dsrom_sys/engram/clock_partition_1015/ot_s81_engram_hash_clock_roots.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_hash_home_clock_roots.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_dispatch.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_fetch_program.sv','rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv']
 paths+=['rtl/hbm_accel/engram_static_20261015/'+f for f in ['ot_hbm_engram_row_store_decode.sv','ot_hbm_engram_home_client.sv','ot_hbm_native_client_mux.sv','ot_hbm_engram_home_shared_stack.sv','ot_hbm_engram_rank_fetch.sv']]
 script='read_verilog -sv -lib /src/'+macro+' /src/'+common+'; read_verilog -sv '+' '.join('/src/'+p for p in paths)+f'; chparam -set HOME_RANK {rank} ot_hbm_engram_rank_fetch; hierarchy -check -top ot_hbm_engram_rank_fetch; proc; opt; memory_map; opt; setattr -unset keep_hierarchy; flatten; opt; stat; write_json /out/actual_generic.json\n'
 (out/'census.ys').write_text(script);cp=subprocess.run(['docker','run','--rm','-v',str(ROOT)+':/src:ro','-v',str(out)+':/out','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh && yosys -s /out/census.ys'],capture_output=True,text=True);(out/'yosys.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout[-3000:]+cp.stderr[-1000:]
 mods=json.loads((out/'actual_generic.json').read_text())['modules'];tops=[(n,m)for n,m in mods.items()if m.get('attributes',{}).get('top')not in (None,'0','00000000000000000000000000000000')];assert len(tops)==1;name,m=tops[0]
 roots={}
 for port in ['core_clk','hbm_clk','hash_column_clk','pc_clk']:
  for i,bit in enumerate(m['ports'][port]['bits']):roots[bit]=port if len(m['ports'][port]['bits'])==1 else f'{port}[{i}]'
 ff=collections.Counter();macros=collections.Counter();common_cells=[]
 states={'$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$sdffce','$aldff','$aldffe','$dffsr','$dffsre'}
 for n,c in m['cells'].items():
  t=c['type']
  if t in states:
   ck=c['connections']['CLK'];assert len(ck)==1 and ck[0]in roots,(n,ck);ff[roots[ck[0]]]+=len(c['connections']['Q'])
  elif t=='ot_sram_1r1w_128x256_m1_r2c2':
   ck=c['connections']['clk'];assert len(ck)==1 and ck[0]in roots;macros[roots[ck[0]]]+=1
  elif 'ot_hbm_svc_native_sector_owned_stack'in t:common_cells.append(n)
  else:assert t.startswith('$')and not any(s in t.lower()for s in ['latch','mem','dff','ffsr'])and t not in ('$ff','$sr','$fsm'),(n,t)
 assert len(common_cells)==1 and sum(macros.values())==3,(common_cells,macros)
 assert len(ff)==40,ff
 endpoints={r:ff.get(r,0)+macros.get(r,0)+(13650 if r.startswith('pc_clk[') else 0)for r in roots.values()}
 rep={str(n):dict(hash_programme_frontend_FF=n*sum(ff.values()),programme_and_staging_SRAMs=n*3,stack3_common_response_SRAMs=n*32,physical_common_stack_owners=n,source_clock_roots=n*40)for n in [8,16,96]}
 result=dict(schema='opentallas.hbm.engram.rank_local_inventory.v1',status='pass',HOME_RANK=rank,actual_top=name,actual_logical_FF_excluding_common=dict(sorted(ff.items())),programme_and_staging_macro_clock_pins=dict(macros),actual_common_owner_instances=len(common_cells),common_owner_inventory=dict(source_sha256=hashlib.sha256((ROOT/common).read_bytes()).hexdigest(),PCs=32,conservative_clock_endpoints_per_PC=13650,response_SRAMs=32,source_receipt_commit='fcea51da7',normalization_commit='a7b86347d'),composed_inventory_clock_endpoints=dict(sorted(endpoints.items())),maximum_inventory_clock_endpoints=max(endpoints.values()),replica_scenarios=rep,all_inventory_roots_at_most15000=max(endpoints.values())<=15000,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in paths+[macro,common]},scope='Complete actual rank-local source producer/hash/programme/front-end/mux clocks; three real SRAMs plus sole existing common owner explicit. Common source census imported once, not duplicate controllers or jointly mapped physical proof. Eight active homes/layer and sixteen/two layers are instantiated candidates;96 uniform replicas is a priced upper-bound scenario, not adoption. Whole-rank other three PHY stacks, downstream COLL/consumer, HOST/C10/token delivery, universal timing, joint mapping and physical qualification remain open.')
 assert result['all_inventory_roots_at_most15000'];(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--rank',type=int,default=8);a=ap.parse_args();run(a.out,a.rank)
