#!/usr/bin/env python3
"""NC6 direct component enrollment, before new RTL; no whole-route admission."""
import json
from w2_pc_exact_completion_model import size, OUT

def model():
    base=size(nc=6)
    facts=json.loads((OUT/'inputs/cell_prices.json').read_text())['facts']
    # Explicit conservative gate budget, not a mapped netlist/loaded path.
    guard_nand=2*(4*39+38+8)+64
    guard_inv=2*(39+38+4)+32
    guard_area=(guard_nand*facts['NAND2x1_ASAP7_75t_R']['SS']['area_um2']+
                guard_inv*facts['INVx1_ASAP7_75t_R']['SS']['area_um2'])/1e6
    return dict(geometry=dict(NC=6,MAX_OUT=16,CTAGW=32,GENW=4,SIDW=3,PTAGW=35,scoped_tag_plus_generation=39,AW=34),
        default_enable=0,new_directory_client=False,sector_bytes=32,R14_LEN=1,R14_BEAT=0,
        clock=dict(functional_fixture_period_ps=1000,domain='single component service clock',
            lookup_stages=1,source_R14_clock_not_inherited=True,SS_setup_hold_qualified=False,
            physical_loaded_clock_budget=None,physical_admission=False),
        reset=dict(cold_rst_n='External all-copy-fenced cold initialization only; unsafe asynchronous reset outside component contract',
            runtime='rearm_v && admission_stop && provider_fenced && reset_fenced && idle',
            rearm_erases_live_debt=False,unfenced_rearm_latches_fault=True,
            fault_freezes_normal_acceptance_and_release=True,
            fault_with_live_debt_requires_external_provider_recovery=True),
        state=dict(base_raw_bits=base['state_bits_per_PC'],same_edge_issue_capture_invalid_bits=2,
            implemented_raw_bits=base['state_bits_per_PC']+2,
            protected_bits=base['protected_storage']['bits_per_PC'],
            invalid_bits_fit_existing_query_protection_padding=True,
            capture_guard_extra_comparators=2,capture_guard_key_bits=39,
            extra_guard_and_fence_logic_NAND2_budget=guard_nand,
            extra_guard_and_fence_logic_INV_budget=guard_inv,
            old_gross_body_mm2_assumed=base['protected_storage']['gross_body_mm2_per_PC_ASSUMED'],
            extra_guard_fence_body_mm2_ASSUMED=guard_area,
            protected_gross_body_mm2_perPC_ASSUMED=base['protected_storage']['gross_body_mm2_per_PC_ASSUMED']+guard_area,
            all128PC_50pct_screen_mm2_ASSUMED=2*128*(base['protected_storage']['gross_body_mm2_per_PC_ASSUMED']+guard_area),
            updated_physical_area_qualified=False,storage_protection_implemented=False),
        ports=base['port_signal_bits'],additional_controls=dict(admission_stop=1,rearm_v=1,provider_fenced=1,reset_fenced=1,rearm_rdy=1,idle=1),
        latency=dict(request_selection_to_backend_accept_min=1,backend_read_to_client_accept_min=2,
            backend_write_to_client_accept_min=3,request_read_II=2,write_query_II=1,
            clocks='service edges; no crossclock sum, physical latency unqualified'),
        gate=dict(scope='NC6 functional completion component only; no native caller or R14 backend provider',
            tests=['heldrequest','heldread','heldwrite','full16credit','outoforder','duplicate','wrongtag','wronggen','wrongdirection','validcode_mutation','rearm_live_debt','unfenced_wrap','fenced_wrap','reset_stale','simultaneous_release_badquery'],
            cannot_prove='old-copy absence comes from explicit external receipts, not a local empty/timer',
            build_requires_measured_CPU_headroom=True))

if __name__=='__main__':print(json.dumps(model(),indent=2,sort_keys=True))
