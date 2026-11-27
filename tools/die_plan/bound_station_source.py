"""Qualify source-only station preparation across a reviewed physical crop."""
import copy
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "opentallas.bound_station_source.v1"
FAMILY_SCHEMA = "opentallas.bound_station_source.family.v1"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _omit(row, fields):
    return {key: value for key, value in row.items() if key not in fields}


def _station_logic(row):
    return dict(_omit(row, ("regs_um", "from_um", "to_um", "bit_sites_um", "bit_site_cell_um")),
                depth=len(row["regs_um"]))


def _landing_logic(clock):
    landing = {key: copy.deepcopy(value) for key, value in clock.items() if key.startswith("landing_")}
    contract = landing["landing_contract"]
    for key in ("collector_tree", "bound_reset_placement"):
        contract.pop(key, None)
    for key, band in contract["bands"].items():
        contract["bands"][key] = _omit(band, ("rect_um", "placement", "spread"))
    for source in contract["collector_local_sources"]:
        source["band"] = _omit(source["band"], ("rect_um", "placement", "spread"))
    contract["pins"] = [_omit(pin, ("xy_um",)) for pin in contract["pins"]]
    landing["landing_local_resets"] = [_omit(row, ("xy_um",)) for row in landing["landing_local_resets"]]
    for branch in landing["landing_writer_start"]["branches"].values():
        branch["stages"] = [_omit(row, ("xy_um",)) for row in branch["stages"]]
    return landing


def _type_logic(typ):
    logical = _omit(typ, ("outline_um", "clock", "relay_sites", "relay_split", "buses", "ft_slots",
                          "hard_cores", "internal_stations", "reset"))
    logical["buses"] = [_omit(bus, ("window_um",)) for bus in typ["buses"]]
    logical["ft_slots"] = [
        dict(_omit(slot, ("in_window_um", "out_window_um", "regs_um", "bit_sites_um")),
             depth=len(slot["regs_um"])) for slot in typ["ft_slots"]]
    logical["hard_cores"] = [_omit(core, ("origin_um", "lef")) for core in typ["hard_cores"]]
    logical["internal_stations"] = [_station_logic(row) for row in typ["internal_stations"]]
    logical["reset"] = _omit(typ.get("reset", {}), ("consumer_sites_um",))
    logical["landing"] = _landing_logic(typ["clock"])
    physical_clock = {"added_taps", "band_fixed_um", "reset_tree_anchor", "tap_cap_cascade", "tap_group",
                      "tap_max_sinks", "tap_mode", "tap_um", "taps"}
    logical["clock"] = {key: value for key, value in typ["clock"].items()
                        if key not in physical_clock and not key.startswith("landing_")}
    return logical


def _require(ok, detail):
    if not ok:
        raise ValueError(f"KIT_TOPOLOGY_BOUND_STATION_SOURCE: {detail}")


def _family_type_logic(typ):
    """Ignore the reviewed physical fields while retaining landing and station identities."""
    normalized = copy.deepcopy(typ)
    clock = normalized["clock"]
    for key in ("sink_sites_um", "tap_pitch_um", "tap_pin_heights_um"):
        clock.pop(key, None)
    for edge in clock.get("edge_clocks", ()):
        edge.pop("tap_um", None)
    landing = clock.setdefault("landing_contract", {})
    for key, empty in (("bands", {}), ("collector_local_sources", []), ("pins", [])):
        landing.setdefault(key, empty)
    for child in landing.get("collector_children", ()):
        child.pop("xy_um", None)
    clock.setdefault("landing_local_resets", [])
    clock.setdefault("landing_writer_start", {"branches": {}})
    return _type_logic(normalized)


def _changed_keys(previous, current):
    return (previous.keys() ^ current.keys()
            | {key for key in previous.keys() & current.keys() if previous[key] != current[key]})


