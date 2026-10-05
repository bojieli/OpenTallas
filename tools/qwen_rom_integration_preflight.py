#!/usr/bin/env python3
"""Source-bound preparation for joining Qwen ROM runtime to physical tile/spine.

Analytical/source checks only. Does not generate RTL, launch builds or replace
pinned inputs. A blocked report is the expected verdict until all paths join.
"""
import argparse
import ast
import base64
import difflib
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARITH = dict(ACC_LAT=7, TREE_LAT=7, MUL_LAT=6, FAST_ISSUE=1, KV_PREP=3)
MAPPING = {
 'rtl/hdc/ot_hdc_matvec.sv': 'rtl/hdc/ot_qwen_w12_matvec.sv',
 'rtl/hdc/ot_qwen_me_array.sv': 'rtl/hdc/ot_qwen_me_array_w12.sv',
 'rtl/hdc/ot_qwen_rom_tile.sv': 'rtl/hdc/ot_qwen_rom_tile_w12.sv',
 'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die.sv': 'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv',
 'rtl/test/qwen_rom_runtime/qwen_rom_rt.cpp': 'rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp',
 'tools/qwen_rom_rt_core_emit.py': 'tools/qwen_rom_rt_core_emit_w12.py',
 'tools/qwen_rom_rt_token.py': 'tools/qwen_rom_rt_token_w12.py',
}


def digest(data):
 return hashlib.sha256(data).hexdigest()


def latency_extra(groups, acc, tree, mul):
 """Longest full-tree path: the partition bench's explicit LX expression."""
 return mul-5 + acc-5 + (groups-1).bit_length()*(tree-3)


