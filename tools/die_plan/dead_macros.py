"""Plan macros a bound kit netlist cannot carry: every output unloaded (DIE-HBM-97/HBM-SM-MPL 11-11, COORD MPL-0020).

q_sm0-3 stopped at macro_place.tcl line 6, MPL-0020 "Couldn't find a macro named u_bound.u_u_sm_g_c_0_g_p_0_u_t.
u_seed.u_pte": the plan places 236 hard cores, the synthesized kit has 232.  The 4 missing ones are the pt_e cores of the
chain-end tiles (as-built ot_hbm_accel_smh_attn t_ro / t_bo of c = 0 and c = NC-1 have no reader).  Their only outputs
rout / bout reach nothing, so synthesis removes the blackbox, as it does in the as-built die.

This module proves such a macro dead from the kit's own bound RTL, conservatively: starting at the kit top, it follows the
macro's plan physical path down plain instances (a generate scope `g_x[i]`, a positional or ambiguous instance, an
attribute on the instance: not proven), then from each output of the macro (its liberty `direction : output` pins) back
up: an output that is unconnected, or a plain identifier read nowhere else in its module (a local wire, or an output
port of that module whose own connection in the parent is again unread), is unloaded.  A macro is dead only when every
output is unloaded and it has at least one output.  Anything else keeps the macro (unchanged kit).

project() returns a copy of the plan without the dead hard cores and their clock taps, and per-type receipts
(dead_macros.json).  A type with no dead macro is untouched (byte-identical kits).  OT_DEAD_MACROS=0: off.
"""
import copy
import os
import re
from pathlib import Path

SCHEMA = "opentallas.die_plan.dead_macros.v1"
RECEIPT = "dead_macros.json"

_ID = r"[A-Za-z_][\w$]*"
_MODULE = re.compile(r"(?s)\bmodule\s+(" + _ID + r")\b(.*?)\bendmodule\b")
_DECL = re.compile(r"\b(input|output|inout|wire|logic|reg|tri)\b((?:\s+(?:wire|logic|reg|signed|unsigned|var))*)\s*"
                   r"((?:\[[^\]]*\]\s*)*)(" + _ID + r")\s*(?=[,;)\[=])")
_LIB_PIN = re.compile(r"\b(?:pin|bus)\s*\(\s*\"?(" + _ID + r")\"?\s*\)\s*\{[^{}]*?\bdirection\s*:\s*(\w+)")


def strip_comments(text):
    return re.sub(r"//[^\n]*", "", re.sub(r"(?s)/\*.*?\*/", " ", text))


def module_index(texts):
    """{module name: body text} of comment-stripped SV sources; a name defined twice is dropped (ambiguous)."""
    out, seen = {}, set()
    for text in texts:
        for m in _MODULE.finditer(strip_comments(text)):
            name = m.group(1)
            if name in seen:
                out.pop(name, None)
                continue
            seen.add(name)
            out[name] = m.group(2)
    return out