def _family_reset_scope(proof, old, physical, reference, captured):
    """Qualify the incident edges of a named family against the captured release schedule."""
    import reset_tree as RT

    members = proof["family_types"]
    _require(isinstance(members, dict) and all(isinstance(part, str) for part in members.values())
             and members.get(proof["type"]) == proof["instance"]
             and len(members) == len(set(members.values())), "invalid family type selection")
    _require(old.parts.keys() == physical.parts.keys(), "family changes the partition inventory")
    for part, row in old.parts.items():
        typ = row["type"]
        _require(physical.parts[part]["type"] == typ, f"family changes type at {part}")
        if typ in members:
            _require(members[typ] == part, f"family type {typ} is shared by another instance")
            continue
        _require(physical.rect(part) == old.rect(part) and physical.parts[part] == row
                 and all(physical.types[typ].get(key) == old.types[typ].get(key)
                         for key in ("reset", "clock", "hard", "hard_cores")),
                 f"reset geometry or ownership outside family changes at {part}")
    _require(all(part in old.parts and old.parts[part]["type"] == typ for typ, part in members.items()),
             "family names an unbound instance")
    for typ in members:
        _require(_family_type_logic(old.types[typ]) == _family_type_logic(physical.types[typ]),
                 f"station, landing or macro logic changed for family type {typ}")
    prior_parts = captured["parts"]
    member_parts = set(members.values())
    edges = {p for p, row in prior_parts.items() if p in member_parts or row.get("parent") in member_parts}
    reset = physical.reset
    original = reference["reset"]
    roles = reset["boundary_roles"]
    previous_roles = original.get("boundary_roles", {})
    _require(set(roles["outputs"]) == set(members) and set(roles["parents"]) == member_parts,
             "named reset boundary does not exactly match the family")
    _require(set(previous_roles.get("outputs", {})) <= members.keys()
             and set(previous_roles.get("parents", {})) <= member_parts,
             "family removes existing boundary roles outside its scope")
    changes = {"in_sites": set(members), "keep_outs": set(members),
               "parent_pins": edges, "die_relays": edges}
    _require(_changed_keys(original, reset) <= changes.keys() | {"boundary_roles"},
             "unrelated global reset inputs changed")
    for key, allowed in changes.items():
        _require(_changed_keys(original.get(key, {}), reset.get(key, {})) <= allowed,
                 f"unrelated {key} changed")

    fields = ("source", "type", "entry_stages", "depth_K", "release")
    for p in member_parts:
        role = roles["parents"][p]
        _require(all(prior_parts[p][field] == role[field] for field in fields)
                 and reset["in_sites"][role["type"]] == role["input_um"],
                 f"native parent source, entry or release changed at {p}")
    typed_outputs = {}
    for typ in members:
        rows = roles["outputs"][typ]
        previous = captured["types"][typ]["outs"]
        expected_names = [port for port, *_ in previous]
        _require([row["port"] for row in rows] == expected_names
                 and reset["keep_outs"][typ] == [row["site"] for row in rows],
                 f"named reset outputs or order changed for {typ}")
        typed_outputs[typ] = {row["port"]: row for row in rows}

    maximum = 0.0
    with RT.site_rule(physical):
        for p in sorted(edges):
            old_edge = prior_parts[p]
            q, port = old_edge["source"].rsplit(".", 1)
            parent_type = prior_parts[q]["type"]
            site_parent, slot = reset["parent_pins"][p]
            _require(q == site_parent, f"named parent changed at {p}")
            parent_slots = RT.face_sites(physical, parent_type)
            _require(type(slot) is int and 0 <= slot < len(parent_slots), f"invalid parent slot at {p}")
            out = parent_slots[slot]["xy"]
            if parent_type in members:
                named = typed_outputs[parent_type].get(port, {})
                _require(named.get("site") == slot and tuple(named.get("xy_um", ())) == tuple(out),
                         f"named parent output changed at {p}")
            else:
                out_before = {name: xy for name, *xy in captured["types"][parent_type]["outs"]}
                _require(port in out_before and tuple(out_before[port]) == tuple(out),
                         f"captured external parent output changed at {p}")
            if p in member_parts:
                role = roles["parents"][p]
                _require(tuple(role["output_um"]) == tuple(out), f"declared parent output differs at {p}")
                entry = role["input_um"]
            else:
                entry = captured["types"][old_edge["type"]]["in_um"]
            bridge = reset.get("die_relays", {}).get(p)
            old_bridge = original.get("die_relays", {}).get(p)
            sites = bridge["sites_um"] if bridge else []
            _require(len(sites) == old_edge.get("die_relays", 0)
                     and (not bridge or (bridge["parent"], bridge["site"]) == (q, slot)),
                     f"registered bridge identity or depth changed at {p}")
            _require(_changed_keys(old_bridge or {}, bridge or {}) <= {"site", "sites_um"},
                     f"registered bridge policy changed at {p}")
            route = [physical.to_die(q, out), *sites, physical.to_die(p, entry)]
            hop = max(sum(abs(a - b) for a, b in zip(u, v)) for u, v in zip(route, route[1:]))
            _require(hop <= RT.hop_um(physical) + 1e-6, f"named reset bridge exceeds reach at {p}")
            maximum = max(maximum, hop)
    return {"types": sorted(members), "reset_edges": len(edges), "max_reset_hop_um": round(maximum, 6)}


