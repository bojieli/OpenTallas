#!/usr/bin/env python3
"""CPU-only audit of completed QC-NAM core; never a full verdict/finalizer.

Execute only the original pinned NumPy stability functions (no Torch imports),
then independently recompute integer-count selection and finite/saturation
checks. Core-dependent universal failures cannot be diluted by later lanes.
"""
import ast
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import warnings

import numpy as np
import qcnam_finalize_guard as G

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/quality/qcnam_completed_core_audit_20261001.json"


def safe(x):
    if isinstance(x, dict):
        return {k: safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [safe(v) for v in x]
    if isinstance(x, (np.integer, np.floating)):
        return safe(x.item())
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    return x


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT, help="new immutable audit output; never a full verdict")
    args=parser.parse_args()
    observation = json.loads((ROOT / "results/quality/qcnam_orchestration_observation.json").read_text())
    assert G.source_identity() == observation["source_sha256"]
    core = G.RUNS / "core"
    G.completed(core)
    hashes = {n: G.digest(core / n) for n in ("run.json", "raw.json", "status", "log.txt")}
    rec, raw = json.loads((core / "run.json").read_text()), json.loads((core / "raw.json").read_text())
    G.validate_run("core", rec, raw, [])
    pin_path = G.WT / "tools/deepseek_v41_nam_quality.py"
    source = pin_path.read_bytes()
    assert source == subprocess.check_output(["git", "show", G.PIN + ":tools/deepseek_v41_nam_quality.py"], cwd=ROOT)
    names = {"_load_run", "_by_position", "_growth", "_growth_ctx", "_ratio", "_every", "_sum_layers", "stability"}
    selected = []
    for n in ast.parse(source).body:
        if isinstance(n, ast.FunctionDef) and n.name in names:
            selected.append(n)
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("POS_EDGES", "STABILITY_RULE") for t in n.targets):
            selected.append(n)
    namespace = dict(np=np, math=math, Path=Path, json=json)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(pin_path), "exec"), namespace)
    with warnings.catch_warnings(record=True) as observed_warnings:
        warnings.simplefilter("always")
        criteria = namespace["stability"]({"core": namespace["_load_run"](core)})
    rule = namespace["STABILITY_RULE"]
    limit = Fraction(str(rule["X_RATIO_MAX"]))
    independent = {}
    witnesses = []

    finite_events = 0
    finite_checks = 0
    saturation = {"b": {}, "b_nam": {}}
    for l in rec["layers"]:
        for mode in ("b_nam", "b_nam_tf"):
            for category, keys in (("quant", ("nan_in", "inf_in", "nan_out", "inf_out")),
                                   ("mv", ("nan_in", "inf_in", "nan_out", "inf_out")),
                                   ("norm", ("nan", "inf"))):
                for d in l["instr"][mode][category].values():
                    finite_events += sum(int(d[k]) for k in keys)
                    finite_checks += 1
        for mode in saturation:
            for site,d in l["instr"][mode]["quant"].items():
                saturation[mode][site]=saturation[mode].get(site,0)+int(d["saturated"])
    for category,keys in (("mv",("nan_in","inf_in","nan_out","inf_out")),("norm",("nan","inf"))):
        for d in rec["head_instr"]["b_nam"][category].values():
            finite_events += sum(int(d[k]) for k in keys)
            finite_checks += 1
    finite_events += sum(int(r["nan_logits"])+int(r["inf_logits"]) for r in raw["b_nam"])
    finite_checks += 1
    assert finite_checks == criteria["S1_no_nan_inf"]["checks"]
    assert (finite_events==0) == criteria["S1_no_nan_inf"]["pass"]
    saturation_totals={m:sum(s.values()) for m,s in saturation.items()}
    assert saturation_totals==criteria["S2_saturation_not_above_b"]["saturated_total"]
    saturation_pass=all(saturation["b_nam"].get(s,0)<=saturation["b"].get(s,0)
                        for s in set(saturation["b_nam"])|set(saturation["b"]))
    saturation_pass &= saturation_totals["b_nam"]<=saturation_totals["b"]
    assert saturation_pass==criteria["S2_saturation_not_above_b"]["pass"]

    # Every-layer ratios from integer events; compare exact fractions with 1.10.
    for mode, base in (("b_nam", "b"), ("b_nam_tf", "b_tf")):
        for key, count, total in (("router", "tokens_with_flip", "tokens"),
                                  ("index", "queries_with_diff", "queries")):
            failures = []
            for l in rec["layers"]:
                if mode not in l[key]:
                    continue
                n, b = l[key][mode], l[key][base]
                assert abs(n[count] / n[total] - n["flip_rate" if key == "router" else "query_flip_rate"]) < 1e-12
                assert abs(b[count] / b[total] - b["flip_rate" if key == "router" else "query_flip_rate"]) < 1e-12
                ratio = Fraction(n[count], n[total]) / Fraction(b[count], b[total]) if b[count] else (Fraction(1) if n[count] == 0 else math.inf)
                if ratio > limit:
                    failures.append(dict(layer=l["layer"], mode=mode, baseline=base,
                        numerator=dict(events=n[count], samples=n[total]), denominator=dict(events=b[count], samples=b[total]),
                        ratio=float(ratio), exact_ratio=str(ratio)))
            label=f"core.{key}.{mode}/{base}"
            assert bool(failures) == criteria["S3b_not_above_contract_every_layer"]["tests"][label]["fails"]
            independent[label] = dict(failure_layers=len(failures), witnesses=failures)
            if failures:
                witnesses.append(dict(criterion="S3b", metric=key, **max(failures, key=lambda x: x["ratio"])))

    # Position buckets: sum event/sample integers, exclude BOS, enforce 500.
    edges = namespace["POS_EDGES"]
    for mode, base in (("b_nam", "b"), ("b_nam_tf", "b_tf")):
        for key, total in (("router_by_pos", "tokens"), ("index_by_pos", "queries")):
            sums = {m: dict(events=[0]*9, samples=[0]*9) for m in (mode, base)}
            for l in rec["layers"]:
                for m in (mode, base):
                    if m in l[key]:
                        for k in range(9):
                            sums[m]["events"][k] += l[key][m]["flips"][k]
                            sums[m]["samples"][k] += l[key][m][total][k]
            failures = []
            for k in range(1, 9):
                nn, bn = sums[mode]["samples"][k], sums[base]["samples"][k]
                if min(nn, bn) < rule["min_bucket_samples"]:
                    continue
                nf, bf = sums[mode]["events"][k], sums[base]["events"][k]
                ratio = Fraction(nf, nn) / Fraction(bf, bn) if bf else (Fraction(1) if nf == 0 else math.inf)
                if ratio > limit:
                    failures.append(dict(bucket=edges[k:k+2], mode=mode, baseline=base,
                        numerator=dict(events=nf,samples=nn),denominator=dict(events=bf,samples=bn),
                        ratio=float(ratio),exact_ratio=str(ratio)))
            label=f"core.{key}.{mode}/{base}"
            assert bool(failures) == criteria["S4b_not_above_contract_every_bucket"]["tests"][label]["fails"]
            independent[label]=dict(failure_buckets=len(failures),witnesses=failures)
            if failures:
                witnesses.append(dict(criterion="S4b",metric=key,**max(failures,key=lambda x:x["ratio"])))

    # S3 core depth tests: arithmetic means of layer ratios, not ratio of means.
    depth = {}
    for label,key,sub,mode,base in (
        ("router_flip_free","router","flip_rate","b_nam","a2"),
        ("router_flip_one_layer","router","flip_rate","b_nam_tf","a2_tf"),
        ("hidden_rel_rms_free","hidden_rel_rms",None,"b_nam","a2"),
        ("hidden_rel_rms_one_layer","hidden_rel_rms",None,"b_nam_tf","a2_tf")):
        values=[]
        for l in rec["layers"]:
            n,b=l[key][mode],l[key][base]
            values.append((n[sub] if sub else n)/max(b[sub] if sub else b,1e-30))
        lo,hi=sum(values[:10])/10,sum(values[30:40])/10
        fail=hi>rule["X_RATIO_MAX"] or hi>lo*(1+rule["X_GROWTH_MAX"])
        test=criteria["S3_no_growth_with_depth"]["tests"][label]
        assert fail==test["fails"] and abs(hi-test["mean_layers_30_39"])<1e-12
        depth[label]=dict(mean_layers_0_9=lo,mean_layers_30_39=hi,fails=fail)

    assert hashes == {n:G.digest(core/n) for n in hashes}, "completed core changed during audit"
    assert G.source_identity() == observation["source_sha256"]
    assert witnesses and not criteria["S3b_not_above_contract_every_layer"]["pass"]
    result=dict(schema="opentallas.qcnam.completed-core-audit.v1",observed_utc=datetime.now(timezone.utc).isoformat(),
        main_basis="5559269a7c6f2aa60fb7a5eb34a9a22e5815bb10",run_pin=G.PIN,
        source_sha256={"tools/deepseek_v41_nam_quality.py":hashlib.sha256(source).hexdigest(),
                       "tools/audit_qcnam_completed_core.py":G.digest(__file__)},
        input=dict(directory=str(core),files_sha256=hashes,validated_depth=40,
                   argument_and_instrumentation_guard_pass=True,successful_exit_and_done_marker=True),
        stability_rule=rule,criteria=criteria,independent_selection_checks=independent,independent_depth_checks=depth,
        independent_finite_and_saturation=dict(finite_events=finite_events,finite_checks=finite_checks,
                                              saturation_totals=saturation_totals,core_only=True),
        definitive_selection_witnesses=witnesses,
        scope="Completed core only. Original pinned stability code, integer-count crosschecks and independent depth means. No quality verdict, no full-model finalization, no changed threshold, no GPU execution.",
        definitive_core_failure=True,
        irreversibility="S3 is defined on core; S3b/S4/S4b retain per-run core tests and require every test to pass. Later lanes cannot dilute these core violations. S1/S2 pass here only, not globally.",
        full_gate_complete=False,full_verdict=None,finalized=False,hardware_adopted=False,
        model_treatment="Exclude this DeepSeek QC-NAM norm-after-matvec variant as an eligible performance gain: core already violates unchanged mandatory stability criteria. Preserve pending all-lane finalization; do not restate headlines. Qwen's existing arithmetic contract and golden-exact fusion are not covered by this variant's audit.",
        warnings=[str(w.message) for w in observed_warnings],
        warning_scope="Pinned probes with no usable late-depth samples retain their original NaN handling. Definitive finite selection witnesses above do not depend on those empty means.",
        live_handles=G.active_jobs(),next_action="Keep existing lanes/watcher; full guard and original pinned finalizer only after all required outputs complete.")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open("x") as f:
        json.dump(safe(result),f,indent=2,allow_nan=False)
        f.write("\n")
    print(json.dumps(dict(output=str(args.out),core_criteria={k:v["pass"] for k,v in criteria.items()},full_verdict=None)))


if __name__ == "__main__":
    main()