def _balanced(text, i):
    """index after the parenthesis group opening at text[i] == '('; -1 when unbalanced."""
    depth = 0
    for j in range(i, len(text)):
        c = text[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j + 1
    return -1


def _split_top(s):
    parts, depth, cur = [], 0, []
    for c in s:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    parts.append("".join(cur))
    return [p.strip() for p in parts]


def find_instance(body, inst):
    """(module name or None, {formal: actual}) of the one named-port instance `inst` in body; None when absent,
    repeated, positional or carrying an attribute (keep / dont_touch)."""
    hits = [m for m in re.finditer(r"(?<![\w$.\\])" + re.escape(inst) + r"\s*\(", body)]
    if len(hits) != 1:
        return None
    m = hits[0]
    end = _balanced(body, m.end() - 1)
    if end < 0:
        return None
    # module name: identifier before the instance name, skipping a balanced #( ... ) parameter list
    j = m.start() - 1
    while j >= 0 and body[j].isspace():
        j -= 1
    if j >= 0 and body[j] == ")":
        depth = 0
        while j >= 0:
            if body[j] == ")":
                depth += 1
            elif body[j] == "(":
                depth -= 1
                if depth == 0:
                    break
            j -= 1
        j -= 1
        while j >= 0 and body[j].isspace():
            j -= 1
        if j < 0 or body[j] != "#":
            return None
        j -= 1
        while j >= 0 and body[j].isspace():
            j -= 1
    k = j
    while k >= 0 and (body[k].isalnum() or body[k] in "_$"):
        k -= 1
    mod = body[k + 1:j + 1] or None
    pre = body[max(0, k - 1):k + 1]
    if mod and (pre.endswith("`") or mod in ("endif", "else", "elsif")):
        mod = None                                     # `ifdef-chosen master: not needed for a leaf, unproven above it
    if body[max(0, k - 200):k + 1].rstrip().endswith("*)"):
        return None                                    # (* keep *) and friends: synthesis keeps the instance
    ports = {}
    for p in _split_top(body[m.end():end - 1]):
        if not p:
            continue
        pm = re.fullmatch(r"\.\s*(" + _ID + r")\s*(?:\((.*)\))?", p, re.S)
        if not pm:
            return None                                # positional connection: not proven
        ports[pm.group(1)] = (pm.group(2) if pm.group(2) is not None else pm.group(1)).strip()
    return mod, ports


def _refs(body, ident):
    """(declaration kinds, expression references) of ident in a module body."""
    kinds, spans = [], []
    for m in _DECL.finditer(body):
        if m.group(4) == ident:
            nxt = body[m.end():m.end() + 1]
            if nxt == "=":
                continue                               # wire x = ...: a driver, counted as a reference below
            kinds.append(m.group(1))
            spans.append(m.start(4))
    refs = [m.start() for m in re.finditer(r"(?<![\w$.\\'])" + re.escape(ident) + r"(?![\w$])", body)
            if m.start() not in spans]
    return kinds, refs


def lib_outputs(lib_text):
    """output pin / bus names of a liberty cell; None when the liberty names no pin direction at all."""
    pins = {}
    for m in _LIB_PIN.finditer(lib_text):
        pins.setdefault(m.group(1), m.group(2))
    if not pins:
        return None
    return sorted(p for p, d in pins.items() if d in ("output", "inout"))


def dead_reason(mods, top, path, outputs):
    """why the macro at hierarchical `path` under module `top` is dead (str), or None when not proven."""
    if not outputs:
        return None
    segs = path.split(".")
    if any(not re.fullmatch(_ID, s) for s in segs):
        return None                                    # generate scope / escaped name: not proven
    chain = []                                         # [(module body, instance name, ports)] top -> leaf
    mod = top
    for i, s in enumerate(segs):
        body = mods.get(mod)
        if body is None:
            return None
        hit = find_instance(body, s)
        if hit is None:
            return None
        sub, ports = hit
        chain.append((mod, body, s, ports))
        if i < len(segs) - 1:
            if not sub:
                return None
            mod = sub
    for o in outputs:
        level = len(chain) - 1
        formal = o
        while True:
            mname, body, s, ports = chain[level]
            if formal not in ports:
                return None                            # liberty pin the instance does not name: not proven
            act = ports[formal]
            if act == "":
                break                                  # unconnected output: unloaded
            if not re.fullmatch(_ID, act):
                return None                            # slice / concat / expression: not proven
            kinds, refs = _refs(body, act)
            if len(refs) != 1:
                return None                            # read (or driven) elsewhere
            if kinds in (["wire"], ["logic"]):
                break                                  # local net read by nobody: unloaded
            if kinds in (["output"], ["output", "wire"], ["output", "logic"]) and level > 0:
                level -= 1                              # output port of this module: follow it in the parent
                formal = act
                continue
            return None                                # top port, input, reg, unknown declaration: live
    return f"all {len(outputs)} output(s) ({', '.join(outputs)}) unloaded in the bound RTL"


def _type_libs(t, lib_of):
    return {c["inst"]: lib_of(c) for c in t.get("hard_cores", []) or []}


def project(raw, kit_rtl, lib_text, types_key="partition_types"):
    """(projected raw plan, {type: receipt}) without the proven-dead hard cores of kit-rtl types.
    lib_text(hard_core) -> liberty text or None.  No dead macro anywhere: (raw, {}) unchanged."""
    if not kit_rtl or os.environ.get("OT_DEAD_MACROS", "1") == "0":
        return raw, {}
    types = raw.get(types_key) or raw.get("types") or {}
    receipts = {}
    for tn in sorted(kit_rtl):
        t = types.get(tn)
        if not t or not t.get("hard_cores"):
            continue
        fl = [Path(x) for x in Path(kit_rtl[tn]).read_text().split() if x and not x.startswith(("+", "-"))]
        mods = module_index(p.read_text(errors="replace") for p in fl if p.is_file())
        top = t.get("module")
        rows = []
        for c in t["hard_cores"]:
            pinst = c.get("physical_inst") or c["inst"]
            if not pinst.startswith("u_bound."):
                continue
            lt = lib_text(c)
            outs = lib_outputs(lt) if lt else None
            why = dead_reason(mods, top, pinst, outs) if outs else None
            if why:
                rows.append({"inst": c["inst"], "physical_inst": pinst,
                             "module": c.get("physical_master") or c.get("module"), "why": why})
        if rows:
            receipts[tn] = {"schema": SCHEMA, "type": tn, "removed": rows,
                            "note": "hard cores whose every output is unloaded in the kit's bound RTL: synthesis "
                                    "removes them, so the kit neither places nor taps them (plan of record unchanged)"}
    if not receipts:
        return raw, {}
    out = copy.deepcopy(raw)
    otypes = out.get(types_key) or out.get("types")
    for tn, rec in receipts.items():
        gone = {r["inst"] for r in rec["removed"]}
        t = otypes[tn]
        t["hard_cores"] = [c for c in t["hard_cores"] if c["inst"] not in gone]
        ck = t.get("clock")
        if isinstance(ck, dict) and isinstance(ck.get("taps"), list):
            ck["taps"] = [x for x in ck["taps"] if not (x.get("kind") == "core" and x.get("name") in gone)]
    return out, receipts
