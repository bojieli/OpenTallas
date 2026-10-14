#!/usr/bin/env python3
"""Gather logical requirements only: final physical station coordinates absent."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/qwen_tp8_1012/vm_band_gather_plan_codex.json'

def main():
 base=ROOT/'physical/ref_tile/qfd_vm_xrelay_t';spec=json.loads((base/'spec.json').read_text());assert spec['params']==dict(W=512,MEREG=1)
 ins=base/'views/ot_qfd_vm_xrelay_t/insertion.json';assert ins.exists()
 rec=dict(schema='opentallas.qwen.vm-band-gather-plan.v1',status='LOGICAL_ONLY_UNMEASURED_ROOT_DELIVERY_AND_PRICE',root_delivery='UNMEASURED',production_throughput='UNMEASURED',production_price='UNMEASURED',qualification=False,
 input_order='q[128*col+4*root+k]',output_order='rootword[128*root+32*k+col]',roots=32,columns=32,elements_per_root_per_phase=4,data_bits=4096,
 tags=dict(phase_native_bits=2,phase_fallback_bits=4,epoch_bits=16,valid_bits=1,logical_designated_column=list(range(32)),physical_assignment='PENDING'),
 logical_latency_parameters_tested=[1,3],routing_latency='UNASSIGNED; LAT is not a physical route intent',
 master=dict(name='qfd_vm_xrelay_t',params=spec['params'],outline=spec['outline'],view=str((base/'views/ot_qfd_vm_xrelay_t').relative_to(ROOT)),insertion_source=str(ins.relative_to(ROOT)),insertion_sha256=hashlib.sha256(ins.read_bytes()).hexdigest()),
 logical_child_counts_per_latency_stage=dict(data_W512=8,padded_tag_W512=2,own_child_clock_entries=10),
 tag_padding=dict(padded_width=1024,input_tags=896,unused_bits=128),
 bench_alignment='EXACTLY logicalproxyalignment: full116fan composition followed by data through3actualrelay stages to match fan-control enableddepth. No actual sourceconsumer/line_store pipeline instantiated.',
 physical_requirements=['Die assigned32root stations and registered pin payload order including tags.','All actual data and designated-source-tag paths need equal enabled-edge latency with ME free-running path depth and localMEREG correctly scheduled.','Final paths stay entirely VM owned within existing band; no die signal/reset distribution over blockedVM.','Keep all270existing tiles/4096lanes and allfine/permutation mappings.','Every physical relay has independent phi-R childclock entry and actual per-pin TT/FF hop budget <=500um; no parent CTS.','Longer fan/gather depths need fullscheduler sourceconsumer c_a/c_nv/control alignment proof and measured rootdelivery.','Need physical cut tracks and PG subtraction at .48/net M8/M9 pitch9.091um; current reserved fraction10.56percent until authority resolves5.3percent claim.','Every new gather/relay physical tile must fit the assigned contract; accepted closed views stand.','Production throughput/price remains UNMEASURED pending integratedrealroots/end-to-end benchmark.'],
 bench_record='results/rtl/qwen_tp8_vm_plane_20261013/vm_band_gather/record.json')
 OUT.write_text(json.dumps(rec,indent=2)+'\n');print('PASS gather logicalplan roots=32 data_bits=4096 source_designation=32 UNMEASURED_rootdelivery_price')
if __name__=='__main__':main()
