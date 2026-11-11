#!/usr/bin/env python3
"""KIT-ISTATIONS 11-10: proof that a kit_hbm_cstations kit equals the STAGED GOLDEN, per link class.

Staged golden = the ORIGINAL bound module in which every leaf->leaf link item of a stationed leaf pair (the class table
of the kit receipt: class -> depth D, leaf pairs) reaches its sink D cycles later.  The golden is built here from the
original text with its own link detection and its own explicit delay registers (not ot_dp_dly, not the generator's
link list), so the generator's mapping is under test.

  (1) TEXT   the kit text minus its appended station block is line-for-line the original, except leaf input-port lines;
             every port line holding a stationed link is changed, no other line is; every u_hcs_ chain is read.
  (2) SAT    per class: a vehicle of every port line holding a link of that class (kit side: the kit's port
             expressions + the u_hcs_ chains they read, ot_dp_dly from --cells; gold side: original expressions,
             link items delayed by their class D), leaf outputs / other items as free inputs.  yosys miter,
             sat -tempinduct -set-init-zero (both sides zero at reset, k-induction to D+3) must PROVE.
  (3) NEG    per class: the same vehicle with one kit chain of the class at D-1 (a MISSING stage) and at D+1 (an
             EXTRA stage) must FAIL (rc != 0).
usage: hbm_cstation_proof.py ORIG.sv KIT.sv RECEIPT.json --cells CELLS.sv --out DIR [--classes a,b] [--jobs N]
       RECEIPT = kit_rtl.json (kit_hbm_core_stations) or hcs_report.json; run DIR/run.sh with $YOSYS (or --run)."""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ID = r"[A-Za-z_][A-Za-z0-9_$]*"
START = re.compile(rf"^\s*({ID})\s+(?:#\(.*\)\s+)?(u_\w+)\s*\(\s*$")
PORT = re.compile(rf"^(\s*)\.({ID})\((.*)\)(,?)(\s*(?://.*)?)$")
MARK = "    // kit_hbm_cstations: HBM core<->core plan stations"
HCS = re.compile(r"^\s*ot_dp_dly #\(\.W\((\d+)\), \.D\((\d+)\)\) (u_hcs_\d+) \(\.clk\(clk\), \.d\((.*)\), \.q\((hcs_\d+)\)\);")


def items_of(expr):
    e = expr.strip()
    if not (e.startswith("{") and e.endswith("}")):
        return [e]
    out, depth, cur = [], 0, ""
    for ch in e[1:-1]:
        depth += ch in "{(" or 0
        depth -= ch in "})" or 0
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def decls(txt):
    """id -> (hi, lo) for wires / ports / parameters"""
    d = {}
    for m in re.finditer(rf"^\s*(?:wire|logic|reg|input\s+wire|output\s+wire|input|output|parameter)\s*(?:\[(\d+):(\d+)\])?\s*({ID})\b",
                         txt, re.M):
        d[m.group(3)] = (int(m.group(1)), int(m.group(2))) if m.group(1) else (0, 0)
    return d


def width(it, D):
    it = it.strip()
    m = re.match(rf"^({ID})(?:\[(\d+)(?::(\d+))?\])?$", it)
    if m:
        if m.group(2) is None:
            hi, lo = D[m.group(1)]
            return abs(hi - lo) + 1
        return abs(int(m.group(2)) - int(m.group(3) if m.group(3) is not None else m.group(2))) + 1
    m = re.match(r"^(\d+)'[bdhBDH][0-9a-fA-FxXzZ_]+$", it)
    if m:
        return int(m.group(1))
    m = re.match(r"^\{(\d+)\{(.*)\}\}$", it)
    if m:
        return int(m.group(1)) * sum(width(x, D) for x in items_of("{" + m.group(2) + "}"))
    if it.startswith("{"):
        return sum(width(x, D) for x in items_of(it))
    raise ValueError(f"unsized item {it!r}")


def leaf_lines(lines):
    """[(line no, leaf inst, port, expr)] of multi-line leaf instance blocks"""
    out, cur = [], None
    for i, ln in enumerate(lines):
        m = START.match(ln)
        if m:
            cur = None if m.group(1).startswith("ot_dp_") else m.group(2)
            continue
        if re.match(r"^\s*\);", ln):
            cur = None
            continue
        pm = PORT.match(ln)
        if cur and pm:
            out.append((i, cur, pm.group(2), pm.group(3)))
    return out


