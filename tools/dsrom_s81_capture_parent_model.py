"""Finite enclosing native VM contract for selected S81 (functional admission).

This prices added roles without claiming that a behavioral VM is a physical
multiport SRAM. ROM/capture primitives retain their independent model charges.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]

def model(*,SUN=256,SW=8,ROOTS=128,G=4,W=16,rank_dies=324):
    if (ROOTS,G,W)!=(128,4,16):raise ValueError('selected native S81 port census differs')
    later_rom=ROOTS*(ROOTS-1)//2
    competing_per_root=G*W+2*SW+SUN+SUN//8+1+64+80
    comparators=later_rom+ROOTS*competing_per_root
    pins=['tools/dsrom_s81_capture_parent.py','tools/dsrom_s81_capture_install.py',
          'tools/dsrom_s81_phase_capture_join.py','rtl/chip/ckvsel/ot_chip_v41x_tile.sv',
          'rtl/v41die/ot_v41_rom_adapt.sv','rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv']
    return dict(schema='dsrom.s81.native_capture_parent.v1',selected=dict(stages=81,NP=2417,BF=519,R=128,RD=64,rank_dies=rank_dies),
      numerical_MACs_per_cycle_added=0,VM_bytes_per_cycle=ROOTS*4,root_bits_per_cycle=ROOTS*69,
      VM_address_data_bits_per_cycle=ROOTS*(30+32),VM_positive_accept_bits_per_cycle=ROOTS,
      capture_raw_state_bits_per_rank=16527,additional_enclosing_FF_per_rank=0,
      all_rank_raw_state_bits=16527*rank_dies,existing_row_register_subtraction_bits=0,
      quota_ROM_added_bits=0,quota_source='actual emitted PHROM rowcount and accepted s_np; Nash internal quota combinational profile',
      capture_capacity_per_root=1,real_service='same-edge surviving retained behavioral VM assignments; any denied valid faults and preserves debt, no producer READY',
      added_idle_edges_per_actual_executed_phase=2,added_phase_issue_edges=0,
      token_delta_ns='2/1.2 * actual executed phase count; count not equated with all checkpoint matrix declarations',
      last_write_wins=dict(later_ROM_address_compares=later_rom,other_writer_word_compares_per_root=competing_per_root,
        total_19bit_equality_comparators_upper_bound=comparators,full_address_range_checks=ROOTS,
        compare_input_bit_reads_upper_bound=comparators*38,
        comparator_mask_OR_input_count_upper_bound=comparators,
        fanout='each source writer address/mask to128 root checks; original later writer precedence preserved'),
      adapter_change='separate command admission before phase lookup from actual S_GO spine-ready; no new state or pipeline',
      retirement='saved47 identity, coordinated cold-empty or actual phase completion requires real helper drained; C8 write quiet also fences KV/CKV owners',
      reset='warm request quarantines and retains capture debt; rst_n remains coordinated cold fence only',
      physical=dict(admitted=False,slot=None,route_track_capacity=None,SS_FF=None,
        conditional_extra_logic='native source visibility guard comparators above plus mask/OR, profile multiply/add and existing capture address multiplication',
        area_credit=0,physical_VM_ports_not_proven=True,
        required='replace behavioral VM with source-sized protected finite bank provider or prove compiler disjointness and map surviving context guards; clock/reset/routes/slot still required'),
      functional_source_integration_admitted=True,full_token_admitted=False,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins})

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(model(),sort_keys=True,indent=2)+'\n')
