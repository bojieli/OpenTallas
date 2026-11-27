"""Qualify source-only station preparation across a reviewed physical crop."""
import copy
import hashlib
import json
import re
from pathlib import Path


SCHEMA = "opentallas.bound_station_source.v1"


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


def verify(receipt, plan, native_plan, tn, rtl_dir, manifest):
    """Validate the named source artifact. This does not qualify a bind or a physical run."""
    import bind_component
    import bound_reset_contract as BRC
    import gen_phys
    import kit_topology as KT
    import reset_tree as RT
    import schema

    proof = json.loads(Path(receipt).read_bytes())
    _require(proof.get("schema") == SCHEMA and proof.get("type") == tn, "wrong receipt type")
    _require(native_plan and manifest, "an explicit native plan and asbuilt manifest are required")
    plan, native_plan, rtl_dir = map(Path, (plan, native_plan, rtl_dir))
    _require((_sha(plan), _sha(native_plan)) ==
             (proof["prepared_plan_sha256"], proof["producer_plan_sha256"]), "stale plan or producer")
    raw, producer = [json.loads(path.read_bytes()) for path in (plan, native_plan)]
    typ, old = [value["partition_types"][tn] for value in (raw, producer)]
    current_outline, old_outline = typ["outline_um"], old["outline_um"]
    _require(current_outline != old_outline and all(0 < a <= b for a, b in zip(current_outline, old_outline)),
             "selected outline is not a crop")
    _require(_type_logic(typ) == _type_logic(old), "selected type changes logical station, landing or macro inputs")
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
    physical = schema.Plan(raw, path=plan)
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
            "native_out_depths": depths, "glue_ports": sorted(glue)}