def owners(txt, pl):
    """wire -> leaf for w_<inst minus u_>_<port> bound to its own port, driven by nothing else"""
    driven = set(re.findall(rf"^\s*assign\s+({ID})\b", txt, re.M))
    for ln in re.findall(r"^\s*(?:ot_dp_\w+|ot_bind_native\w*)\b.*$", txt, re.M):
        for m in re.finditer(r"\.(?:q|eq|Y)\(([^()]*)\)", ln):
            driven.update(re.findall(ID, m.group(1)))
    return {e.strip(): inst for _, inst, p, e in pl if e.strip() == f"w_{inst[2:]}_{p}" and e.strip() not in driven}


def load_classes(receipt):
    r = json.loads(Path(receipt).read_text())
    cl = (r.get("kit_hbm_core_stations") or {}).get("classes") or (r.get("report") or {}).get("classes") or r.get("classes")
    pair = {}
    for c, v in cl.items():
        for lp in v["leaf_pairs"]:
            s, d = lp.split("->")
            if (s, d) in pair:
                raise SystemExit(f"leaf pair {lp} in two classes")
            pair[(s, d)] = (c, int(v["depth"]))
    return cl, pair


def analyse(orig, kit, pair):
    """TEXT check + per-line golden plan -> (problems, lines, chains)"""
    ol, kl = orig.split("\n"), kit.split("\n")
    probs = []
    mk = [i for i, x in enumerate(kl) if x.startswith(MARK)]
    if len(mk) > 1:
        probs.append("more than one station block")
    if mk:
        m = mk[0]
        e = next(i for i in range(m, len(kl)) if kl[i].startswith("endmodule"))
        block, kl2 = kl[m + 1:e], kl[:m] + kl[e:]
    else:
        block, kl2 = [], kl
    chains = {}
    for b in block:
        if b.startswith("    wire [") and "hcs_" in b:
            continue
        h = HCS.match(b)
        if not h:
            probs.append(f"unexpected station-block line: {b[:120]}")
            continue
        cm = re.search(r"// kit_hbm_cstations: (\S+)", b)
        chains[h.group(5)] = dict(W=int(h.group(1)), D=int(h.group(2)), inst=h.group(3), d=h.group(4), line=b,
                                  cls=cm.group(1) if cm else None)
    if len(kl2) != len(ol):
        probs.append(f"line count differs outside the station block: {len(kl2)} vs {len(ol)}")
        return probs, [], chains
    pl = leaf_lines(ol)
    own = owners(orig, pl)
    portline = {i: (inst, p, e) for i, inst, p, e in pl}
    changed = set()
    for i, (a, b) in enumerate(zip(ol, kl2)):
        if a == b:
            continue
        pa, pb = PORT.match(a), PORT.match(b)
        if i not in portline or not pb or (pa.group(1), pa.group(2), pa.group(4), pa.group(5)) != \
                (pb.group(1), pb.group(2), pb.group(4), pb.group(5)):
            probs.append(f"line {i + 1}: changed outside a leaf port connection")
            continue
        changed.add(i)
    lines = []
    for i, inst, p, e in pl:
        its = items_of(e)
        dl = []
        for k, it in enumerate(its):
            m = re.match(rf"^({ID})(?:\[[0-9:]+\])?$", it)
            src = own.get(m.group(1)) if m else None
            if src and src != inst and (src, inst) in pair:
                dl.append((k, pair[(src, inst)]))
        if dl and i not in changed:
            probs.append(f"line {i + 1} {inst}.{p}: stationed link left unregistered (missing stage)")
        if not dl and i in changed:
            probs.append(f"line {i + 1} {inst}.{p}: edited without a stationed link (extra stage)")
        if dl and i in changed:
            lines.append(dict(no=i, inst=inst, port=p, orig=e, kit=PORT.match(kl2[i]).group(3), delayed=dl))
    used = set()
    for L in lines:
        used.update(re.findall(r"\b(hcs_\d+)\b", L["kit"]))
    for w in sorted(set(chains) - used):
        probs.append(f"{chains[w]['inst']}: chain read by no port (dangling)")
    for w in sorted(used - set(chains)):
        probs.append(f"{w}: read but not in the station block")
    return probs, lines, chains


