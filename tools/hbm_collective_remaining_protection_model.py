#!/usr/bin/env python3
"""Source inventory of remaining protection debt; never a full mapping claim."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES=['rtl/hbm_accel/collective_native_link_20261007/ot_hbm_collective_native_link_candidate.sv','rtl/hbm_accel/ha2_ar/ot_ha2_parent_quiet_prims.sv','rtl/hbm_accel/ha2_ar/ot_ha2_truecredit.sv','rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_banked_half.sv','rtl/hbm_accel/ha2_ar/ot_ha2_tu_owner_banked.sv']

def model():
    rows=[]
    for name,w,d,n in [('hub_issue_flight',544,35,2),('delivery_flight',545,35,4),('truecredit_forward_flight',560,7,2),('truecredit_return_flight',16,7,2)]:
        rows.append(dict(name=name,implementation='ot_ha2_delay_quiet',replicas=n,width=w,depth=d,payload_bits=n*w*d,valid_bits=n*d,pointer_declared_bits=n*32,protection='none; quiet/finite credits detect occupancy, not bit corruption',count_scope='RTL declared storage; synthesized pointer width may optimize'))
    rows.append(dict(name='partial_launch',payload_bits=8*545,valid_bits=8,protection='none',count_scope='one registered stage before half-rate owner'))
    return {
        'status':'OPEN_MUTABLE_PROTECTION_CENSUS_NOT_ADOPTED',
        'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES},
        'native_shape':dict(NC=8,NPT=8,INJ=2,DEL=4,LANES=16,PFMAX=384,HUBW=35,WSTG=14,TC_FWD=7,TC_RET=7),
        'raw_relay_rows':rows,
        'raw_relay_declared_bits_subtotal':sum(r.get('payload_bits',0)+r.get('valid_bits',0)+r.get('pointer_declared_bits',0) for r in rows),
        'internal_truecredit':dict(owner='/root/hbm/w2',payload_queue_bits=2*64*560,model_total_TX_FF_bits=1216,model_total_RX_FF_bits=72900,protection='Tag sequence and count/overflow checks are protocol checks; no payload SECDED. Actual current sources use plain registers/FIFOs. Source owner confirms scope before successor.',double_count='TX/RX model totals already include payload queues and endpoint registers; do not add queue bits again'),
        'half_rate_shell':dict(peer_queue_payload_bits=8*8*545,own_queue_payload_bits=2*8*528,queue_control_declared_bits=10*(8+8+4+1),fast_input_capture_bits=2*528+8*545+1+1+8+16+2+8,output_capture_and_status_bits=16+512+5,phase_gate_arm_hold_ready_bits=1+1+1+4+8+2,protection='Plain data/control flops, one-hot pointers, count/overflow checks; no payload ECC or protected phase/clock enable.',double_count='These registers are a subset of actual full h2 mapped171444FF, not additional to that census.'),
        'h2_operand_SRAM':dict(macros=8,rows_per_macro=64,payload_bits_per_row=512,physical_payload_bits=8*64*512,encoded_bits_required_per_payload_row=8*72,extra_check_bits_if_SECDED64=8*64*64,actual_source='u_col64x512 read output mq feeds reductiontree without an SECDED decoder or separately stored checks',protection='Absent in selected source. ROM no-ECC exemption does not cover mutable operand SRAM.',physical_obligation='576 encoded bits per512bit payload need a real wider macro or priced sidecar. Eight existing64x512 macros cannot hold full encoded rows. Do not silently reuse current840x480 outline for changed storage.'),
        'native_context_control':dict(protection='Context identity/range checks exist; context latches, routing counters, delivery accounting and scheduling state still require explicit per-register fault coverage.',exact_register_count=None),
        'h2_core_control_and_arithmetic_pipeline':dict(protection='Mapped full h2 inventory is known; full semantic fault/protection census remains pending. Register count alone is not proof of protection.',exact_unprotected_bits=None),
        'already_separately_protected':'New33packet/landingqueues,16dataCDC,16flight14 paths, externallink credit/session protocols. Their counts are excluded from this raw-state subtotal.',
        'replacement_constraints':'A protected elastic relay may stall during scrub: it cannot replace an unstallable delay unless actual upstream reservation/injection and downstream acceptance are bound. Model repair stalls, row capture, extra check storage and real CTS/area before a successor. Fault quarantine is distinct from corrected successful continuation.',
        'adoption_hold':'No complete protected collective or reliability claim. Existing fullshape arithmetic and physical screens remain useful, source-pinned evidence for their stated narrower scope.'
    }

if __name__=='__main__':print(json.dumps(model(),indent=2))
