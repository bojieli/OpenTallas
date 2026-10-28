#!/usr/bin/env python3
"""Per-type LEC of the R8 strap-pad banks the binder emits (OWNER 2026-10-28 KV R8 decision; bind.py
asbuilt.land_r8_strap_pads; METHODOLOGY 1.8 "LEC per master vs every constant variant").

    python3 tools/die_plan/r8_strap_lec.py BIND_OUT [--jobs N] [--timeout S] [--image IMG]
        BIND_OUT = the bind --out dir (bind_report.json, bind_parent_id_straps.json, rtl/<type module>.sv)
        -> BIND_OUT/r8_strap_lec/receipt.json; exit 0 only when every variant is EQUIVALENT and every mutant DECIDED

For every partition type with strap_r8pad_* pins and every distinct tie-value set its instances use:
  (1) STRUCTURE: the type module with its strap_r8pad_* port lines and ot_dp_dly_cnt bank lines removed must equal the
      same text with the bank lines of the parameter form removed, i.e. the strap master differs from the per-copy
      parameter form ONLY in the bank instances (checked once per type: the rest of the module is shared text);
  (2) LEC of those bank instances: gate = every ot_dp_dly_cnt of the type with its strap pin tied to the instance's
      manifest value; gold = ot_dp_dly #(D = pad - base) (wire for 0), pad = the instance's R8 landing pad as the bind
      report lists it (bind_report.r8_strap_sites, from the R8 table), so the tie value is checked against the table;
      yosys proc; memory_map; flatten; equiv_make; equiv_simple -seq; equiv_induct -seq; equiv_status -assert;
  (3) MUTANT per type: the first variant with one site's tie moved to another legal count must be DECIDED
      not-equivalent (unproven $equiv cells); a TIMEOUT / tool error is UNDECIDED, never caught.
"""
import argparse
import concurrent.futures
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANK_RE = re.compile(r"^\s*ot_dp_dly_cnt #\(\.W\((\d+)\), \.DMAX\((\d+)\)\) (\w+) \(\.clk\(clk\), "
                     r"\.strap_cnt\((strap_r8pad_\w+)\), \.d\(([^;]*?)\), \.q\((\w+)\)\);.*$", re.M)
PORT_RE = re.compile(r"^\s*input wire \[3:0\] (strap_r8pad_\w+)\b.*$", re.M)
INST_RE = re.compile(r"(?m)^\s*([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*([A-Za-z_]\w*)\s*\(")
DLY = """module ot_dp_dly #(parameter integer W = 1, parameter integer D = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [0:D-1];
    integer i;
    always @(posedge clk) begin
        r[0] <= d;
        for (i = 1; i < D; i = i + 1) r[i] <= r[i-1];
    end
    assign q = r[D-1];
endmodule
"""


def banks_of(text):
    return [dict(W=int(m[1]), DMAX=int(m[2]), inst=m[3], site=m[4], d=m[5], q=m[6]) for m in BANK_RE.finditer(text)]


def structure_ok(text):
    """(1): removing the strap port lines and the bank lines leaves the module the parameter form also has"""
    stripped = re.sub(r"//[^\n]*", "", PORT_RE.sub("", BANK_RE.sub("", text)))
    # no other use of a strap pin (the bank output wires r8b_strap_r8pad_* are ordinary names)
    return "ot_dp_dly_cnt" not in stripped and not re.search(r"(?<!\w)strap_r8pad_\w+", stripped)


def harness(tn, banks, gold, ties, tag):
    """gold/gate modules over the type's banks only; inputs/outputs = per-bank d/q vectors.
    gold {site: count} = ot_dp_dly #(D = count) (wire for 0); ties {site: value} = the gate's strap constants"""
    ins = ",\n".join(f"    input wire [{b['W'] - 1}:0] d{k}" for k, b in enumerate(banks))
    outs = ",\n".join(f"    output wire [{b['W'] - 1}:0] q{k}" for k, b in enumerate(banks))
    hdr = f"(\n    input wire clk,\n{ins},\n{outs}\n);\n"
    txt = f"// {tn} {tag}\nmodule gold {hdr}"
    for k, b in enumerate(banks):
        c = gold[b["site"]]
        txt += (f"    assign q{k} = d{k};\n" if c == 0 else
                f"    ot_dp_dly #(.W({b['W']}), .D({c})) u{k} (.clk(clk), .d(d{k}), .q(q{k}));\n")
    txt += f"endmodule\nmodule gate {hdr}"
    for k, b in enumerate(banks):
        txt += (f"    wire [3:0] t{k} = 4'd{ties[b['site']]};\n"
                f"    ot_dp_dly_cnt #(.W({b['W']}), .DMAX({b['DMAX']})) u{k} (.clk(clk), .strap_cnt(t{k}), "
                f".d(d{k}), .q(q{k}));\n")
    return txt + "endmodule\n"


