#!/usr/bin/env python3
"""svc_width_gate.py -- S81-SVC-H8W 11-20 (COORD / S81-DIE-R3 J3 r7): fail closed on a port-width truncation or
extension anywhere on the S81 service-slice path, under the H setting the manifest elaborates.

Why: J3 r7 bound the H8 svc form (OT_SVC_H8) through the frozen bind178 PORTFIX copy of dsdv_svc_rs_fv.sv, whose
gather faces were [2131:0] (H16) around a dsdv_svc_rs_c that is 4*(H*132+20) = 4,304 b at H8.  Yosys / slang resized the
port silently; the bind then tied 26,540 LIVE dsdv_svc_sx gi_d bits (gather quarters 2/3) to 0.  No existing gate saw
it: the bind's dead-input proof only reported the ties.  This gate checks, before elaboration, with the same defines:

  (1) SOURCE: every instance inside the given modules (default: the svc slice chain, dsdv_svc_rs*_fv_*, the
      PORTFIX / source dsdv_svc_rs_pvso_entry, dsdv_svc_rs_f / _entry_f, the landed wrappers) against its master's
      ANSI header: connection width == port width, both evaluated under the parent's / instance's parameters, with
      `OT_SVC_HV from the defines (OT_SVC_H8 -> 8, else 16).
  (2) NETLIST (--netlist): every svc slice instance (dsdv_svc_rs*_fv_*) and every dsdv_svc_busland_<W> instance of the
      die netlist, its connection widths (netlist wire declarations) against the master ports under the same H.

    svc_width_gate.py --root REPO [--asbuilt ASBUILT.json] [--define D ...] [--netlist DIE.v] [--src F ...]
                      [--module RE ...] [--out JSON]

--asbuilt takes the defines and the svc source files from the manifest (`defines`, `files` entries matching svc).
Exit 0 = PASS, 1 = FAIL (any width mismatch, unknown master port, or a width it cannot resolve on a checked port).
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import port_bind_gate as PBG  # noqa: E402

SVC_FILE = re.compile(r"(svc_rs|pv_so/dsdv_svc_rs_pvso_entry|portfix178/dsdv_svc_rs_|land/dsdv_svc_busland|svc_rs_lp|dsdv_svc_rs_glue)")
DEFAULT_MODULES = [r"dsdv_svc_rs(_pvso_entry)?_fv_\w+", r"dsdv_svc_rs_pvso_entry", r"dsdv_svc_rs_(entry_)?f",
                   r"dsdv_svc_rs_(entry_)?lp", r"dsdv_svc_rs", r"dsdv_svc_rs_entry", r"dsdv_svc_rs_attw1?"]
NETLIST_MASTERS = re.compile(r"^(dsdv_svc_rs(_pvso_entry)?_fv_\w+|dsdv_svc_busland_\d+)$")
MOD = re.compile(r"(?ms)^\s*module\s+(\w+)\b(.*?)^\s*endmodule\b")
INST = re.compile(r"(?<![\w.$`])([A-Za-z_]\w*)\s*(?:#\s*\((?P<par>(?:[^()]|\((?:[^()]|\([^()]*\))*\))*)\))?\s+"
                  r"([A-Za-z_]\w*)\s*\(", re.S)
KW = PBG._KW | {"always_ff", "always_comb", "unique", "priority", "return", "assert", "bit", "logic", "integer", "int"}


def h_of(defines):
    return 8 if "OT_SVC_H8" in defines else 16


def macros(defines):
    m = {"OT_SVC_HV": str(h_of(defines))}
    for d in defines:
        if "=" in d:
            k, v = d.split("=", 1)
            m[k] = v
    return m


def prep(text, defines):
    t = PBG.preprocess(text, tuple(defines) + ("SYNTHESIS",))
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    mac = macros(defines)
    for m in re.finditer(r"(?m)^[ \t]*`define\s+(\w+)[ \t]+([^\n]+)", t):   # live `define values (e.g. OT_SVC_GP)
        mac.setdefault(m.group(1), m.group(2).strip())
    t = re.sub(r"^[ \t]*`(define|undef|timescale|default_nettype|include)\b[^\n]*", "", t, flags=re.M)
    return re.sub(r"`(\w+)", lambda m: mac.get(m.group(1), m.group(0)), t)


def header(text_after_name):
    """(params_txt, ports_txt, body) of a module given the text after its name"""
    s, i = text_after_name, 0
    while s[i].isspace():
        i += 1
    par = ""
    if s[i] == "#":
        k = s.index("(", i)
        e = _match(s, k)
        par, i = s[k + 1:e], e + 1
        while s[i].isspace():
            i += 1
    if s[i] != "(":
        return par, "", s[i:]
    e = _match(s, i)
    semi = s.index(";", e)
    return par, s[i + 1:e], s[semi + 1:]


def _match(s, k):
    d = 0
    for j in range(k, len(s)):
        d += {"(": 1, ")": -1}.get(s[j], 0)
        if d == 0:
            return j
    raise ValueError("unbalanced")


def params(par_txt, body):
    out = {}
    for it in PBG._split_top(par_txt, ","):
        m = re.match(r"\s*(?:parameter|localparam)?\s*(?:integer|int|logic|bit|signed)?\s*(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*(.+)",
                     it, re.S)
        if m:
            out[m.group(1)] = m.group(2).strip()
    for m in re.finditer(r"\blocalparam\b\s*(?:integer|int|logic|bit)?\s*(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*([^;,]+)", body):
        out[m.group(1)] = m.group(2).strip()
    return out


def ports(ports_txt):
    out, d, r = {}, None, ""
    for it in PBG._split_top(ports_txt, ","):
        it = " ".join(it.split())
        if not it:
            continue
        m = re.match(r"(input|output|inout)?\s*(?:wire|reg|logic)?\s*(?:signed)?\s*(\[[^\]]*\])?\s*(\w+)$", it)
        if not m:
            raise ValueError(f"port item {it!r}")
        if m.group(1):
            d, r = m.group(1), m.group(2) or ""
        elif m.group(2):
            r = m.group(2)
        out[m.group(3)] = (d, r)
    return out


def decls(ports_txt, body):
    """{name: range text} of ports and wires/regs (ANSI ports + body declarations)"""
    out = {k: r for k, (_, r) in ports(ports_txt).items()}
    for m in re.finditer(r"(?<![\w.$`])(?:wire|reg|logic)(?:\s+|(?=\[))(?:signed\s+)?(\[[^\]]*\])?\s*([^;]+);", body):
        for nm in PBG._split_top(m.group(2), ","):
            nm = nm.split("=")[0].strip()
            if re.fullmatch(r"[A-Za-z_]\w*", nm):
                out[nm] = m.group(1) or ""
    return out


def ev(expr, env):
    return PBG._eval(expr, env)


def width(rng, env):
    return PBG._width(rng, env) if rng else 1


def expr_width(e, dw, env):
    """width of a connection expression: name, name[i], name[a:b], name[a +: w], literals, concatenations"""
    e = e.strip()
    while e.startswith("(") and e.endswith(")") and PBG._balanced(e[1:-1]):
        e = e[1:-1].strip()
    if e.startswith("{") and e.endswith("}") and PBG._balanced(e[1:-1]):
        inner = e[1:-1].strip()
        m = re.match(r"^([^{},]+)\{(.*)\}$", inner, re.S)
        if m and PBG._balanced(m.group(2)):
            n = ev(m.group(1), env)
            w = expr_width("{" + m.group(2) + "}", dw, env)
            return None if w is None else n * w
        ws = [expr_width(x, dw, env) for x in PBG._split_top(inner, ",")]
        return None if any(w is None for w in ws) else sum(ws)
    m = re.fullmatch(r"(?:(\d+|\([^']*\))\s*)?'\s*[sS]?[bBdDhH]\s*[0-9a-fA-F_xXzZ]+", e)
    if m:
        return ev(m.group(1), env) if m.group(1) else 32
    m = re.fullmatch(r"([A-Za-z_]\w*)\s*(\[(.*)\])?", e, re.S)
    if not m or m.group(1) not in dw:
        return None
    if not m.group(2):
        return dw[m.group(1)]
    inner = m.group(3)
    for op in ("+:", "-:"):
        parts = inner.split(op)
        if len(parts) == 2 and PBG._balanced(parts[0]):
            return ev(parts[1], env)
    cut = [i for i, c in enumerate(inner) if c == ":" and PBG._balanced(inner[:i])]
    if not cut:
        return 1
    return abs(ev(inner[:cut[0]], env) - ev(inner[cut[0] + 1:], env)) + 1


def library(texts):
    lib = {}
    for t in texts:
        for m in MOD.finditer(t):
            name = m.group(1)
            par, pt, body = header(m.group(2))
            lib[name] = dict(params=params(par, body), ports=ports(pt), ports_txt=pt, body=body)
    return lib


def inst_env(master, par_txt, penv):
    env = dict(master["params"])
    for pm in re.finditer(r"\.(\w+)\s*\(", par_txt or ""):
        k = pm.end()
        e = _match(par_txt, k - 1)
        v = par_txt[k:e].strip()
        try:
            env[pm.group(1)] = str(ev(v, penv))
        except Exception:
            env[pm.group(1)] = v
    return env


def check_module(name, mod, lib, rec, env_over=None):
    env = dict(mod["params"])
    env.update(env_over or {})
    dws = {}
    for n, r in decls(mod["ports_txt"], mod["body"]).items():
        try:
            dws[n] = width(r, env)
        except Exception:
            pass
    for im in INST.finditer(mod["body"]):
        mst, inst = im.group(1), im.group(3)
        if mst in KW or mst not in lib:
            continue
        k = im.end() - 1
        e = _match(mod["body"], k)
        conns = PBG._conns(mod["body"][k + 1:e])
        master = lib[mst]
        ienv = inst_env(master, im.group("par"), env)
        rec["instances"] += 1
        where = f"{name}.{inst} ({mst})"
        for pn, ex in conns.items():
            if pn not in master["ports"]:
                rec["unknown"].append(f"{where}.{pn}")
                continue
            if not ex:
                continue
            try:
                pw = width(master["ports"][pn][1], ienv)
            except Exception:
                pw = None
            try:
                cw = expr_width(ex, dws, env)
            except Exception:
                cw = None
            if pw is None or cw is None:
                rec["unresolved"].append(f"{where}.{pn}({ex[:80]})")
            elif pw != cw:
                kind = "TRUNC" if cw > pw else "EXT"
                rec["width_mismatch"].append(f"{where}.{pn}: port {pw} b <- {ex[:80]} {cw} b ({kind})")
            else:
                rec["ok_ports"] += 1


def shared_blackbox_widths(lib, blackboxed, parameterized, scope=re.compile(r"^dsdv_svc_")):
    """a slang empty blackbox (--blackboxed-module, not in slang_parameterized_blackboxes) gets ONE interface: the first
    instance's widths (asbuilt parameterized_interface_note).  Any such master whose instances in the svc modules have
    different port widths is resized silently (J r7: dsdv_svc_mem_ar u_qmem_mem rd 512 -> 256 b, q_w[511:256] tied 0;
    u_wq_mem rd 341 -> 256 b) -> [(master, {signature: [where]})]"""
    sigs = {}
    for name, mod in lib.items():
        if not scope.match(name):
            continue
        env = dict(mod["params"])
        for im in INST.finditer(mod["body"]):
            mst = im.group(1)
            if mst not in blackboxed or mst in parameterized or mst not in lib:
                continue
            ienv = inst_env(lib[mst], im.group("par"), env)
            sig = []
            for pn, (_, r) in sorted(lib[mst]["ports"].items()):
                try:
                    sig.append((pn, width(r, ienv)))
                except Exception:
                    sig.append((pn, None))
            sigs.setdefault(mst, {}).setdefault(tuple(sig), []).append(f"{name}.{im.group(3)}")
    out = []
    for mst, d in sorted(sigs.items()):
        if len(d) > 1:
            ex = []
            for sig, where in d.items():
                ex.append(dict(where=where[:4], widths={k: v for k, v in sig if any(k == k2 and v != v2 for s2 in d
                                                                                     for k2, v2 in s2 if s2 != sig)}))
            out.append(dict(master=mst, interfaces=len(d), instances=ex))
    return out


def run(root, defines, srcs, mods, netlist=None, blackboxed=(), parameterized=()):
    texts = [prep((root / f).read_text(errors="replace"), defines) for f in srcs]
    lib = library(texts)
    rec = dict(instances=0, ok_ports=0, width_mismatch=[], unknown=[], unresolved=[], modules=[])
    pats = [re.compile(rf"^{p}$") for p in mods]
    for name in sorted(lib):
        if any(p.match(name) for p in pats):
            rec["modules"].append(name)
            check_module(name, lib[name], lib, rec)
    if netlist:
        nt = prep(Path(netlist).read_text(errors="replace"), defines)
        for m in MOD.finditer(nt):
            par, pt, body = header(m.group(2))
            sub = dict(params={}, ports=ports(pt) if pt and "input" in pt else {}, ports_txt=pt if "input" in pt else "",
                       body="\n".join(ln for ln in body.split(";\n") if True))
            # restrict to the svc masters (the die netlist is ~10 MB; other instances are other gates' scope)
            keep = []
            for im in INST.finditer(body):
                if NETLIST_MASTERS.match(im.group(1)):
                    e = _match(body, im.end() - 1)
                    keep.append(body[im.start():e + 1] + ";")
            wires = re.findall(r"(?m)^\s*wire\b[^;]*;", body)
            sub["body"] = "\n".join(wires) + "\n" + "\n".join(keep)
            n0 = rec["instances"]
            check_module(f"netlist:{m.group(1)}", sub, lib, rec)
            rec.setdefault("netlist_instances", 0)
            rec["netlist_instances"] += rec["instances"] - n0
    rec["shared_blackbox"] = shared_blackbox_widths(lib, set(blackboxed), set(parameterized)) if blackboxed else []
    bad = {k: v for k, v in rec.items() if k in ("width_mismatch", "unknown", "unresolved", "shared_blackbox") and v}
    verdict = "PASS" if not bad and rec["instances"] else "FAIL"
    return dict(verdict=verdict, H=h_of(defines), defines=sorted(defines), instances=rec["instances"],
                netlist_instances=rec.get("netlist_instances", 0), ok_ports=rec["ok_ports"],
                modules=len(rec["modules"]), **{k: len(rec[k]) for k in ("width_mismatch", "unknown", "unresolved", "shared_blackbox")},
                examples={k: v[:40] for k, v in bad.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(HERE.parents[1]))
    ap.add_argument("--asbuilt")
    ap.add_argument("--define", action="append", default=[])
    ap.add_argument("--netlist")
    ap.add_argument("--src", action="append", default=[])
    ap.add_argument("--module", action="append", default=[])
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    root = Path(a.root)
    defines, srcs = list(a.define), list(a.src)
    if a.asbuilt:
        ab = json.loads(Path(a.asbuilt).read_text())
        defines += [d.removeprefix("-D") for d in ab.get("defines", [])]
        srcs += [f for f in ab.get("files", []) if SVC_FILE.search(f) and f.endswith((".sv", ".v"))]
        bb_par = ab.get("slang_parameterized_blackboxes", [])
        diss = set(ab.get("dissolve", [])) | {ab.get("top")}
        if not a.netlist and ab.get("netlist"):
            a.netlist = str(root / ab["netlist"][0])
    if not srcs:
        ap.error("no sources (--src or --asbuilt)")
    bb = pbb = ()
    if a.asbuilt and ab.get("frontend") == "slang":
        names = set(library([prep((root / f).read_text(errors="replace"), defines) for f in srcs]))
        bb, pbb = names - diss, set(bb_par)
    r = run(root, defines, list(dict.fromkeys(srcs)), a.module or DEFAULT_MODULES, a.netlist, bb, pbb)
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    print("SVC_WIDTH_GATE", r["verdict"], json.dumps({k: v for k, v in r.items() if k != "examples"}))
    for k, v in r["examples"].items():
        for x in v[:8]:
            print(" ", k, x)
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
