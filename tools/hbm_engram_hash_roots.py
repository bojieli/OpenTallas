#!/usr/bin/env python3
"""Actual complete HBM hash/dispatcher clock inventory; no physical admission."""
import argparse,collections,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
 paths=['rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/dsrom_sys/engram/clock_partition_1015/ot_s81_engram_hash_clock_roots.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_home_dispatch.sv','rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_hash_home_clock_roots.sv']
 script='read_verilog -sv '+' '.join('/src/'+p for p in paths)+'; hierarchy -check -top ot_hbm_engram_hash_home_clock_roots; proc; opt; memory_map; opt; flatten; opt; stat; write_json /out/actual_generic.json\n'
 (out/'census.ys').write_text(script)
 cp=subprocess.run(['docker','run','--rm','-v',str(ROOT)+':/src:ro','-v',str(out)+':/out','openroad/orfs:asap7lock','bash','-lc','source /OpenROAD-flow-scripts/env.sh && yosys -s /out/census.ys'],capture_output=True,text=True)
 (out/'yosys.log').write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout[-3000:]+cp.stderr[-1000:]
 modules=json.loads((out/'actual_generic.json').read_text())['modules'];m=modules['ot_hbm_engram_hash_home_clock_roots']
 names={m['ports']['clk']['bits'][0]:'clk'};names.update({bit:f'clk_columns[{i}]'for i,bit in enumerate(m['ports']['clk_columns']['bits'])})
 states={'$dff','$dffe','$adff','$adffe','$sdff','$sdffe','$sdffce','$aldff','$aldffe','$dffsr','$dffsre'};counts=collections.Counter();types=collections.Counter()
 for n,c in m['cells'].items():
  t=c['type'];types[t]+=1
  if t in states:
   ck=c['connections']['CLK'];assert len(ck)==1 and ck[0] in names,(n,ck);counts[names[ck[0]]]+=len(c['connections']['Q'])
  else:assert t.startswith('$') and not any(s in t.lower()for s in ['latch','mem','dff','ffsr']) and t not in ('$ff','$sr','$fsm'),(n,t)
 assert set(counts)==set(names.values()),counts
 result=dict(schema='opentallas.hbm.engram.hash_clock_roots.v1',status='pass',logical_FF_by_clock_root=dict(sorted(counts.items())),total_logical_FF=sum(counts.values()),maximum_root_FF=max(counts.values()),all_roots_at_most15000=max(counts.values())<=15000,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in paths},scope='Complete actual 48-column hash, held outputs and both released eight-home dispatch streams. Seven 1:1 same-phase source clocks; no inserted stages or reduced workload. Actual min/max crossing STA, CTS, route and immutable performance admission remain open.')
 assert result['all_roots_at_most15000'];(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();run(a.out)
