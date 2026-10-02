#!/usr/bin/env python3
"""Bind local ROM KV addresses to persistent layer homes and required provider events.

Executable mapping/calendar prerequisites only. No provider execution, clocks,
allocation reservation, measured latency or unified-model changes.
"""
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from qwen_kv_bank_prototype import k_element, v_element

ROOT=Path(__file__).resolve().parents[1]
LAYERS, HEADS, CONTEXT, HD, WIDTH, TP = 36, 2, 8192, 128, 16, 4
WINDOW=HEADS*CONTEXT*HD
K_TOTAL=LAYERS*WINDOW
SECTOR_BYTES=32


def external_byte(layer, local_element):
 if not 0<=layer<LAYERS or not 0<=local_element<2*WINDOW:
  raise ValueError('Invalid source-owned layer/local element')
 return layer*WINDOW+local_element if local_element<WINDOW else K_TOTAL+layer*WINDOW+local_element-WINDOW


def home(layer, kind):
 if kind not in ('K','V'):raise ValueError('Unknown KV kind')
 base=external_byte(layer,0 if kind=='K' else WINDOW)
 return dict(layer=layer,kind=kind,logical_byte_begin=base,logical_byte_end_exclusive=base+WINDOW,
             logical_sector_begin=base//SECTOR_BYTES,logical_sector_end_exclusive=(base+WINDOW)//SECTOR_BYTES,
             physical_stack_map=None,allocation_reserved=False)


def event_dependencies(layer):
 if not 0<=layer<LAYERS:raise ValueError('Unknown layer')
 return dict(layer=layer,owner_fields=['user_slot','rank','layer','head','token_epoch','allocation_generation'],
  nodes=[dict(id='bind_owner',requires=['legal_resident_extent','selected_stack_map','published_old_position_version']),
   dict(id='prefetch_accept',requires=['bind_owner','finite_read_credit']),
   dict(id='return_to_tile_fill',requires=['prefetch_accept','matching_provider_tag_owner','codec_contract','tile_write_credit']),
   dict(id='local_read_permission',requires=['return_to_tile_fill','macro_write_visible','tail_current_row_published']),
   dict(id='consume_and_drain',requires=['local_read_permission','actual_last_read','return_reverse_retirement']),
   dict(id='tail_writeback_publish',requires=['actual_tail_flush_or_V_word_ready','full_sector_or_RMW_complete','actual_backing_commit','provider_completion_fence']),
   dict(id='local_window_reuse',requires=['consume_and_drain','no_stale_fill_or_reader_lease']),
   dict(id='tail_epoch_reuse',requires=['tail_writeback_publish','reverse_completion_retirement','no_reader_lease'])],
  timestamps=None,finite_service_cycles=None,
  note='Existing tail policy defers K writeback until position-tile closure; do not force K sector RMW per token or conflate local-window reuse with persistent tail reuse.')


