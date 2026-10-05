#!/usr/bin/env python3
"""Reconcile existing Qwen ROM HBM residence policy before adding finite refill costs."""
import argparse
import datetime
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def generate(context=8192):
 import arch_budget_qwen3 as Q
 import uarch_model as U
 if Path(Q.__file__).resolve()!=(ROOT/'tools/arch_budget_qwen3.py').resolve() or Path(U.__file__).resolve()!=(ROOT/'tools/uarch_model.py').resolve():
  raise ValueError('Model imports belong to another source root')
 paths=['tools/qwen_rom_kv_residence_gate.py','configs/models/qwen3-8b.json','configs/hardware/technology.json','tools/arch_budget_qwen3.py','tools/uarch_model.py','tools/hdc_program.py',
        'tools/hdc_qwen_fullshape_program_w12.py','tools/qwen_kv_bank_prototype.py',
        'rtl/hdc/kv/ot_hdc_kv_stream.sv','rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp',
        'tools/qwen_rom_rt_token_w12.py','rtl/hdc/ot_qwen_rom_tile_w12.sv']
 raw={p:(ROOT/p).read_bytes() for p in paths}
 pins={p:hashlib.sha256(b).hexdigest() for p,b in raw.items()}
 wl=Q.workload(context);global_read=Q.kv_bytes(wl,'fp8')
 die_read=global_read*2/8 # selected TP4 slice: 2 of 8 KV heads
 bandwidth=4*U.HBM_STACK_BPS
 host=raw['rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp'].decode()
 driver=raw['tools/qwen_rom_rt_token_w12.py'].decode()
 layer=raw['tools/hdc_qwen_fullshape_program_w12.py'].decode()
 stream=raw['rtl/hdc/kv/ot_hdc_kv_stream.sv'].decode()
 assert 'ROM_KV_HBM' in raw['tools/arch_budget_qwen3.py'].decode()
 assert 'assert layer == 0' in layer and 'std::fill(mem[d].kv.begin(), mem[d].kv.end(), 0u)' in host
 assert '"-GKV_LOCAL=0"' in driver
 assert 'ot_hdc_kv_stream' not in host and 'ot_hdc_kv_stream' not in driver
 header=stream.split(') (',1)[1].split(');',1)[0]
 header=re.sub(r'//[^\n]*','',header)
 input_ports=re.findall(r'\binput\s+(?:wire|reg)\s+(?:\[[^\n]*\]\s*)?(\w+)',header)
 assert 'hq_rdy' in input_ports and not any('ack' in name.lower() or 'fence' in name.lower() for name in input_ports)
 # The arithmetic identity reconciles the earlier conditional reload count
 # to the existing whole-program KV byte charge; it does not add latency.
 derived=36*2*2*128*context
 if die_read!=derived:raise ValueError('Existing KV byte term differs from dimension analysis')
 if any((ROOT/p).read_bytes()!=b for p,b in raw.items()):raise ValueError('Sources changed')
 return dict(schema='opentallas.qwen-rom-kv-residence-reconciliation.v1',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  status='blocked',source_sha256=pins,context=context,tp=4,
  residence_policy_in_source=True,actual_runtime_persistent_hbm_bound=False,
  existing_policy='Own heads reside in die-local HBM; layer l+1 prefetch overlaps layer l. Current token row stays in tail and writes back behind stream. This is the existing policy, not a new architecture.',
  existing_generic_streamer='ot_hdc_kv_stream has HBM read response tags, finite window and tail; writes have request acceptance but no explicit writer completion ACK port. Its described ordered pseudo-channel service is not a bound current TP4 tile-fill provider.',
  current_runtime='LayerZero asserts layer==0; images and stage-local host KV service switch/reset. KV_LOCAL0 and host global KV reads bypass macro-local fill and the generic HBM streamer. Original position-zero checkpoints do not prove persistent multi-token HBM state.',
  persistent_address_gap='Generic Layout/prototype includes layer in K/V addresses; current layer-local emitted images omit it. Need external owner/translation identity (user, rank/head, layer, token epoch, address extent), not a raw copy of generic all-layer element addresses into A24 local ISA fields.',
  byte_ledger=dict(existing_fp8_kv_read_bytes_whole_model=global_read,existing_fp8_kv_read_bytes_per_TP4_die=die_read,
   earlier_conditional_reload_bytes_per_die=derived,same_bytes=True,
   existing_kv_write_bytes_whole_model=wl['bytes']['kv_write']/2,
   aggregate_bandwidth_assumption_bytes_s=bandwidth,
   aggregate_read_lower_bound_cycles_at_1p2GHz=die_read/bandwidth*1.2e9,
   incremental_full_reload_bytes_to_add=0,incremental_finite_refill_cycles=None),
  existing_model_terms=[dict(function='arch_budget_qwen3.rom_token',scope='max(compute, aggregate KV stream) token bound; not a finite layer calendar'),
   dict(function='arch_budget_qwen3.kv_prefetch_buffer_bytes',scope='one-layer ring plus bandwidth*tRFC; historical TP2/package sizing, not adopted TP4 tile-slot allocation'),
   dict(function='uarch_model.qwen_tp_point',scope='KV stream in saturated bounds/capacity; cycles assignment is sequencer+exchange+embedding, without actual finite refill calendar'),
   dict(function='arch_budget_qwen3.as_built',scope='KV on-core assumption, stream separately priced; no accepted HBM response/visibility stalls in sequencer timing')],
  required_binding=[
   'Retain existing HBM policy; bind legal per-layer/rank/user extents and packed K/V codecs to selected emitted local program addresses.',
   'Bind old-position HBM fetch and current/open-tail producer identity, publication and read visibility at layer switch and next token.',
   'Specify concrete finite fill lane count, pseudo-channel ownership, ring/tile buffers, credits, masks and service latency; reconcile codec/transport terms already charged.',
   'Qualify writes via provider completion/fence, not request acceptance; prevent refill/eviction until required ACK and reader drain; reset/stale tags must be checked.',
   'Compose exposed issue waits and layer-hop transfer/codec/CDC costs with existing read term exactly once; Maxwell prices only the incremental finite-service gap.',
   'Join actual macro-local read/fill/collision and persistent current-source token before physical/model qualification.'],
  model_rates_changed=False,physical_build_ready=False,adoption=False,heavy_jobs_launched=0,
  claim_boundary='Source-owned existing-policy and byte-charge reconciliation only; no actual HBM residence/runtime/provider correctness, finite-service latency calibration or adopted new topology.')


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result',type=Path,required=True);a=ap.parse_args()
 if a.result.exists():ap.error('Refusing to overwrite evidence')
 r=generate();a.result.parent.mkdir(parents=True,exist_ok=True)
 with a.result.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({k:r[k] for k in ('status','residence_policy_in_source','actual_runtime_persistent_hbm_bound','byte_ledger')},indent=2))
 return 1


if __name__=='__main__':raise SystemExit(main())
