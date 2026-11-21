"""CLAND-TIE-1 (COORD 11-14, S81 FABLE-REVIEW-COL step B): tieable clock-landing monitor children.

A partition type may declare clock.landing_contract.tieable_children = [{"index": i, "seam": bool}, ...].  Those child
pins (cland_dn_ready_i, cland_dn_fault_i and, for a seam child, fclk_in_cland_dn_i) exist on every instance of the type;
a seam child also receives a separately audited use strap. It masks the checked receiver status before reduction,
because a tied forwarded clock does not train its ring.
an instance whose die-level collector has no child at index i (or is not in the collector at all) ties them to constants:
ready 1'b1, fault 1'b0, forwarded clock 1'b0.  The tie is a neutral element of the collector (a permanently ready,
fault-free child), so the monitor result of the real children is unchanged.  Emit writes the literals
(clock_landings.emit_top); the bind tie-off audit (straps.audit_top_ties) accepts exactly this pin / value set for that type
and nothing else; die_constant_cells.tcl gives each bit its own TIEHI/TIELO (same rows as ID straps).
"""
READY, FAULT, CLOCK = "1'b1", "1'b0", "1'b0"


def tie_ports(tieable):
    """{port: literal} for a tieable_children list."""
    out = {}
    for c in tieable or []:
        i = int(c["index"])
        out[f"cland_dn_ready_{i}"] = READY
        out[f"cland_dn_fault_{i}"] = FAULT
        if c.get("seam"):
            out[f"fclk_in_cland_dn_{i}"] = CLOCK
    return out


def tie_connections(tieable, connected):
    """Verilog named connections for the declared children an instance does not use (connected: set of indices that
    have a real collector edge into this instance)."""
    conn = []
    for c in sorted(tieable or [], key=lambda c: int(c["index"])):
        i = int(c["index"])
        if i in connected:
            continue
        conn += [f"        .cland_dn_ready_{i}({READY})", f"        .cland_dn_fault_{i}({FAULT})"]
        if c.get("seam"):
            conn.append(f"        .fclk_in_cland_dn_{i}({CLOCK})")
    return conn


# UNIFY-TOOLS ROLE-STRAP (count_align_bind.role_strap): the start pin a copy does not use -- cland_rstart_in on an
# origin copy, cland_tstart_in on a relay copy -- is tied 0 at the parent (strap_ca_relay selects the other one).
ROLE_STRAP_TIES = {"cland_rstart_in": "1'b0", "cland_tstart_in": "1'b0"}


DORMANT_PREFIX = "strap_ca_off_"   # == count_align_bind.DORMANT_PREFIX


def landing_ties(types):
    """{type name: {port: literal}} from plan partition types (bind tie-off audit input)."""
    out = {}
    for tn, t in types.items():
        lc = ((t.get("clock") or {}).get("landing_contract") or {})
        ports = tie_ports(lc.get("tieable_children"))
        if t.get("landing_role_strap") is True:
            ports = dict(ports, **ROLE_STRAP_TIES)
        # UNIFY-TOOLS-R3 DORMANT: a copy that leaves a landed class slot spare ties that ring's forwarded clock and
        # start 0 (its strap_ca_off_<b> = 1 masks the ring status, count_align_bind / clock_landings DORMANT)
        dorm = [c["name"][len(DORMANT_PREFIX):] for c in t.get("count_straps", []) if c["name"].startswith(DORMANT_PREFIX)]
        if dorm:
            ports = dict(ports, **{f"{pin}_{b}": "1'b0" for b in dorm for pin in ("fclk_in", "cland_fstart_in")})
        if ports:
            out[tn] = ports
    return out


def validate(tieable, pins):
    """Plan check: every tieable child names an input pin of the contract; returns the missing ports."""
    names = {p["name"]: p.get("dir") for p in pins}
    return [port for port in tie_ports(tieable) if names.get(port) != "in"]


MONITOR_USE_PREFIX = "strap_cland_use_"


