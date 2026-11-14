"""CLAND-TIE-1 (COORD 11-14, S81 FABLE-REVIEW-COL step B): tieable clock-landing monitor children.

A partition type may declare clock.landing_contract.tieable_children = [{"index": i, "seam": bool}, ...].  Those child
pins (cland_dn_ready_i, cland_dn_fault_i and, for a seam child, fclk_in_cland_dn_i) exist on every instance of the type;
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


def landing_ties(types):
    """{type name: {port: literal}} from plan partition types (bind tie-off audit input)."""
    out = {}
    for tn, t in types.items():
        lc = ((t.get("clock") or {}).get("landing_contract") or {})
        ports = tie_ports(lc.get("tieable_children"))
        if ports:
            out[tn] = ports
    return out


def validate(tieable, pins):
    """Plan check: every tieable child names an input pin of the contract; returns the missing ports."""
    names = {p["name"]: p.get("dir") for p in pins}
    return [port for port in tie_ports(tieable) if names.get(port) != "in"]
