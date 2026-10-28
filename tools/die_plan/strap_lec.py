#!/usr/bin/env python3
"""LEC of the count-strap form (MESO-STRAP-1, OWNER 12.15a; METHODOLOGY 1.8 "LEC per master vs every constant variant").

    python3 tools/die_plan/strap_lec.py LANDED_PLAN.json --landing SIDECAR.json --rtl-root ROOT --out DIR
            [--types T1,T2] [--mutant] [--image IMG]          # exit 0 every variant EQUIVALENT, 1 otherwise

One hard-core type per design: the strap master (clock_landings strap form: ot_dp_clk_landing_cas / ot_dp_landing_origin_s,
K / PAD / EDGE_FALL / tree select / root on strap_ca_* input pins) is compared, for EVERY distinct tie-value set the die
uses (count_align_bind.strap_ties variants), against the parameter form of one copy with that set (the per-copy
Verilog-parameter wrapper the binder emitted before 12.15a: ot_dp_clk_landing_ca #(.K) / ot_dp_landing_origin #(.PAD,
.EDGE_FALL), clock_landings.Landings(ca_variants=True).type_rtl(inst=copy), ring DEPTH = the master's).

  gold  parameter wrapper of the representative copy (module <mod>__ref), each ring with the strap master's ready
        TIMEOUT (the one intended difference: the strap ring's timeout covers every K residue, 2^KW - 1 counts
        instead of max(K,0); a fault-timing-only change at bring-up, data path and arming are compared as is);
  gate  the strap master with its strap_ca_* input pins replaced by the variant's constants (module <mod>__tied): the
        tie cells the parent places, nothing else changed;
  both  are the SAME generated wrapper text (gen_rtl.wrapper of the plan type) before the landing insertion, so the
        leaf cores are identical instances on both sides: read as black boxes (read_verilog -lib of the type's
        sources; equiv_make merges identical black-box cells and compares their inputs);
  check yosys proc; flatten; async2sync; opt -full (constant propagation of the ties); equiv_make ref tied;
        equiv_struct; equiv_simple; equiv_induct; equiv_status -assert (key-point / register-correspondence LEC by
        name, sequential induction; every $equiv proved -> EQUIVALENT).
  --mutant  also runs the first variant of each type with one tie bit flipped (lowest bit of the first strap): it must NOT be equivalent
        (the LEC sees a wrong constant; the tie-VALUE audit in straps.py is the G0 check of the die top / netlist).
Writes DIR/strap_lec.json {variants: [...], verdict}.  yosys from PATH, else docker IMG (default openroad/orfs:asap7lock).
"""
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landings as CL  # noqa: E402
import gen_rtl as GR  # noqa: E402
import schema as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
COMMON = ["rtl/common/ot_meso_fifo.sv", "rtl/common/ot_dp_clk_landing.sv", "rtl/common/ot_dp_clk_landing_ca.sv"]
YOSYS_DOCKER = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"
# the ASAP7 cells gen_rtl.CELLS instantiates (BUFx4f relay drivers): black boxes, identical on both sides
CELL_TYPES = ["BUFx4f_ASAP7_75t_R"]
CELL_LIBS = ["/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz"]
STRAP_DECL = re.compile(r",\n\s*input\s+wire\s+(?:\[(\d+):0\]\s+)?(strap_ca_\w+)")


def tie_module(text, mod, values, new):
    """the strap master with each strap_ca_* input pin replaced by its constant (module renamed `new`)"""
    seen = {}

    def drop(m):
        seen[m.group(2)] = int(m.group(1)) + 1 if m.group(1) else 1
        return ""
    head, body = text.split("\n);\n", 1)
    head = STRAP_DECL.sub(drop, head)
    if set(seen) != set(values):
        raise ValueError(f"{mod}: strap pins {sorted(seen)} != tie values {sorted(values)}")
    ties = [f"    wire [{w - 1}:0] {sp} = {w}'b{int(values[sp]) % (1 << w):0{w}b};" for sp, w in sorted(seen.items())]
    head = re.sub(r"\bmodule\s+" + re.escape(mod) + r"\b", f"module {new}", head, count=1)
    return head + "\n);\n" + "\n".join(ties) + "\n" + body.replace(f"endmodule : {mod}", f"endmodule : {new}")


