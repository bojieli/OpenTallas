"""Explicit opt-in effective layer model; not a per-net router layer constraint.

The pinned router can use lower layers outside its GRT clock preference. This
contract prices every declared layer conservatively and applies the existing
2w2s NDR there. Actual post-route layer/width/spacing qualification is separate.
"""
import math


class RoutingError(ValueError):
    pass


def _number(value, name, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise RoutingError(f"effective clock routing: invalid {name}")
    return value


def profile(sl):
    contract = sl.get("effective_clock_routing")
    if contract is None:
        return None
    if not isinstance(contract, dict) or contract.get("mode") != "directional_envelope":
        raise RoutingError("effective clock routing requires explicit directional_envelope mode")
    layers = contract.get("layers")
    # Deliberately bounded first use. This does not silently generalize the
    # historical M4/M5 geometric model or change signal-net routing limits.
    if layers != ["M3", "M4", "M5"]:
        raise RoutingError("effective clock routing supports explicit M3/M4/M5 only")
    ndr = sl.get("clock_ndr") or {}
    if (ndr.get("layers") != layers or ndr.get("width_multiplier") != 2
            or ndr.get("spacing_multiplier") != 2):
        raise RoutingError("effective clock routing requires matching existing 2w2s NDR on every declared layer")
    pg = sl.get("pg_obstructions_um")
    if not isinstance(pg, dict) or any(layer not in pg for layer in layers):
        raise RoutingError("effective clock routing requires explicit PG obstacles for every declared layer")
    rc = contract.get("layer_rc")
    if not isinstance(rc, dict) or set(rc) != set(layers):
        raise RoutingError("effective clock routing requires exact per-layer prebuild RC")
    if not isinstance(contract.get("rc_source"), str) or not contract["rc_source"].strip():
        raise RoutingError("effective clock routing requires an explicit prebuild RC source")
    if contract.get("measured_timing_used") is not False:
        raise RoutingError("effective clock routing refuses measured timing input")
    for layer in layers:
        values = rc[layer]
        if not isinstance(values, dict) or values.get("width_multiplier") != 2 or values.get("spacing_multiplier") != 2:
            raise RoutingError(f"effective clock routing: {layer} RC must price the actual 2w2s rule")
        for key in ("resistance_kohm_per_um", "capacitance_ff_per_um"):
            _number(values.get(key), f"{layer} {key}", positive=True)
        if not isinstance(pg[layer], list):
            raise RoutingError(f"effective clock routing: invalid {layer} PG obstacles")
        for rect in pg[layer]:
            if not isinstance(rect, (list, tuple)) or len(rect) != 4:
                raise RoutingError(f"effective clock routing: invalid {layer} PG rectangle")
            for v in rect:
                _number(v, f"{layer} PG coordinate")
            if rect[0] >= rect[2] or rect[1] >= rect[3]:
                raise RoutingError(f"effective clock routing: invalid {layer} PG rectangle")
    clearance = _number(contract.get("clearance_um"), "clearance_um")
    def envelope(group):
        return [max(rc[layer][key] for layer in group)
                for key in ("resistance_kohm_per_um", "capacitance_ff_per_um")]
    return dict(horizontal_rc=envelope(["M4"]), vertical_rc=envelope(["M3", "M5"]),
                obstacles=pg["M4"], vertical_obstacles=pg["M3"] + pg["M5"], clearance=clearance,
                outline_um=sl["outline_um"])


def check_trunks(sl, plan):
    model = profile(sl)
    if model is None:
        return
    tree = plan.get("core_tree")
    if not tree:
        raise RoutingError("effective clock routing requires an actual planned tree")
    from core_infra_wire import channel_path
    xy = {n["name"]: n["xy_um"] for n in tree["nodes"]}
    if plan.get("clock_entry"):
        xy["port:" + tree["clock_port"]] = plan["clock_entry"]["xy_um"]
    for node in tree["nodes"] + tree.get("gates", []):
        parent, target = xy.get(node["parent"]), node["xy_um"]
        if parent is None:
            # A primary port without a geometric entry cannot receive a model
            # qualification merely because its coordinates were absent.
            raise RoutingError("effective clock routing requires every trunk endpoint geometry")
        try:
            path = channel_path(parent, target, model["obstacles"], model["clearance"], model["vertical_obstacles"], return_points=True)
            width, height = plan["outline_um"]
            if any(not (0 <= x <= width and 0 <= y <= height) for x, y in path):
                raise ValueError("conservative PG envelope leaves the physical outline")
        except ValueError as error:
            raise RoutingError(f"effective clock routing PG envelope: {error}") from error


def check_qualification(sl):
    """Building the RC model is allowed; emitting a physical plan needs results."""
    if sl.get("effective_clock_routing") is None:
        return
    q = (sl.get("core_tree") or {}).get("model_qualification", {})
    if (q.get("model") != "effective_directional_envelope"
            or q.get("measured_timing_used") is not False
            or q.get("effective_clock_routing") != sl["effective_clock_routing"]
            or not isinstance(q.get("source"), str) or not q["source"].strip()):
        raise RoutingError("effective clock routing requires matching two-corner envelope model qualification before emission")
    for corner in ("TT", "FF"):
        result = q.get("corners", {}).get(corner, {})
        values = {key: _number(result.get(key), f"{corner} model {key}")
                  for key in ("leaf_min", "leaf_max", "leaf_window", "slew_max")}
        if (values["leaf_max"] < values["leaf_min"]
                or abs(values["leaf_max"] - values["leaf_min"] - values["leaf_window"]) > .001
                or values["slew_max"] > 80
                or (q.get("window_policy", "gate") != "info" and values["leaf_window"] > 20)):
            raise RoutingError(f"effective clock routing {corner} model target FAIL before emission")
