"""Wire planned early-core clocks into the actual kit-only bound leaf pins.

The source bind remains unchanged. Each declared clock input has a real child
clock consumer before synthesis, preserving the planned ABI without keep cells.
"""
import re

def rtl_wired(receipt):
    """True when wire() changed the bound source (a private kit copy is needed)."""
    return any(r.get("mode", "rtl") == "rtl" for r in receipt)


# DIE-QC-68/TYPES 11-04 (QC CB kit_rtl "core clock clk_c0: expected one bound leaf u_t22, got 0", 17 types): the QC bind
# flattens the as-built tile c16_E0_0.u_t_2_2 to the native leaf `qfd_tile_nk_rp2_romleaf_rr u_u_t_2_2`, with its 38
# clock-entry ports all on clk, while the plan places the A0 hard core `u_t22` = qfd_tile_nk_a0c.  The core module is that
# native body with the entries as internal nets of one `ck` (rtl/physical/a0_core/qfd_tile_nk_a0c.sv): same data ports,
# same cycles.  In the private kit copy only (the source bind stays immutable) the native leaf becomes the planned core,
# so a kit can never build around the native tile.  Exact master pairs only; anything else fails closed.
NATIVE_CORE_BODY = {"qfd_tile_nk_a0c": "qfd_tile_nk_rp2_romleaf_rr", "qfd_tile_nl_a0c": "qfd_tile_nl_rp2_romleaf_rr"}


def swap_native_cores(bound, hard_cores):
    """-> (bound, receipt): each planned A0 core u_t<r><c> replaces its native bound leaf u_u_t_<r>_<c> (see above)."""
    bound, receipt = swap_ahub_boundary(bound, hard_cores)
    for core in hard_cores or []:
        master, inst = core.get("module"), core.get("inst", "")
        name = re.fullmatch(r"u_t(\d)(\d)", inst)
        if master not in NATIVE_CORE_BODY or not name:
            continue
        leaf = f"u_u_t_{name.group(1)}_{name.group(2)}"
        heads = list(re.finditer(r"^([ \t]+)(\w+)[ \t]+" + leaf + r"[ \t]*\(", bound, re.M))
        if len(heads) != 1:
            raise ValueError(f"core {inst}: expected one native leaf {leaf}, got {len(heads)}")
        head = heads[0]
        if head.group(2) != NATIVE_CORE_BODY[master]:
            raise ValueError(f"core {inst} ({master}): native leaf {leaf} is {head.group(2)}, "
                             f"expected {NATIVE_CORE_BODY[master]}")
        end = bound.find("\n    );", head.end())
        if end < 0:
            raise ValueError(f"core {inst}: unclosed native leaf {leaf}")
        body = bound[head.end():end]
        clocks = re.findall(r"^[ \t]*\.(ck\w*)\(([^()]*)\),?[ \t]*$", body, re.M)
        nets = {net.strip() for _, net in clocks}
        if "ck" not in {pin for pin, _ in clocks} or len(nets) != 1:
            raise ValueError(f"core {inst}: native clock entries of {leaf} are not one net: {sorted(nets)}")
        body = re.sub(r"^[ \t]*\.ck_\w+\([^()]*\),?[ \t]*\n", "", body, flags=re.M)
        bound = bound[:head.start()] + f"{head.group(1)}{master} {inst} (" + body + bound[end:]
        receipt.append(dict(inst=inst, module=master, native_leaf=leaf, native_module=head.group(2),
                            clock_entries_merged=len(clocks), clock_net=nets.pop(), cycles_changed=0))
    return bound, receipt


