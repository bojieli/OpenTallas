"""QC-SLECTL-B 11-05: named wrappers of a parameterized module, so one paramod can be a distinct hard-core master.

A plan hard core may carry param_wrap {"base": <module>, "params": {name: int, ...}}: its physical_master is a generated
module that only instantiates <base> #(params) as u_w with every port passed through by name (no logic, no cycles).
The kit-rtl step renames the bound instantiation `<base> #(<params>) <inst> (` to `<master> <inst> (` (exact parameter
text match, else fail closed) and adds the generated wrapper source; the child core kit builds the same wrapper.
Supported bases: PORTS below (port list with widths as functions of the parameters).

STRAP-MASTER-1115 (CORE-ROWS-1115, FABLE-PD-QCC-0740): a row may carry param_wrap.straps {strap_pin: int} for a base whose
parameters became strap pins of the hard master (QC sta_region: SKEW_N / SKEW_S -> strap_skew_n[4:0] / strap_skew_s[4:0], tied
at the parent).  wrap_bound then (a) matches the bound instance on the NON-skew parameters only (SKEW, SKEW_N, SKEW_S are the
straps; hard_core_param.py compares them with the strap values), (b) inserts .<strap>(<width>'d<value>) ties into the instance
connections, (c) names a master that does not depend on the strap values (the wrapper source is the same for every value;
row key wrapper=false when the master RTL comes with the core kit and no stand-in is wanted)."""
import math
import re


def _clog2(v):
    return max(0, math.ceil(math.log2(v))) if v > 1 else 0


# base -> [(dir, name, width(params) )]; widths follow the base module header exactly
PORTS = {
    "ot_dp_clk_landing_cas": [
        ("input", "fclk", lambda p: 1), ("input", "t_rst_n", lambda p: 1), ("input", "clk", lambda p: 1),
        ("input", "rst_n", lambda p: 1),
        # CLAND-MACRO-1 11-14: RSTREP-1 rst_xn copies are a real port of the base (the bind connects .rst_xn whenever
        # RSTREP > 0, clock_landings ring_rst); 0 = not connected, not declared.
        ("input", "rst_xn", lambda p: int(p.get("RSTREP", 0))),
        ("input", "strap_k", lambda p: _clog2(p.get("DEPTH", 4)) + 4),
        ("input", "d", lambda p: p["W"]), ("output", "q", lambda p: p["W"]), ("output", "ready", lambda p: 1),
        ("output", "fault", lambda p: 1)],
    # CLAND-MACRO-1 11-14 (FABLE-WAVE-REVIEW fix 7): the plain forwarded-clock ring (S81 stations / leaves, KV monitor
    # rings) as a signed hard child: W, WNEG, DSREP, LOCAL, ... exactly as the bind emits them.
    "ot_dp_clk_landing": [
        ("input", "fclk", lambda p: 1), ("input", "clk", lambda p: 1), ("input", "rst_n", lambda p: 1),
        ("input", "d", lambda p: p["W"]), ("output", "q", lambda p: p["W"]), ("output", "ready", lambda p: 1),
        ("output", "fault", lambda p: 1)],
}


# STRAP-MASTER-1115: the nb0 station tail (QC sta_region): same ports as rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv
PORTS["qfd_dv_s8_station_tail1_nb0"] = [
    ("input", "ck", lambda p: 1), ("input", "rst_n", lambda p: 1), ("input", "cfg_v_p", lambda p: 1),
    ("input", "cfg_mode_p", lambda p: 2), ("input", "cfg_wsrc_p", lambda p: 1), ("input", "cfg_nwords_p", lambda p: 8),
    ("input", "cfg_sbase_p", lambda p: 9), ("input", "cfg_kcm1_p", lambda p: 8),
    ("input", "rs_s_lo_p", lambda p: 64), ("input", "rs_s_hi_p", lambda p: 64), ("input", "rs_n_lo_p", lambda p: 64),
    ("input", "rs_n_hi_p", lambda p: 64), ("input", "rs_s_c_p", lambda p: 4), ("input", "rs_n_c_p", lambda p: 4),
    ("output", "nb_od", lambda p: 64), ("output", "nb_oc", lambda p: 2), ("output", "bt_re", lambda p: 1),
    ("output", "bt_word", lambda p: 9), ("input", "bt_q_p", lambda p: 32), ("output", "r_v", lambda p: 1),
    ("output", "r_idx", lambda p: 8), ("output", "r_last", lambda p: 1), ("output", "r_d", lambda p: 64),
    ("input", "flt_bank_i", lambda p: 4), ("input", "flt_vld_i", lambda p: 4), ("output", "flt_bank_o", lambda p: 4),
    ("output", "flt_vld_o", lambda p: 4), ("output", "fault", lambda p: 1)]
