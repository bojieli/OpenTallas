#!/usr/bin/env python3
"""Reconcile historical handoff claims with current protected native ingress."""
import hashlib,json
from pathlib import Path
from hbm_result_context_codec_model import context_codec_model
from hbm_sm_result_provider_model import model as durable_model
R=Path(__file__).resolve().parents[1]
def model():
 p=R/'results/rtl/hbm_sm_su_result_contract_20261007/contract.json';old=json.loads(p.read_text())
 assert old['summary']['rows_per_token']==3313 and old['summary']['barrier_handoffs']==343
 prot=context_codec_model();durable=durable_model()
 rows=max(x['rows_per_sm'] for x in old['rows_table'])
 assert rows==43
 estimated_entries=[x['node'] for x in old['rows_table'] if x['est']]
 nsm,frame=32,318
 payload_ff=nsm*rows*frame
 # Two independent reservation/sequence/bitmap/control copies perSM.
 controls_per_sm=2*(94+6+6+4+1+16+7+43)+2*rows*16
 read_mux2_per_sm=(rows-1)*frame
 base_forward=72+3+4+1+4+1
 mixed_forward=91+3+4+1+4+1
 known_ff=payload_ff+nsm*controls_per_sm+prot['all32_encoder_two_checker_FF_bits']
 return dict(schema='opentallas.hbm.native_su_ingress.reconciled.v1',selected=False,adopted=False,
  recommendation='Native reserved ingress is latency target; checked shared-memory endpoint is retained fallback. Neither path is a qualified fullSU execution join.',
  scope='DSV4.1 matched AR walk only. Admission checks perSM op_rows<=43 from exactwalk. Generic4096 native output and othertargets retain fallback until separatelysized.',
  legacy={'handoff_targets':old['summary']['handoff_targets'],'published_cycles_per_token':343,'historical_native_proposal':1029,'rejected_assumptions':['unprotected5slice transport','36station geometry','43x268buffer','2 SRAM perSM','wire alwayshidden under barrier']},
  fallback=dict(implemented_endpoint='ot_hbm_su_installed_span plus source-owned resultprovider and same5client sharedservice',
    memory_rows_per_token=3313,legacy_comparator_estimate_cycles=132520,
    legacy_formula='3313*(4+3*12); historical comparatorfloor only, not measurednative service',
    current_cost_formula='sum(perrow capture/drain +native measuredwriteACK +checkedreadback +SUreadreturn +adapter stages/contendedservice)',
    extra_adapter_cycles_per_sector_read=2,current_complete_cycles_per_token=None,
    scope='Actual new native sharedservice is distinct from comparator backend; do not publish132520 as its measured latency.'),
  native=dict(admission_evidence=dict(max_rows_source='contract.rows_table',estimated_entries=estimated_entries,
    required_runtime_gate='Reject launch unless actual protected op_rows is in1..43 and exact destination reservation has acknowledged; table bound is not universal model admission.'),per_sm_reserved_rows=rows,parallel_SM_count=nsm,stored_frame_bits=frame,
    additional_ingress_FF_bits=payload_ff,additional_ingress_rawFF_area_um2=payload_ff*.37908,
    protected_control_FF_bits_per_SM=controls_per_sm,
    protected_expected_row_sequence_FF_bits_per_SM=2*rows*16,
    codec_area_all32_at55pct_um2=prot['all32_encoder_two_checker_area_at55pct_um2'],
    read_mux_2to1_bits_per_SM=read_mux2_per_sm,
    full_row_read_wire_bits=frame,write_bits_per_cycle_per_SM=frame,bytes_per_valid_row=32,
    data_MACs_per_cycle=0,buffer_rawbits=payload_ff,
    buffer_slot_requirement='Place perSM or subgroup distributedbank, not one central318x43mux; finite readselection fanout and realconsumer pinmap remainunqualified',
    SRAM_existing_macro_alternative=dict(macros_per_SM=5,macro_shape='512x64',physical_rows=512,
       raw_macro_area_all_SM_um2=nsm*durable['macro_area_um2']/8,
       note='Existing512x64 compiler shape stores318bits in5macros; historical2macroestimatecannothold43fullprotectedframes'),
    durability=dict(retained=True,store_macros_all_SM=nsm*40,raw_store_area_all_SM_um2=nsm*durable['macro_area_um2'],
       critical_path=False,release='Durablepublication and SUconsumption trackedseparately; allocationcannotretire untilboth complete; do not countdurabilitycostaszero if it stallsnextoperation'),
    transport=dict(physical_frame_bits=318,slices=6,current_balanced_cycles=72,mixed_geometry_candidate_cycles=91,
       mixed_geometry_complete=False,encoder_cycles=3,ingress_checker_cycles=4,buffer_capture_cycles=1,consume_checker_cycles=4,lane_capture_cycles=1,
       extra_read_checker_FF_all_SM=nsm*prot['duplicated_checker_FF_bits'],
       encoder_area_revision='Context codec380 modeled:1654encoderFF and4304FF perduplicatedchecker, three+four+fourcycles; floorplan stillOPEN'),
    identity=dict(context_bits=94,layout='{owner73,record16,source5}',
       proposal='CRC covers independentlyheld protectedcontext94 +payload270+sequence16. Physicalframe remains318; fullcontext explicitheader alternative would be412bits/7slices.',
       current_crc_context_bound=True,context_binding_RTL_qualified=False,
       epoch_gate='Owner73 must contain a generation unique across retained frames; same owner/record/source cannot be rebound before all frame, buffer, consumer and durable debts drain. At65536 beat wrap receiver must quarantine unless bounded stale lifetime is proved; reset must flush both endpoints and transport before a new permit.',
       negative_gates=['same-sequence wrongSM','same-sequence wrongrecord','same-sequence oldowner generation','context DMR mismatch','sequencewrap with retained frame','reset in flight','duplicate or missing row','consume row mismatch'],source='actual checked runowner +installedrecord +fixedSM identity',
       lifetime='Reservation before sourcepermit; sequencechecked EVERY idle/valid beat. Native_done alone doesnotpublish: waitexactunique rows and allcheckerflight drained. Boundcontextcannotchange until consumer/drain/durable debts retire.',
       reset='Cold reset must suppress source permit and flush both ends under coordinated generation; warmreset cannot drop frame/buffer/owner debt.',
       recheck='Retain originalCRC/frame throughbuffer; compare checkedrow torequestedrow and independentlivecontext atactualSUread. No strip before unprotectedstorage.'),
    deterministic_forward_cycles_lower_bound=base_forward,
    deterministic_forward_cycles_incomplete_geometry_candidate=mixed_forward,
    no_overlap_exposure_accounting=dict(base_cycles_per_token=343*base_forward,mixed_candidate_cycles_per_token=343*mixed_forward,
       base_us=343*base_forward/1200,mixed_us=343*mixed_forward/1200,
       caveat='Forwardpipe accounting only; add actualreservation/control andconsumer contention. Neither overlap norcompletegeometryqualified, so nofinalheadline claim.'),
    known_additional_ff_including_codec=known_ff,
    physical_admitted=False,consumer_execution_bound=False,
    graph_liveness=dict(qualified=False,per_operation43_does_not_bound_simultaneously_live_leases=True,
      counterexample='wqa followed bywkv beforecombinedgather: holding sole producer context untilultimateSU release can deadlock',
      required='Bind actual nextconsumer publication and independently retained span/context leases; derive maximum live rows/reservations fromsourcegraph before selecting queue depth')),
  source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest(),
    'tools/hbm_result_context_codec_model.py':hashlib.sha256((R/'tools/hbm_result_context_codec_model.py').read_bytes()).hexdigest()})
if __name__=='__main__':print(json.dumps(model(),indent=2))
