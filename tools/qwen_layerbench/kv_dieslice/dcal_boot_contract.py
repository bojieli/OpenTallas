#!/usr/bin/env python3
"""Prepare the measured DSTG1 boot-calendar tuple correction for one KV event.

The historical R8 reference is retained. The result is a proposed landing table
and a separate source-event contract; it is not an R8 waiver or an adopted plan.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

FACE_SHA256 = "1f43f8d36a8f2d4ababbace304a53712edf51bdfaf1b4de6689ffcb5120835e2"
PORTS = {"bcfg_addr": ("link_cfg_addr", [[0, 5]]),
         "bcfg_data": ("link_cfg_data", [[0, 31]]),
         "bcfg_rx_we": ("link_cfg_rx_we", [[0, 0]]),
         "bcfg_tx_we": ("link_cfg_tx_we", [[0, 0]])}


def prepare(landing: dict, groups: dict, face: bytes, provider: str) -> tuple[dict, dict]:
    if hashlib.sha256(face).hexdigest() != FACE_SHA256:
        raise ValueError("boot dispatcher differs from the measured DSTG1 source")
    instances = re.findall(r"qkd_static_kv_boot_dispatch_mu_nc32\s*#\((.*?)\)\s*u_boot\s*\(", provider, re.S)
    if len(instances) != 1 or not re.search(r"\.DSTG\(\s*1\s*\)", instances[0]):
        raise ValueError("selected provider must contain exactly one measured u_boot DSTG1")
    gs = [g for g in groups.get("landing", []) if g.get("sink") == "dcal"
          and g.get("sink_part") == "sys_c" and g.get("src_part") == "hub_C"
          and any(m.get("sink_port") in PORTS for m in g["members"])]
    if len(gs) != 1:
        raise ValueError("expected one actual hub_C-to-sys_c dcal boot tuple")
    ms = {m["sink_port"]: m for m in gs[0]["members"] if m.get("sink_port") in PORTS}
    if len(ms) != 4 or sum(m.get("sink_port") in PORTS for m in gs[0]["members"]) != 4:
        raise ValueError("boot tuple is missing or duplicates a member")
    for port, (source, bits) in PORTS.items():
        if ms[port].get("source") != "kvs_ctl.boot__" + source or ms[port].get("sink_bits") != bits:
            raise ValueError(f"unexpected actual source/width for {port}")
    target = ms["bcfg_data"]["landed_stages"]
    if ms["bcfg_addr"]["landed_stages"] != target:
        raise ValueError("address/data already disagree; this correction is insufficient")
    result = copy.deepcopy(landing)
    changes = []
    for port in ("bcfg_rx_we", "bcfg_tx_we"):
        m = ms[port]
        if m["landed_stages"] != target - 1:
            raise ValueError(f"{port}: expected the diagnosed one-edge-early strobe")
        hits = [r for r in result["members"] if r.get("sink") == "dcal"
                and r.get("sink_port") == port and r.get("source") == m["source"]]
        if len(hits) != 1:
            raise ValueError(f"expected one landing-table row for {port}")
        r = hits[0]
        if (r["asbuilt"], r["bound"], r["landed"]) != (m["asbuilt_stages"], m["bound_stages"], m["landed_stages"]):
            raise ValueError(f"landing-table/source-group mismatch for {port}")
        before = copy.deepcopy(r)
        r["pad"] += 1
        r["landed"] += 1
        changes.append({"id": r["id"], "before": before, "after": copy.deepcopy(r)})
    receipt = {"schema": "opentallas.kv.dcal_boot_source_event.v1",
               "status": "CANDIDATE_REQUIRES_QUALIFIED_R8_REFERENCE",
               "producer_face_sha256": FACE_SHA256,
               "selected_provider_sha256": hashlib.sha256(provider.encode()).hexdigest(),
               "selected_producer": "qkd_static_kv_boot_dispatch_mu_nc32 u_boot DSTG1",
               "consumer": "qkd_d2d_cal_seq_pin_bc4.bcfg_*",
               "source_event_relative_edges": {p: 0 for p in PORTS},
               "historical_reference_stages": {p: m["asbuilt_stages"] for p, m in ms.items()},
               "producer_event_offset": {p: int(p.endswith("_we")) for p in PORTS},
               "candidate_landed_edges": {p: target for p in PORTS},
               "changes": changes, "added_boot_strobe_edges": 1,
               "added_boot_landing_flops": 2, "added_layer_cycles": 0, "added_token_cycles": 0,
               "integration_required": "Apply the qualified current source-event reference to these four members before R8; retain raw historical groups and member IDs. Generic R8 on the old reference must still fail this candidate. Preserve all PV/calendar and unrelated landing rows."}
    digest = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt["contract_sha256"] = digest
    changed_ids = {c["id"] for c in changes}
    for r in result["members"]:
        if r.get("id") in changed_ids:
            r["producer_event_offset"] = 1
            r["legacy_asbuilt"] = r["asbuilt"]
            r["source_event_contract_sha256"] = digest
    if "pad_flops" in result.get("summary", {}):
        result["summary"]["pad_flops"] += 2
    result["source_event_contract"] = receipt
    return result, receipt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("landing", "groups", "face", "provider", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    a = ap.parse_args()
    candidate, receipt = prepare(json.loads(a.landing.read_text()), json.loads(a.groups.read_text()),
                                 a.face.read_bytes(), a.provider.read_text())
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / "landing_candidate.json").write_text(json.dumps(candidate, indent=2) + "\n")
    (a.out / "source_event_contract.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
