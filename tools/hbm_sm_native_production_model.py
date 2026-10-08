#!/usr/bin/env python3
"""Pre-build composition for one native owner and its actual sector clients."""
import json,hashlib
from pathlib import Path
from hbm_sm_serial_protection_model import model as owner
from hbm_sm_descriptor_bridge_model import model as descriptor
from hbm_sm_program_provider_model import model as program
from hbm_sm_weight_x_model import model as readers
from hbm_sm_result_provider_model import model as result
from hbm_sm_native_allocation_model import model as allocation

def model(records=256):
    p,w,r=program(),readers(),result()
    cp=Path(__file__).resolve().parents[1]/'results/uarch/hbm_sm_control_u_path_20261007/probe.json'
    paths=json.loads(cp.read_text());stages=[x['forward_register_stages'] for x in paths['rows']]
    return dict(status='prebuild_parent_candidate',replicas=32,MACs_per_cycle=0,
        owner=owner(),descriptor=descriptor(),allocation=allocation(records),
        program=p,readers=w,result=r,
        shared_service_join_instances_per_owner=1,
        duplicated_join_state_removed_bits=2*677,
        source_selection='program0, weight1, X2, result3; one reserved service response; selected client retained across backpressure; actual reverse grant gates next request',
        program_source='literal installed program_base/program_limit and sector-padded program_storage_limit from native installer; exact ten-word native record unchanged',
        per_record_metadata_ROM_bits=records*(1+13+24+32+37+8+7+37+37),
        mutable_parent_state=dict(run_context_bits=194,context='duplicate owner73+source5+issuer_tag16 latched only on accepted native run; live flag dualrail and actual arrive toggle; immutable tuple indexed by protected owner record',association='each accepted service request captures {owner73,record16,source5}; real returned192identity checked before consumer qualification'),
        reservation='owner allocation accepted only when actual full4096 result-store reservation accepts; allocation response withheld until64-cycle bitmap clear completes and source_permit asserts',
        publication_guard_bits=8,publication_guard_latency='durable visibility followed by actual SU publication, exact SU reads/consumption and matching release before ownerretirement;2extra phase edges',
        result_identity='reserve record is actual alloc_record; publication_record comes from result store after actual arrive, all unique rows, all write ACKs and readbacks',
        minimum_traffic_per_record='program10*32bytes + weight_lines*160bytes + optional Xextent*3328bytes + result_rows*64bytes write/readback',
        service_peak_bytes_per_edge=32,
        serialized_latency='program10 service RTTs + result reserve64 edges overlapped only with allocation wait + Xextent*104 service RTTs + actual weight/arithmetic result timing + result_rows*(4+write/read RTTs) + descriptor2P+2; precise measured component latencies compose without assumed overlap',
        north_south_geometry=dict(status=paths['status'],source_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),paths=paths['successful_paths'],min_P=min(stages),max_P=max(stages),sum_P=sum(stages),register_bits_all_SM=120*sum(stages)+239*len(stages),per_SM_P={x['sm']:x['forward_register_stages'] for x in paths['rows']},physical_BPins_SSFF_qualified=False),
        result_macro_area_all32_mm2=32*r['macro_area_um2']/1e6,
        physical_capacity='no result macro reservation yet; existing VM rejected because one shared seat and66,016total payload bytes, below one full result burst',
        open=['actual installed hardware recipe/enrollment','real shared-client identity issuer arbitration','independent mapped protection banks','registered verifier consuming-edge fault protection','result SRAM placement and pinpaths','SS/FF','native arithmetic integrated exactness'],
        production_installation_complete=False,physical_admitted=False)
if __name__=='__main__':print(json.dumps(model(),indent=2))
