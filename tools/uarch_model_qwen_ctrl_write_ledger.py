#!/usr/bin/env python3
"""Model-before-build sizing of the default-off native PC write commit ledger."""
import json

def qwen_ctrl_write_ledger_model():
    ingress = 16 * (24 + 256 + 9)
    committed = 64 * (24 + 9)
    rows = 32 * (19 + 1)
    control = 3*4 + 2*5 + 2*6 + 7 + 2
    state = ingress + committed + rows + control
    ff = 2*state + 2
    cell = ff*2.1 + state*0.5 + 8000
    return {
      "status": "SIZED_NOT_PHYSICALLY_QUALIFIED", "enable_default": 0,
      "controller_cycle_ps": 1024, "functional_domain_change": False,
      "macs_per_cycle": 0, "compute_intensity": "control only",
      "ingress_depth": 16, "committed_depth": 64, "replicas_per_pc": 2,
      "payload_bytes_per_cycle": {"ingress":32,"physical_write":32},
      "boundary_bits_per_cycle": {"native_write":290,"native_done":10,
        "scheduler_write":12,"physical_row":28,"physical_column":12,
        "physical_write_payload_tag_sector":289},
      "state_bits_per_replica":state,"retained_ff_per_pc":ff,
      "total_pc":128,"target_ff":128*ff,
      "mutable_protection":"two retained copies; full state equality, plus two sticky quarantine rails; single sequential upset only",
      "comparator_bits":state,"mux_cost":"three 16:1 289-bit ingress selections (handoff/commit/write address), 64:1 33-bit completion head, 32:1 19-bit open row; synthesis pending",
      "cell_area_um2_estimate":cell,"area_estimate_basis":"2.1um2/FF conservative closure reserve (library DFF_UM2=.2916), 0.5um2/compared bit, 8000um2 mux/control reserve; not measured cell area",
      "floorplan_width_um":300,"floorplan_height_um":300,"utilization_estimate":cell/90000,
      "target_frame_area_mm2":128*90000/1e6,
      "routing": {"native_face_tracks":320,"scheduler_tracks":12,"controller_command_tracks":41,"phy_face_tracks":339,"clock_reset_tracks":2,"aggregate_tracks":714,"signal_pitch_um":0.288,"face_capacity_tracks_per_plane":1041,"corridor_width_um":64,"reserved_signal_planes":4,"corridor_capacity_tracks":888,"corridor_margin_tracks":174,"status":"analytical reservation only; actual station pin layers and routed extraction pending"},
      "library_ff_area_um2":0.2916,"library_ff_only_area_um2":ff*0.2916,
      "closure_reserve_ff_area_um2":2.1,
      "all_storage_ports_bytes_per_cycle": {"ingress_write_each_copy":289/8,"ingress_handoff_read_each_copy":289/8,"ingress_commit_read_each_copy":289/8,"completion_write_each_copy":33/8,"completion_read_each_copy":33/8,"row_write_each_copy":20/8,"row_read_each_copy":20/8,"full_state_compare_read_each_copy":state/8},
      "latency_added_command_cycles":0,"latency_added_completion_cycles":0,
      "flow_control":"w_room requires at least 3 free native ingress slots; bridge may emit at most two more pulses after deassertion. Completion reservation at scheduler handoff includes all handed-but-uncommitted and committed slots.",
      "latency_composition":"Native ingress-to-handoff >=1 controller edge; existing bridge/CDC visibility priced outside this cut. Existing commit-to-real-completion unchanged. A full 64-entry reserved completion queue stalls handoff; no assumed fixed PHY completion bound or speculative performance credit.",
      "single_user_token_added_cycles_without_capacity_stall":0,
      "energy":f"two state banks clocked for every mutation plus {state}-bit equality; switching/power measurement pending",
      "refresh":"independent protected external owner must continuously snoop accepted commands and own absolute phase/deadline/bank timings. Request starts with abort, independently of write drain; acknowledgment is custody only, not a fabricated refresh guarantee.",
      "epoch":"advance only after committed writes actually drain and external refresh custody acknowledged; external owner must establish/release safe initialized next epoch. Quarantine cannot clear via either input. Cold reset requires no outstanding physical transactions.",
      "adoption_blocks":["actual bridge CDC/room latency binding","external refresh owner and safe epoch restart","actual mapped replica retention","SS/FF>=15ps at real loads and DRC0","station/corridor track fit","PHY payload custody and real completion contract"]}
if __name__ == "__main__": print(json.dumps(qwen_ctrl_write_ledger_model(),indent=2,sort_keys=True))
