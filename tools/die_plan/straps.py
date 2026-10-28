"""Declared ID straps for the flow gates (OWNER DECISION 2026-10-25 07:01, strap question option B; METHODOLOGY R7).

ID straps (HBM tile_tid / map_lane_j / lane_lane_id, KV head_eighth BSEL/HID, astk variant IDs) are INPUT PINS of ONE
hardened design, tied to constants at the parent.  Allowed for ID straps ONLY: every other input stays driven and the
no-tie-off rule is unchanged.

The DECLARATION lives in one place: parent_id_straps.py (plan contents[] / hard_cores[] "parent_id_straps" /
"straps", strict approved-ID schema, Codex).  This module only answers "which PORTS of a kit / partition are declared
straps" for the gates, from what each kit or bind step already records:
  * a hardened core kit: core.json report.straps entries with kind == "id_strap" (gen_core_kit_kv.py), or the kit's
    straps.json ({"straps": [...]}), or the "straps" key of the kit's sdc_lint.json context;
  * a bound partition: the binder manifest bind_parent_id_straps.json (types.<type>.<port>).
Every gate port name must match STRAP_RE (strap_*, owner rule 1); anything else is refused (fail-closed).

Gate rules (owner rules 2-3): inside the block a strap is quasi-static -> no pin register (face_guard exempt), the kit
SDC has set_false_path -from [get_ports {straps}] (sdc_lint accepts it on declared straps only), a strap landing
register is not a register-fanout merge (reg_fanout exempt); at the parent each strap bit is a constant driven by its
own TIEHI/TIELO cell next to the pin (die_constant_cells.tcl maps constants with max_fanout 1; tie_check_tcl verifies)
and the tie-off audit accepts a constant only on a declared strap bit (audit_ties / audit_top_ties).

COUNT STRAPS (OWNER 12.15a, MESO-STRAP-1): the 1.8 rule extends to count-aligned crossing constants: strap_ca_* pins
(ring K per landed bus, origin PAD / EDGE_FALL / tree select / root) of one hardened design per partition type, declared by
count_align_bind.strap_ties (core.json kind "count_strap" / kit straps.json like ID straps).  Their VALUES matter (a wrong
tie fails silently at bring-up: no data, only a ready-timeout fault), so the tie-off audit also checks values: every
strap_ca_* pin of every instance must carry exactly the bind's value, as a literal in the RTL top
(audit_count_strap_values) and as the TIEHI/TIELO pattern of the die netlist (audit_netlist_strap_values,
tie_check_tcl rows built from the bind values); a missing tie or a mismatch is a G0 ERROR.
"""
import json
import re
from collections import defaultdict
from pathlib import Path

STRAP_RE = re.compile(r"^strap_[A-Za-z0-9_]+$")
COUNT_STRAP_RE = re.compile(r"^strap_ca_[A-Za-z0-9_]+$")
STRAP_KINDS = ("id_strap", "count_strap")
_BIT = re.compile(r"^(.*?)(\[\d+\])?$")
TIE_CELLS = {0: "TIELOx1_ASAP7_75t_R", 1: "TIEHIx1_ASAP7_75t_R"}


def declared(names, inputs=None):
    """-> (straps list, errors).  names: strap port (bus) names; inputs: optional set of the block's input buses."""
    s = list(names or [])
    err = []
    for n in s:
        if not isinstance(n, str) or not STRAP_RE.match(n):
            err.append(f"strap '{n}': must be named strap_<id> (OWNER 10-25 option B rule 1)")
        elif inputs is not None and n not in inputs:
            err.append(f"strap '{n}': not an input port of the block")
    if len(set(s)) != len(s):
        err.append("straps: duplicate names")
    return s, err


def checked(names, inputs=None):
    s, err = declared(names, inputs)
    if err:
        raise ValueError("; ".join(err))
    return s


def bus_of(pin):
    """'strap_tid[3]' / '\\strap_tid [3]' -> 'strap_tid'"""
    p = str(pin).lstrip("\\").replace(" ", "")
    return _BIT.match(p).group(1)