def adapt_core_ports(bound, hard_cores):
    """-> (bound, receipt): a plan core with native_port_adapter has a different port form from the leaves the bind
    wired (DIE-KV-69 11-04, kv3_astk).  In the private kit copy, each merge group becomes one connection, which must
    be one net already, and each tie names a core input.  Same cycles; anything else fails closed."""
    receipt = []
    for core in hard_cores or []:
        spec = core.get("native_port_adapter")
        if not spec:
            continue
        inst, master = "u_" + core["inst"], core["module"]
        heads = list(re.finditer(r"^([ \t]+)" + re.escape(master) + r"(?:[ \t]+#\([^\n]*\))?[ \t]+" + re.escape(inst) + r"[ \t]*\(", bound, re.M))
        if len(heads) != 1:
            raise ValueError(f"core {core['inst']}: expected one {master} {inst}, got {len(heads)}")
        head = heads[0]
        end = bound.find("\n" + head.group(1) + ");", head.end())
        if end < 0:
            raise ValueError(f"core {core['inst']}: unclosed instance")
        body = bound[head.end():end]
        rows = []
        for port, names in spec.get("merge", {}).items():
            nets = set()
            for name in names:
                body, n = re.subn(r"^[ \t]*\." + name + r"\(([^()]*)\),?[ \t]*\n?",
                                  lambda m: nets.add(m.group(1).strip()) or "", body, flags=re.M)
                if n != 1:
                    raise ValueError(f"core {core['inst']}: merge pin {name} found {n} times")
            if len(nets) != 1:
                raise ValueError(f"core {core['inst']}: {port} merge group is not one net: {sorted(nets)}")
            rows.append((port, nets.pop()))
        for port, value in spec.get("tie", {}).items():
            if re.search(r"\." + port + r"\(", body):
                raise ValueError(f"core {core['inst']}: tie {port} is already connected")
            rows.append((port, value))
        # Explicit dead consumer bits may be omitted by a physical child. The
        # native producer remains intact; only this opted-in connection narrows.
        slices = []
        for port, rule in spec.get("slice", {}).items():
            if not isinstance(rule, dict) or set(rule) != {"msb", "lsb", "source_width", "evidence"}:
                raise ValueError(f"core {core['inst']}: slice {port} needs exact bounds, source width and evidence")
            hi, lo, width = rule["msb"], rule["lsb"], rule["source_width"]
            if (any(type(v) is not int for v in (hi, lo, width)) or
                    not width > hi >= lo >= 0 or not isinstance(rule["evidence"], str) or not rule["evidence"].strip()):
                raise ValueError(f"core {core['inst']}: invalid slice {port}: {rule}")
            matches = list(re.finditer(r"^[ \t]*\." + re.escape(port) + r"\(([^()]*)\),?[ \t]*(?:\n|$)", body, re.M))
            if len(matches) != 1:
                raise ValueError(f"core {core['inst']}: slice pin {port} found {len(matches)} times")
            match = matches[0]
            source = match.group(1).strip()
            net_match = re.fullmatch(r"([A-Za-z_$][A-Za-z0-9_$]*)(?:\[(\d+):(\d+)\])?", source)
            if not net_match or (net_match.group(2) is not None and
                    (int(net_match.group(2)), int(net_match.group(3))) != (width - 1, 0)):
                raise ValueError(f"core {core['inst']}: slice {port} requires a simple net or exact [{width-1}:0] selection: {source}")
            net = net_match.group(1)
            # Limit declarations to this actual containing module. Reject a
            # parameterized, ascending or inconsistent range rather than guess.
            starts = list(re.finditer(r"^\s*module\b", bound[:head.start()], re.M))
            if not starts:
                raise ValueError(f"core {core['inst']}: slice {port} has no containing module")
            scope = bound[starts[-1].start():head.start()]
            declared = []
            for decl in re.finditer(r"\b(?:wire|logic|reg)\s+(?:signed\s+)?\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*([^;]+);", scope):
                names = [v.strip() for v in decl.group(3).split(",")]
                if net in names:
                    declared.append((int(decl.group(1)), int(decl.group(2))))
            if not declared or set(declared) != {(width - 1, 0)}:
                raise ValueError(f"core {core['inst']}: slice {port} native {net} needs [{width-1}:0], found {declared}")
            body = body[:match.start()] + body[match.end():]
            rows.append((port, f"{net}[{hi}:{lo}]"))
            slices.append(dict(port=port, net=net, source_width=width, msb=hi, lsb=lo, evidence=rule["evidence"]))
        body = body.rstrip().rstrip(",")
        add = ",\n".join(f"{head.group(1)}    .{p}({v})" for p, v in rows)
        bound = bound[:head.end()] + body + ",\n" + add + bound[end:]
        receipt.append(dict(inst=core["inst"], module=master, ports=[p for p, _ in rows], cycles_changed=0, **({"slices": slices} if slices else {})))
    return bound, receipt


