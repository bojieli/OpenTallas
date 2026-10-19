#!/usr/bin/env python3
"""Pre-RTL XC split sizing; no timing or utilisation qualification is implied."""
import json, math

def model():
    tiles = {
      "descriptor": {"outline_um": [164.16,198.72], "macros":2,
        "macro_um":[94.824,41.04], "origins_um":[[43.2,43.2],[43.2,129.6]],
        "macro_area_um2":2*94.824*41.04, "clock_port":"clk_desc",
        "input_bits_per_edge":328, "output_link_bits_per_edge":313,
        "macro_face_density_W_E":[410/41.04,411/41.04]},
      "programme": {"outline_um":[241.92,267.84], "macros":2,
        "macro_um":[174.744,70.47], "origins_um":[[43.2,43.2],[43.2,172.8]],
        "macro_area_um2":2*174.744*70.47, "clock_port":"clk_prog",
        "input_link_bits_per_edge":313,"output_bits_per_edge":176,
        "macro_face_density_W_E":[417/70.47,414/70.47]}}
    for t in tiles.values():
        w,h=t["outline_um"]; t["outline_area_um2"]=w*h
        t["worst_diagonal_reach_um"]=math.hypot(w,h)
        t["macro_only_fill"]=t["macro_area_um2"]/(w*h)
        t["std_area_um2"]=None # measured synthesis, then resize, before gate
        t["full_width_cell_band_y_um"]=[t["origins_um"][0][1]+t["macro_um"][1],129.6 if t is tiles["descriptor"] else 172.8]
    return {"schema":"hbm.xcal.partition.model.v1","status":"PROTOTYPE_NOT_GATE_READY",
      "replicas_per_sm":1,"sm_per_die":16,"MACs_per_cycle":0,
      "memory_ports_bytes_per_edge":{"programme_read":32,"programme_write":32,"descriptor_read":32,"descriptor_write":32},
      "tiles":tiles,"link":{"payload_bits":313,"registered_captures":2,"storage_bits":626,
        "input_to_output_edges":2,"flow_control":"fixed latency, no credits or ready",
        "control_replication":"one kept valid copy per <=16 data bits; verify mapped survival",
        "routing_signal_tracks":313,"channel_capacity_tracks":None,
        "channel_note":"one complete facing edge; multilayer detailed capacity audit remains OPEN",
        "clock_policy":"two actual same-frequency phase0 roots; adjacent native pin captures; normal one-edge STA, no MCP/false paths"},
      "schedule":{"added_programme_cfg_edges":2,"added_GO_edges":2,
        "early_internal_GO_edges":2,"external_command_delta_edges_if_eligible":0,
        "eligibility":"descriptor available before e_at-2; e_at>=2; next GO does not overlap programme busy",
        "ineligible":"fault, never silently issue late; compiler must separately price any launch shift",
        "status_return_edges":2,"token_latency_credit":0},
      "safe_design":{"reach":"PASS model bounding diagonal <405um within either tile; parent final pin hop must be <=100um",
        "pins":"planned registered interfaces; existing programme and RELOC capture retained",
        "reset":"two registered release stages per root; no operation before both roots settled",
        "storage":"all table storage remains canonical SRAM; two313bit register captures=626bits below2kb",
        "fanout":"OPEN mapped kept-copy audit; RTL bank-select copies16bits and output identity/valid copies16bits; SRAM strobes need audit",
        "depth":"OPEN synthesis <=600ps/20levels; descriptor compare/GO only in control tile",
        "floorplan":"origins43.2 lattice; macro-pin face clearance>=20um; actual std area OPEN",
        "clock":"OPEN TT/FF <=80ps spread, root boundary matched and >=0.03ns hold margin",
        "canonical_descriptor_face":"BLOCKED: canonical128x256 master W/E 9.99/10.015pins/um exceeds6; preserve abstract pending explicit owner scope decision"},
      "fanout_revision": {"baseline_std_area_um2":{"descriptor":690.27552,"programme":637.01478},"measured_failure":"wire keep merged Q copies; bank514/157loads and qualifier173loads", "repair":"preserved one-bit FF hierarchy; same-edge input/control copies, unconditional invalid payload updates in native collar", "added_latency_edges":0,"control_storage_budget_bits":128,"actual_final_area":"pending remap"},
      "adoption":"No gate, REVIEW, physical claim, or calendar adoption from this model alone."}
if __name__ == "__main__": print(json.dumps(model(),indent=2))
