#!/usr/bin/env python3
"""Actual used origin-strap constants versus the parameter origin leaf."""
import argparse
import concurrent.futures
import json
from pathlib import Path
from cas_signature_lec import ROOT, SL


def wrapper(name, pw, pad, fall, strap):
    params = f".PADW({pw})" if strap else f".PAD({pad}),.EDGE_FALL({fall})"
    ports = f".strap_pad({pw}'d{pad}),.strap_efall(1'b{fall})," if strap else ""
    return f"""module {name}(input clk,rst_raw_n,p_start,output start);
ot_dp_landing_origin{'_s' if strap else ''} #({params}) u (
.clk(clk),.rst_raw_n(rst_raw_n),.p_start(p_start),{ports}.start(start));
endmodule
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("straps")
    ap.add_argument("out")
    a = ap.parse_args()
    s = json.load(open(a.straps))
    signatures = {}
    for inst, row in s["instances"].items():
        origin = s["types"][row["type"]]["origin"]
        if origin.get("form") != "strap":
            continue
        vals = row["values"]
        key = (origin["padw"], vals["strap_ca_pad"], vals["strap_ca_efall"])
        signatures.setdefault(key, []).append(inst)
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    items = [(k, uses, False) for k, uses in sorted(signatures.items())]
    k = min(signatures)
    items.append((k, signatures[k], True))
    def one(item):
        (pw, pad, fall), uses, mutant = item
        d = out / (f"pw{pw}_p{pad}_f{fall}" + ("_mutant" if mutant else ""))
        d.mkdir(exist_ok=True)
        src = d / "wrappers.sv"
        src.write_text(wrapper("gold", pw, pad, fall, False) + wrapper("gate", pw, pad, fall ^ mutant, True))
        r = SL.run_lec(d, [str(ROOT / f) for f in SL.COMMON] + [str(src)], [],
                       "gold", "gate", 1, "openroad/orfs:asap7lock", None)
        r.update(padw=pw, pad=pad, fall=fall, uses=uses, mutant=mutant,
                 passed=(r["rc"] != 0 and bool(r["unproven"])) if mutant else r["equivalent"])
        (d / "receipt.json").write_text(json.dumps(r, indent=1) + "\n")
        print(pw, pad, fall, mutant, r["passed"], flush=True)
        return r
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        rows = list(pool.map(one, items))
    rep = dict(signatures=len(signatures), equivalent=sum(not r["mutant"] and r["passed"] for r in rows),
               mutants_caught=sum(r["mutant"] and r["passed"] for r in rows), rows=rows)
    (out / "receipt.json").write_text(json.dumps(rep, indent=1) + "\n")
    return 0 if rows and all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