def generate(provider_root):
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=provider_root,text=True).strip()
 provider_paths=['rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv',
                 'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv',
                 'results/uarch/qwen_hbm_endpoint_r14_20261002/review_r14.json']
 provider={p:subprocess.check_output(['git','show',revision+':'+p],cwd=provider_root) for p in provider_paths}
 review=json.loads(provider[provider_paths[2]])
 pkg=provider[provider_paths[0]].decode()
 if 'logic die; logic [1:0] stack; logic [33:0] sector;' not in pkg:
  raise ValueError('Re-review changed provider identity geometry')
 local_paths=['tools/qwen_rom_kv_owner_calendar_join.py','tools/qwen_kv_bank_prototype.py',
              'tools/hdc_qwen_fullshape_program_w12.py','rtl/hdc/kv/ot_hdc_kv_stream.sv',
              'tools/uarch_model.py','rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp']
 sources={p:(ROOT/p).read_bytes() for p in local_paths}
 homes=[home(layer,kind) for kind in ('K','V') for layer in range(LAYERS)]
 intervals=sorted((h['logical_byte_begin'],h['logical_byte_end_exclusive']) for h in homes)
 if intervals[0][0]!=0 or any(a[1]!=b[0] for a,b in zip(intervals,intervals[1:])):raise ValueError('Persistent-home overlap/gap')
 if any((ROOT/p).read_bytes()!=raw for p,raw in sources.items()):raise ValueError('Local sources changed')
 return dict(schema='opentallas.qwen-rom-kv-owner-calendar-join.v1',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='blocked',
  selected_configuration={'TP':TP,'layers':LAYERS,'KV_heads_per_die':HEADS,'context':CONTEXT,'head_dim':HD,'single_user':True},
  source_sha256={p:hashlib.sha256(raw).hexdigest() for p,raw in sources.items()},
  provider_ref=revision,provider_source_sha256={p:hashlib.sha256(raw).hexdigest() for p,raw in provider.items()},
  provider_review_status=review['status'],provider_review_blockers=review['blockers'],
  persistent_homes=homes,logical_total_bytes=2*K_TOTAL,logical_sector_count=2*K_TOTAL//SECTOR_BYTES,
  local_program_element_address_bits_required=(2*WINDOW-1).bit_length(),
  external_byte_address_bits_required=(2*K_TOTAL-1).bit_length(),external_sector_bits_required=(2*K_TOTAL//SECTOR_BYTES-1).bit_length(),
  translation='Keep A24 layer-local program addresses. External owner supplies layer/rank/user/allocation identity; map FP8 local elements into source-equivalent all-layer K/V layout. Physical base/stack allocation is deliberately unbound.',
  provider_identity_gap={'current_die_bits':1,'TP4_rank_bits_required':2,
   'action':'Cannot silently transfer the r14 two-die identity to four ROM ranks. Kepler/Maxwell must bind physical die versus logical rank and price any width/state/CDC changes before reuse.'},
  tail_geometry_candidate={'LOG_HD':7,'LOG_TW':9,'LLG':7,
   'meaning':'Generic stream K-tail word address slices: 128 dimension words, 512 position tiles, 72 layer/head owners rounded to 128.',
   'banks':2,'BF16_words_per_bank':16384,'capacity_bytes':1048576,'useful_two_tile_bytes':589824,
   'source_match_and_allocation_ready':False,'replica_read_port_and_mux_cost':None},
  provider_adapter_gaps=['Generic streamer FP8 words are 16B; provider sectors are 32B and tile fills are 64B. Bind sector assembly, masks and returned-beat ownership.',
   'Generic descriptor/request tags and 32-sector provider bursts require finite lookup/fragmentation/credits; do not truncate tags or assume full layer accepted at once.',
   'Tail group read ports/replicas and write arbitration need priced area/clock/latency beyond the two-bank capacity bookkeeping.',
   'Pinned r14 review blockers include reverse retirement/quarantine and composed accounting; Kepler remains provider owner.'],
  calendar=[event_dependencies(layer) for layer in range(LAYERS)],
  model_bridge_present='def qwen_rom_physical_successor(' in sources['tools/uarch_model.py'].decode(),
  existing_read_bytes_per_die=2*K_TOTAL,incremental_read_bytes_to_add=0,
  incremental_finite_service_cycles=None,allocated_stack_map=None,actual_provider_join=False,
  physical_build_ready=False,adoption=False,heavy_jobs_launched=0,
  claim_boundary='Canonical logical residence and event dependency preparation, not allocated HBM or connected provider proof. No synthetic timestamps, no added aggregate refill charge, no actual provider campaign or new architecture.')


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--provider-root',type=Path,required=True);ap.add_argument('--result',type=Path,required=True);a=ap.parse_args()
 if a.result.exists():ap.error('Refusing to overwrite evidence')
 r=generate(a.provider_root);a.result.parent.mkdir(parents=True,exist_ok=True)
 with a.result.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps({k:r[k] for k in ('status','logical_total_bytes','local_program_element_address_bits_required','external_byte_address_bits_required','provider_review_status','provider_identity_gap','model_bridge_present')},indent=2))
 return 1


if __name__=='__main__':raise SystemExit(main())
