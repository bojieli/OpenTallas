#!/usr/bin/env python3
"""Fail-closed die reset PAD gate of a bound die (PATH-KV-POR 10-25; PATH-KV DECISION 14:19 + CLOCK-RESET amendments
A/B 14:32; reset_tree.py "die reset pad").

    python3 tools/die_plan/por_gate.py PLAN.json BOUND_DIR       # BOUND_DIR/rtl/*.sv (+ bind_por.json); exit 1 = FAIL

A plan with reset.source.pad has ONE external reset pad = the die reset root pin.  On the bound RTL this gate proves:
  G1 top      the pad port is one top input whose ONLY load is the reset ROOT partition's arst_n (no other partition,
              no assign, no expression): no raw pad net crosses the die.
  G2 root     inside the root type, arst_n (= the raw pad) has EXACTLY the loads {u_rst_root.async_rst_n} + the
              declared analog loads (PLL por_n), each a plain connection (no `arst_n & x`): u_rst_root's async input is
              the pad ONLY, the one reset false path.  With reset.source.lock: u_rst_root -> rst_por_n ->
              ot_dp_lockq u_rst_lockq (.d(rst_por_n), .locked(pll_locked_i), .q(rst_root_n)) and the lock net feeds
              ONLY u_rst_lockq.locked (no combinational por_n & locked, no lock into any reset).
  G3 others   no other module has a pad-named port (io_<pad>) and its arst_n feeds only the u_rst_in pin register
              (or the native hard-partition alias `wire rst_n = arst_n`).
  G4 rebinds  every rebound por_n leaf (bind_por.json, written by bind.py) sits in a start_role BOOTSTRAP type, and that
              type's leaf rst_n is a RAW wavefront tap (ot_dp_rrelay, not START-gated ot_dp_rgate): power-on resets
              (sys_c D2D / UCIe phy_rst_n, host) release at the published wavefront offset, before START.
Mutants that must FAIL (test_por_gate.py): raw pad wired into sys_c; combinational `arst_n & pll_locked_i` at
u_rst_root; a mission-role sys_c."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


class PorGateError(Exception):
    pass


def _strip(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def modules(text):
    """{module name: (header port text, body text)} of a (comment-stripped) SV file."""
    out = {}
    for m in re.finditer(r"\bmodule\s+(\w+)\s*(#\s*\(.*?\)\s*)?\((.*?)\);(.*?)\bendmodule\b", _strip(text), re.S):
        out[m.group(1)] = (m.group(3), m.group(4))
    return out


def _balanced(s, i):
    """index just past the ')' closing the '(' at s[i]."""
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j + 1
    raise PorGateError("unbalanced parentheses")


def instances(body):
    """[(module, inst, {pin: expr})] of the named-connection instances in a module body."""
    out = []
    for m in re.finditer(r"(?m)^\s*(\w+)\s*(#\s*\()?", body):
        mod = m.group(1)
        if mod in ("wire", "reg", "logic", "assign", "input", "output", "inout", "always", "localparam", "parameter",
                   "genvar", "generate", "endgenerate", "initial", "if", "else", "begin", "end", "for"):
            continue
        k = m.end()
        if m.group(2):
            k = _balanced(body, m.end() - 1)
        mm = re.compile(r"\s*(\w+)\s*\(").match(body, k)
        if not mm:
            continue
        inst = mm.group(1)
        j = mm.end() - 1
        end = _balanced(body, j)
        txt = body[j + 1:end - 1]
        conns = {}
        q = 0
        while True:
            c = re.compile(r"\s*,?\s*\.(\w+)\s*\(").search(txt, q)
            if not c:
                break
            e = _balanced(txt, c.end() - 1)
            conns[c.group(1)] = txt[c.end():e - 1].strip()
            q = e
        if conns:
            out.append((mod, inst, conns))
    return out


def _uses(body, net):
    """count of `net` tokens in a module body."""
    return len(re.findall(rf"(?<![\w.$]){re.escape(net)}(?![\w$])", body))


def check(P, rtl_dir, record=None):
    """the gate verdict {verdict, errors, ...} (PASS also when the plan declares no pad: nothing to check)."""
    import reset_tree as RT
    import gen_rtl
    ps = RT.pad_spec(P)
    if ps is None:
        return dict(verdict="PASS", note="no die reset pad declared (reset.source.pad)", errors=[])
    errs = []
    rtl_dir = Path(rtl_dir)
    mods = {}
    for f in sorted(rtl_dir.glob("*.sv")):
        mods.update(modules(f.read_text()))
    W = RT.wf_plan(P)
    root, rtype = W["root"], W["root_type"]
    port = gen_rtl.sv_id(ps["port"])
    die = gen_rtl.sv_id(P.name) + "_bound_top"
    if die not in mods:
        raise PorGateError(f"no bound top module {die} in {rtl_dir}")
    # G1 top fan-out
    hdr, body = mods[die]
    decl = re.findall(rf"\binput\s+wire\s+(?:\[[^\]]*\]\s*)?{re.escape(port)}\s*;", body)
    if len(decl) != 1:
        errs.append(f"G1 top: pad {port} declared {len(decl)} times as a top input (want exactly 1)")
    loads = [(mod, inst, pin, e) for mod, inst, cs in instances(body) for pin, e in cs.items()
             if _uses(e, port)]
    inconn = sum(_uses(e, port) for *_x, e in loads)
    other = _uses(body, port) - inconn - len(decl)
    want_inst = gen_rtl.sv_id(root)
    good = [x for x in loads if x[1] == want_inst and x[2] == "arst_n" and x[3] == port]
    if len(good) != 1 or len(loads) != 1 or other:
        errs.append(f"G1 top: pad {port} loads {[(x[1], x[2], x[3]) for x in loads]} (+{other} other uses); want only "
                    f"{want_inst}.arst_n (the reset root partition)")
    root_mod = P.types[rtype]["module"]
    for mod in mods:
        if mod != die and re.search(rf"\bio_{re.escape(port)}\b", mods[mod][0]):
            errs.append(f"G3 {mod}: has a raw pad port io_{port} (no raw pad net may cross the die)")
    # G2 root type
    if root_mod not in mods:
        errs.append(f"G2 root: no module {root_mod} (type {rtype})")
    else:
        hdr, body = mods[root_mod]
        allowed = {("u_rst_root", "async_rst_n")}
        for a in ps["analog_loads"]:
            allowed |= {(a["inst"], a["pin"]), ("u_" + a["inst"], a["pin"])}
        insts = instances(body)
        seen, n_in = set(), 0
        for mod, inst, cs in insts:
            for pin, e in cs.items():
                k = _uses(e, "arst_n")
                if not k:
                    continue
                n_in += k
                if (inst, pin) not in allowed or e != "arst_n":
                    errs.append(f"G2 root {root_mod}: arst_n (raw pad) reaches {inst}.{pin} = ({e}); allowed only plain "
                                f"connections to u_rst_root.async_rst_n + analog loads")
                else:
                    seen.add((inst, pin))
        if _uses(body, "arst_n") != n_in:
            errs.append(f"G2 root {root_mod}: arst_n (raw pad) used {_uses(body, 'arst_n') - n_in} time(s) outside "
                        "instance connections (assign / expression)")
        if ("u_rst_root", "async_rst_n") not in seen:
            errs.append(f"G2 root {root_mod}: u_rst_root.async_rst_n is not the raw pad")
        for a in ps["analog_loads"]:
            if not ({(a["inst"], a["pin"]), ("u_" + a["inst"], a["pin"])} & seen):
                errs.append(f"G2 root {root_mod}: declared analog load {a['inst']}.{a['pin']} not on the raw pad")
        if ps.get("lock"):
            lq = [(cs) for mod, inst, cs in insts if inst == "u_rst_lockq" and mod == "ot_dp_lockq"]
            rr = [(cs) for mod, inst, cs in insts if inst == "u_rst_root"]
            if len(lq) != 1 or lq[0].get("d") != "rst_por_n" or lq[0].get("q") != "rst_root_n" or \
                    lq[0].get("locked") != RT.LOCK_SRC:
                errs.append(f"G2 root {root_mod}: no u_rst_lockq ot_dp_lockq (.d(rst_por_n), .locked({RT.LOCK_SRC}), "
                            ".q(rst_root_n)) PLL lock qualifier")
            if len(rr) != 1 or rr[0].get("sync_rst_n") != "rst_por_n":
                errs.append(f"G2 root {root_mod}: u_rst_root must drive rst_por_n (into the lock qualifier)")
            lk_loads = [(inst, pin) for mod, inst, cs in insts for pin, e in cs.items() if _uses(e, RT.LOCK_SRC)]
            n_assign = len(re.findall(rf"\bassign\s+{RT.LOCK_SRC}\s*=", body))
            n_decl = len(re.findall(rf"\bwire\s+{RT.LOCK_SRC}\s*;", body))
            if lk_loads != [("u_rst_lockq", "locked")] or \
                    _uses(body, RT.LOCK_SRC) != len(lk_loads) + n_assign + n_decl or n_assign != 1:
                errs.append(f"G2 root {root_mod}: PLL lock {RT.LOCK_SRC} loads {lk_loads} (+other uses); want only "
                            "u_rst_lockq.locked (no combinational lock into a reset)")
    # G3 other types: arst_n only into the pin register
    for tn, t in sorted(P.types.items()):
        mod = t["module"]
        if tn == rtype or mod not in mods:
            continue
        hdr, body = mods[mod]
        n_in = 0
        for m_, inst, cs in instances(body):
            for pin, e in cs.items():
                k = _uses(e, "arst_n")
                if not k:
                    continue
                n_in += k
                if not (inst == "u_rst_in" and pin == "d" and e == "arst_n"):
                    errs.append(f"G3 {mod}: arst_n reaches {inst}.{pin} = ({e}); a non-root partition registers it "
                                "in u_rst_in only")
        alias = len(re.findall(r"\bwire\s+rst_n\s*=\s*arst_n\s*;", body))
        if _uses(body, "arst_n") != n_in + alias:
            errs.append(f"G3 {mod}: arst_n used outside the u_rst_in pin register")
    # G4 rebinds: bootstrap role + raw wavefront leaf tap
    rec = record
    if rec is None and (rtl_dir.parent / "bind_por.json").is_file():
        rec = json.loads((rtl_dir.parent / "bind_por.json").read_text())
    rebinds = (rec or {}).get("rebinds", [])
    roles = {}
    for r in rebinds:
        tn = r["type"]
        if tn not in roles:
            T = RT.for_type(P, tn) if not P.types[tn].get("hard") else None
            role = (T or {}).get("start_role", "mission") if T else "hard"
            raw = None
            if T and P.types[tn]["module"] in mods:
                body = mods[P.types[tn]["module"]][1]
                m = re.search(r"\bwire\s+rst_n\s*=\s*(rst_n_t\d+)\s*;", body) or \
                    re.search(r"\bassign\s+rst_n\s*=\s*(rst_n_t\d+)\s*;", body)
                if m:
                    drv = [mod_ for mod_, inst, cs in instances(body) if cs.get("q") == m.group(1)]
                    raw = drv == ["ot_dp_rrelay"]
            roles[tn] = dict(role=role, raw_leaf_tap=raw)
        if roles[tn]["role"] != "bootstrap":
            errs.append(f"G4 {r['pin']}[{r['bit']}] (type {tn}): rebound power-on reset in a {roles[tn]['role']} type; "
                        "its type must be start_role bootstrap (a POR leaf cannot wait for START)")
        elif roles[tn]["raw_leaf_tap"] is False:
            errs.append(f"G4 {r['pin']} (type {tn}): leaf rst_n is not a raw wavefront tap (ot_dp_rrelay)")
    if rec is not None and not rec.get("analog"):
        errs.append("G4 bind record: no analog pad load bound (the declared PLL por_n)")
    out = dict(verdict="FAIL" if errs else "PASS", pad=ps["pad"], port=ps["port"], root=root, root_type=rtype,
               rebinds=len(rebinds), rebind_types=roles, analog=(rec or {}).get("analog", []),
               lock=ps.get("lock"), lock_stages=RT.lock_stages(P), errors=errs)
    return out


def main(argv=None):
    import argparse
    import schema as S
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("bound", help="bound dir (rtl/ + bind_por.json)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    P = S.Plan(json.loads(Path(a.plan).read_text()), a.plan)
    r = check(P, Path(a.bound) / "rtl")
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    for e in r["errors"]:
        print("ERROR", e)
    print(f"POR GATE {r['verdict']}: {len(r['errors'])} errors")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