_BF_COL3_C_LEF_SHA256 = "cd64688b278cd2aa57985fef07bffad35c6049ed3b8a233ea44ce554821e8148"
_BF_COL3_C = "ot_v41_bf_col3_c"


def _reviewed_artifact(record):
    path = Path(record["path"])
    _require(path.is_absolute() and _sha(path) == record["sha256"], f"reviewed macro power artifact changed: {path}")
    return path


def _bf_col3_c_pg_predecessor(raw, tn, proof):
    prior_path = _reviewed_artifact(proof["prior_plan"])
    prior = json.loads(prior_path.read_bytes())
    parts = raw["partition_types"]
    typ = parts[tn]
    previous = dict(raw, partition_types={**parts, tn: _omit(typ, {"core_pg_connect"})})
    _require(typ.get("core_pg_connect") is True and "core_pg_connect" not in prior["partition_types"][tn]
             and prior == previous, "macro power transition must add only the selected type's explicit grid")
    return prior_path, prior


def _m5_grid_change(before, after, targets):
    """The only new executable effect is two named memberships in an existing grid."""
    a, b = ([line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
            for text in (before, after))
    grid = "define_pdn_grid -macro -name {core_pg_M5} -instances "
    connection = "add_pdn_connect -grid {core_pg_M5} -layers {M5 M6}"
    _require(a.count(connection) == b.count(connection) == 1, "macro power grid must connect M5 to M6")
    changed = [(old, new) for old, new in zip(a, b) if old != new]
    _require(len(a) == len(b) and len(changed) == 1, "macro power changes unrelated executable PDN")
    old, new = changed[0]
    _require(old.startswith(grid) and new.startswith(grid), "macro power changes the wrong grid")

    def grid_arguments(line):
        body, delim, options = line.removeprefix(grid + "{").partition("} -voltage_domains ")
        members = re.findall(r"\{(\^[^}]+\$)\}", body)
        _require(delim and body == " ".join("{" + member + "}" for member in members),
                 "macro power membership list is not canonical")
        return members, options

    old_members, old_options = grid_arguments(old)
    new_members, new_options = grid_arguments(new)
    spellings = set(re.findall(r"\{(\^[^}]+\$)\}", targets))
    _require(len(spellings) == 2 and not set(old_members) & spellings
             and len(new_members) == len(old_members) + 2 and spellings <= set(new_members)
             and [member for member in new_members if member not in spellings] == old_members,
             "macro power changes membership outside the two approved macros")
    _require(new_options == old_options, "macro power changes the existing grid options")
    core_commands = ("define_pdn_grid -macro -name {core_pg_", "add_pdn_connect -grid {core_pg_")
    core = tuple(line for line in a if line.startswith(core_commands))
    return core, len(old_members), len(new_members)


def _verify_bf_col3_c_pg(required, raw, tn, plan, prior_plan, prior, bound_source):
    import bound_macro_paths
    import cores
    import gen_phys
    import schema

    root = Path(required["source_tree"])
    _require(root.is_absolute() and root.is_dir(), "macro power requires a named source tree")
    typ = raw["partition_types"][tn]
    anchors = {row["inst"]: row for row in typ["hard_cores"] if row.get("module") == _BF_COL3_C}
    mapped = bound_macro_paths.resolve(typ, bound_source.read_text())
    aliases = {row["inst"]: row["physical_inst"] for row in mapped if row["physical_master"] == _BF_COL3_C}
    _require(len(anchors) == 2 and anchors.keys() == aliases.keys()
             and aliases == required["macro_aliases"], "macro power target differs from the captured BF_COL3_C aliases")
    _require(all(_sha(cores.resolve(row["lef"], root)) == _BF_COL3_C_LEF_SHA256 for row in anchors.values()),
             "macro power views do not match the reviewed signed BF_COL3_C LEF")

    bound = {row["inst"]: row["physical_inst"] for row in mapped}

    def stock(data, path):
        physical = schema.Plan(data, path=path)
        macros = [(bound.get(row[0], row[0]), *row[1:]) for row in gen_phys.type_macros(physical, tn, root=root)]
        return "\n".join(gen_phys.core_pg_grids(physical, tn, macros, root=root))

    targets = gen_phys._pdn_inst_patterns(aliases.values())
    expected = _m5_grid_change(stock(prior, prior_plan), stock(raw, plan), targets)
    old_pdn, new_pdn = (_reviewed_artifact(required[name]) for name in ("before_pdn", "after_pdn"))
    observed = _m5_grid_change(old_pdn.read_text(), new_pdn.read_text(), targets)
    _, before, after = observed
    _require(expected == observed and before == required["old_m5_memberships"],
             "macro power grid receipt disagrees with stock generation")
    return {"macro_aliases": aliases, "before_memberships": before, "after_memberships": after}


def verify(receipt, plan, native_plan, tn, rtl_dir, manifest):
    """Validate the named source artifact. This does not qualify a bind or a physical run."""
    import bind_component
    import bound_reset_contract as BRC
    import gen_phys
    import kit_topology as KT
    import native_istations as NI
    import reset_tree as RT
    import schema

    proof = json.loads(Path(receipt).read_bytes())
    family = proof.get("schema") == FAMILY_SCHEMA
    _require((family or proof.get("schema") == SCHEMA) and proof.get("type") == tn, "wrong receipt type")
    _require(native_plan and manifest, "an explicit native plan and asbuilt manifest are required")
    plan, native_plan, rtl_dir = map(Path, (plan, native_plan, rtl_dir))
    _require((_sha(plan), _sha(native_plan)) ==
             (proof["prepared_plan_sha256"], proof["producer_plan_sha256"]), "stale plan or producer")
    raw, producer = [json.loads(path.read_bytes()) for path in (plan, native_plan)]
    typ, old = [value["partition_types"][tn] for value in (raw, producer)]
    pg = proof.get("reviewed_bf_col3_c_pg")
    prior_plan, logical_raw = _bf_col3_c_pg_predecessor(raw, tn, pg) if pg is not None else (None, raw)
    current_outline, old_outline = typ["outline_um"], old["outline_um"]
    _require(current_outline != old_outline and all(0 < a <= b for a, b in zip(current_outline, old_outline)),
             "selected outline is not a crop")
    logic = _family_type_logic if family else _type_logic
    _require(logic(logical_raw["partition_types"][tn]) == logic(old),
             "selected type changes logical station, landing or macro inputs")
    man = json.loads((rtl_dir / "kit_rtl.json").read_bytes())
    instance = proof["instance"]
    _require(man["bound_type"] == man["plan_type"] == tn and man["instances"] == [instance],
             "wrapper does not select the same unique instance and bound type")
    _require(not any(man.get(key) for key in ("narrow_buses", "plan_buses_unbound", "spare_out_bits")),
             "wrapper loses a logical port or bit")
    for value in (raw, producer):
        parts = [part["name"] for part in value["partitions"] if part["type"] == tn]
        _require(parts == [instance], "plan does not select the same unique instance")
    out = Path(man["bind_out"])
    prov = json.loads((out / "provenance_bind.json").read_bytes())["provenance"]
    _require(prov["plan_sha256"] == proof["producer_plan_sha256"], "producer receipt differs")
    bind_report = json.loads((out / "bind_report.json").read_bytes())
    _require(bind_report["n_errors"] == 0, "producer native bind is not closed")
    _require(KT.bind_matches(producer, tn, out, manifest, native_plan), "producer topology no longer matches")
    current = KT.native_contract(raw, manifest, plan)
    original = json.loads((out / "native_topology.json").read_bytes())
    _require(current["transport"] == original["transport"]
             and current["ownership"][tn] == original["ownership"][tn], "transport or station ownership changed")
    depths = {row["conn"]: row["stages"] for row in current["ownership"][tn] if row["phase"] == "NATIVE"}
    _require(depths == proof["native_out_depths"], "producer native output depth changed")
    if family:
        native_buses = {conn.removeprefix("bus:") for conn in depths}
        _require(NI.source_entries(typ, native_buses) == NI.source_entries(old, native_buses),
                 "family changes the captured native output station geometry")

    files = [Path(path) for path in man["files"]]
    readset = {path.name: _sha(path) for path in files}
    expected_readset = proof["rtl_sha256"].copy()
    stamp = rtl_dir / "kit_topology_prepared.json"
    receipt_sha = _sha(receipt)
    if stamp.is_file():
        saved = json.loads(stamp.read_bytes())
        _require(saved.get("reviewed_station_source_sha256") == receipt_sha, "prepared station receipt changed")
        expected_readset[man["bound_module"] + ".sv"] = saved["source_sha256"]
    _require(len(readset) == len(files) and readset == expected_readset, "kit RTL readset changed")
    approved_pg = {}
    if pg is not None:
        bound_source, = (path for path in files if path.stem == man["bound_module"])
        approved_pg["reviewed_bf_col3_c_pg"] = _verify_bf_col3_c_pg(
            pg, raw, tn, plan, prior_plan, logical_raw, bound_source)
    physical = schema.Plan(logical_raw, path=plan)
    capture = BRC.kit(files, tn)
    _require(capture is not None and capture["tree_sha256"] == proof["bound_tree_sha256"], "staged reset differs")
    producer_rtl = out / "rtl" / (bind_report["types"][tn]["module"] + ".sv")
    original_reset = BRC.validate(json.loads(producer_rtl.with_suffix(".reset_tree.json").read_bytes()), tn)
    landing = typ["clock"]["landing_contract"]
    _require(original_reset["tree_sha256"] == capture["tree_sha256"]
             and original_reset["bound_rtl_sha256"] == _sha(producer_rtl)
             and landing["collector_tree"] == capture["tree"]
             and landing["bound_reset_placement"]["source_tree_sha256"] == capture["tree_sha256"],
             "captured reset authority changed")

    ports, _ = bind_component.interface(files[0].read_text(), man["plan_module"])
    glue = {name for name in ports if re.fullmatch(r"clk(?:_t[0-9]+)?", name)}
    planned = {name for name, *_ in schema.tap_grid(physical, tn) if re.fullmatch(r"clk(?:_t[0-9]+)?", name)}
    previous = schema.Plan(producer, path=native_plan)
    old_glue = {name for name, *_ in schema.tap_grid(previous, tn) if re.fullmatch(r"clk(?:_t[0-9]+)?", name)}
    wrapper_taps = set(man["taps"]) | {"clk"}
    _require(glue == planned == set(proof["glue_taps"]) and old_glue <= glue <= wrapper_taps
             and all(ports.get(name) == {"direction": "input", "width": 1} for name in wrapper_taps),
             "actual wrapper clock census differs from the reviewed plan")
    verified = gen_phys.install_bound_native_reset(physical, tn, files, source_contract=capture)
    _require(verified["tree"] == original_reset["tree"], "native graph changed")
    if family:
        captured = json.loads((out / "bind_reset.json").read_bytes())
        schedule = _family_reset_scope(proof, previous, physical, producer, captured)
        return {"receipt_sha256": receipt_sha, "bound_tree_sha256": capture["tree_sha256"],
                "native_out_depths": depths, "glue_ports": sorted(glue), "family": schedule, **approved_pg}

    # A restored physical reset output can have the same release relation as the
    # producer. Check the mapped parent/source names and ages using stock wavefront.
    roles = raw["reset"]["boundary_roles"]
    _require(set(roles["outputs"]) == {tn} and instance in roles["parents"]
             and all(name == instance or role["source"].split(".", 1)[0] == instance
                     for name, role in roles["parents"].items()), "named boundary exceeds the selected instance scope")
    allowed = {"boundary_roles", "in_sites", "keep_outs", "parent_pins"}
    _require(_omit(raw["reset"], allowed) == _omit(producer["reset"], allowed), "unrelated global reset inputs changed")
    for key, names in (("in_sites", {tn}), ("keep_outs", {tn}), ("parent_pins", set(roles["parents"]))):
        _require(_omit(raw["reset"].get(key, {}), names) == _omit(producer["reset"].get(key, {}), names),
                 f"unrelated {key} changed")
    prior_roles = json.loads((out / "bind_reset.json").read_bytes())["parts"]
    source_roles = RT.wf_plan(schema.Plan(raw, path=plan))["parts"]
    for name in roles["parents"]:
        fields = ("source", "entry_stages", "depth_K", "release")
        _require(all(prior_roles[name][field] == source_roles[name][field] for field in fields),
                 f"native parent source or release changed at {name}")
    return {"receipt_sha256": receipt_sha, "bound_tree_sha256": capture["tree_sha256"],
            "native_out_depths": depths, "glue_ports": sorted(glue), **approved_pg}