def wire(bound, module, rows):
    ports = {}
    receipt = []
    consumers = set()
    for port, physical_inst, pin, _early, _insertion in rows:
        # LP_STAR_1104 (KW6-CLASS, S81 *_LP__t* kit_rtl): a plan tap `<inst>` with no pin takes every clock pin of the
        # core (gen_phys.core_tap_rows, clock_taps.tcl `port inst *`).  No single RTL connection names that, so the kit
        # source keeps the bind's clock connections and clock_taps.tcl hangs the pins on the wrapper port, as for a
        # nested leaf below.
        if pin == "*":
            receipt.append(dict(port=port, instance=physical_inst, pin=pin, previous_net=None, mode="physical_tap"))
            continue
        # The plan wrapper owns u_bound. Physical specialization may name it;
        # otherwise the binder's native leaf instances have their standard u_ prefix.
        candidates = ([physical_inst[len("u_bound."):]] if physical_inst.startswith("u_bound.")
                      else [physical_inst, "u_" + physical_inst])
        if all("." in c for c in candidates):
            # NESTED_LEAF_1101 (FLOW-21, KIT-WAVE-14: S81 kit_rtl failed on every type whose core clock reaches a leaf
            # inside a bound child, e.g. u_r2.u_e10 / u_lf.u_ve.u_m).  The pin sits in a child module shared with other
            # instances, so the kit source keeps the bind's own clock connection (as before 66c713ed6); the planned
            # early-core tap stays a wrapper port that clock_taps.tcl hangs the pin on, as for every kit before.
            receipt.append(dict(port=port, instance=physical_inst, pin=pin, previous_net=None, mode="physical_tap"))
            continue
        found = []
        for local in candidates:
            if "." in local:
                continue
            pat = re.compile(r"^[ \t]+\w+(?:[ \t]+#\([^\n]*\))?[ \t]+" +
                             re.escape(local) + r"[ \t]*\(", re.M)
            found.extend((local, h) for h in pat.finditer(bound))
        if len(found) != 1:
            raise ValueError(f"core clock {port}: expected one bound leaf {physical_inst}, got {len(found)}")
        local, h = found[0]
        body_start = h.end()
        depth, body_end = 1, body_start
        while depth and body_end < len(bound):
            if bound[body_end] == "(":
                depth += 1
            elif bound[body_end] == ")":
                depth -= 1
            body_end += 1
        if depth:
            raise ValueError(f"core clock {port}: unclosed instance {local}")
        body_end -= 1
        original_body = bound[body_start:body_end]
        conn = re.compile(r"(\." + re.escape(pin) + r"\s*\()([^()]+)(\))")
        matches = list(conn.finditer(original_body))
        if len(matches) != 1:
            raise ValueError(f"core clock {port}: expected one {local}.{pin} connection")
        if (local, pin) in consumers:
            raise ValueError(f"core clock {port}: duplicate consumer {local}.{pin}")
        consumers.add((local, pin))
        prior = matches[0].group(2).strip()
        if port in ports and ports[port] != "input":
            raise ValueError(f"core clock {port}: conflicting port")
        ports[port] = "input"
        body = conn.sub(lambda m: m.group(1) + port + m.group(3), original_body, count=1)
        bound = bound[:body_start] + body + bound[body_end:]
        receipt.append(dict(port=port, instance=local, pin=pin, previous_net=prior, mode="rtl"))
    if ports:
        header = re.compile(r"(\bmodule\s+" + re.escape(module) + r"\s*(?:#\(.*?\)\s*)?\(\n)", re.S)
        if len(list(header.finditer(bound))) != 1:
            raise ValueError(f"core clocks: ambiguous header for {module}")
        declarations = "".join(f"    input wire {p},  // planned early-core clock\n" for p in ports
                               if not re.search(r"^\s*input\s+(?:wire\s+)?" + re.escape(p) + r"\s*[,)]", bound, re.M))
        bound = header.sub(lambda m: m.group(1) + declarations, bound, count=1)
    return bound, receipt


