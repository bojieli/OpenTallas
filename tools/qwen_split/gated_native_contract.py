#!/usr/bin/env python3
"""Source-bound contract MODEL. Never emits SDC or a physical PASS.

Reuses immutable real-edge observations; no root phase is selected here.
"""
import hashlib
import json
from pathlib import Path
import argparse
import importlib.util

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(root):
    pinned = {'qfd_fwd_lane.sv':'271bbf832f28a5bb9d9d0562c46b185c94ebd0c2b8ec61303f6537d3534e79cf',
              'ot_hdc_cg.sv':'151f926bd2822e0fb2a684930748fbf79feba020f6618f8af543f88eb6bef047',
              'bench_fwd_lane.sh':'3514631b3f151503cbad224cbd6b78a0673e3d5fc052a83583b7af70b2b96786',
              'qfd_gated_land180_r2_masters.sv':'53f75e67188a4dc061b60e31067b95debffb9569028bb0aaebcfc054966c94ef',
              'land_generated_clocks.py':'ee4ec12294a3524b014c2d604d7820a003c29a3280a702d7890885a162e9ce31'}
    for name, digest in pinned.items():
        assert sha(root/'source'/name)==digest, f'source bytes changed: {name}'
    cert = json.loads((root/'behavioral_certificate.json').read_text())
    assert sha(root/'behavioral_witness.log') == cert['witness_sha256']
    src = (root/'source/qfd_fwd_lane.sv').read_text()
    cg = (root/'source/ot_hdc_cg.sv').read_text()
    for fragment in ['always @(posedge wclk[0]) b0 <= i;',
                     'always @(posedge rclk[0]) r0 <= ~b0;',
                     'wire read_run=warm && ready1;',
                     'wire ready_reset_n=rs1 && full_w;',
                     'always @(posedge ck) k_q<=k;']:
        assert fragment in src, fragment
    assert "ICGx1_ASAP7_75t_R u_icg (.CLK(clk), .ENA(en), .SE(1'b0), .GCLK(gclk));" in cg
    assert 'always_latch if (!clk) en_l = en;' in cg
    rows=[]
    seen=set()
    for row in cert['rows']:
        key=(row['scenario'],row['bank'])
        assert key not in seen
        seen.add(key)
        k=row['scenario']%8
        phase=(row['scenario']//8)%8
        assert k==row['K'] and phase/8==row['root_phase_T']
        age=row['min_age_T']
        gap=row['min_overwrite_gap_T']
        assert abs(age+gap-4)<1e-6
        for side in ('write','read'):
            p=row[side+'_phase_cycles']
            assert row[side+'_generated_edges']==[1+2*p,2+2*p,9+2*p]
            edge=(row['first_w_ns' if side=='write' else 'first_r_ns']-5)/10
            if side=='read': edge-=phase/8
            assert abs(edge-round(edge))<1e-6 and round(edge)%4==p
        assert abs(row['actual_capture_ns']-row['actual_launch_ns']-10*age)<1e-6
        assert abs(row['actual_next_overwrite_ns']-row['actual_capture_ns']-10*gap)<1e-6
        rows.append(dict(scenario=key[0],bank=key[1],K=k,
                         write_edges=row['write_generated_edges'],read_edges=row['read_generated_edges'],
                         observed_root_phase_T=phase/8,phase_authority='BEHAVIORAL_ONLY',
                         age_T=age,overwrite_gap_T=gap,
                         ideal_setup_budget_ps=age*(2500/3)-210,
                         ideal_hold_budget_ps=gap*(2500/3)-125,
                         # No measured C2Q, setup, hold, skew, or route is subtracted.
                         physical_admission='REFUSED'))
    assert seen=={(s,b) for s in range(384) for b in range(4)}
    proposal=importlib.util.spec_from_file_location('typed_land_proposal',root/'source/land_generated_clocks.py')
    typed=importlib.util.module_from_spec(proposal)
    proposal.loader.exec_module(typed)
    typed_rows,typed_cases=typed.validate_certificate(cert)
    assert len(typed_rows)==1536 and len(typed_cases)==384
    clocks=[]
    for side,master,port in [('w','ot_entry_1','ck_s'),('r','ot_entry_0','ck')]:
        for b in range(4):
            clocks.append(dict(name=f'qfd_{side}bank{b}',master=master,source_port=port,
                source_pin=f'u_land.u_gated.u_{side}bank{b}/u_cg.u_icg/CLK',
                target_pin=f'u_land.u_gated.u_{side}bank{b}/u_cg.u_icg/GCLK',
                cell='ICGx1_ASAP7_75t_R',enable_pin='ENA',test_pin='SE',test_value=0,
                active_edge='rising',period_parent_cycles=4,high_parent_cycles=.5,
                enable=('meta_we && wslot' if side=='w' else 'warm && ready1 && readsel')+f'[{b}]',
                edge_indices=None,edge_binding='per admitted reset epoch; source-bound phase required'))
    later=[]
    for row in rows:
        age=row['age_T']+1
        later.append(dict(scenario=row['scenario'],bank=row['bank'],K=row['K'],
                          age_T=age,overwrite_gap_T=4-age,
                          ideal_setup_ps=age*(2500/3)-210,
                          ideal_hold_ps=(4-age)*(2500/3)-125))
    def size(D,W):
        aw=D.bit_length()-1
        regions=(W+15)//16
        # Generalization of the actual D4 declaration inventory, not new RTL.
        global_ff=2+2+3*(aw+1)+D+(aw+1)+1+2+1+D+2*D*(aw+1)+(aw+1)+aw+1+1
        icg=2*D+1
        return dict(D=D,W=W,regions=regions,data_ff=(2*D+1)*W,
                    region_ff=(D+1)*regions,global_ff=global_ff,icg_latches=icg,
                    total_state=(2*D+1)*W+(D+1)*regions+global_ff+icg,
                    bank_period_T=D,epoch_modulus=2*D,K_bits=aw+1,
                    native_area_um2=None,physical_admission='REFUSED')
    assert size(4,180)['total_state']==1748 # prior conservative source bound, mapped1746
    comparison=dict(
        status='MODEL_ONLY_NO_SOURCE_AUTHORIZATION',production_legal_K=None,hardware_legal_K=list(range(8)),
        production_inventory_reason='No selected gated production GEN/netlist/strap exists; actual dv2f18dh2 is legacy.',
        minK2_is_not_age_bound=dict(retained_K=list(range(2,8)),
            remaining_nonpositive_setup_bank_cases=sum(r['K']>=2 and r['ideal_setup_budget_ps']<=0 for r in rows)),
        extra_final_capture=dict(extra_receiver_edges=1,extra_payload_ff=180,
            diagnostic_alignment_ff_upper_model=1,internal_bank_age_change_T=0,
            remaining_nonpositive_setup_bank_cases=sum(r['ideal_setup_budget_ps']<=0 for r in rows)),
        uniform_later_read_D4=dict(extra_receiver_edges=1,
            at_or_after_overwrite_bank_cases=sum(r['overwrite_gap_T']<=0 for r in later),
            negative_ideal_hold_bank_cases=sum(r['ideal_hold_ps']<0 for r in later),
            maximum_age_T=max(r['age_T'] for r in later),rows=later),
        deeper_D8_uniform_later_read=dict(extra_receiver_edges=1,extra_initial_fill_source_edges=4,
            minimum_overwrite_gap_T=min(8-r['age_T'] for r in later),
            single_W180=size(8,180),split_W108=size(8,108),split_W96=size(8,96),
            boundary600_W108=dict(tiles=6,padding_bits=48,total_state=6*size(8,108)['total_state'],icgs=102),
            boundary600_W96=dict(tiles=7,padding_bits=72,total_state=7*size(8,96)['total_state'],icgs=119),
            state_threshold='W180 exceeds2kb source bound; partition or a genuine SRAM architecture required',
            all_fields='payload,valid,slot,epoch,command controls must move together',
            prologue='8physicalwrites then actualready/warm and2receiveredges; absoluteorigins unbound',
            reset_abort='No-use/drain, pairedreset, modulo16 epoch and K-wrap firstuse require new source proof'))
    return dict(schema='opentallas.qwen.gated_native_contract.MODEL.v1',
        status='SOURCE_EDGE_MODEL_PASS_PHYSICAL_ADMISSION_REFUSED',
        source_commit='6b61a90c197f8248a026ca4937c9aebd9ff7dccb',
        tools_commit='59835e962',
        source_sha256={str(p.relative_to(root)):sha(p) for p in (root/'source').glob('*') if p.is_file()},
        source_model_checks=len(rows),behavioral_checks=cert['checks'],
        scenario_count=384,banks=4,K=list(range(8)),clocks=clocks,
        parent_phase_guarantee=None,native_liberty_arc_bounds=None,
        compiled_reset_epoch_manifest=None,native_clock_family_receipt=None,
        cold_warm_abort_production_manifest=None,
        reserves_ps=dict(crossroot_setup=150,crossroot_hold=100,setup_uncertainty=60,hold_uncertainty=25),
        current_direct_D4_E2_ideal_setup_ps=(2500/3)-(210+.75*(2500/3)),
        minimum_candidate_ideal_setup_ps=min(r['ideal_setup_budget_ps'] for r in rows),
        nonpositive_candidate_ideal_setup_bank_cases=sum(r['ideal_setup_budget_ps']<=0 for r in rows),
        minimum_candidate_ideal_hold_ps=min(r['ideal_hold_budget_ps'] for r in rows),
        architecture_comparison=comparison,
        rows=rows)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('packet',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    result=build(args.packet)
    args.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','clocks','source_sha256','architecture_comparison')}))
