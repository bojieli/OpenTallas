#!/usr/bin/env python3
"""DS-ROM 1M: the ROM-field nodes re-measured on the element the S81 die is built from (2026-10-05).

The 1M composition (tools/dsrom_1m_allmeasured.py) takes its ROM-field nodes from field.json, measured by
tools/dsrom_1m_field.py on the field vehicle with the PINNED W10 element ot_v41_rom_elem_w10 (segment tree
ot_v41_segtree2, lane ot_v41_bterm2_w10).  The S81 die's FP8/FP4 pairs are the DS q-element (the routed
ot_v41_rom_elem_q_qp_w10 abstract today; the closure successor ot_v41_rom_elem_q_qx_w10).  This tool compares field
records measured with `dsrom_1m_field.py --qelem N` against the base record (same plan, same vehicle otherwise),
recomposes AR / MTP with each (same --baseline, other inputs unchanged) and writes the delta.

    python3 tools/dsrom_field_qelem_delta.py --base FIELD_BASE.json --q 9=FIELD_Q9.json [--q 8=FIELD_Q8.json]
        --out results/rtl/dsrom_field_qelem_20261005/composition_delta.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def compose(field: Path, work: Path, tag: str) -> dict:
    """allmeasured with REC's inputs and `field` in place of field.json."""
    rec = work / f"rec_{tag}"
    shutil.copytree(REC, rec)
    shutil.copy(field, rec / "field.json")
    out = work / f"comp_{tag}.json"
    p = subprocess.run([sys.executable, str(ROOT / "tools/dsrom_1m_allmeasured.py"), "--rec", str(rec), "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        raise SystemExit(f"compose {tag} failed:\n{p.stdout[-2000:]}\n{p.stderr[-2000:]}")
    return json.loads(out.read_text())


def field_on_path(comp: dict, field: dict) -> list:
    """Critical-path nodes whose time is a field.json node (dsrom_1m_allmeasured_adapters.field_rows mapping)."""
    from dsrom_1m_allmeasured_adapters import field_rep
    by = {x["node"] for x in field["node_summary"]}
    hits = []
    for c in comp["critical_path"]:
        name = c["node"]
        head, _, suf = name.partition(".")
        if head.startswith("L") and head[1:].isdigit():
            src = name if name in by else f"L{field_rep(int(head[1:]))}.{suf}"
            if src in by:
                hits.append(dict(node=name, field_node=src, us=c["us"]))
        elif head.startswith("E") and name in by:
            hits.append(dict(node=name, field_node=name, us=c["us"]))
    return hits


def compose_minimum(record_path: Path) -> dict:
    """Compose retained phase/region measurements without replacing full nodes."""
    record = json.loads(record_path.read_text())
    if record.get("schema") != "opentallas.dsrom-qx10-field-min-functional.v1":
        raise ValueError("expected the source-pinned native QX10 minimum-field record")
    if record.get("verdict") != "PASS_MINIMAL_FUNCTIONAL":
        raise ValueError("minimum field record did not pass")
    if record["shape"] != dict(NP=32, R=1, NBF=5, real_pairs=18,
                               real_BF_capable_pairs=4, QELEM=1, QXV=10):
        raise ValueError("minimum field vehicle shape changed")
    inputs = {str(record_path): sha(record_path)}
    floorplan = ROOT / "results/rtl/dsrom_s81_fulldie_20261004/floorplan.json"
    inputs[str(floorplan.relative_to(ROOT))] = sha(floorplan)
    fp = json.loads(floorplan.read_text())["trunk_stages"]
    # Same term as dsrom_1m_field.record: the measured vehicle already
    # contains the two broadcast stages. Do not count those stages twice.
    wire = 2 * fp["stages_at_504"]["field_one_way"] - 2
    terms = []
    for case in record["cases"]:
        raw = {}
        for variant in ("qx9", "qx10"):
            rel = f"{variant}/{case['phase']}/result.json"
            p = record_path.parent / rel
            digest = sha(p)
            if digest != record["artifact_sha256"][rel]:
                raise ValueError(f"retained artifact changed: {rel}")
            inputs[str(p)] = digest
            r = raw[variant] = json.loads(p.read_text())
            if (r["phase"], r["region"]) != (case["phase"], case["region"]):
                raise ValueError(f"phase/region identity differs: {rel}")
            if not r["pass_"] or any(r[k] for k in ("fault", "extra", "mismatched")):
                raise ValueError(f"failed exact measurement: {rel}")
            if r["rows"] != r["nrows"] or r["rows"] != case["rows_checked"]:
                raise ValueError(f"incomplete row coverage: {rel}")
            if (r["pairs"], r["bf_pairs"]) != (18, 4):
                raise ValueError(f"minimum field return region changed: {rel}")
        for k in ("pairs", "bf_pairs", "nbeat", "t_read", "nrows", "xcheck"):
            if raw["qx9"][k] != raw["qx10"][k]:
                raise ValueError(f"baseline vehicle differs at {case['phase']}: {k}")
        r, b = raw["qx10"], raw["qx9"]
        terms.append(dict(phase=case["phase"], region=case["region"], rows=r["rows"],
                          measured_last_cycles=r["go_to_last_w"],
                          measured_idle_cycles=r["go_to_idle"],
                          additional_last_cycles_vs_qx9=r["go_to_last_w"] - b["go_to_last_w"],
                          additional_idle_cycles_vs_qx9=r["go_to_idle"] - b["go_to_idle"],
                          existing_s81_wire_cycles=wire,
                          phase_region_last_cycles_with_wire=r["go_to_last_w"] + wire,
                          phase_region_last_us_with_wire=(r["go_to_last_w"] + wire) / 1200))
    return dict(schema="opentallas.dsrom-field-qelem-minimum-composition.v1",
                element_source_commit=record["element_source_commit"], terms=terms,
                scope="Individual measured phase/region terms; incomplete nodes are not substituted into the token graph.",
                complete_field_campaign=False, node_summary=None, AR_tok_s=None, MTP_tok_s=None,
                physical_qualified=False, missing_input_clocks=True, inputs=inputs,
                analytical_qx10_additional_pipeline_cycles=0,
                tool_sha256=sha(Path(__file__)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path)
    ap.add_argument("--minimum", type=Path, help="retained minimum-field record; compose only its phase/region terms")
    ap.add_argument("--q", action="append", default=[], help="QX=field.json (repeatable)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.minimum:
        if a.base or a.q:
            ap.error("--minimum cannot replace a complete --base/--q campaign")
        result = compose_minimum(a.minimum)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=1) + "\n")
        print(json.dumps(result["terms"]))
        return 0
    if not a.base:
        ap.error("--base or --minimum is required")
    base = json.loads(a.base.read_text())
    qs = {int(k): Path(v) for k, v in (x.split("=", 1) for x in a.q)}
    (ROOT / "build").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / "build") as td:     # under ROOT: the composer records relative paths
        work = Path(td)
        comps = {"base": compose(a.base, work, "base")}
        for k, p in qs.items():
            comps[f"q{k}"] = compose(p, work, f"q{k}")
    fields = {"base": base, **{f"q{k}": json.loads(p.read_text()) for k, p in qs.items()}}
    nodes = []
    bn = {x["node"]: x for x in base["node_summary"]}
    for name, x in bn.items():
        row = dict(node=name, base_cycles=x["total_cycles"], base_us=x["total_us_s81_floorplan_wire"],
                   rows=x["rows_checked"], base_exact=x["exact"])
        for t, f in fields.items():
            if t == "base":
                continue
            y = {z["node"]: z for z in f["node_summary"]}.get(name)
            row[f"{t}_cycles"] = y and y["total_cycles"]
            row[f"{t}_us"] = y and y["total_us_s81_floorplan_wire"]
            row[f"{t}_exact"] = y and y["exact"]
            row[f"{t}_delta_cycles"] = y and y["total_cycles"] - x["total_cycles"]
        nodes.append(row)
    summ = {}
    for t, c in comps.items():
        m = c["MTP"]
        summ[t] = dict(AR_us=c["AR_us"], AR_tok_s=c["AR_tok_s"], MTP_tok_s=m["MTP_tok_s"], step_us=m["step_us"],
                       II_us=m["II_us"], verify_us=m["verify_us"], tau=m["tau"],
                       field_nodes_on_critical_path=field_on_path(c, fields[t]),
                       field_us_on_critical_path=round(sum(h["us"] for h in field_on_path(c, fields[t])), 3))
        # Carry the composer's physical rejection through the comparison.
        for key in ("physical_qualified", "qualified_headline_rate", "wavefront_implementation"):
            if key in m:
                summ[t][f"MTP_{key}"] = m[key]
    for t in summ:
        if t != "base":
            summ[t]["delta_vs_base"] = dict(
                AR_us=round(summ[t]["AR_us"] - summ["base"]["AR_us"], 3),
                AR_tok_s=round(summ[t]["AR_tok_s"] - summ["base"]["AR_tok_s"], 1),
                AR_pct=round(100 * (summ[t]["AR_tok_s"] / summ["base"]["AR_tok_s"] - 1), 2),
                MTP_tok_s=round(summ[t]["MTP_tok_s"] - summ["base"]["MTP_tok_s"], 1),
                MTP_pct=round(100 * (summ[t]["MTP_tok_s"] / summ["base"]["MTP_tok_s"] - 1), 2))
    rec = dict(schema="opentallas.dsrom-field-qelem-delta.v1",
               claim_boundary=("ROM-field nodes measured in RTL (Verilator, tools/dsrom_1m_field.py, S81 plan, every "
                               "phase x region, bit-exact) with the pinned W10 element (base) and with the DS q-element "
                               "on the FP8/FP4 pairs (--qelem N); AR / MTP recomposed by tools/dsrom_1m_allmeasured.py "
                               "with only field.json replaced.  No SS/FF claim: the q-element is not yet closed."),
               composition=summ, nodes=nodes,
               inputs={str(a.base): sha(a.base), **{str(p): sha(p) for p in qs.values()}},
               tool_sha256=sha(Path(__file__)),
               composer_sha256=sha(ROOT / "tools/dsrom_1m_allmeasured.py"),
               uarch_model_sha256=sha(ROOT / "tools/uarch_model.py"),
               git_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                       text=True).stdout.strip())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    for t, s in summ.items():
        print(t, s["AR_tok_s"], s["MTP_tok_s"], s.get("delta_vs_base"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
