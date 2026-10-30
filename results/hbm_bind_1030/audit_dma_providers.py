#!/usr/bin/env python3
"""Supplemental existing-R7 audit of DMA providers in an emitted native source.

These are internal production requests, not physical die inputs. The audit does
not alter the historical G0 verdict or invent a provider for an exposed port.
"""
import argparse
import json
import re
from pathlib import Path


def audit(top, bound_dir):
    src = Path(top).read_text()
    inputs = {name: int(msb) + 1 for msb, name in re.findall(
        r"^\s*input\s+wire\s+\[(\d+):0\]\s+(\w+)\s*;", src, re.M)}
    instances = {}
    for m in re.finditer(r"^  (\w+)(?: #\((.*?)\))? (\w+) \(\n(.*?)\n  \);", src, re.M | re.S):
        master, params, name, body = m.groups()
        instances[name] = dict(module=master, parameters=params or "", body=body)
    findings = []
    for role in ("SW", "SE"):
        name, net = f"hb_dbk_{role}", f"hb_dbk_{role}__rq"
        if net not in inputs:
            continue
        bound = []
        for path in sorted(Path(bound_dir).glob("*.sv")):
            for lineno, line in enumerate(path.read_text().splitlines(), 1):
                if f"io_hb_dbk_{role}_rq" in line and "input" in line:
                    bound.append(dict(file=str(path), line=lineno, declaration=line.strip()))
        findings.append(dict(level="ERROR", check="R7_MISSING_DMA_PROVIDER", role=role,
            instance=name, instance_present=name in instances, net=net,
            width=inputs[net], source="external_top_input", bound_die_input=bound,
            reason="An internal production VM request is exposed as die IO; no native DMA producer drives it"))
    generic = {n: v["module"] for n, v in instances.items()
               if re.match(r"ot_hgi_(?:b2_dma_q$|dma_engines$|dma_front(?:_|$)|dma_mover(?:_|$))", v["module"])}
    if not generic:
        findings.append(dict(level="ERROR", check="MISSING_PRODUCTION_LOAD_PROVIDER",
            reason="No native generic HGI LOAD/mover provider is instantiated. A Python descriptor replay is not a source provider"))
    back = []
    for n, v in instances.items():
        if v["module"] != "ot_hgi_dma_back_static_vp4_banks_cp":
            continue
        conns = dict(re.findall(r"\.(\w+)\((.*?)\)(?:,|\s*$)", v["body"], re.M))
        back.append(dict(instance=n, module=v["module"], parameters=v["parameters"],
                         stk=conns.get("stk"), target=conns.get("tgt"),
                         launch=conns.get("launch_v"), request=conns.get("rq")))
    return dict(schema="opentallas.hbm.native_dma_provider_audit.v1",
                status="FAIL_R7_SOURCE" if findings else "PASS_SOURCE_PROVIDERS",
                top=str(top), historical_plan_g0="UNCHANGED", rtl_modified=False,
                dma_back_instances=back, generic_load_instances=generic,
                findings=findings, errors=len(findings),
                scope="Existing R7 production-source obligations only; no physical or token qualification")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("top"); p.add_argument("bound_dir"); p.add_argument("out")
    a = p.parse_args()
    if Path(a.out).exists():
        p.error("output exists; preserve previous failed verdicts")
    result = audit(a.top, a.bound_dir)
    Path(a.out).write_text(json.dumps(result, indent=1) + "\n")
    print(result["status"], result["errors"], "errors")
    for f in result["findings"]:
        print(f["check"], f.get("net", ""), f.get("width", ""))
    raise SystemExit(bool(result["errors"]))


if __name__ == "__main__":
    main()