def vehicle(cls, lines, chains, D, cells, mutate=None):
    """miter text for one class; mutate = ('drop' | 'add', chain wire) changes one kit chain depth by -1 / +1"""
    sel = [L for L in lines if any(c == cls for _, (c, _) in L["delayed"])]
    ins = set()
    kw = sorted({w for L in sel for w in re.findall(r"\b(hcs_\d+)\b", L["kit"])}, key=lambda w: int(w[4:]))
    for L in sel:
        ins.update(x for x in re.findall(ID, L["orig"]) if x in D)
    for w in kw:
        ins.update(x for x in re.findall(ID, chains[w]["d"]) if x in D)
    ins = sorted(ins)
    ports = ", ".join(["input wire clk"] + [f"input wire [{D[x][0]}:{D[x][1]}] {x}" for x in ins] +
                      [f"output wire [{width(L['orig'], D) - 1}:0] o{n}" for n, L in enumerate(sel)])
    K = [f"module kitv({ports});"]
    for w in kw:
        c = chains[w]
        dd = c["D"] + (0 if not mutate or mutate[1] != w else (-1 if mutate[0] == "drop" else 1))
        K.append(f"  wire [{c['W'] - 1}:0] {w};")
        K.append(f"  ot_dp_dly #(.W({c['W']}), .D({dd})) {c['inst']} (.clk(clk), .d({c['d']}), .q({w}));" if dd > 0 else
                 f"  assign {w} = {c['d']};")
    for n, L in enumerate(sel):
        K.append(f"  assign o{n} = {L['kit']};")
    K.append("endmodule")
    G = [f"module goldv({ports});"]
    g = 0
    for n, L in enumerate(sel):
        its = items_of(L["orig"])
        flat = not L["orig"].strip().startswith("{")
        for k, (c, d) in L["delayed"]:
            w = width(its[k], D)
            regs = [f"g{g}_{j}" for j in range(d)]
            G.append(f"  reg [{w - 1}:0] " + ", ".join(regs) + ";")
            G.append("  always @(posedge clk) begin " + " ".join(
                f"{regs[j]} <= {its[k] if j == 0 else regs[j - 1]};" for j in range(d)) + " end")
            its[k] = regs[-1]
            g += 1
        G.append(f"  assign o{n} = {its[0] if flat else '{' + ', '.join(its) + '}'};")
    G.append("endmodule")
    conns = ", ".join([".clk(clk)"] + [f".{x}({x})" for x in ins])
    M = [f"module miter(input wire clk, " + ", ".join(f"input wire [{D[x][0]}:{D[x][1]}] {x}" for x in ins) + ", output wire trigger);"]
    for n, L in enumerate(sel):
        wd = width(L["orig"], D)
        M.append(f"  wire [{wd - 1}:0] k{n}, g{n};")
    M.append(f"  kitv uk ({conns}, " + ", ".join(f".o{n}(k{n})" for n in range(len(sel))) + ");")
    M.append(f"  goldv ug ({conns}, " + ", ".join(f".o{n}(g{n})" for n in range(len(sel))) + ");")
    M.append("  assign trigger = " + " | ".join(f"(k{n} != g{n})" for n in range(len(sel))) + ";")
    M.append("endmodule")
    depth = max([d for L in sel for _, (_, d) in L["delayed"]] + [1])
    return "\n".join([cells] + K + G + M) + "\n", kw, depth, len(sel)


YS = """read_verilog -sv miter.sv
hierarchy -check -top miter
proc; opt_clean; memory -nomap; memory_map; opt -fast; flatten; opt_clean
sat -verify -tempinduct -prove trigger 0 -set-init-zero -seq 1 -maxsteps {steps} miter
"""