def is_strap(pin, straps):
    b = bus_of(pin)
    return bool(STRAP_RE.match(b)) and b in set(straps or ())


def core_json_straps(cj):
    """core.json (dict or path) report.straps kind == id_strap -> [port]"""
    if not isinstance(cj, dict):
        cj = json.loads(Path(cj).read_text())
    rep = (cj.get("report") or {}).get("straps") or []
    return [s["port"] for s in rep if isinstance(s, dict) and s.get("kind") in STRAP_KINDS]


def kit_straps(kitdir):
    """declared straps of a kit dir: straps.json, else sdc_lint.json "straps", else core.json id_strap entries.
    [] when none (then no tie / exemption is allowed)."""
    kd = Path(kitdir)
    out = []
    f = kd / "straps.json"
    if f.is_file():
        d = json.loads(f.read_text())
        out = list(d.get("straps", []) if isinstance(d, dict) else d)
    elif (kd / "sdc_lint.json").is_file() and json.loads((kd / "sdc_lint.json").read_text()).get("straps"):
        out = list(json.loads((kd / "sdc_lint.json").read_text())["straps"])
    elif (kd / "core.json").is_file():
        out = core_json_straps(kd / "core.json")
    return checked(out)


def write_kit(kitdir, straps, source=""):
    """record the kit's declared straps (face_guard / signoff / port-bind read it)."""
    s = checked(straps)
    (Path(kitdir) / "straps.json").write_text(json.dumps(dict(
        schema="opentallas.straps.v1", straps=sorted(s), source=source,
        rule="OWNER 10-25 option B ID straps (METHODOLOGY R7) + OWNER 12.15a count straps (strap_ca_*)"), indent=1) + "\n")


def manifest_straps(manifest):
    """binder manifest (bind_parent_id_straps.json dict or path) -> {type: {port: width}} (partition-level ports)"""
    if not isinstance(manifest, dict):
        manifest = json.loads(Path(manifest).read_text())
    out = {}
    for tn, ports in (manifest.get("types") or {}).items():
        checked(list(ports))
        out[tn] = {p: int(d["width"]) for p, d in ports.items()}
    return out


def audit_ties(ties, straps):
    """tie-off audit: ties = [(port_bit, value)] constants found on a block's inputs.  A tie is accepted ONLY on a
    declared strap_* port; anything else FAILs.  -> dict(verdict, accepted, rejected, reason)"""
    ok, bad = [], []
    for pb, v in ties:
        (ok if is_strap(pb, straps) else bad).append((pb, v))
    return dict(verdict="PASS" if not bad else "FAIL", accepted=ok, rejected=bad,
                reason=None if not bad else f"{len(bad)} tied input bit(s) not on a declared ID strap: "
                + ", ".join(f"{p}={v}" for p, v in bad[:8]))


_INST_RE = re.compile(r"^\s*(\\?[A-Za-z_][\w$]*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?(\\?[A-Za-z_][\w$]*)\s*\(",
                      re.M)
_CONN_RE = re.compile(r"\.\s*(\\?[\w$]+)\s*\(\s*(\d+\s*'\s*[bBhHdD]\s*[0-9a-fA-FxXzZ_]+|1'b[01])\s*\)")


def audit_top_ties(top_text, manifest, module_type=None):
    """audit a bound die top: every literal constant on a partition instance pin must be a declared parent ID strap
    (strap_*) of that instance's type (binder manifest); any other literal FAILs.  module_type: {module: type}
    (default: module bt_<type>).  -> audit_ties-style result + rows [(inst, port, literal)] for tie_check_tcl."""
    decl = manifest_straps(manifest)
    ok, bad, rows = [], [], []
    for m in _INST_RE.finditer(top_text):
        mod, inst = m.group(1).lstrip("\\"), m.group(2).lstrip("\\")
        if mod in ("module", "input", "output", "wire", "assign", "always", "if", "case"):
            continue
        tn = (module_type or {}).get(mod, mod[3:] if mod.startswith("bt_") else mod)
        depth, i = 0, m.end() - 1
        while i < len(top_text):
            depth += {"(": 1, ")": -1}.get(top_text[i], 0)
            if depth == 0:
                break
            i += 1
        for c in _CONN_RE.finditer(top_text[m.end():i]):
            port, lit = c.group(1).lstrip("\\"), c.group(2).replace(" ", "")
            if STRAP_RE.match(port) and port in decl.get(tn, {}) and len(literal_bits(lit)) == decl[tn][port]:
                ok.append((f"{inst}.{port}", lit))
                rows.append((inst, port, lit))
            else:
                bad.append((f"{inst}.{port}", lit))
    return dict(verdict="PASS" if not bad else "FAIL", accepted=ok, rejected=bad, rows=rows,
                reason=None if not bad else f"{len(bad)} literal partition pin(s) not a declared ID strap: "
                + ", ".join(f"{p}={v}" for p, v in bad[:8]))


