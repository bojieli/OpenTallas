#!/usr/bin/env python3
"""Read literal CDC port contracts; reject bare pulse ACK as protected binding.

Source-only preparation. Does not compile/run or qualify a physical source.
The existing protected adapter may be used for additive port integration; the
owner r9 endpoint still requires a genuine protected source/physical handoff.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def ports(source, module):
    text=source.read_text()
    at=text.index('module '+module)
    end=text.index('\n);',at)
    header=text[at:end]
    # Literal ANSI port names (each declaration may carry several names).
    names=set()
    for decl in re.findall(r'\b(?:input|output)\s+(.*?)(?=\binput\b|\boutput\b|$)',header,re.S):
        decl=re.sub(r'\[[^\]]*\]|//[^\n]*','',decl)
        words=re.findall(r'\b[A-Za-z_]\w*\b',decl)
        names.update(w for w in words if w not in {'wire','reg','integer','signed'})
    return names


def finite_boundary(source):
    """Export actual selected inventory/cuts; no new hardware or signoff."""
    import sys
    import math
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root/'tools'))
    from qwen_stream4_protected_model import model
    m=model(root)
    rings=[]
    keys=('name','payload_bits','depth','pointer_bits','source_domain','destination_domain',
          'sealed_word_bits','read_ports','write_ports','cache_read_ports',
          'encode_stage1_DMR_bits','decoder_DMR_stage_bits','coded_memory_FF',
          'pointer_counter_fault_DMR_and_sync_FF','checked_HCLK_write_cache_DMR_FF',
          'port_credit_extra_DMR_FF','encoder_capture_stages','accept_to_publication_source_edges',
          'pointer_visibility_destination_edges','decoder_capture_stages','decoder_cuts','reclamation')
    for row in m['rings']:
        rings.append({k:row[k] for k in keys})
    # Minimal missing term IF the owner agrees to exporting its read-select
    # leaf for this coded landing width. Never silently select/prize this.
    group_bits=math.ceil(281/10);groups=math.ceil(504/group_bits)
    selector_FF=2*64*groups*128
    checks=3*64*groups*128*2 # primary/inverse and exact fetch-index relation
    buffers=math.ceil(selector_FF/7)
    cell=(selector_FF*.2916+checks*.08748+buffers*.10206)/1e6
    core=cell/m['utilization']
    link=m['selected_transport']
    planned_total=link['conservative_area_charge_die_mm2']+core
    return dict(scope='ACTUAL PROTECTED r9 READ SOURCE; opt-in functional runtime candidate, not physical qualification',
        owner_successor=dict(source_commit='c8ba43664',variant='r9 RSEL1',
            historical_routes=dict(r6='VOID_HELD_SLOT_RELOAD_BUG',r7='VOID_HELD_SLOT_RELOAD_BUG',r8='VOID_HELD_SLOT_RELOAD_BUG'),
            owner_reported_old_mismatches=11950,owner_reported_checked_beats=23867,
            owner_reported_r9_mismatches=0,report_is_not_protected_context_gold=True),
        actual_domains=m['actual_parent_clock_relation'],rings=rings,
        visibility='2-edge dual-rail pointer sampling +4 destination checked decode cuts after committed encoded slot; not an unconditional CDC metastability/backpressure bound',
        write_cache='actual WB16 checked cache, separate handoff and completion heads; capture only matching actual WR column. Cache-fill/head publication are real HCLK edges.',
        ACK_retirement='local AD64 -> checked stack Rpool bardy; root ticket/Rpool retires only consumer marker/live-slot/generation/PC stream_wd_accept',
        warm='fresh root admission closes; already-reserved control/data drain or hold. POR alone erases pointers/encoder/decoder/cache/ACK debt.',
        descriptor_GO='4 backend shared boundaries; real desc_commit/go_commit+ordinal3 cross in existing sealed callback rings. No reset-replayed mailbox ACK.',
        local_wire_spans='literal128PC existing context mapping5..14; ring code/credit hops are in SOURCE clock, receiver is real CLK/HCLK SYNC2. Global stack links41CLK.',
        receiving_cut=dict(module='ot_qwen_s4_protected_ring u_d0',
            existing_coded_word_bits=504,landing_owner_valid_bits=8,
            existing_DMR_capture_FF=2*(504+8),
            enable='advance = rd_online && !rd_fault && (!v3 || rd_ready)',
            risk='r6/r7/r8 unconditional reload corrupts held output after read pointer advances. r9 RSEL1 uses per-group kept valid vg and !vg || l_pop capture enable. Protected u_d0 holds code/owner/valid on !advance; preserve that enable and validate actual group-valid/selector alignment, not raw unconditional timing.',
            timing_arcs='actual select Q -> local column mux -> checked u_d0.D; actual advance/fault -> u_d0.EN; both code/owner rails; retain decoder u_d1/u_d2/u_d3 and actual hold minima',
            added_latency_edges=0,latency_equivalence='minimum changed-mechanism golden edge comparison PASS; not full-token or SSFF equivalence',physical_qualified=False),
        loaded_setup_hold_or_slew_measured=False,protected_ETM=None,
        owner_leaf_reuse=dict(owner='Claude QWEN-PHYS raw structure; Codex protected binding',agreement='OWNER_AUTHORIZED_FUNCTIONAL_BINDING_IMPLEMENTED',selected=False,
            mechanism='owner r9 registered onehot selection/column mux with held-valid per-group capture enable; no raw pointer/payload/ACK state becomes authority',
            ports='existing ring internal fetch_bin/fetch_next/mem -> read_code/read_select_fault; held capture is existing u_d0.EN=advance, no new external ABI',
            source_module='ot_qwen_s4_protected_ring READ_RSEL=1 / r9_read.column[0..17]',
            consumer_parameters='ot_qwen_s4_transport_context ENABLE=1 CDC_CONSUMER_JOIN=1 LANDING_RSEL=1',
            owner_source_commit='c8ba43664',required_variant='RSEL1; RSEL0 branch remains unconditional and is not the corrected leaf',
            raw_group_enable='!vg || l_pop; vg_next = l_ren ? 1 : (l_pop ? 0 : vg)',
            protected_group_enable='implemented checked u_d0.en=advance; fetch qualifies captured code/owner/valid. Selectors track fetch_next; read_select_fault prevents advance/fetch/retirement.',
            existing_protection='checked_state selector INIT1 + existing protected_ring rd_fault/advance/fetch/debt; existing u_d0 captures code_word',
            raw_width=281,raw_groups=10,max_column_bits=group_bits,
            coded_landing_bits=504,protected_groups=groups,
            pieces_per_selector=64,replicated_PC=128,
            candidate_added_selector_DMR_FF=selector_FF,
            candidate_selector_check_NAND2=checks,candidate_buffer_estimate=buffers,
            candidate_added_cell_mm2=cell,candidate_added_core_mm2=core,
            unchanged_existing_composed_die_mm2=link['conservative_area_charge_die_mm2'],
            candidate_composed_die_mm2=planned_total,candidate_scalar_margin_to858_mm2=858-planned_total,
            candidate_composed_latency='existing four protected cuts retained; minimum golden edge comparison passes, queues/stalls and actual parent clocks still count',
            candidate_added_decoder_cycles=0,global_payload_bits_delta=0,
            r9_group_valid_DMR_FF_added=0,
            candidate_area_scope='actual selected source reuses existing1024FF D0 held-valid capture, adds18checked onehot groups; no extra payload/valid capture. Model price remains estimate, not slot/pin/clock fit.',
            local_leaf_input_pins_max=64*group_bits,
            local_leaf_output_bits_max=group_bits,
            slot_fit=None,actual_caps_tracks_pin_access_and_clock_loads='owner finite loaded leaf/context required; no raw load equivalence assumed',
            complete_parent_rebuild_required=False,
            reuse='existing protected parent/codec/control/source+retained engine archives; incremental changed read-leaf/receiving-cut timing with actual SS60/FF25 loads/clock and zero slew'),
        source_SHA256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [root/'rtl/hdc/kv/ot_qwen_s4_protected_ring.sv',
                      root/'rtl/hdc/kv/ot_qwen_s4_protected_pc.sv',
                      root/'rtl/hdc/kv/ot_qwen_s4_protected_control.sv',
                      root/'rtl/hdc/kv/ot_qwen_s4_checked_state.sv',
                      root/'tools/qwen_stream4_protected_model.py',
                      root/'tools/qwen_stream4_transport_model.py']})


def inspect(source,module):
    names=ports(source,module)
    required={'clk','hclk','por_n','warm_rst_n','l_v','l_sec','l_row','l_data','l_pop',
              'w_v','w_sec','w_data','w_tag','w_room','wd_v','wd_tag','wd_accept',
              'h_lv','h_lsec','h_lrow','h_ldata','h_cred','h_wv','h_wsec','h_hand',
              'h_wcon','h_cv','h_csec','h_cdata','h_ctag','h_av','h_atag','c_fault','h_fault'}
    missing=sorted(required-names)
    result=dict(source=str(source),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),module=module,
                verdict='PORT_CONTRACT_READY_PHYSICAL_BINDING_PENDING' if not missing else 'REJECT_PROTECTED_PORT_BINDING',
                missing_required_ports=missing,ports=sorted(names),physical_qualified=False,
                qualification='port match alone never proves selected mutable-state protection or SS60FF25/slew closure')
    if module=='ot_qwen_s4_protected_cdc_consumer_join' and not missing:
        result['finite_protected_boundary']=finite_boundary(source)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--module',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=inspect(a.source,a.module)
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(r['verdict'])
    raise SystemExit(1 if r['missing_required_ports'] else 0)