def seam_use_ports(tieable):
    """Physical use straps needed only for seam children with a trainable ring."""
    return {int(c["index"]): MONITOR_USE_PREFIX + str(int(c["index"]))
            for c in tieable or [] if c.get("seam")}


def use_connections(tieable, connected):
    return [f"        .{port}(1'b{int(i in connected)})"
            for i, port in sorted(seam_use_ports(tieable).items())]


def qualified_status(ready, fault, use):
    """Mask the checked ring status, including training and guard failures."""
    if use is None:
        return ready, fault
    return f"(!{use} || ({ready}))", f"({use} && ({fault}))"


def instance_use(plan):
    """Expected (width, value), derived from physical landing edges, not emitted RTL."""
    incoming = {}
    for edge in plan.get("clock", {}).get("landing_network", {}).get("edges", []):
        dst = edge["dst"]
        incoming.setdefault(dst["part"], set()).add(dst["bus"])
    result = {}
    for part in plan["partitions"]:
        tn = part["type"]
        lc = plan["partition_types"][tn].get("clock", {}).get("landing_contract", {})
        for i, port in seam_use_ports(lc.get("tieable_children")).items():
            pins = {f"fclk_in_cland_dn_{i}", f"cland_dn_ready_{i}", f"cland_dn_fault_{i}"}
            live = incoming.get(part["name"], set()) & pins
            if live and live != pins:
                raise ValueError(f"{part['name']}: partial landing monitor child {i}: {sorted(live)}")
            result.setdefault(part["name"], {})[port] = (1, int(bool(live)))
    return result


def with_use_pins(pins, tieable, outline):
    """Place a use strap on a free neighboring track of the monitor control pins.

    The two mandatory control pins provide the layer, face and track interval.
    G0 still checks the proposed site against the rest of the tile.
    """
    placed = [dict(pin) for pin in pins]
    for i, name in sorted(seam_use_ports(tieable).items()):
        lookup = {pin["name"]: pin for pin in placed}
        if name in lookup:
            continue
        ready, fault = (lookup[f"cland_dn_{role}_{i}"] for role in ("ready", "fault"))
        x, y = ready["xy_um"]
        delta = tuple(round(b - a, 6) for a, b in zip(ready["xy_um"], fault["xy_um"]))
        if ready["layer"] != fault["layer"] or (delta[0] == 0) == (delta[1] == 0):
            raise ValueError(f"{name}: control pins need a common track axis")
        occupied = {tuple(round(v, 6) for v in pin["xy_um"]) for pin in placed
                    if pin["layer"] == ready["layer"]}
        for step in (2, -1, 3, -2, 4, -3, 5, -4):
            xy = (round(x + step * delta[0], 6), round(y + step * delta[1], 6))
            if xy not in occupied and all(0 <= v <= lim for v, lim in zip(xy, outline)):
                placed.append(dict(name=name, dir="in", kind="ctl", epoch=False,
                                   layer=ready["layer"], xy_um=list(xy)))
                break
        else:
            raise ValueError(f"{name}: no free neighboring control pin site")
    return placed


def physical_use_pins(type_row):
    """Placed scalar strap declarations from the landing contract."""
    lc = type_row.get("clock", {}).get("landing_contract", {})
    expected = set(seam_use_ports(lc.get("tieable_children")).values())
    return {p["name"]: 1 for p in lc.get("pins", []) if p["name"] in expected
            and p.get("dir") == "in" and p.get("kind") == "ctl"}


def with_use_manifest(manifest, types, expected):
    """Include use straps in the ordinary die parent tie/physical contract."""
    from copy import deepcopy
    manifest = deepcopy(manifest)
    for tn, t in types.items():
        for pin, width in physical_use_pins(t).items():
            manifest["types"].setdefault(tn, {})[pin] = dict(width=width, kind="landing_monitor_use")
    for part, pins in expected.items():
        for pin, (width, value) in pins.items():
            manifest["instances"].setdefault(part, {})[pin] = dict(width=width, value=value, kind="landing_monitor_use")
    return manifest
