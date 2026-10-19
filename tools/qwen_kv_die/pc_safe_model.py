"""Reclassify retained native ODB metadata; no EDA or candidate RTL generation.

All assertions bind an auditable finite source-repair lower bound, not a
post-repair certificate. Run against the immutable pc-contract-1019 pickup.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


def read(path):
    with (gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)) as f:
        return json.load(f)


def audit(root, terminal, tile):
    source = root / tile
    cells, drivers, roots, boundary = [read(source / (n + ".json.gz"))
                                       for n in ("cells", "drivers", "roots", "boundary")]
    geom = read(terminal / tile / "gate_dump.json")
    binding = read(terminal / tile / "gate_result.json")["source_binding"]
    source_path = "rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv"
    provenance = next(f for f in binding["files"] if f["path"] == source_path)
    repo = Path(__file__).resolve().parents[2]
    assert subprocess.check_output(["git", "-C", str(repo), "rev-parse", "--show-toplevel"], text=True).strip() == str(repo)
    text = subprocess.check_output(["git", "-C", str(repo), "show", provenance["git_blob"]])
    assert hashlib.sha256(text).hexdigest() == provenance["sha256"]
    sv = re.sub(r"//[^\n]*", "", text.decode())
    parent_module = sv.split("endmodule", 1)[0]
    assert len(re.findall(r"\bfront_co\b", parent_module)) == 3
    assert ".co_out(front_co)" in parent_module and ".controller_co(front_co)" in parent_module
    nc_return = sv.split("module qkd_static_kv_return_slots_mc_nc", 1)[1]
    packing = "hd<={controller_epoch,controller_co[17:12],controller_co[11:9],controller_co[7:1],controller_co[281:26]}"
    assert packing in re.sub(r"\s+", "", nc_return)
    used_co_bits = set(range(26,282)) | set(range(12,18)) | set(range(9,12)) | set(range(1,8))
    omitted_co_bits = sorted(set(range(1,282)) - used_co_bits)
    masters = collections.Counter(c["master"] for c in cells.values())
    assert all(m == "TIELOx1_ASAP7_75t_R" or
               (m in geom["masters"] and geom["masters"][m]["type"] in ("CORE", "CORE_TIEHIGH") and
                not geom["masters"][m]["block"]) for m in masters)
    ff_masters = {"DFFASRHQNx1_ASAP7_75t_R", "DFFHQNx1_ASAP7_75t_R"}
    ffs = {n for n, c in cells.items() if c["master"] in ff_masters}
    assert all("DFF" not in m or m in ff_masters for m in masters)
    assert all(d in ("INPUT", "OUTPUT", "INOUT")
               for c in cells.values() for _, d in c["pins"].values())
    assert all(n is None for c in cells.values() for p, (n, d) in c["pins"].items()
               if d == "INOUT"), "Connected INOUT requires explicit role proof"
    # Independent endpoint reconstruction from actual master-pin directions.
    # Compare each source, not merely a repeated summary or intermediary count.
    parent = {}
    def find(net):
        parent.setdefault(net, net)
        while parent[net] != net:
            parent[net] = parent[parent[net]]
            net = parent[net]
        return net
    transparent = set()
    for i, c in cells.items():
        ins = [n for n,d in c["pins"].values() if n and d == "INPUT"]
        outs = [n for n,d in c["pins"].values() if n and d == "OUTPUT"]
        for n,d in c["pins"].values():
            if n:
                find(n)
        if re.match(r"^(BUF|INV)", c["master"]) and len(ins) == len(outs) == 1:
            transparent.add(i)
            parent[find(ins[0])] = find(outs[0])
    independent_endpoints = collections.defaultdict(set)
    for i,c in cells.items():
        if i not in transparent:
            for pin,(net,direction) in c["pins"].items():
                if net and direction == "INPUT":
                    independent_endpoints[find(net)].add((i,pin))
    for name, net, signal, direction, boxes in geom["bterms"]:
        if signal not in ("POWER", "GROUND") and direction == "OUTPUT":
            independent_endpoints[find(net)].add(("@PORT",name))
    for d in drivers:
        assert d["transparent_intermediate"] == (d["driver"][0] in transparent)
        assert d["logical_pins"] == len(independent_endpoints[find(d["net"])])
    records = {tuple(d["driver"]): d for d in drivers if not d["transparent_intermediate"]}
    assert len(records) == sum(not d["transparent_intermediate"] for d in drivers)
    endpoint_sets = collections.defaultdict(set)
    for canonical in roots:
        assert canonical["logical_pins"] == len(canonical["endpoints"])
        assert len({tuple(e) for e in canonical["endpoints"]}) == canonical["logical_pins"]
        for d in canonical["drivers"]:
            assert tuple(d) in records
            assert records[tuple(d)]["logical_pins"] == canonical["logical_pins"]
            endpoint_sets[tuple(d)].update(map(tuple, canonical["endpoints"]))
            assert set(map(tuple, canonical["endpoints"])) == independent_endpoints[find(records[tuple(d)]["net"])]
    port_faces = {}
    for name, _, signal, direction, boxes in geom["bterms"]:
        if signal in ("POWER", "GROUND"):
            continue
        xx, yy = geom["die"][2:]
        faces = set()
        for _, b in boxes:
            eps = 1e-6
            faces.update(s for s, v in (("W", b[0]), ("S", b[1]),
                                       ("E", xx-b[2]), ("N", yy-b[3])) if abs(v) < eps)
        assert len(faces) == 1, (name, faces)
        port_faces[name] = next(iter(faces))
    assert set(port_faces) == {b["port"] for b in boundary}
    owner_faces = collections.defaultdict(set)
    boundary_rows = []
    root_for_output = {p: r for r in roots for i, p in r["endpoints"] if i == "@PORT"}
    for b in boundary:
        port = b["port"]
        if b["direction"] == "INPUT":
            ep = endpoint_sets.get(("@PORT", port), set())
            sequential_only = bool(ep) and all(i in ffs for i, p in ep)
            data_only = sequential_only and all(p == "D" for i, p in ep)
            direct_owners = sorted({i for i, p in ep if i in ffs}) if data_only else []
            category = ("unused_input" if not ep else "direct_data" if data_only else
                        "clock_or_reset" if sequential_only else "active_comb_before_FF")
        else:
            r = root_for_output.get(port, {"drivers": []})
            sequential_only = bool(r["drivers"]) and all(i in ffs for i, p in r["drivers"])
            data_only = sequential_only
            direct_owners = sorted({i for i, p in r["drivers"] if i in ffs}) if sequential_only else []
            category = ("direct_data" if data_only else "literal_output" if r["drivers"] and
                        all(i in cells and cells[i]["master"].startswith(("TIEHI", "TIELO"))
                            for i,p in r["drivers"]) else "active_comb_after_FF")
        for owner in direct_owners:
            owner_faces[owner].add(port_faces[port])
        boundary_rows.append(dict(port=port, direction=b["direction"], face=port_faces[port],
                                  direct_sequential=sequential_only, direct_data=data_only,
                                  category=category, owners=direct_owners))
    role_counts = collections.defaultdict(lambda: dict(drivers=0, max_pins=0, over32=0,
                                                       extra_copies_target32_lower_bound=0,
                                                       extra_copies_target24_lower_bound=0))
    violations = []
    for driver, d in records.items():
        i, p = driver
        endpoints = endpoint_sets.get(driver, set())
        # Clock exemption is based on the complete actual native endpoint pins.
        clock_only = bool(endpoints) and all(a in ffs and b == "CLK" for a, b in endpoints)
        reset_pins = sum(a in ffs and b in ("RESETN", "SETN") for a, b in endpoints)
        if clock_only:
            role = "clock_only"
        elif i == "@PORT":
            role = "top_input"
        elif i in ffs:
            role = "FF"
        elif cells[i]["master"].startswith(("TIEHI", "TIELO")):
            role = "constant"
        else:
            role = "comb"
        s = role_counts[role]
        s["drivers"] += 1
        s["max_pins"] = max(s["max_pins"], d["logical_pins"])
        s["over32"] += d["logical_pins"] > 32
        if role != "clock_only" and d["logical_pins"] > 32:
            extra = math.ceil(d["logical_pins"] / 24) - 1
            extra32 = math.ceil(d["logical_pins"] / 32) - 1
            s["extra_copies_target32_lower_bound"] += extra32
            s["extra_copies_target24_lower_bound"] += extra
            violations.append(dict(driver=list(driver), master=None if i == "@PORT" else cells[i]["master"],
                                   role=role, pins=d["logical_pins"], reset_endpoint_pins=reset_pins,
                                   extra_copies_target32_lower_bound=extra32,
                                   extra_copies_target24_lower_bound=extra))
    storage = collections.defaultdict(lambda: collections.defaultdict(set))
    ff_groups = collections.Counter()
    for n in ffs:
        plain = n.replace("\\", "")
        ff_groups[plain.split("[")[0].split("$_")[0]] += 1
        if ".u_front.g_storage[" in plain:
            bank, word, bit = map(int, re.findall(r"\[(\d+)\]", plain))
            storage[bank][word].add(bit)
    banks = []
    for bank in range(4):
        words = storage[bank]
        assert set(words) == set(range(32))
        bits = words[0]
        assert all(v == bits for v in words.values())
        banks.append(dict(bank=bank, declared_width=[75,75,75,72][bank],
                          native_width=len(bits), omitted_declared_bits=sorted(set(range([75,75,75,72][bank]))-bits)))
    assert banks[0]["omitted_declared_bits"] == [b-1 for b in omitted_co_bits]
    assert all(not b["omitted_declared_bits"] for b in banks[1:])
    missing_area_masters = sorted(set(masters)-set(geom["masters"]))
    native_area = sum(geom["masters"][m]["w"] * geom["masters"][m]["h"] * count
                      for m, count in masters.items() if m in geom["masters"])
    extra_ff_area_lb = sum(v["extra_copies_target32_lower_bound"] *
                          geom["masters"][v["master"]]["w"] * geom["masters"][v["master"]]["h"]
                          for v in violations if v["role"] == "FF")
    summary = dict(tile=tile, evidence_sha256={n: hashlib.sha256((source/n).read_bytes()).hexdigest()
                    for n in ("cells.json.gz", "drivers.json.gz", "roots.json.gz", "boundary.json.gz", "summary.json")},
                   cells=len(cells), FF=len(ffs), macro_count=0, masters=dict(sorted(masters.items())),
                   canonical_roots=len(roots), multi_driver_components=sum(len(r["drivers"])>1 for r in roots),
                   unknown_source_components=sum(not r["drivers"] for r in roots),
                   source_driver_roles=dict(role_counts),
                   nonclock_violating_roots=len(violations),
                   direct_boundary=dict(total=len(boundary_rows),
                       sequential_only=sum(b["direct_sequential"] for b in boundary_rows),
                       data_only=sum(b["direct_data"] for b in boundary_rows),
                       categories=dict(collections.Counter(b["category"] for b in boundary_rows)),
                       direct_registered_FF=len(owner_faces),
                       FF_shared_across_faces={k:sorted(v) for k,v in owner_faces.items() if len(v)>1}),
                   front_storage_banks=banks,
                   frozen_source=dict(path=source_path, blob=provenance["git_blob"], sha256=provenance["sha256"],
                       manifest_sha256=binding["manifest_sha256"],
                       actual_front_module="qkd_kv_hbm_elastic_front_mc_nc",
                       actual_return_module="qkd_static_kv_return_slots_mc_nc",
                       exclusive_front_co_consumer="u_return.controller_co",
                       downstream_unused_co_payload_bits=omitted_co_bits,
                       native_storage_pruning_explained_bits=32*len(omitted_co_bits)),
                   ff_groups=dict(ff_groups.most_common()),
                   native_master_area_known_subtotal_um2=native_area,
                   missing_area_masters=missing_area_masters,
                   FF_extra_area_lower_bound_um2=extra_ff_area_lb,
                   floorplan_known_subtotal_lower_bound_at50pct_um2=2*(native_area+extra_ff_area_lb),
                   complete_successor_area_um2=None, added_clock_sinks=None,
                   physical_stage_reach_um=None, successor_token_cycle_delta=None,
                   status="MODEL_BLOCKED_STORAGE_CLOCK_LIFETIME_RECURSIVE_FANOUT_AND_PHYSICAL")
    return summary, sorted(violations,key=lambda v:(-v["pins"],v["driver"])), boundary_rows


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pickup",type=Path,required=True)
    p.add_argument("--terminal",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    reports = {}
    for tile in ("pc","pc_h"):
        summary, violations, boundary=audit(args.pickup,args.terminal,tile)
        for name,obj in (("summary",summary),("violations",violations),("boundary",boundary)):
            (args.out/(tile+"_"+name+".json")).write_text(json.dumps(obj,indent=2)+"\n")
        print(tile,summary["nonclock_violating_roots"],summary["source_driver_roles"])
        reports[tile] = summary
    model = dict(
        status="ROOT_MODEL_REVIEW_REQUIRED_NO_RTL_OR_GATE",
        acceptance_logical_pins_per_nonclock_driver=32,
        actual_complete_successor_copy_fixed_point=None,
        all_driver_costs_include_recursive_D_enable_reset_upstream_tax=True,
        matching_uninitialized_state_assumption_permitted=False,
        phase_and_collision_proof_complete=False,
        successor_latency_edges=None,
        successor_token_cycles=None,
        successor_complete_area_um2=None,
        successor_outline_um=None,
        front_candidate=dict(
            primitive="ot_sram_1r1w2c_32x64_m1", primitive_source="e26d92503",
            diagnostic_only_contact_audit="3e95aae81", diagnostic_source="3ff02bde1",
            banks=4, declared_widths=[75,75,75,72], macros_per_bank=2,
            macro_instances=8, physical_bits=8*32*64, declared_bits=32*297,
            declared_packing_unused_bits=8*32*64-32*297,
            width_um=31.992, height_um=17.304, macro_area_um2=8*31.992*17.304,
            macro_clock_contacts=16, writer_clock_domains=4, reader_clock_domains=1,
            logical_write_bits_per_hbm_edge=297, logical_read_bits_per_hbm_edge=297,
            useful_payload_bits_per_hbm_edge=256,
            actual_nominal_holds_or_waits_added=0,
            added_read_edge=None,
            preread_request_equation="(rp + (take ? 1 : 0)) modulo 32",
            consume_equation="unchanged out_q captures current rp word exactly on take",
            first_put_source_age_edges=3,
            collision_rule="disable undefined macro same-address read; exact previous/current write forwarding required",
            collision_forward_payload_FF_reserve=297,
            collision_forward_control_FF_reserve=4*(5+1)+4*(5+1),
            macro_grid_um=43.2, west_east_contacts_per_macro_face=103,
            full_face_contacts_per_um=103/17.304,
            replicated_PG_OBS_via_contact_escape_proven=False,
            pin_face_channel_and_parent_slot=None,
            proof_obligations=["fixed 4 storage-clock phases relative to pll_hbm",
                "first take after cold reset and every restart",
                "back-to-back last-take/start and pointer wrap",
                "nominal no-overwrite lifetime and OLD read semantics",
                "overflow/go fault cases preserve original behavior",
                "arbitrary uninitialized storage, output hold when not take",
                "unchanged occupancy/pending/hold/drain/fault/reset priorities"]),
        other_observed_runtime_storage=dict(
            return_payload=dict(native_bits=8*288, bank_pointer_FF_excluded=48,
                candidate_macro_instances=8, write_clocks=4, read_clock="ck", lifetime_proven=False),
            control_down_FIFO=dict(native_bits=2304, candidate_macro_instances=5, lifetime_proven=False),
            control_up_FIFO=dict(native_bits=2064, candidate_macro_instances=5, lifetime_proven=False),
            full_source_indexed_storage_inventory_complete=False),
        preexisting_native_costs={t:dict(FF=s["FF"], source_driver_roles=s["source_driver_roles"],
            fixed_face_extra_same_edge_copies_lower_bound=sum(len(v)-1 for v in s["direct_boundary"]["FF_shared_across_faces"].values()),
            native_area_known_subtotal_um2=s["native_master_area_known_subtotal_um2"])
            for t,s in reports.items()},
        scope="Finite architecture candidate and independently reclassified frozen native evidence; no source safety or physical adoption")
    (args.out/"repair_model.json").write_text(json.dumps(model,indent=2)+"\n")