def literal_bits(lit):
    """"4'b0110" -> [0, 1, 1, 0] LSB first"""
    w, v = lit.replace(" ", "").split("'")
    base = {"b": 2, "h": 16, "d": 10}[v[0].lower()]
    n = int(v[1:].replace("_", ""), base)
    return [(n >> b) & 1 for b in range(int(w))]


def tie_check_tcl(rows, max_um=5.0):
    """OpenROAD Tcl run after die_constant_cells.tcl (owner rule 3): every strap bit (inst, port, literal) must be
    driven by its OWN TIEHI/TIELO of the right value (net = tie + this pin only) placed within max_um of the pin.
    Prints OT_STRAP_TIE PASS|FAIL <bits> <failed>; read-only (never moves or adds cells)."""
    t = ["# GENERATED by tools/die_plan/straps.py: TIEHI/TIELO next to each declared ID strap pin (OWNER 10-25 B rule 3)",
         "proc ot_strap_tie_check {inst pin val max_dbu} {",
         "  set blk [ord::get_db_block]; set i [$blk findInst $inst]",
         "  if {$i eq \"NULL\"} { puts \"OT_STRAP_TIE missing instance $inst\"; return 1 }",
         "  set it [$i findITerm $pin]",
         "  if {$it eq \"NULL\"} { puts \"OT_STRAP_TIE missing pin $inst/$pin\"; return 1 }",
         f"  set cell [expr {{$val ? \"{TIE_CELLS[1]}\" : \"{TIE_CELLS[0]}\"}}]",
         "  set n [$it getNet]",
         "  if {$n eq \"NULL\"} { puts \"OT_STRAP_TIE open $inst/$pin\"; return 1 }",
         "  set its [$n getITerms]",
         "  if {[llength $its] != 2 || [llength [$n getBTerms]]} { puts \"OT_STRAP_TIE shared net $inst/$pin\"; return 1 }",
         "  foreach x $its { if {$x ne $it} { set drv $x } }",
         "  if {[[[$drv getInst] getMaster] getName] ne $cell} { puts \"OT_STRAP_TIE $inst/$pin not driven by $cell\"; return 1 }",
         "  set a [[$drv getInst] getBBox]; set b [$it getBBox]",
         "  set d [expr {abs(([$a xMin]+[$a xMax])/2 - ([$b xMin]+[$b xMax])/2) + abs(([$a yMin]+[$a yMax])/2 - ([$b yMin]+[$b yMax])/2)}]",
         "  if {$d > $max_dbu} { puts \"OT_STRAP_TIE $inst/$pin tie [expr {$d / [[ord::get_db_tech] getDbUnitsPerMicron]}] um away\"; return 1 }",
         "  return 0",
         "}",
         f"set ot_strap_max [expr {{int({float(max_um)} * [[ord::get_db_tech] getDbUnitsPerMicron])}}]",
         "set ot_strap_fail 0"]
    n = 0
    for inst, port, lit in rows:
        bits = literal_bits(lit) if isinstance(lit, str) else [int(lit)]
        for b, v in enumerate(bits):
            pin = f"{port}[{b}]" if len(bits) > 1 else port
            t.append(f"incr ot_strap_fail [ot_strap_tie_check {{{inst}}} {{{pin}}} {v} $ot_strap_max]")
            n += 1
    t.append(f"puts \"OT_STRAP_TIE [expr {{$ot_strap_fail ? \"FAIL\" : \"PASS\"}}] {n} bits $ot_strap_fail failed\"")
    return "\n".join(t) + "\n"


