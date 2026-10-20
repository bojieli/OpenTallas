#!/usr/bin/env python3
"""Price candidate receiver-face rings; never treats an owed crossing as bound."""
import argparse, collections, hashlib, json, math
from pathlib import Path
T = 833.333

def window(phases, margin=100., region_reserve=160.):
    # Existing SRAM D8 macro calendar: age=(L-3)*T+phi,
    # calibrated usable aperture [1.25T,4.125T]. No timing mask is added.
    lo=min(phases)-margin-region_reserve
    hi=max(phases)+margin+region_reserve
    choices=[L for L in range(3,17) if (L-3)*T+lo>=1.25*T and (L-3)*T+hi<=4.125*T]
    return dict(phi_interval_ps=[lo,hi], feasible_L=choices,
                selected_L=min(choices) if choices else None,
                window_ok=bool(choices))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('owed',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
    raw=a.owed.read_bytes(); x=json.loads(raw)
    ledger=[]; counts=collections.Counter(); bits=collections.Counter()
    for r in x['detail']:
        if r['cls']=='BUMP': kind='static_strap_source_epoch_required'
        elif r['src_master'].startswith('qfd_dv_slice2') and r['dst_master'].startswith('qfd_dv_slice2'):
            kind='receiver_face_ring'
        else: kind='root_or_endpoint_binding_required'
        counts[kind]+=1; bits[kind]+=r['bits']
        ledger.append(dict(r,mechanism=kind,source_implemented=r['bus']=='n_dv_st_E1_st_u_st',bound=False,
                           schedule_adopted=False))
    phases=[-70.086914,56.322754]
    rec=dict(schema='opentallas.qwen_slice_face_landing_candidate.v1',
      source_receipt_sha256=hashlib.sha256(raw).hexdigest(),physical_qualification_eligible=False,
      totals=dict(links=len(ledger),bits=sum(r['bits'] for r in ledger),by_mechanism=dict(counts),bits_by_mechanism=dict(bits)),
      representative=dict(bus='n_dv_st_E1_st_u_st',src='dvs_E1/st_wo',dst='dvs_E2/st_ei',
       ck_s='dvs_E1/ck[0] = n_clk_r96',ck='dvs_E2/ck[0] = n_clk_r122',
       phases_tt_ff_ps=phases,phase_basis='TT late difference; FF early difference, same corner/pin per subtraction',
       D=8,width=1088,macro_count=17,macro_type='ot_sram_1r1w2c_32x64_m1',
       payload_ring_bits=1088*8,allocated_sram_bits=17*32*64,
       bytes_per_cycle=136,boundary_bits_per_cycle=1088,static_no_backpressure=True,
       schedule_added_receiver_edges=5,token_delta_ps_per_traversal=5*T,
       K_rule='(L+G-R0-2) mod16, latched during reset; G/R0 exact release receipts required',
       macro_area_um2=17*31.992*17.304,physical_area_um2=None,area_status='macro LEF plus mapped control census required before gate',
       **window(phases)),
      # These are FORWARDED lane drift maxima, not the signed phase range
      # of this slice pair. They MUST NOT be substituted for pair measurements.
      global_drift_scope=dict(g5_ps=1536.3,g5b_ps=2568.9,applies_to='forwarded lane drift, not slice pair phase'),
      ledger=ledger)
    cohort=[r for r in ledger if r['src']=='dvs_E1' and r['dst']=='dvs_E2']
    assert len(cohort)==10 and sum(r['bits'] for r in cohort)==2743
    rec['coherent_cohort']=dict(src='dvs_E1',dst='dvs_E2',width=2743,
      buses=[dict(bus=r['bus'],bits=r['bits'],added_receiver_edges=5) for r in cohort],
      byte_equivalent_per_cycle=2743/8,ring_slices=15,macro_count=43,
      allocated_sram_bits=43*32*64,payload_ring_bits=2743*8,
      macro_area_um2=43*31.992*17.304,physical_control_area_um2=None,
      same_epoch_and_offset=True,schedule_adopted=False,**window(phases))
    assert len(ledger)==185 and rec['totals']['bits']==50270
    assert rec['representative']['selected_L']==5
    a.out.write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec['totals']))
if __name__=='__main__': main()