# base -> {strap pin: width}: parameters the hard master takes as strap pins (tied at the parent)
# strap_hi_pad (master sta_region_strap_s2, HI_PAD edges 0..24, 0 = wire) is optional per row; the skew pair is always there
STRAP_PORTS = {"qfd_dv_s8_station_tail1_nb0": {"strap_skew_n": 5, "strap_skew_s": 5, "strap_hi_pad": 5}}
STRAP_REQUIRED = {"qfd_dv_s8_station_tail1_nb0": ("strap_skew_n", "strap_skew_s")}
# bound-instance parameters a strap replaces, and the module defaults when the instance text omits them
SKEW_KEYS = ("SKEW", "SKEW_N", "SKEW_S")
STRAP_PARAM_DEFAULT = {"qfd_dv_s8_station_tail1_nb0": {"SKEW": 14, "HI_PAD": 0}}     # SKEW_N / SKEW_S default to SKEW


def strap_param(strap):
    """strap pin -> the bound parameter it carries: strap_skew_n -> SKEW_N"""
    return strap.removeprefix("strap_").upper()


def check_straps(base, straps):
    """validate a plan param_wrap.straps dict against STRAP_PORTS[base] (the required pins present, every key a strap port, each
    value inside its width); -> {pin: (width, value)}"""
    ports = STRAP_PORTS.get(base)
    if ports is None:
        raise ValueError(f"param_wrap: base {base} has no strap table")
    need = set(STRAP_REQUIRED.get(base, ()))
    if not need <= set(straps) or not set(straps) <= set(ports):
        raise ValueError(f"param_wrap {base}: straps {sorted(straps)} must include {sorted(need)} and be within {sorted(ports)}")
    out = {}
    for k in ports:
        if k not in straps:
            continue
        w, v = ports[k], straps[k]
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < (1 << w):
            raise ValueError(f"param_wrap {base}: strap {k} value {v!r} does not fit {w} bits")
        out[k] = (w, v)
    return out


def strapped_params(straps):
    """bound parameters carried by the strap pins of a row (not matched in the instance text): SKEW, SKEW_N, SKEW_S when the skew pair is
    strapped, HI_PAD when strap_hi_pad is"""
    out = {strap_param(k) for k in straps}
    if out & {"SKEW_N", "SKEW_S"}:
        out |= {"SKEW"}
    return out


def param_text(params):
    """the bind's instantiation parameter text: #(.W(2104), .DEPTH(4), ...) in the given order"""
    return "#(" + ", ".join(f".{k}({int(v)})" for k, v in params.items()) + ")"


def wrapper_sv(master, base, params, straps=None):    # straps: the row's strap pin names (values are not part of the text)
    if base not in PORTS:
        raise ValueError(f"param_wrap: base {base} has no port table")
    ports = [(d, n, w(params)) for d, n, w in PORTS[base]]
    ports = [x for x in ports if x[2] > 0]       # an optional port of width 0 (rst_xn at RSTREP 0) is not declared
    if straps is not None:
        # STRAP-MASTER-1115: stand-in for the strapped master: the strap pins are declared inputs, the body is the base at the
        # non-strap parameters (module defaults for SKEW*); the strap values are NOT in this text, so one source serves every
        # tie value.  The signed master's own RTL replaces it (row wrapper=false when the core kit ships that RTL).
        check_straps(base, {k: 0 for k in straps})
        strap_ports = [("input", k, w) for k, w in STRAP_PORTS[base].items() if k in straps]
        decl = ",\n".join(f"    {d:6} wire {'[' + str(w - 1) + ':0] ' if w > 1 else ''}{n}" for d, n, w in ports + strap_ports)
        conn = ", ".join(f".{n}({n})" for _, n, _ in ports)
        return (f"// GENERATED by tools/die_plan/param_wrap.py (STRAP-MASTER-1115): {master} = {base} {param_text(params)} with strap pins "
                f"{', '.join(n for _, n, _ in strap_ports)}.\n"
                f"// Stand-in: strap pins accepted, the body is the base at its defaults; the strap values are not part of this source.\n"
                f"module {master} (\n{decl}\n);\n    {base} {param_text(params)} u_w ({conn});\nendmodule\n")
    decl = ",\n".join(f"    {d:6} wire {'[' + str(w - 1) + ':0] ' if w > 1 else ''}{n}" for d, n, w in ports)
    conn = ", ".join(f".{n}({n})" for _, n, _ in ports)
    return (f"// GENERATED by tools/die_plan/param_wrap.py (QC-SLECTL-B): {master} = {base} {param_text(params)}.\n"
            f"// Pure pass-through wrapper: one paramod as a named hard-core master; no logic, no cycles.\n"
            f"module {master} (\n{decl}\n);\n    {base} {param_text(params)} u_w ({conn});\nendmodule\n")