def swap_ahub_boundary(bound, hard_cores):
    """Opt-in exact native AHUB -> its already signed ck7/35-bit hard boundary.

    The parent's plan already projects am[35:2],am[0]; bit 1 is not exposed.
    All seven ck pins belong to the same core domain. No state or cycle changes.
    """
    receipt = []
    for core in hard_cores or []:
        if core.get("native_boundary_adapter") != "qkd_ahub_ck7_r27":
            continue
        if core.get("module") != "qkd_ahub" or core.get("inst") != "ahub":
            raise ValueError("AHUB boundary adapter requires qkd_ahub ahub")
        pat = re.compile(r"^([ \t]+)qkd_ahub_static_dw[ \t]+#\(([^\n]*)\)[ \t]+u_ahub[ \t]*\(", re.M)
        heads = list(pat.finditer(bound))
        if len(heads) != 1:
            raise ValueError(f"AHUB boundary: expected one native u_ahub, got {len(heads)}")
        head = heads[0]
        params = dict(re.findall(r"\.(\w+)\(([^()]*)\)", head.group(2)))
        params = {k: re.sub(r"[\s_]", "", v).lower() for k, v in params.items()}
        expected = {"AP_OFS": "64'hffddffdcffdfffdf", "FR_OFS": "-7", "Z_IN_STRIDE": "4"}
        if params != expected:
            raise ValueError(f"AHUB boundary: native parameter signature changed: {params}")
        end = bound.find("\n" + head.group(1) + ");", head.end())
        if end < 0:
            raise ValueError("AHUB boundary: unclosed native instance")
        body = bound[head.end():end]
        clocks = re.findall(r"\.ck\(([^()]*)\)", body)
        if len(clocks) != 1 or not re.fullmatch(r"[A-Za-z_$][\w$]*", clocks[0].strip()):
            raise ValueError("AHUB boundary: expected one simple native ck net")
        clock = clocks[0].strip()
        body = re.sub(r"\.ck\([^()]*\)", ".ck({7{" + clock + "}})", body, count=1)
        projections = {}
        for pin in ("am0", "am1", "am2", "am3"):
            values = re.findall(r"\." + pin + r"\(([^()]*)\)", body)
            if len(values) != 1 or not re.fullmatch(r"[A-Za-z_$][\w$]*", values[0].strip()):
                raise ValueError(f"AHUB boundary: expected one whole bus for {pin}")
            net = values[0].strip()
            body = re.sub(r"\." + pin + r"\([^()]*\)", "." + pin + "({" + net + "[35:2], " + net + "[0]})", body, count=1)
            projections[pin] = dict(native=net, kept_bits="35:2,0", unexposed_bit=1)
        bound = bound[:head.start()] + head.group(1) + "qkd_ahub u_ahub (" + body + bound[end:]
        receipt.append(dict(inst="ahub", module="qkd_ahub", native_leaf="u_ahub", native_module="qkd_ahub_static_dw",
                            native_params=params, clock_net=clock, clock_copies=7, am_projection=projections,
                            cycles_changed=0, tieoffs=[]))
    return bound, receipt