INST_RE = re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*([A-Za-z_]\w*)\s*\(")
KEYWORDS = {"module", "input", "output", "inout", "wire", "logic", "reg", "assign", "always", "if", "else", "for",
            "case", "begin", "end", "function", "task", "generate", "initial", "localparam", "parameter"}


def header_end(text, i):
    """index after the `);` that closes the ANSI header starting at text[i] (`module ...`)"""
    j = text.index("(", i)
    if text[i:j].rstrip().endswith("#"):
        depth, k = 0, j
        while True:
            depth += text[k] == "("
            depth -= text[k] == ")"
            k += 1
            if depth == 0:
                break
        j = text.index("(", k)
    depth, k = 0, j
    while True:
        depth += text[k] == "("
        depth -= text[k] == ")"
        k += 1
        if depth == 0:
            break
    return text.index(";", k) + 1


def leaf_stubs(base, sources_text, defined=()):
    """(* blackbox *) stubs (ANSI header only, parameters kept) of the leaf modules the wrapper instantiates: the leaf
    cores are the same instances on both sides, so only their pins matter (equiv_make merges identical cells)"""
    mods = sorted({m.group(1) for m in INST_RE.finditer(base.split("\n);\n", 1)[1])} - KEYWORDS - set(defined))
    out, missing = [], []
    for m in mods:
        h = re.search(r"\bmodule\s+" + re.escape(m) + r"\b", sources_text)
        if not h:
            missing.append(m)
            continue
        out.append("(* blackbox *)\n" + sources_text[h.start():header_end(sources_text, h.start())] + "\nendmodule\n")
    return "\n".join(out), missing, [m for m in mods if m not in missing]


def strap_timeout(depth):
    """ot_dp_clk_landing_cas default TIMEOUT: covers every K residue (the parameter form's max(K,0) term -> 2^KW - 1)"""
    return (1 << (depth.bit_length() - 1 + 4)) - 1 + (2 * depth + 4) + 2 * depth + 8


def ref_timeout(text):
    """the reference rings get the strap master's TIMEOUT (the ONE intended difference of the strap form: the ready
    timeout cannot depend on K any more, so it covers the largest K; everything else must be identical)"""
    def sub(m):
        return m.group(0)[:-1] + f", .TIMEOUT({strap_timeout(int(m.group(1)))}))"
    return re.sub(r"ot_dp_clk_landing_ca #\(\.W\(\d+\), \.DEPTH\((\d+)\), \.K\(-?\d+\)\)", sub, text)


def rename(text, mod, new):
    text = re.sub(r"\bmodule\s+" + re.escape(mod) + r"\b", f"module {new}", text, count=1)
    return text.replace(f"endmodule : {mod}", f"endmodule : {new}")


def variants(st, tn):
    """[(values, [instances])] per distinct tie-value set of type tn (count_align_bind.strap_ties instances)"""
    g = {}
    for q, v in sorted(st["instances"].items()):
        if v["type"] == tn:
            g.setdefault(json.dumps(v["values"], sort_keys=True), []).append(q)
    return [(json.loads(k), qs) for k, qs in sorted(g.items())]


def yosys_cmd(script, work, image, paths=()):
    y = shutil.which("yosys")
    if y:
        return [y, "-q", "-s", str(script)]
    uid = f"{os.getuid()}:{os.getgid()}"
    vols = sorted({str(work)} | {str(Path(p).resolve().parent) for p in paths})
    cmd = ["docker", "run", "--rm", "-m", "8g", "--user", uid]
    for v in vols:
        cmd += ["-v", f"{v}:{v}"]
    return cmd + ["-w", str(work), image, YOSYS_DOCKER, "-q", "-s", str(script)]


def run_lec(work, files, libs, gold, gate, seq, image, timeout, leaves=()):
    work.mkdir(parents=True, exist_ok=True)
    ys = [f"read_liberty -lib -ignore_miss_func {f}" for f in CELL_LIBS] + \
        [f"read_verilog -sv {f}" for f in libs + files] + [
        "hierarchy -check", "proc", "setattr -mod -unset keep_hierarchy *", f"flatten {gold} {gate}", "memory",
        # black-box leaf cells: their input pins become compare points and their output pins shared free inputs
        ("expose -evert " + " ".join(f"{m}/t:{c}" for m in (gold, gate) for c in list(leaves) + CELL_TYPES))
        if list(leaves) + CELL_TYPES else "", "setundef -undriven -expose", "async2sync", "opt -full", "opt_clean -purge",
        f"equiv_make {gold} {gate} lec_eq", "hierarchy -top lec_eq", "async2sync",
        "equiv_struct", "equiv_simple" + (f" -seq {seq}" if seq > 1 else ""), "equiv_induct", "equiv_status -assert"]
    script = work / "lec.ys"
    script.write_text("\n".join(x for x in ys if x) + "\n")
    log = work / "lec.log"
    try:
        r = subprocess.run(yosys_cmd(script, work, image, list(files) + list(libs)), cwd=work, capture_output=True, text=True, timeout=timeout)
        out = r.stdout + r.stderr
        rc = r.returncode
    except subprocess.TimeoutExpired:
        out, rc = "TIMEOUT", 124
    log.write_text(out)
    unproven = re.findall(r"Found (\d+) unproven \$equiv cells", out)
    ok = rc == 0 and "ERROR" not in out
    return dict(equivalent=ok, rc=rc, unproven=int(unproven[-1]) if unproven else None,
                error=None if ok else (re.findall(r"ERROR:.*", out) or [out[-300:]])[-1][:300], log=str(log))


def lec_type(Ls, Lp, tn, mod, base, libs, common, out, seq=1, image="openroad/orfs:asap7lock", timeout=3600,
             mutant=False, max_variants=0, jobs=1, run=True):
    """LEC rows of plan type tn (module mod, generated wrapper text `base` before the landing insertion): strap master
    tied to each variant's values vs the parameter wrapper of the variant's first copy (+ one flipped-bit mutant)"""
    st = Ls.strap
    info = st["types"][tn]
    master = Ls.type_rtl(tn, base)
    depth = {b: v["depth"] for b, v in info["buses"].items()}
    defined = set(re.findall(r"(?m)^\s*module\s+(\w+)", GR.CELLS))
    for f in common:
        defined |= set(re.findall(r"(?m)^\s*module\s+(\w+)", Path(f).read_text()))
    stubs, missing, leaves = leaf_stubs(base, "\n".join(Path(f).read_text(errors="replace") for f in libs), defined)
    if missing:
        raise SystemExit(f"strap_lec {tn}: leaf module(s) {missing} not found in the type sources")
    vs = variants(st, tn)
    if max_variants:
        vs = vs[:max_variants]
    jobs_in = []
    for i, (vals, qs) in enumerate(vs):
        ref = rename(ref_timeout(Lp.type_rtl(tn, base, inst=qs[0], depth=depth)), mod, f"{mod}__ref")
        cases = [("eq", vals)]
        if mutant and i == 0:
            # one flipped tie bit (lowest bit of the first strap) on the first variant: must NOT be equivalent
            k0 = sorted(vals)[0]
            cases.append(("mutant", dict(vals, **{k0: int(vals[k0]) ^ 1})))
        for kind, vv in cases:
            w = Path(out) / f"{tn}__v{i}_{kind}"
            w.mkdir(parents=True, exist_ok=True)
            (w / "ref.sv").write_text(ref)
            (w / "tied.sv").write_text(tie_module(master, mod, vv, f"{mod}__tied"))
            (w / "cells.sv").write_text(GR.CELLS)
            (w / "leaf_stubs.sv").write_text(stubs)
            jobs_in.append((i, kind, vv, qs, w))

    if not run:
        return [(tn, mod, common, seq, image, timeout, leaves) + j for j in jobs_in]
    return run_jobs([(tn, mod, common, seq, image, timeout, leaves) + j for j in jobs_in], jobs)


def run_jobs(all_jobs, jobs=1):
    """run prepared LEC jobs (lec_type(run=False)) in a pool of `jobs` parallel yosys runs"""
    def one(j):
        tn, mod, common, seq, image, timeout, leaves, i, kind, vv, qs, w = j
        r = run_lec(w, [str(w / "cells.sv")] + list(common) + [str(w / "ref.sv"), str(w / "tied.sv")],
                    [str(w / "leaf_stubs.sv")], f"{mod}__ref", f"{mod}__tied", seq, image, timeout, leaves)
        r.update(type=tn, variant=i, kind=kind, values=vv, copies=len(qs), representative=qs[0])
        # a mutant is CAUGHT only on a decided difference (equiv_status reports unproven cells); a TIMEOUT or any other
        # error decides nothing and is UNDECIDED, never a pass (DIE-KV-7: 6 KV mutant timeouts had been counted caught)
        r["timeout"] = r["rc"] == 124
        caught = (not r["equivalent"]) and not r["timeout"] and bool(r["unproven"])
        r["pass"] = r["equivalent"] if kind == "eq" else caught
        r["undecided"] = r["timeout"] or (kind == "mutant" and not r["equivalent"] and not caught)
        print(f"{tn} v{i} {kind} copies={len(qs)} rep={qs[0]} equivalent={r['equivalent']} "
              f"pass={r['pass']}{' UNDECIDED' if r['undecided'] else ''} {r['error'] or ''}", flush=True)
        return r
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max(1, jobs)) as ex:
        rows = list(ex.map(one, all_jobs))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--landing", required=True, help="clock_landing_plan sidecar with count_aligned.strap_form")
    ap.add_argument("--rtl-root", default=str(ROOT))
    ap.add_argument("--out", required=True)
    ap.add_argument("--types", help="comma list of plan types (default: every type with count straps)")
    ap.add_argument("--max-variants", type=int, default=0, help="0 = every variant")
    ap.add_argument("--mutant", action="store_true")
    ap.add_argument("--seq", type=int, default=1, help="equiv_simple -seq (1 = combinational key points; equiv_induct proves the rest)")
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--image", default="openroad/orfs:asap7lock")
    ap.add_argument("--jobs", type=int, default=1, help="parallel yosys runs per type")
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    side = json.load(open(a.landing))
    if not (side.get("count_aligned") or {}).get("strap_form"):
        raise SystemExit("strap_lec: the sidecar is not in the strap form (count_aligned.strap_form)")
    P = S.Plan(raw, a.plan)
    ep = GR.bus_epochs(P)
    Ls = CL.Landings(raw, side)
    sp = copy.deepcopy(side)
    sp["count_aligned"]["strap_form"] = False
    Lp = CL.Landings(raw, sp, ca_variants=True)
    st = Ls.strap
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    want = a.types.split(",") if a.types else sorted(t for t, v in st["types"].items() if v["straps"])
    common = [str(Path(a.rtl_root) / f) for f in COMMON]
    prepared = []
    for tn in want:
        t = P.types[tn]
        prepared += lec_type(Ls, Lp, tn, t["module"], GR.wrapper(P, tn, ep, a.rtl_root),
                         [str(Path(a.rtl_root) / f) for f in t.get("sources", [])], common, out, seq=a.seq,
                         image=a.image, timeout=a.timeout, mutant=a.mutant, max_variants=a.max_variants,
                         run=False)
    rows = run_jobs(prepared, a.jobs)
    eq = [r for r in rows if r["kind"] == "eq"]
    rep = dict(schema="opentallas.strap_lec.v1", plan=a.plan, landing=a.landing, types=want,
               variants=len(eq), equivalent=sum(r["equivalent"] for r in eq),
               mutants=sum(r["kind"] == "mutant" for r in rows),
               mutants_caught=sum(r["kind"] == "mutant" and r["pass"] for r in rows),
               verdict="PASS" if rows and all(r["pass"] for r in rows) else "FAIL", rows=rows)
    (out / "strap_lec.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "rows"}))
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
