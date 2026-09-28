#!/usr/bin/env python3
"""Fail-closed finite-resource checker for mapped V4.1 schedule witnesses.

This checks a concrete witness, not the architectural DAG. A witness must pin
its inputs and reserve each physical resource for its full operation interval.
An exact standalone stage can be admitted as an opaque operator subset; it
cannot by itself establish a full-layer or token rate.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.v41.finite-schedule.v1"
KINDS = {
    "qe_rom": {"issue", "quant_mac", "weight_rom", "vm_read", "vm_write"},
    "qe_hbm": {"issue", "quant_mac", "weight_hbm", "vm_read", "vm_write"},
    "me_rom": {"issue", "bf16_mac", "weight_rom", "vm_read", "vm_write"},
    "me_hbm": {"issue", "bf16_mac", "weight_hbm", "vm_read", "vm_write"},
    "he_rom": {"issue", "hcp_mac", "weight_rom", "vm_read", "vm_write"},
    "he_hbm": {"issue", "hcp_mac", "weight_hbm", "vm_read", "vm_write"},
    "index_scan": {"issue", "index_mac", "index_hbm", "vm_read", "vm_write"},
    "kv_attention": {"issue", "attention_mac", "kv_sram_read", "vm_read", "vm_write"},
    "kv_prefetch": {"issue", "kv_hbm", "kv_sram_write"},
    "rope_prefetch": {"issue", "constant_hbm", "constant_sram_write"},
    "collective": {"issue", "collective_engine", "link", "vm_read", "vm_write"},
    "stage_hop": {"issue", "link", "vm_read", "vm_write"},
    "vector": {"issue", "vector_lane", "vm_read", "vm_write"},
    "verified_collective_stage": {"collective_engine", "link", "vm_read", "vm_write"},
}


def audit(m: dict, root: Path = ROOT) -> dict:
    errors: list[str] = []
    if m.get("schema") != SCHEMA:
        errors.append("schema: unsupported or missing")
    scope = m.get("scope")
    if scope not in ("operator_subset", "full_layer", "full_token"):
        errors.append("scope: must identify operator_subset, full_layer or full_token")
    pins = m.get("source_sha256")
    if not isinstance(pins, dict) or not pins:
        errors.append("source_sha256: nonempty source pins required")
        pins = {}
    else:
        for path, digest in pins.items():
            f = root / path
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
                errors.append(f"source pin mismatch: {path}")
    contract = m.get("contract", {})
    if not isinstance(contract.get("instruction_ids"), list) or not contract["instruction_ids"]:
        errors.append("contract: complete instruction_ids required")
    if not isinstance(contract.get("tensor_specs"), dict):
        errors.append("contract: tensor_specs required")
    if scope in ("full_layer", "full_token"):
        for key in ("program_path", "checkpoint_manifest_path", "placement_path", "all_unit_trace_path", "clock_hz"):
            if not contract.get(key):
                errors.append(f"contract: {key} required for {scope}")
        for key in ("program_path", "checkpoint_manifest_path", "placement_path", "all_unit_trace_path"):
            if contract.get(key) and contract[key] not in pins:
                errors.append(f"contract: {key} must be source-pinned")
        if not contract.get("tensor_specs"):
            errors.append(f"contract: complete integer tensor coverage required for {scope}")
        if scope == "full_layer" and not isinstance(contract.get("layer_id"), int):
            errors.append("contract: exact layer_id required")
        if scope == "full_token" and contract.get("layer_ids") != list(range(40)):
            errors.append("contract: all 40 ordered layer_ids required")
        program_path = contract.get("program_path")
        if program_path in pins and (root / program_path).is_file():
            try:
                program = json.loads((root / program_path).read_text())
                if program.get("status") != "pass" or program.get("instruction_count") != len(contract.get("instruction_ids", [])):
                    errors.append("contract: complete passing program instruction count required")
            except (ValueError, TypeError):
                errors.append("contract: program manifest must be parseable JSON")
    resources = m.get("resources")
    if not isinstance(resources, dict) or not resources:
        errors.append("resources: concrete physical resources required")
        resources = {}
    phys = {}
    hbm_stack_phys = {}
    for name, r in resources.items():
        if not isinstance(r, dict):
            errors.append(f"resource {name}: malformed")
            continue
        pid, cap, cls, unit = (r.get("physical_id"), r.get("capacity_per_cycle"),
                               r.get("classes"), r.get("unit"))
        if not pid or not isinstance(cap, (int, float)) or cap <= 0 or not cls or not unit:
            errors.append(f"resource {name}: physical_id, capacity, unit and classes required")
            continue
        if pid in phys and phys[pid] != (cap, unit):
            errors.append(f"resource {name}: aliased physical capacity/unit disagrees")
        phys[pid] = (cap, unit)
        if any(c.endswith("_hbm") for c in cls):
            die, stack = r.get("owner_die"), r.get("stack_id")
            if not isinstance(die, int) or not isinstance(stack, int):
                errors.append(f"resource {name}: concrete HBM die/stack owner required")
            else:
                key = (die, stack)
                if key in hbm_stack_phys and hbm_stack_phys[key] != pid:
                    errors.append(f"resource {name}: same physical HBM stack assigned independent service pools")
                hbm_stack_phys[key] = pid
            evidence = r.get("sustained_service_record")
            if scope in ("full_layer", "full_token") and evidence not in pins:
                errors.append(f"resource {name}: source-pinned sustained HBM service record required")
    fragments = m.get("tensor_fragments")
    if not isinstance(fragments, list):
        errors.append("tensor_fragments: explicit list required")
        fragments = []
    covered = defaultdict(list)
    fragment_ids = set()
    for f in fragments:
        key = f.get("tensor_id")
        fragment_id = f.get("fragment_id")
        if not fragment_id or fragment_id in fragment_ids:
            errors.append(f"tensor fragment {key}: unique fragment_id required")
        fragment_ids.add(fragment_id)
        a, b, expert = f.get("row_start"), f.get("row_end"), f.get("expert_id")
        if not key or not isinstance(a, int) or not isinstance(b, int) or b <= a:
            errors.append(f"tensor fragment {key}: integer nonempty row range required")
            continue
        if expert is not None and not isinstance(expert, int):
            errors.append(f"tensor fragment {key}: fractional/noninteger expert ownership")
        if not isinstance(f.get("owner_die"), int) or not isinstance(f.get("owner_cluster"), int):
            errors.append(f"tensor fragment {key}: concrete die/cluster owner required")
        if not isinstance(f.get("physical_bytes"), int) or f["physical_bytes"] <= 0:
            errors.append(f"tensor fragment {key}: physical bytes required")
        covered[key].append((a, b))
    for name, spec in contract.get("tensor_specs", {}).items():
        rows = spec.get("rows") if isinstance(spec, dict) else None
        if not isinstance(rows, int) or rows <= 0:
            errors.append(f"tensor {name}: integer row count required")
            continue
        intervals = sorted(covered.get(name, []))
        cursor = 0
        for a, b in intervals:
            if a != cursor:
                errors.append(f"tensor {name}: gap/overlap at row {cursor}")
            cursor = b
        if cursor != rows:
            errors.append(f"tensor {name}: coverage ends at {cursor}, expected {rows}")
    ops = m.get("operations")
    if not isinstance(ops, list) or not ops:
        errors.append("operations: mapped timed operations required")
        ops = []
    by_id = {}
    events = defaultdict(list)
    used = defaultdict(float)
    useful = defaultdict(float)
    wait_cycles = defaultdict(int)
    max_end = 0
    instruction_seen = set()
    for op in ops:
        oid, kind = op.get("id"), op.get("kind")
        if not oid or oid in by_id:
            errors.append(f"operation {oid}: missing or duplicate id")
            continue
        by_id[oid] = op
        if kind not in KINDS:
            errors.append(f"operation {oid}: unknown kind {kind}")
            continue
        instr = op.get("instruction_id")
        if instr is None:
            errors.append(f"operation {oid}: instruction binding required")
        else:
            instruction_seen.add(instr)
            if instr not in contract.get("instruction_ids", []):
                errors.append(f"operation {oid}: instruction {instr} outside complete program")
        start, end = op.get("start_cycle"), op.get("end_cycle")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start:
            errors.append(f"operation {oid}: integer positive interval required")
            continue
        max_end = max(max_end, end)
        ready = op.get("ready_cycle")
        if not isinstance(ready, int) or ready < 0 or ready > start:
            errors.append(f"operation {oid}: dependency-ready cycle required")
        else:
            wait_cycles[kind] += start - ready
        if scope in ("full_layer", "full_token") and not isinstance(op.get("stall_reasons"), dict):
            errors.append(f"operation {oid}: measured stall reasons required")
        if not isinstance(op.get("die"), int) or not isinstance(op.get("cluster"), int):
            errors.append(f"operation {oid}: concrete die/cluster required")
        if not isinstance(op.get("tensor_fragment_ids"), list):
            errors.append(f"operation {oid}: tensor fragment binding list required")
        elif any(t not in fragment_ids for t in op["tensor_fragment_ids"]):
            errors.append(f"operation {oid}: unknown tensor fragment binding")
        elif kind in ("qe_rom", "qe_hbm", "me_rom", "me_hbm", "he_rom", "he_hbm") and not op["tensor_fragment_ids"]:
            errors.append(f"operation {oid}: weight fragment owner required")
        if not isinstance(op.get("deps"), list):
            errors.append(f"operation {oid}: dependency list required")
        if scope in ("full_layer", "full_token") and kind in ("collective", "index_scan", "kv_prefetch", "rope_prefetch", "qe_hbm", "me_hbm", "he_hbm"):
            queue_ids = op.get("queue_ids")
            if not isinstance(queue_ids, list) or not queue_ids:
                errors.append(f"operation {oid}: shared-service queue IDs required")
        demands = op.get("demands")
        if not isinstance(demands, dict):
            errors.append(f"operation {oid}: per-class physical demands required")
            continue
        if set(demands) != KINDS[kind]:
            errors.append(f"operation {oid}: required resource classes {sorted(KINDS[kind])}")
        for cls, amount in demands.items():
            if not isinstance(amount, (int, float)) or amount <= 0:
                errors.append(f"operation {oid}: positive demand required for {cls}")
        reservations = op.get("reservations")
        if not isinstance(reservations, list):
            errors.append(f"operation {oid}: reservations required")
            continue
        delivered = defaultdict(float)
        for q in reservations:
            rn, cls = q.get("resource"), q.get("class")
            rs, re, rate = q.get("start_cycle"), q.get("end_cycle"), q.get("rate")
            r = resources.get(rn)
            if not isinstance(r, dict) or cls not in r.get("classes", []):
                errors.append(f"operation {oid}: unbound class/resource {cls}/{rn}")
                continue
            if (not isinstance(rs, int) or not isinstance(re, int) or
                    not isinstance(rate, (int, float)) or rate <= 0 or rs < start or re > end or re <= rs):
                errors.append(f"operation {oid}: invalid reservation {rn}")
                continue
            delivered[cls] += rate * (re - rs)
            pid = r["physical_id"]
            events[pid].extend(((rs, rate), (re, -rate)))
            used[pid] += rate * (re - rs)
        for cls, amount in demands.items():
            if isinstance(amount, (int, float)) and delivered[cls] < amount:
                errors.append(f"operation {oid}: under-reserved {cls}: {delivered[cls]} < {amount}")
            if isinstance(amount, (int, float)):
                useful[cls] += amount
        if kind == "verified_collective_stage":
            proof = op.get("exact_stage_record")
            if not isinstance(proof, dict) or proof.get("path") not in pins or proof.get("case") not in ("act", "y"):
                errors.append(f"operation {oid}: pinned exact stage case required")
            else:
                rec = json.loads((root / proof["path"]).read_text())
                case = rec.get("summary", {}).get(proof["case"], {})
                for path, digest in rec.get("source_sha256", {}).items():
                    f = root / path
                    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
                        errors.append(f"operation {oid}: exact stage source mismatch {path}")
                selected = [x for x in rec.get("cases", []) if x.get("case", "").startswith(proof["case"] + "_d128")]
                if len(selected) != 1 or selected[0].get("mismatches") != 0 or any(selected[0].get("faults", [1])):
                    errors.append(f"operation {oid}: exact selected stage has no passing case")
                if (case.get("selected_tail_cycles") != proof.get("tail_cycles") or
                    case.get("input_words_per_die") != proof.get("input_words") or
                    case.get("output_words_per_die") != proof.get("output_words") or
                    end - start < proof["input_words"] + proof["tail_cycles"]):
                    errors.append(f"operation {oid}: stage interval or measured case mismatch")
    missing = set(contract.get("instruction_ids", [])) - instruction_seen
    if missing:
        errors.append(f"program instructions not scheduled: {sorted(missing, key=str)[:8]}")
    for oid, op in by_id.items():
        for dep in op.get("deps", []):
            if dep not in by_id or by_id[dep].get("end_cycle", 10**18) > op.get("start_cycle", -1):
                errors.append(f"operation {oid}: unmet dependency {dep}")
    peak = {}
    for pid, steps in events.items():
        occ = 0
        for cycle, delta in sorted(steps, key=lambda x: (x[0], x[1])):
            occ += delta
            peak[pid] = max(peak.get(pid, 0), occ)
            if occ > phys.get(pid, (0, None))[0] + 1e-9:
                errors.append(f"physical resource {pid}: over capacity at cycle {cycle}")
                break
    queues = m.get("queues")
    if not isinstance(queues, dict):
        errors.append("queues: explicit queue ledger required")
        queues = {}
    for name, q in queues.items():
        if not isinstance(q.get("depth"), int) or q["depth"] <= 0 or not isinstance(q.get("events"), list):
            errors.append(f"queue {name}: depth and events required")
            continue
        occ = 0
        for ev in sorted(q["events"], key=lambda e: e.get("cycle", -1)):
            if ev.get("op") not in by_id or not isinstance(ev.get("delta"), int):
                errors.append(f"queue {name}: unbound event")
                continue
            occ += ev["delta"]
            if occ < 0 or occ > q["depth"]:
                errors.append(f"queue {name}: underflow/overflow at cycle {ev.get('cycle')}")
        if occ != 0:
            errors.append(f"queue {name}: nonempty at completion")
    for oid, op in by_id.items():
        for queue_id in op.get("queue_ids", []):
            if queue_id not in queues:
                errors.append(f"operation {oid}: missing shared-service queue {queue_id}")
    return {
        "status": "pass_resource_witness" if not errors else "blocked",
        "errors": errors,
        "scope": scope,
        "makespan_cycles": max_end if not errors else None,
        "physical_peak_per_cycle": peak,
        "physical_reserved_fraction": {k: used[k] / (max_end * phys[k][0]) for k in used} if max_end else {},
        "useful_demand_by_class": dict(useful),
        "wait_cycles_by_kind": dict(wait_cycles),
        "claim_boundary": "A passing operator subset cannot establish full-layer/token rate; no physical timing or power is inferred.",
    }


def main():
    manifest = Path(sys.argv[1])
    result = audit(json.loads(manifest.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass_resource_witness" else 1)


if __name__ == "__main__":
    main()