def run(job, out, image, timeout):
    tag, txt, seq = job["tag"], job["text"], job["seq"]
    (out / f"{tag}.sv").write_text(txt)
    script = (f"read_verilog -sv /work/dly.sv /work/bank.sv /work/{tag}.sv; hierarchy -check; proc; memory_map; "
              f"setattr -mod -unset keep_hierarchy; flatten gold gate; opt_clean; equiv_make gold gate equiv; "
              f"hierarchy -top equiv; equiv_simple -seq {seq}; equiv_induct -seq {seq + 1}; equiv_status -assert")
    cmd = ["docker", "run", "--rm", "--memory=4g", "--cpus=1", "-v", f"{out}:/work", "-w", "/work", image, "bash", "-lc",
           'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec yosys -Q -T -p "$1"', "bash", script]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        log, rc = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        log, rc = "TIMEOUT", 124
    (out / f"{tag}.log").write_text(log)
    proven = rc == 0 and "Equivalence successfully proven" in log
    m = re.findall(r"ERROR: Found (\d+) unproven \$equiv cells", log)
    decided_diff = rc not in (0, 124) and bool(m) and int(m[-1]) > 0
    ok = proven if job["kind"] == "eq" else decided_diff
    return dict({k: v for k, v in job.items() if k != "text"}, rc=rc, proven=proven,
                unproven=int(m[-1]) if m else None, timeout=rc == 124, pass_=ok,
                undecided=not proven and not decided_diff)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bind_out")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--image", default="openroad/orfs:asap7lock")
    a = ap.parse_args(argv)
    bo = Path(a.bind_out).resolve()
    rep = json.loads((bo / "bind_report.json").read_text())
    man = json.loads((bo / "bind_parent_id_straps.json").read_text())
    sites = rep["r8_strap_sites"]["list"]
    top = next((bo / "rtl").glob("*_bound_top.sv")).read_text()
    inst_mod = {m[2]: m[1] for m in INST_RE.finditer(top)}
    out = bo / "r8_strap_lec"
    out.mkdir(exist_ok=True)
    (out / "dly.sv").write_text(DLY)
    (out / "bank.sv").write_text((ROOT / "rtl/common/ot_dp_dly_cnt.sv").read_text())
    jobs, structure = [], {}
    for tn, ports in sorted(man["types"].items()):
        r8 = sorted(p for p, d in ports.items() if d.get("kind") == "r8pad_strap")
        if not r8:
            continue
        base_tn = tn if tn in sites else rep["types"][tn].get("split_of") if tn in rep["types"] else None
        if base_tn not in sites:
            base_tn = next((x for x in sites if tn.startswith(x + "__v")), None)
        mod = rep["types"][tn]["module"]
        text = (bo / "rtl" / f"{mod}.sv").read_text()
        banks = banks_of(text)
        structure[tn] = dict(module=mod, banks=len(banks), sites=len(r8), ok=structure_ok(text)
                             and {b["site"] for b in banks} == set(r8))
        insts = sorted(i for i, m in inst_mod.items() if m == mod)
        variants = {}
        for i in insts:
            ties = {sp: man["instances"][i][sp]["value"] for sp in r8}
            # gold count from the R8 table pad (bind report), independent of the tie the binder wrote
            gold = {sp: sites[base_tn][sp]["pads"][i] - sites[base_tn][sp]["base"] for sp in r8}
            key = json.dumps([ties, gold], sort_keys=True)
            variants.setdefault(key, dict(ties=ties, gold=gold, instances=[]))["instances"].append(i)
        seq = max(b["DMAX"] for b in banks) + 1
        for k, (key, v) in enumerate(sorted(variants.items())):
            txt = harness(tn, banks, v["gold"], v["ties"], f"variant {k} instances {v['instances']}")
            jobs.append(dict(tag=f"{mod}_v{k}_eq", type=tn, module=mod, kind="eq", ties=v["ties"], gold=v["gold"],
                             instances=v["instances"], seq=seq, text=txt))
            if k == 0:
                b0 = banks[0]
                bad = dict(v["ties"])
                bad[b0["site"]] = bad[b0["site"]] + 1 if bad[b0["site"]] + 1 <= b0["DMAX"] else bad[b0["site"]] - 1
                jobs.append(dict(tag=f"{mod}_v{k}_mutant", type=tn, module=mod, kind="mutant", ties=bad,
                                 gold=v["gold"], instances=v["instances"], seq=seq,
                                 text=harness(tn, banks, v["gold"], bad, f"MUTANT of variant {k}")))
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda j: run(j, out, a.image, a.timeout), jobs))
    eq = [r for r in rows if r["kind"] == "eq"]
    mu = [r for r in rows if r["kind"] == "mutant"]
    ok = all(r["pass_"] for r in rows) and all(s["ok"] for s in structure.values()) and bool(rows)
    res = dict(schema="opentallas.r8_strap_type_lec.v1", bind=str(bo), types=len(structure), structure=structure,
               variants=len(eq), equivalent=sum(r["pass_"] for r in eq), mutants=len(mu),
               mutants_caught=sum(r["pass_"] for r in mu), undecided=sum(r["undecided"] for r in rows),
               verdict="PASS" if ok else "FAIL", rows=rows)
    (out / "receipt.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k not in ("rows", "structure")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
