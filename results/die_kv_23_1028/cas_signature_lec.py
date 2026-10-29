#!/usr/bin/env python3
"""Prove the real CA strap leaf at each used (width, depth, K) signature.

The independent native binder checks composition and parent tie values. This
proof compares the unmodified actual CAS leaf with its constant-parameter CA
form; it does not invent leaf bindings for packed native buses.
"""
import argparse
import concurrent.futures
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import strap_lec as SL
# These RTL leaves instantiate no standard cells. Avoid the generic wrapper
# harness's optional ASAP7 relay library, which is only present inside ORFS.
SL.CELL_LIBS = []
SL.CELL_TYPES = []


def wrapper(name, w, depth, k, strap):
    kw = depth.bit_length() - 1 + 4
    params = f".W({w}), .DEPTH({depth})"
    if not strap:
        params += f", .K({k}), .TIMEOUT({SL.strap_timeout(depth)})"
    strap_port = f".strap_k({kw}'d{k % (1 << kw)})," if strap else ""
    return f"""module {name}(input fclk,t_rst_n,clk,rst_n,
 input [{w-1}:0] d,output [{w-1}:0] q,output ready,fault);
 ot_dp_clk_landing_ca{'s' if strap else ''} #({params}) u (
 .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(rst_n),
 {strap_port}
 .d(d),.q(q),.ready(ready),.fault(fault));
endmodule
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan")
    ap.add_argument("straps")
    ap.add_argument("out")
    ap.add_argument("--bound-rtl", required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--max-signatures", type=int, default=0)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    straps = json.load(open(a.straps))
    # Strap inventory is emitted by the real event. Each type bus declares its
    # own production width, including epoch, and its fixed ring depth.
    rawtypes = plan["partition_types"]
    types = {t["name"]: t for t in rawtypes} if isinstance(rawtypes, list) else rawtypes
    signatures = {}
    for inst, row in straps["instances"].items():
        tn = row["type"]
        typ = types[tn]
        actual = (Path(a.bound_rtl) / (typ["module"] + ".sv")).read_text()
        cells = re.findall(r"ot_dp_clk_landing_cas\s*#\((.*?)\)\s+\w+\s*\((.*?)\);", actual, re.S)
        buses = {}
        for pars, ports in cells:
            w = re.search(r"\.W\((\d+)\)", pars)
            depth = re.search(r"\.DEPTH\((\d+)\)", pars)
            strap = re.search(r"\.strap_k\(strap_ca_k_(\w+)\)", ports)
            if not (w and depth and strap):
                raise ValueError("non-canonical actual CAS instance")
            buses[strap[1]] = (int(w[1]), int(depth[1]))
        for bn, spec in straps["types"][tn]["buses"].items():
            w, depth = buses[bn]
            assert depth == int(spec["depth"])
            key = (w, depth, int(row["K"][bn]))
            signatures.setdefault(key, []).append([inst, bn])
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    common = [str(ROOT / f) for f in SL.COMMON]
    def one(item):
        (w, depth, k), uses, mutant = item
        work = out / (f"w{w}_d{depth}_k{k}" + ("_mutant" if mutant else ""))
        work.mkdir(exist_ok=True)
        src = work / "wrappers.sv"
        src.write_text(wrapper("gold", w, depth, k, False) + wrapper("gate", w, depth, k + int(mutant), True))
        r = SL.run_lec(work, common + [str(src)], [], "gold", "gate", 1,
                       "openroad/orfs:asap7lock", None)
        caught = r["rc"] != 0 and bool(r["unproven"])
        r.update(width=w, depth=depth, k=k, uses=uses, mutant=mutant,
                 passed=caught if mutant else r["equivalent"])
        (work / "receipt.json").write_text(json.dumps(r, indent=1) + "\n")
        print(w, depth, k, "mutant" if mutant else "nominal", r["passed"], flush=True)
        return r
    items = [(key, uses, False) for key, uses in sorted(signatures.items())]
    if a.max_signatures:
        items = items[:a.max_signatures]
    for depth in sorted({k[1] for k in signatures}):
        key = min(k for k in signatures if k[1] == depth)
        items.append((key, signatures[key], True))
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as pool:
        rows = list(pool.map(one, items))
    rep = dict(scope="actual CAS leaves, all used full-width signatures; composition independently bound",
               signatures=sum(not r["mutant"] for r in rows),
               equivalent=sum(r["equivalent"] for r in rows if not r["mutant"]),
               mutants_caught=sum(r["mutant"] and r["passed"] for r in rows), rows=rows)
    (out / "receipt.json").write_text(json.dumps(rep, indent=1) + "\n")
    return 0 if rows and all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
