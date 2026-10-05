#!/usr/bin/env python3
"""Join existing measured HA components to physical integration demands.

No model replay or physical tool. Emit usable area/port/clock constraints even
while coordinates are unassigned. An owner-pinned allocation adds service slot
and corridor costs; unknown bounds remain unknown, never zero.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

from hbm_accel_fulldie_inputs import ROOT, DEFAULT, record, box, contains, finite, require


def loader_allocation(allocation, geometry, width):
    demand = dict(name="service.loader", contained_in="service",
                  memory_clients_per_die=1, request_bits=337, response_bits=273,
                  payload_bytes_per_accepted_memory_edge=32,
                  host_dma_payload_bits=64, host_dma_instances="per selected host hierarchy",
                  local_crc_data_bits=256, local_crc_state_bits=32,
                  gross_cell_bound_um2=geometry["retained_plus_matrix_cell_area_um2_ESTIMATE"],
                  required_slot_before_repair_um2=geometry["required_slot_area_before_additional_repair_um2_ESTIMATE"],
                  conservative_crc_cut_tracks=geometry["all_cut_edge_upper_bound_tracks"],
                  default_enabled=False, crc_recipe_selected=False,
                  allocation=None, additional_service_area_um2=None,
                  added_corridor_area_um2=None, added_composed_latency_ns=None,
                  loader_geometric_bound_pass=False)
    # Required full-address successor is a separate source candidate. Preserve
    # baseline CRC cost but never transfer its closure to widened packets.
    demand.update(request_bits=width["request_service_packet_bits"],
                  internal_request_bits=width["request_internal_packet_bits"],
                  width_successor_price=width, widened_source_clock_closed=False,
                  added_address_FF_area_floor_um2=width["FF_area_floor_um2_ESTIMATE"],
                  additional_address_guard_mux_CDC_area_um2=None)
    demand["gross_cell_bound_um2"] += width["FF_area_floor_um2_ESTIMATE"]
    demand["required_slot_before_repair_um2"] = demand["gross_cell_bound_um2"]/geometry["maximum_slot_cell_utilization"]
    if allocation is None:
        return demand
    finite(allocation["address_guard_mux_CDC_cell_area_um2"], "widened address guard/CDC cost")
    require(allocation["wide_source_price_complete"] is True, "incomplete widened loader price")
    demand["gross_cell_bound_um2"] += allocation["address_guard_mux_CDC_cell_area_um2"]
    # This is the existing service budget, not an extra free-standing loader.
    service = box(allocation["service_box_um"], "existing service")
    region = box(allocation["loader_box_um"], "service.loader")
    require(contains(service, region), "loader outside existing service budget")
    require(allocation["parent_budget_name"] == "service", "loader budget ownership")
    require(allocation["parent_includes_loader_area"] is True, "double charged loader")
    blocked = finite(allocation["blocked_area_um2"], "loader blockages")
    usable = region[2]*region[3]-blocked
    repair = finite(allocation["repair_clock_buffer_area_um2"], "repair headroom")
    utilization = geometry["maximum_slot_cell_utilization"]
    require(usable*utilization >= demand["gross_cell_bound_um2"]+repair,
            "loader region cannot hold gross cells plus repair")
    require(set(allocation["fold_regions"]) == {"crc_got_load", "crc_got_store", "vcrc_load", "mcrc_store"},
            "missing host/memory CRC locality regions")
    for fold in allocation["fold_regions"].values():
        require(contains(region, box(fold, "CRC fold")), "CRC fold outside loader")
    routes = allocation["corridors"]
    require({r["name"] for r in routes} == {"MREQ", "RSP", "DMA64", "CRC"}, "missing loader corridor")
    area = latency = 0
    for route in routes:
        corridor = box(route["box_um"], "loader corridor")
        require(contains(service, corridor), "corridor outside service allocation")
        require(route["layers"], "missing actual routing layers")
        bits = {"MREQ":demand["request_bits"], "RSP":273, "DMA64":64, "CRC":demand["conservative_crc_cut_tracks"]}[route["name"]]
        # Track count uses physical bus widths; no duty-cycle discount. PG,
        # clocks, blockages and existing service wires consume reserved tracks.
        capacity = 0
        for layer in route["layers"]:
            span = corridor[3] if layer["direction"] == "horizontal" else corridor[2]
            require(layer["direction"] in {"horizontal", "vertical"}, "layer direction")
            capacity += max(0, math.floor(span/finite(layer["pitch_um"], "track pitch", True))
                            - finite(layer["reserved_tracks"], "reserved tracks"))
        require(capacity >= bits, "loader corridor over capacity: "+route["name"])
        require(route["port_coordinates_um"], "missing physical endpoint coordinates")
        for xy in route["port_coordinates_um"]:
            require(len(xy)==2 and corridor[0]<=xy[0]<=corridor[0]+corridor[2]
                    and corridor[1]<=xy[1]<=corridor[1]+corridor[3], "port outside corridor")
        # Owner specifies incremental exclusive area and exposed traversal
        # count so overlapped service paths are not credited or charged twice.
        exclusive = finite(route["additional_exclusive_area_um2"], "corridor area")
        require(exclusive <= corridor[2]*corridor[3], "invalid corridor area")
        area += exclusive
        period = finite(route["clock_period_ns"], "actual route domain", True)
        wire = finite(route["wire_cycles"], "wire cycles")
        cdc = finite(route["cdc_cycles"], "CDC cycles")
        credit = finite(route["credit_cycles"], "credit cycles")
        traversals = finite(route["exposed_token_traversals"], "exposed traversals")
        latency += (wire+cdc+credit)*period*traversals
    require(area <= finite(allocation["unallocated_service_area_um2"], "service spare area"),
            "added corridors exceed remaining service budget")
    demand.update(allocation=allocation, usable_slot_um2=usable,
                  additional_service_area_um2=0, added_corridor_area_um2=area,
                  added_composed_latency_ns=latency, loader_geometric_bound_pass=True)
    # This is geometric/model admission only, not Turing recipe selection or STA.
    return demand


def join(root, manifest, target):
    refs = manifest["physical_join"]
    authority = record(root, refs["component_authority"])
    portmap = record(root, refs["current_portmap"])
    phy = record(root, refs["phy"])
    geometry = record(root, refs["loader_geometry"])
    width = record(root, refs["loader_width_successor"])
    budgets = refs["budget_authorities"]
    old = record(root, budgets["historical_ds" if target == "deepseek" else "historical_qwen"])
    service = record(root, budgets["ds_service_r11" if target == "deepseek" else "qwen_service_r11"])
    # Read the actual existing budget constant without invoking its legacy
    # GPU sizing model, which is explicitly not the selected accelerator.
    from hbm_accel_fulldie_inputs import pinned
    uref = budgets["uarch"]
    if "git_commit" in uref:
        require(re.fullmatch(r"[0-9a-f]{40}", uref["git_commit"]), "invalid frozen budget commit")
        raw_bytes = subprocess.check_output(["git", "show", uref["git_commit"]+":"+uref["path"]], cwd=root)
        require(hashlib.sha256(raw_bytes).hexdigest()==uref["sha256"], "frozen budget source drift")
        raw = raw_bytes.decode()
    else:
        raw = pinned(root, uref).decode()
    shore = re.search(r"HBM_SHORE\s*=\s*dict\(\s*phy_edge_mm=([0-9.]+)", raw)
    corners = re.search(r"corner_mm=([0-9.]+), corner_basis", raw)
    require(shore and corners, "missing existing right-size shoreline budget")
    old_edge = 2*float(shore[1])*1000+2*float(corners[1])*1000
    actual_edge = 2*phy["footprint"]["width_um"]+2*float(corners[1])*1000
    budget_join = dict(current_die_core_service_budget=refs["current_die_core_service_budget"],
        historical_die_um=old["die_um"], historical_core_um=old["core_um"],
        historical_sm_module=old["sm_tile"]["abstract"],
        historical_sm_view=old["sm_tile"]["abstract_lef"],
        inherited_as_current=False,
        right_size_edge_um=old_edge, actual_phy_required_edge_um=actual_edge,
        missing_edge_um=max(0,actual_edge-old_edge),
        DS_service_provider_area_fit=service.get("DS_provider_area_fit") if target=="deepseek" else None,
        decision_required="Bind current accelerator die/core/service rectangle; existing right-size edge uses8.5mm/PHY but actual LEF is12.000096mm. Historical GPU slots are not current component slots.")
    alloc = record(root, refs["allocation"])[target] if refs["allocation"] else None
    loader = loader_allocation(alloc, geometry, width)
    if refs.get("isolated_loader_slot"):
        isolated = record(root, refs["isolated_loader_slot"])
        require(isolated["name"] == "service.loader" and not isolated["actual_fit"],
                "isolated loader allocation must retain provisional status")
        loader.update(isolated_closure_input=isolated,
                      isolated_reserved_area_um2=isolated["outer_area_um2"],
                      full_parent_anchor_bound=False)
        # This area is a concrete service debit for either target. It does
        # not imply a bound parent rectangle or transfer old failed STA.
        loader["required_slot_before_repair_um2"] = isolated["outer_area_um2"]
    common = dict(stacks_per_die=4, pseudo_channels_per_stack=32,
                  pseudo_channels_per_die=128,
                  phy_count=4, phy_outline_grade=phy["footprint"]["area_basis"]["grade"],
                  phy_area_um2=4*phy["footprint"]["area_mm2"]*1e6,
                  phy_min_shoreline_um_per_stack=phy["footprint"]["width_um"],
                  phy_pins_per_stack=phy["pins"]["signal_pins"],
                  phy_min_period_ps=phy["timing"]["ss"]["min_period_ps"],
                  service_loader=loader)
    # New current composition constraints, not inherited GPU regions. These
    # are necessary bounds until actual component halos/channel/PG/clock costs
    # fill the frame. The four PHYs occupy two opposing edges, two per edge.
    frame = dict(reticle_um=[33000,26000], maximum_area_um2=858e6,
        sizing_authority="actual four ot_hbm3e_phy outlines; 340.5mm2 estimate superseded",
        bare_phy_long_edge_min_um=2*phy["footprint"]["width_um"],
        bare_phy_total_depth_um=2*phy["footprint"]["height_um"],
        die_um=None, core_um=None, service_um=None, loader_region_um=None,
        minimum_feasible_area_um2=None, actual_component_bounds_complete=False,
        edge_keepout_um=None, signal_corridor_area_um2=None,
        clock_repair_area_um2=None, IR_PG_area_um2=None,
        equation="W>=2*PHYwidth+edge/escape/corridor; H>=2*PHYheight+service+compute+dedicated/collective+channels+PG/clock; W<=33000,H<=26000,W*H<=858e6",
        no_die_count_pivot=True)
    if target == "deepseek":
        ds = authority["DS_current_model"]
        ports = portmap["DS"]
        sm = record(root, refs["sm_context"])
        capture = record(root, refs["sm_capture"])
        n = ds["SM_per_die_intended_by_current_performance_walk"]
        measured = record(root, refs["ds_measured"])
        common.update(dies=ds["ranks"], sm_per_die=n, sm_module=ds["selected_SM_component"],
                      network="TU96", measured_AR_us=measured["AR_us"],
                      AR_price_terms_us=measured["AR_by_term"],
                      physical_clock_price=measured["at_closing_clocks"],
                      sm_candidate_context=dict(source_sha256=capture["source_sha256"],
                        parameters=capture["parameters"], macros_per_sm=sm["macros"]["count"],
                        macros_for_32_sm=n*sm["macros"]["count"],
                        area_um2_for_32_sm=n*sm["die_area_um2"],
                        macro_area_um2_for_32_sm=n*sm["macro_area_um2"],
                        source_matches_current= capture["source_sha256"] == authority["source_pins"]["rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv"]["sha256"],
                        charged_as_adopted=False))
        common.update(source_portmap=ports, loader_source_portmap=portmap["loader"],
                      required_stream_rate_to_service_ratio=ports["port_prices"]["SM_ingest_byte_upper_bound_per_fast_edge"]*
                        ports["port_prices"]["clock_target_fast_Hz"]/ports["port_prices"]["die_column_peak_Bps"],
                      HBM_stretch_added_to_measured_AR=False,
                      HBM_stretch_basis="peak ratio1.2288 is a calendar constraint, not extra measured latency; retain actual HBM term once")
        # Existing source organisation is four groups of eight SMs. Carry the
        # actual captured 202-macro element dimensions into a four-by-two
        # packing per group, with every unknown halo/channel explicit. This
        # computes a lower envelope, never substitutes for a hardened SM.
        sw, sh = sm["die"][2], sm["die"][3]
        frame.update(compute_group_count=4, SM_per_group=8,
            candidate_group_array=[4,2], bare_group_um=[4*sw,2*sh],
            bare_two_group_width_um=8*sw, bare_two_group_depth_um=4*sh,
            candidate_SM_source_sha256=capture["source_sha256"],
            candidate_source_compatibility_required=True,
            conditional_known_area_um2=n*sm["die_area_um2"]+common["phy_area_um2"]+
                loader["required_slot_before_repair_um2"],
            conditional_known_area_excludes=["SM source compatibility/halo", "all service except loader bound",
                "SU/index/attention/mHC/quantise/select/DSpark", "TU PHY/arbitration and host hierarchy",
                "shared storage", "signal corridors", "clock/IR/PG repair"])
    else:
        q = record(root, refs["qwen_measured"])
        common.update(dies=4, die_module="ot_qwen_hbmacc_rt_die_w12",
                      measured_design_point=q["design_point"], memory_calendar=q["memory_system"],
                      resident_bytes_per_die=q["memory_system"]["sram_mib_per_die"]*2**20,
                      resident_macro_area_um2=None, sm_per_die=None,
                      clock_domains_ps=dict(compute=q["memory_system"]["core_clock_ps"],
                                            controller=q["memory_system"]["hbm_ctl_clock_ps"]))
        if refs.get("payload_store_geometry"):
            common["payload_store_geometry"] = record(root, refs["payload_store_geometry"])
        require(q["design_point"]["tp"] == 4, "selected Qwen measured TP is not4")
        common.update(source_portmap=portmap["Qwen"], loader_source_portmap=portmap["loader"],
                      tiles_per_die=portmap["Qwen"]["component_census_per_die"]["tiles"],
                      parameter_authority_conflict={key:dict(measured=q["design_point"][key.lower()],
                        portmap=portmap["Qwen"]["die_parameters"][key])
                        for key in ["BD", "TCUT", "NWS", "TWS", "ORD"]
                        if q["design_point"][key.lower()] != portmap["Qwen"]["die_parameters"][key]},
                      window_bytes=portmap["Qwen"]["storage"]["window_payload_bytes"],
                      window_area_added_to_resident=False,
                      window_residence_overlap=portmap["Qwen"]["storage"]["resident_and_window_overlap_binding"])
        frame.update(compute_group_count=1536, tile_grouping="actual TG4 array",
                     tile_geometry_um=None, resident_storage_geometry_um=None,
                     conditional_known_area_um2=common["phy_area_um2"]+loader["required_slot_before_repair_um2"],
                     conditional_known_area_excludes=["1536 actual tiles", "core/spine/VM",
                         "441974784 resident bytes and window containment", "service", "collective",
                         "payload writer/address translator", "signal corridors", "clock/IR/PG repair"])
    # Physical integration nodes retain exact current source hooks and traffic.
    # Missing geometry is a missing bound on a real component, not a small
    # substitute. Sagan's unresolved source hooks are never made into wires.
    integration = dict(parent_hooks=common["source_portmap"]["parent_hooks"],
                       port_calendar=common["source_portmap"]["port_prices"],
                       slots={"service":None, "service.loader":loader["allocation"],
                              "compute":None, "storage":None, "collective":None},
                       layer_reservations=None, mux_fanout_area_um2=None,
                       exposed_wire_cdc_credit_latency_ns=None,
                       loader_address_check=portmap["loader"]["address_check"],
                       unpriced_terms=portmap["minimum_price"]["unpriced_terms"])
    if target == "deepseek":
        integration["compute_replica_count"] = n
        integration["collective_port_demands"] = ports["TU"]
    else:
        integration["compute_replica_count"] = common["tiles_per_die"]
        integration["collective_port_demands"] = portmap["Qwen"]["system_collective"]
    return dict(target=target, component_demands=common, current_frame=frame, budget_join=budget_join, source_bindings=refs,
                integration=integration,
                contradictions=authority["contradictions"],
                physical_fit=False, signoff=False, adopted=False,
                total_die_area_um2=None, composed_physical_token_latency_ns=None,
                next_binding="Sagan component census/ports/clocks; existing core/service rectangles and all component slot/route costs")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--bindings", type=Path)
    ap.add_argument("--target", choices=["deepseek", "qwen"], required=True)
    args = ap.parse_args()
    manifest = json.loads((args.bindings or args.root/DEFAULT).read_text())
    print(json.dumps(join(args.root, manifest, args.target), indent=2))


if __name__ == "__main__":
    main()