# ---------------- MESO-STRAP-1: count-strap VALUE audit (COORD addition to 12.15a; extends the 1.8 tie-off audit) -----

def _bits_of(value, width):
    return [(int(value) >> b) & 1 for b in range(int(width))]


def _expected_bits(expected):
    """{inst: {port: (width, value)}} -> {(inst, port, bit): value} for strap_ca_* ports"""
    out = {}
    for inst, ports in expected.items():
        for port, (w, v) in ports.items():
            if not COUNT_STRAP_RE.match(port):
                raise ValueError(f"count strap {inst}.{port}: not a strap_ca_* port")
            if not 0 <= int(v) < (1 << int(w)):
                raise ValueError(f"count strap {inst}.{port}: value {v} does not fit {w} bits")
            for b, x in enumerate(_bits_of(v, w)):
                out[(inst, port, b)] = x
    return out


def _verdict(errs, n, what):
    return dict(verdict="PASS" if not errs else "FAIL", severity=None if not errs else "G0 ERROR", checked_bits=n,
                errors=errs, reason=None if not errs else f"{len(errs)} count-strap {what} error(s): " + "; ".join(errs[:6]))


def audit_count_strap_values(top_text, expected):
    """RTL die top: every declared count strap pin (strap_ca_*) of every instance in `expected`
    ({inst: {port: (width, value)}} = clock_landings.Landings.strap_expected() = count_align_bind.strap_ties values)
    must be connected to a literal of exactly that width and value.  Missing pin / non-literal / wrong width / wrong
    value, and any strap_ca_* literal on an instance or port the bind does not list -> G0 ERROR."""
    want = _expected_bits(expected)
    seen, errs = set(), []
    for m in _INST_RE.finditer(top_text):
        mod, inst = m.group(1).lstrip("\\"), m.group(2).lstrip("\\")
        if mod in ("module", "input", "output", "wire", "assign", "always", "if", "case"):
            continue
        depth, i = 0, m.end() - 1
        while i < len(top_text):
            depth += {"(": 1, ")": -1}.get(top_text[i], 0)
            if depth == 0:
                break
            i += 1
        body = top_text[m.end():i]
        for c in re.finditer(r"\.\s*(\\?strap_ca_[\w$]*)\s*\(([^()]*)\)", body):
            port, arg = c.group(1).lstrip("\\"), c.group(2).strip()
            exp = expected.get(inst, {}).get(port)
            if exp is None:
                errs.append(f"{inst}.{port}: strap_ca_* connection with no bind value")
                continue
            seen.add((inst, port))
            if not re.fullmatch(r"\d+\s*'\s*[bBhHdD]\s*[0-9a-fA-F_]+", arg):
                errs.append(f"{inst}.{port}: not a literal tie ({arg})")
                continue
            bits = literal_bits(arg)
            if len(bits) != int(exp[0]):
                errs.append(f"{inst}.{port}: literal width {len(bits)} != declared {exp[0]}")
            elif bits != _bits_of(exp[1], exp[0]):
                errs.append(f"{inst}.{port}: tied {arg} != bind value {exp[1]} ({exp[0]}'b{format(int(exp[1]), '0' + str(exp[0]) + 'b')})")
    for inst, ports in expected.items():
        for port in ports:
            if (inst, port) not in seen:
                errs.append(f"{inst}.{port}: missing tie (no connection in the die top)")
    return _verdict(errs, len(want), "tie value")


_NL_TIE = re.compile(r"^\s*(TIEHI|TIELO)\w*\s+(\\?\S+)\s*\((.*?)\);", re.M | re.S)


def _nl_bus_bits(conn):
    """netlist pin connection text -> list of nets MSB first ({a, b} concatenation, single net, or literal)"""
    conn = conn.strip()
    if conn.startswith("{"):
        return [x.strip() for x in conn[1:-1].split(",")]
    return [conn]