def cells_text(path):
    t = Path(path).read_text()
    m = re.search(r"module ot_dp_dly\b.*?endmodule", t, re.S)
    if not m:
        raise SystemExit(f"{path}: no ot_dp_dly")
    return m.group(0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("orig"); ap.add_argument("kit"); ap.add_argument("receipt")
    ap.add_argument("--cells", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--classes", default=""); ap.add_argument("--run", action="store_true")
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    orig, kit = Path(a.orig).read_text(), Path(a.kit).read_text()
    cl, pair = load_classes(a.receipt)
    probs, lines, chains = analyse(orig, kit, pair)
    D = decls(orig)
    for w, c in chains.items():
        D[w] = (c["W"] - 1, 0)
    cells = cells_text(a.cells)
    want = [c for c in (a.classes.split(",") if a.classes else sorted(cl))]
    cases = []
    for ci, c in enumerate(want):
        base, kw, depth, n = vehicle(c, lines, chains, D, cells)
        if not n:
            probs.append(f"class {c}: no stationed port line in the kit")
            continue
        mine = [w for w in kw if chains[w]["cls"] == c]
        if not mine:
            probs.append(f"class {c}: no kit chain of the class")
            continue
        for mut in (None, ("drop", mine[0]), ("add", mine[0])):
            d = out / f"c{ci:03d}_{'base' if not mut else mut[0]}"
            d.mkdir(exist_ok=True)
            txt = base if not mut else vehicle(c, lines, chains, D, cells, mut)[0]
            (d / "miter.sv").write_text(txt)
            (d / "prove.ys").write_text(YS.format(steps=depth + 3))
            cases.append(dict(dir=d.name, cls=c, expect="PROVE" if not mut else "FAIL", depth=depth, lines=n,
                              mutate=list(mut) if mut else None))
    (out / "cases.json").write_text(json.dumps(dict(text_problems=probs, stationed_lines=len(lines), chains=len(chains),
                                                    cases=cases), indent=1))
    sh = ["#!/bin/bash", "# expect: base PROVED (rc 0), drop/add mutants FAILED (rc != 0)", 'Y=${YOSYS:-yosys}',
          'cd "$(dirname "$0")"', "J=${JOBS:-%d}" % a.jobs,
          # verdict from the log, not the rc alone: an OOM kill (137) or a parse error is UNRESOLVED, never a FAIL
          "one() { ( cd $1 && timeout ${CASE_TIMEOUT:-21600} $Y -q -l prove.log -s prove.ys >/dev/null 2>&1 ); r=$?; "
          "v=UNRESOLVED; grep -q 'Induction step proven: SUCCESS' $1/prove.log 2>/dev/null && [ $r -eq 0 ] && v=PROVED; "
          "grep -q 'model found for base case: FAIL' $1/prove.log 2>/dev/null && v=FAILED; echo \"$1 rc=$r $v\"; }",
          "export -f one; export Y",
          "ls -d ${CASES:-c[0-9]*_*} | xargs -P $J -I{} bash -c 'one {}' >> rc.txt",
          "python3 -I - <<'PY'", "import json", "C=json.load(open('cases.json'))",
          "rc={l.split()[0]:l.split()[2] for l in open('rc.txt') if len(l.split())>2}",   # last line per case wins
          "want={'PROVE':'PROVED','FAIL':'FAILED'}",
          "bad=[c['dir'] for c in C['cases'] if rc.get(c['dir'])!=want[c['expect']]]",
          "json.dump(dict(cases=len(C['cases']),bad=bad,text_problems=C['text_problems'],verdicts=rc),open('verdict.json','w'),indent=1)",
          "print('RESULT', 'PASS' if not bad and not C['text_problems'] else 'FAIL', len(C['cases']), 'cases', len(bad), 'bad')",
          "PY"]
    (out / "run.sh").write_text("\n".join(sh) + "\n")
    print(json.dumps(dict(text_problems=probs[:20], n_text_problems=len(probs), stationed_lines=len(lines),
                          chains=len(chains), cases=len(cases))))
    if a.run:
        r = subprocess.run(["bash", str(out / "run.sh")], capture_output=True, text=True)
        print(r.stdout[-2000:])
        return 0 if "RESULT PASS" in r.stdout else 1
    return 0 if not probs else 1


if __name__ == "__main__":
    sys.exit(main())