def kv_geometry(groups=6144, tp=4, context=8192):
 if tp not in (2,4) or context<=0 or context & (context-1):
  raise ValueError('Requires TP2/4 and a positive power-of-two window')
 heads=8//tp; hb=context.bit_length()-1+3; prk=groups>>7
 if not prk or groups%4:raise ValueError('Invalid tile group geometry')
 rounds=math.ceil((1<<(hb-7))/prk); region=rounds*heads
 return dict(groups=groups,tp=tp,context=context,KV_NH=heads,KV_HB=hb,KV_VB=heads<<hb,
             K_local_words=region,V_local_words=region,total_local_words=2*region,
             slice_words=128,capacity_fits=2*region<=128,tiles_per_die=groups//4,
             macro_count_per_die=groups//4*2,macro_capacity_bytes_per_die=groups//4*2*128*32,
             padded_used_bytes_per_die=groups//4*2*region*64)


def declared(text, module):
 header=re.search(r'\bmodule\s+'+re.escape(module)+r'\s*#\s*\((.*?)\)\s*\(',text,re.S)
 if not header:raise ValueError('Missing actual module '+module)
 return set(re.findall(r'parameter\s+integer\s+(\w+)',header[1]))


def emitter_params(text):
 tree=ast.parse(text)
 for node in tree.body:
  if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SPINE_PARAMS' for t in node.targets):
   return set(ast.literal_eval(node.value))
 raise ValueError('Missing SPINE_PARAMS')


def source_reconcile(package, root):
 rows={}
 for old,new in MAPPING.items():
  item=package['files']['source/'+old];raw=base64.b64decode(item['base64'],validate=True)
  if digest(raw)!=package['source_sha256_at_capture'][old] or digest(raw)!=item['sha256']:
   raise ValueError('Runtime snapshot pin mismatch: '+old)
  current=(root/old).read_bytes();candidate=(root/new).read_bytes()
  rows[old]=dict(captured_sha256=digest(raw),current_sha256=digest(current),candidate_path=new,
                candidate_sha256=digest(candidate),captured_equals_current=raw==current,
                captured_to_candidate_diff=list(difflib.unified_diff(raw.decode().splitlines(),candidate.decode().splitlines(),fromfile=old,tofile=new,n=1)),
                acceptance='Candidate namespace is a separate source; differences require connected exactness. No hash transfer.')
 return rows


def physical_reconcile(physical, root):
 aliases = {'ot_hdc_matvec': 'ot_qwen_w12_matvec', 'ot_hdc_matvec_part': 'ot_qwen_w12_matvec_part',
  'ot_qwen_me_array': 'ot_qwen_me_array_w12', 'ot_qwen_me_spine': 'ot_qwen_me_spine_w12',
  'ot_qwen_me_node': 'ot_qwen_me_node_w12', 'ot_qwen_rom_tile': 'ot_qwen_rom_tile_w12',
  'ot_qwen_rom_tile_logic': 'ot_qwen_rom_tile_logic_w12', 'ot_hdc_tadd': 'ot_qwen_w12_tadd',
  'ot_hdc_ladd': 'ot_qwen_w12_ladd', 'ot_hdc_kadd': 'ot_qwen_w12_kadd',
  'ot_hdc_ksum': 'ot_qwen_w12_ksum', 'ot_hdc_ksa': 'ot_qwen_w12_ksa'}
 rows = {}
 expected = {item['path']: item['sha256'] for item in physical['design']['sources']}
 for old, new in list(MAPPING.items())[:3]:
  proc = subprocess.run(['git', 'show', physical['git']['commit'] + ':' + old], cwd=root, capture_output=True)
  if proc.returncode or digest(proc.stdout) != expected[old]:
   raise ValueError('Historical physical source pin mismatch: ' + old)
  text = proc.stdout.decode()
  renamed = re.sub(r'\b(?:' + '|'.join(sorted(aliases,key=len,reverse=True)) + r')\b', lambda m: aliases[m[0]], text)
  candidate = (root/new).read_text()
  rows[old] = dict(physical_sha256=digest(proc.stdout),candidate_path=new,candidate_sha256=digest(candidate.encode()),
   namespace_map=aliases,namespace_only_equal=renamed==candidate,
   residual_diff=list(difflib.unified_diff(renamed.splitlines(),candidate.splitlines(),fromfile='physical-namespace-renamed/'+old,tofile=new,n=1)),
   acceptance='Explicit namespace map is for review only; residual defaults, memory forwarding and arithmetic implementation differences need same-source gate.')
 return dict(commit=physical['git']['commit'],raw_status=physical['status'],source_joins=rows)


def prepare(package, root=ROOT):
 import sys
 sys.path.insert(0,str(root/'tools'))
 import uarch_model as U
 pins={};sources={}
 paths=set(MAPPING)|set(MAPPING.values())|{'tools/uarch_model.py','rtl/hdc/ot_qwen_w12_arith.sv',
  'rtl/test/tb_qwen_me_partition_w12.sv','tools/qwen_o4_kv_slice_map_w12.py','tools/qwen_rom_wire_budget_w12.py'}
 for name in sorted(paths):
  data=(root/name).read_bytes();pins[name]=digest(data);sources[name]=data.decode()
 reconciled=source_reconcile(package,root)
 physical_path=root/'results/rtl/qwen_rom_sidecar_20261002/tile_i518_terminal/00_physical.json'
 physical=physical_reconcile(json.loads(physical_path.read_text()),root)
 driver=sources['tools/qwen_rom_rt_token_w12.py']
 die=sources['rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv']
 emitter=sources['tools/qwen_rom_rt_core_emit_w12.py']
 tile=sources['rtl/hdc/ot_qwen_rom_tile_w12.sv']
 spine=sources['rtl/hdc/ot_qwen_me_array_w12.sv']
 arithmetic_chain={}
 for name,value in ARITH.items():
  arithmetic_chain[name]=dict(target=value,
   driver_tile_flag=f'-G{name}=' in driver,die_declared=name in declared(die,'ot_qwen_rom_rt_die_w12'),
   generated_core_declared_and_forwarded=name in emitter_params(emitter),
   tile_declared=name in declared(tile,'ot_qwen_rom_tile_logic_w12'),
   spine_declared=name in declared(spine,'ot_qwen_me_spine_w12'),
   tile_forwarded_to_engine=f'.{name}({name})' in tile,
   spine_forwarded_to_engine=f'.{name}({name})' in spine)
 missing={name:[k for k,v in row.items() if k!='target' and v is False] for name,row in arithmetic_chain.items()}
 geom=kv_geometry()
 expected=latency_extra(6144,7,7,6);priced=U.QWEN_SS['me_lat_extra']-U.QWEN_W12_TP4_ME_EXTRA_SS
 model=U.qwen_l0_rtl_vs_model()
 return dict(schema='opentallas.qwen-rom-integration-preflight.v1',status='blocked',adoption=False,build_ready=False,
  source_sha256=pins,source_reconciliation=reconciled,physical_reconciliation=physical,physical_record_sha256=digest(physical_path.read_bytes()),arithmetic_chain=arithmetic_chain,missing_arithmetic_paths=missing,
  model=dict(model_sha256=pins['tools/uarch_model.py'],existing_l0_body_cycles=model['model_layer_chain_cycles'],
   existing_per_allreduce_cycles=model['model_allreduce_cycles'],wire_cycles=U.QWEN_W12_TP4_ME_EXTRA_SS,
   source_formula_arithmetic_extra_cycles=expected,model_arithmetic_extra_cycles=priced,
   unpriced_cycles_per_me=expected-priced,model_kv_prep_token_cycles=U.QWEN_KV_PREP_CYCLES_TOKEN,
   latency_basis='LX=(MUL_LAT-5)+(ACC_LAT-5)+clog2(GT)*(TREE_LAT-3), pinned partition bench. Longest tree path; analytical discrepancy, not a measurement.',
   unpriced_token_delta='Reprice each actual ME issue in the composed token; do not use a layer ratio or blindly add to a prior calibrated record.',
   fast_issue='Physical target FAST_ISSUE=1; unified-model comment describes FAST_ISSUE=0. Same-cycle claim still needs same-source connected gate.'),
  kv=geom,kv_connection=dict(driver_forces_global='"-GKV_LOCAL=0"' in driver,
   host_reads_global_kv='x.kv_addr' in sources['rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp'],
   local_macro_fill_connected=False,local_read_capture_connected=False,
   required='Real macro-model local KV read/fill/mask service, TP4 KV_NH2/KV_VB131072, source-bound data and read-before-write collision semantics; current global address map defaults are dormant.'),
  sizing=dict(peak_macs_per_cycle_per_tile=64,tiles_per_die=1536,peak_macs_per_cycle_per_die=98304,
   active_code_read_bits_per_cycle_per_tile=532,active_code_read_bytes_per_cycle_per_tile=66.5,
   code_macro_bus_bits_per_tile=2*5*266,kv_read_bits_per_cycle_per_tile=512,kv_read_bytes_per_cycle_per_tile=64,
   kv_fill_data_bits_per_tile=512,kv_fill_mask_bits_per_tile=512,kv_fill_address_bits_per_tile=7,
   instruction_payload_bits_per_tile=3*18+13*24+13,x_boundary_bits_per_tile=128,
   subtree_result_bits_per_tile=512,node_input_bits_per_tile=1024,node_output_bits_per_tile=512,
   replica_fanout='6144 groups/4=1536 tiles per die; actual broadcast/fill mux/demux and repeaters remain unbound.',
   track_demand=None,channel_capacity=None,slot_fit=None,contextual_macro_clk_to_q=None,
   note='Counts price port demand and replica count; missing composed hub/fill routing, fanout, fit and corners prevent build readiness. Peak counts do not assert useful MAC utilization.'),
  blockers=['Connected driver/die/generated-core arithmetic parameter chain is absent',
   'MUL_LAT6 adds one longest-path ME cycle beyond the current +54 model price',
   'Global-KV runtime does not execute macro-local KV fill/read paths',
   'Historical physical tile differs from isolated companion defaults and MEM_EXTRA forwarding; default override alone is not source identity',
   'Hub/fill track demand versus capacity, mux/demux cost, final slot fit and contextual SS/FF unbound'],
  next_gate='Prepare whole driver->die->generated core->spine and driver->tile propagation together only after unified-model audit prices the actual issue-count delta and missing physical/fill demands. Then parent GO for one connected L0 global/local macro-KV comparison, golden tree order and all-rank checkpoints; keep candidate off by default.',
  heavy_jobs_launched=0,processes_signalled=[],claim_boundary='Source reconciliation and analytical target preparation only. No RTL build, timing closure, actual macro-local KV exactness, token/rate or adoption credit.')


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--package',type=Path,required=True);ap.add_argument('--result',type=Path,required=True)
 a=ap.parse_args()
 if a.result.exists():ap.error('Refusing to overwrite evidence')
 record=prepare(json.loads(a.package.read_text()));record['package_sha256']=digest(a.package.read_bytes());record['verifier_sha256']=digest(Path(__file__).read_bytes())
 a.result.parent.mkdir(parents=True,exist_ok=True)
 with a.result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(dict(status=record['status'],missing=record['missing_arithmetic_paths'],model=record['model'],kv=record['kv']),indent=2))


if __name__=='__main__':main()