def audit_netlist_strap_values(netlist_text, expected, cells=TIE_CELLS):
    """Gate-level die netlist after die_constant_cells.tcl: every bit of every strap_ca_* pin of every instance in
    `expected` must be driven by a TIEHI (1) / TIELO (0) cell whose output net reaches only that pin bit (max_fanout 1, own
    tie per bit), and its value must equal the bind value.  Pin connections may be per bit (.\\strap_ca_k_x[3] (n)) or
    a concatenation (.strap_ca_k_x({n5, ..., n0}), MSB first).  Any bit without its own tie, a shared tie net, a literal
    left in the netlist or a value mismatch -> G0 ERROR."""
    tie_val = {}
    for m in _NL_TIE.finditer(netlist_text):
        val = 1 if m.group(1) == "TIEHI" else 0
        for c in re.finditer(r"\.\s*(\w+)\s*\(\s*(\\?[^()\s]+)\s*\)", m.group(3)):
            tie_val[c.group(2).lstrip("\\")] = val
    use = defaultdict(int)
    for c in re.finditer(r"\(\s*(\\?[^(){},\s]+)\s*\)|[{,]\s*(\\?[^(){},\s]+)\s*(?=[,}])", netlist_text):
        n = (c.group(1) or c.group(2)).lstrip("\\")
        if n in tie_val:
            use[n] += 1
    want = _expected_bits(expected)
    got = {}
    for m in _INST_RE.finditer(netlist_text):
        inst = m.group(2).lstrip("\\")
        if inst not in expected:
            continue
        depth, i = 0, m.end() - 1
        while i < len(netlist_text):
            depth += {"(": 1, ")": -1}.get(netlist_text[i], 0)
            if depth == 0:
                break
            i += 1
        body = netlist_text[m.end():i]
        for c in re.finditer(r"\.\s*(\\?strap_ca_\w+)\s*(\[\d+\])?\s*\(((?:[^()]|\{[^{}]*\})*)\)", body):
            port = c.group(1).lstrip("\\")
            if port not in expected[inst]:
                continue
            w = int(expected[inst][port][0])
            nets = _nl_bus_bits(c.group(3))
            if c.group(2):
                got[(inst, port, int(c.group(2)[1:-1]))] = nets[0]
            else:
                if len(nets) != w:
                    got.update({(inst, port, b): f"<width {len(nets)} != {w}>" for b in range(w)})
                    continue
                for b, n in enumerate(reversed(nets)):
                    got[(inst, port, b)] = n
    errs = []
    for k, v in sorted(want.items()):
        inst, port, b = k
        n = got.get(k)
        tag = f"{inst}.{port}[{b}]"
        if n is None:
            errs.append(f"{tag}: missing tie (pin bit not connected)")
        elif n.startswith("<"):
            errs.append(f"{tag}: {n}")
        elif re.fullmatch(r"\d+'[bB][01]", n):
            errs.append(f"{tag}: literal {n} left in the netlist (no TIEHI/TIELO)")
        elif n.lstrip("\\") not in tie_val:
            errs.append(f"{tag}: net {n} is not driven by a TIEHI/TIELO cell")
        else:
            nn = n.lstrip("\\")
            if use[nn] != 2:
                errs.append(f"{tag}: tie net {nn} is shared ({use[nn] - 1} loads; one tie per bit)")
            if tie_val[nn] != v:
                errs.append(f"{tag}: tied {'TIEHI' if tie_val[nn] else 'TIELO'} != bind bit {v}")
    return _verdict(errs, len(want), "netlist tie")


def count_strap_rows(expected):
    """tie_check_tcl rows (inst, port, literal) built from the BIND values (not from the top's literals), so the OpenROAD
    check after die_constant_cells.tcl verifies the tie VALUE of every count-strap bit against count_align_bind"""
    return [(inst, port, f"{w}'b{format(int(v), '0' + str(w) + 'b')}") for inst, ports in sorted(expected.items())
            for port, (w, v) in sorted(ports.items())]