def _bound_params(txt):
    return {k: v for k, v in re.findall(r"\.(\w+)\s*\(\s*([^()]*?)\s*\)", txt or "")}


def _iv(v):
    try:
        return int(str(v).replace("_", ""), 0)
    except ValueError:
        return None


def bound_strap_value(base, bound_params, strap):
    """the bound instance's value of the parameter a strap carries (SKEW_N for strap_skew_n, HI_PAD for strap_hi_pad): the
    instance's own, for SKEW_N / SKEW_S else its SKEW, else the module default; None when the text holds a non-integer"""
    k = strap_param(strap)
    names = (k, "SKEW") if k in ("SKEW_N", "SKEW_S") else (k,)
    for name in names:
        if name in bound_params:
            return _iv(bound_params[name])
    d = STRAP_PARAM_DEFAULT.get(base, {})
    return d.get("SKEW") if k in ("SKEW_N", "SKEW_S") else d.get(k)


def wrap_bound(bound, hard_cores):
    """-> (bound, receipt, {master: wrapper text}): rename every planned param_wrap instance in the bound text.
    A row with param_wrap.straps matches the non-skew parameters only and ties the strap pins (STRAP-MASTER-1115)."""
    receipt, srcs = [], {}
    for hc in hard_cores or []:
        pw = hc.get("param_wrap")
        if not pw:
            continue
        master, base, params = hc.get("physical_master") or hc["module"], pw["base"], pw["params"]
        straps = check_straps(base, pw["straps"]) if pw.get("straps") is not None else None
        inst = (hc.get("physical_inst") or "").removeprefix("u_bound.")
        if not inst or "." in inst:
            raise ValueError(f"param_wrap {hc['inst']}: physical_inst must be u_bound.<local> (got {hc.get('physical_inst')})")
        opt = "?" if straps else ""     # a strapped base left at its defaults has no #(...) text
        pat = re.compile(r"^([ \t]+)(\w+)(?:[ \t]+(#\([^\n]*?\)))" + opt + r"[ \t]+" + re.escape(inst) + r"[ \t]*\(", re.M)
        hits = list(pat.finditer(bound))
        if len(hits) != 1:
            raise ValueError(f"param_wrap {hc['inst']}: expected one instance {inst}, got {len(hits)}")
        h = hits[0]
        if straps is None:
            if h.group(2) != base or re.sub(r"\s", "", h.group(3)) != re.sub(r"\s", "", param_text(params)):
                raise ValueError(f"param_wrap {hc['inst']}: {inst} is {h.group(2)} {h.group(3)}, plan says {base} {param_text(params)}")
            bound = bound[:h.start()] + f"{h.group(1)}{master} {inst} (" + bound[h.end():]
            txt = wrapper_sv(master, base, params)
        else:
            skip = strapped_params(straps)
            have = {k: v for k, v in _bound_params(h.group(3)).items() if k not in skip}
            want = {k: str(int(v)) for k, v in params.items() if k not in skip}
            if h.group(2) != base or {k: _iv(v) for k, v in have.items()} != {k: int(v) for k, v in want.items()}:
                raise ValueError(f"param_wrap {hc['inst']}: {inst} is {h.group(2)} {h.group(3)}, plan says {base} "
                                 f"{param_text({k: int(v) for k, v in want.items()})} ({sorted(skip)} are straps)")
            ties = ", ".join(f".{k}({w}'d{v})" for k, (w, v) in straps.items())
            rest = bound[h.end():]
            comma = "" if re.match(r"\s*\)", rest) else ","
            bound = bound[:h.start()] + f"{h.group(1)}{master} {inst} (\n{h.group(1)}    {ties}{comma}" + rest
            txt = wrapper_sv(master, base, params, straps=list(straps)) if pw.get("wrapper", True) else None
        if txt is not None:
            if srcs.get(master, txt) != txt:
                raise ValueError(f"param_wrap: master {master} declared with two parameter sets")
            srcs[master] = txt
        receipt.append(dict(inst=hc["inst"], physical_inst=hc["physical_inst"], master=master, base=base,
                            params=dict(params), cycles_changed=0,
                            **({"straps": {k: v for k, (w, v) in straps.items()}} if straps else {})))
    return bound, receipt, srcs
