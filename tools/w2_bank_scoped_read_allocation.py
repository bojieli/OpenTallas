#!/usr/bin/env python3
"""One model-only, concurrency-preserving W2 selector allocation alternative."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P='rtl/experimental/w2_nc6_correction_control_split_20261003/ot_w2_nc6_correction_control.sv'
def model(mapped=None):
 s=(ROOT/P).read_text()
 # Actual source legality, context ownership and stage sequencing, not hypothetical low traffic.
 for clause in ['address>=16*engine && address<16*(engine+1)','address>=96','address>=145+3*engine && address<148+3*engine','g=145;g<169','for(e=0;e<8;e=e+1)','if(reserved[a])error=1;','current_raw[72*a+:72]!=rawword','current_fixed[72*a+:72]!=candidate','scrub_v[r]&&retire_ready[r]']:
  if clause not in s:raise ValueError('source scope changed: '+clause)
 old_raw=8*2*(219-1)*72
 new_raw=6*2*(16-1)*72+2*2*(120-1)*72
 old_peer=8*2*3*(219-1)*44
 new_peer=2*2*(8-1)*96
 return dict(schema='w2.bank-scoped-read-allocation.v1',source_sha256={P:hashlib.sha256(s.encode()).hexdigest()},
  candidate='Static legal-bank selectors, all eight correction engines retained per PC; fixed eight-context peer assembly',
  allocation=dict(controllers_per_die=128,representative_system_controllers=1280,engine_count_per_PC=8,stored_CW_per_PC=219,physical_stored_bits_per_PC=15768,table_engines={str(e):list(range(e*16,(e+1)*16)) for e in range(6)},utility_targets={str(e):[g for g in range(96,219) if not 145+3*e<=g<148+3*e] for e in (6,7)},peer_context_source='Only145..168; eight fixed96-bit assemblies from44+44+8 decoded payloads. Utilities can repair peer, never themselves. Table engines cannot target any context.'),
  concurrency=dict(normal_128_PC_parallelism='unchanged',bank_repairs_per_PC_parallel=6,utility_repairs_per_PC_parallel=2,global_reserved_target_bitmap=219,normal_single_user_added_edges=0,source_CAP=4,source_FIX=4,source_repair_recurring_II=9,source_normal_sameclient_II=19,source_differentclient_prospective_II=10,ready_held_retirement='unchanged; remains phase3 until actual identity-qualified retirement; no sameedge reuse',healthy_request_delay='0 added architecture edges; loaded synthesis/route delay not yet measured'),
  selector_budget=dict(reference_raw_fixed_bitmux_upper=old_raw,candidate_raw_fixed_bitmux_upper=new_raw,reference_peer_payload_bitmux_upper=old_peer,candidate_peer_context_bitmux_upper=new_peer,reference_NAND2_upper=3*(old_raw+old_peer),candidate_NAND2_upper=3*(new_raw+new_peer),upper_removed_NAND2=3*(old_raw+old_peer-new_raw-new_peer),scope='Constructive bitmux bound, not a measured gain. Existing ABC may already exploit legal masks; no savings credited before actual source mapping and subsequent proof/measurement.'),
  equivalence_obligations=['Preserve all219 CURRENT clean/CE/bad validation even outside selected bank; never narrow global fault observability','Illegal address/status/phase remains failclosed BEFORE any phase/offer/update; no out-of-range zero data turns invalid into valid','CURRENT-clean context trust/priority, both utilitiesdirty failclosed and other2words clean checks unchanged','Original/address/currentraw/currentfixed/syndrome/status checks precede offer and are independent of ready','Restore96 CURRENTdecoded peer bits, restart peerphase0 only actualretirement; no owncontext/duplicate-target/peer-write aliases','No new registers, queues, clock domain, SRAM substitute, PCsharing or copied oldstatus. Full219 storage and all8 concurrent contexts remain'],
  rejected_replica_reduction=dict(two_PC_group='Not selected: sixlane requests and different-client overlap do not prove physicalPC exclusivity. Sharing backend acceptance serializes simultaneous PCs, adds wait and changes static PC_ID identity.',bandwidth='Each32B accepted beat and prospective II10 already gives3.84GB/s/PC at1.2GHz, not actual HBM service qualification. Pair-sharing halves group per-PC saturation capability; sameclient II19 may be worse.',absolute_token_penalty=None,needed_before_any_PC_grouping='Actual selected-program per-PC accepted request/read/write calendars, dependency and concurrent service demand; current functional30case gate is not that journal.'),
  current_mapped_result=mapped,decision='MODEL_ONLY_WAIT_CURRENT_MAPPING; no alternative RTL or synthesis launch',new_RTL=False,new_job=False,source_current_job='Yosys304073 full219 source retained unchanged')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--mapped',type=Path);a=p.parse_args();a.out.write_text(json.dumps(model(json.loads(a.mapped.read_text()) if a.mapped else None),sort_keys=True,indent=2)+'\n')
