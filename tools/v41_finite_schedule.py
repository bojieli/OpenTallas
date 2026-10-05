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
import math
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


def _number(value, *, positive=False):
    """Reject bool and nonfinite floats before they reach capacity accounting."""
    return ((type(value) is int or (type(value) is float and math.isfinite(value)))
            and (value > 0 if positive else value >= 0))


def _integer(value, *, positive=False):
    return type(value) is int and (value > 0 if positive else value >= 0)


def audit(m: dict, root: Path = ROOT) -> dict:
    errors: list[str] = []
    if not isinstance(m, dict):
        return {"status": "blocked", "errors": ["manifest: object required"],
                "scope": None, "makespan_cycles": None}
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
            if not isinstance(path, str) or not isinstance(digest, str):
                errors.append("source pin: path and digest strings required")
                continue
            f = root / path
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
                errors.append(f"source pin mismatch: {path}")
    contract = m.get("contract", {})
    if not isinstance(contract, dict):
        errors.append("contract: object required")
        contract = {}
    instruction_ids = contract.get("instruction_ids")
    if not isinstance(instruction_ids, list) or not instruction_ids:
        errors.append("contract: complete instruction_ids required")
        instruction_ids = []
    if any(type(x) not in (str, int) or x == "" for x in instruction_ids):
        errors.append("contract: scalar instruction_ids required")
        instruction_ids = [x for x in instruction_ids if type(x) in (str, int) and x != ""]
    if len(instruction_ids) != len(set(instruction_ids)):
        errors.append("contract: instruction_ids must be unique")
    tensor_specs = contract.get("tensor_specs")
    if not isinstance(tensor_specs, dict):
        errors.append("contract: tensor_specs required")
        tensor_specs = {}
    if scope in ("full_layer", "full_token"):
        for key in ("program_path", "checkpoint_manifest_path", "placement_path", "all_unit_trace_path", "clock_hz"):
            if not contract.get(key):
                errors.append(f"contract: {key} required for {scope}")
        if not _number(contract.get("clock_hz"), positive=True):
            errors.append("contract: finite positive clock_hz required")
        for key in ("program_path", "checkpoint_manifest_path", "placement_path", "all_unit_trace_path"):
            if contract.get(key) and (not isinstance(contract[key], str) or contract[key] not in pins):
                errors.append(f"contract: {key} must be source-pinned")
        if not tensor_specs:
            errors.append(f"contract: complete integer tensor coverage required for {scope}")
        if scope == "full_layer" and not _integer(contract.get("layer_id")):
            errors.append("contract: exact layer_id required")
        if scope == "full_token" and contract.get("layer_ids") != list(range(40)):
            errors.append("contract: all 40 ordered layer_ids required")
        program_path = contract.get("program_path")
        if isinstance(program_path, str) and program_path in pins and (root / program_path).is_file():
            try:
                program = json.loads((root / program_path).read_text())
                if not isinstance(program, dict):
                    raise ValueError("program manifest must be an object")
                if program.get("status") != "pass" or program.get("instruction_count") != len(contract.get("instruction_ids", [])):
                    errors.append("contract: complete passing program instruction count required")
            except (ValueError, TypeError):
                errors.append("contract: program manifest must be parseable JSON")
    resources = m.get("resources")
    if not isinstance(resources, dict) or not resources:
        errors.append("resources: concrete physical resources required")
        resources = {}
    phys = {}
    phys_meta = {}
    hbm_stack_phys = {}
    for name, r in resources.items():
        if not isinstance(r, dict):
            errors.append(f"resource {name}: malformed")
            continue
        pid, cap, cls, unit = (r.get("physical_id"), r.get("capacity_per_cycle"),
                               r.get("classes"), r.get("unit"))
        if (not isinstance(pid, str) or not pid or not _number(cap, positive=True) or
                not isinstance(cls, list) or not cls or
                any(not isinstance(c, str) or not c for c in cls) or
                not isinstance(unit, str) or not unit):
            errors.append(f"resource {name}: physical_id, capacity, unit and classes required")
            continue
        if pid in phys and phys[pid] != (cap, unit):
            errors.append(f"resource {name}: aliased physical capacity/unit disagrees")
        phys[pid] = (cap, unit)
        if scope in ("full_layer", "full_token"):
            die, area, idle, active = (r.get("owner_die"), r.get("area_mm2"),
                                       r.get("idle_w"), r.get("active_w"))
            if (not _integer(die) or any(not _number(x) for x in (area, idle, active))):
                errors.append(f"resource {name}: concrete die, area and idle/active power required")
            elif pid in phys_meta and phys_meta[pid] != (die, area, idle, active):
                errors.append(f"resource {name}: aliased physical area/power disagrees")
            else:
                phys_meta[pid] = (die, area, idle, active)
        if any(c.endswith("_hbm") for c in cls):
            die, stack = r.get("owner_die"), r.get("stack_id")
            if not _integer(die) or not _integer(stack):
                errors.append(f"resource {name}: concrete HBM die/stack owner required")
            else:
                key = (die, stack)
                if key in hbm_stack_phys and hbm_stack_phys[key] != pid:
                    errors.append(f"resource {name}: same physical HBM stack assigned independent service pools")
                hbm_stack_phys[key] = pid
            evidence = r.get("sustained_service_record")
            if scope in ("full_layer", "full_token") and (not isinstance(evidence, str) or evidence not in pins):
                errors.append(f"resource {name}: source-pinned sustained HBM service record required")
    fragments = m.get("tensor_fragments")
    if not isinstance(fragments, list):
        errors.append("tensor_fragments: explicit list required")
        fragments = []
    covered = defaultdict(list)
    fragment_ids = set()
    fragment_by_id = {}
    for f in fragments:
        if not isinstance(f, dict):
            errors.append("tensor fragment: object required")
            continue
        key = f.get("tensor_id")
        fragment_id = f.get("fragment_id")
        if not isinstance(fragment_id, str) or not fragment_id:
            errors.append(f"tensor fragment {key}: string fragment_id required")
            continue
        if fragment_id in fragment_ids:
            errors.append(f"tensor fragment {key}: unique fragment_id required")
        fragment_ids.add(fragment_id)
        fragment_by_id[fragment_id] = f
        a, b, expert = f.get("row_start"), f.get("row_end"), f.get("expert_id")
        if not isinstance(key, str) or not key or not _integer(a) or not _integer(b, positive=True) or b <= a:
            errors.append(f"tensor fragment {key}: integer nonempty row range required")
            continue
        if expert is not None and not _integer(expert):
            errors.append(f"tensor fragment {key}: fractional/noninteger expert ownership")
        if not _integer(f.get("owner_die")) or not _integer(f.get("owner_cluster")):
            errors.append(f"tensor fragment {key}: concrete die/cluster owner required")
        if not _integer(f.get("physical_bytes"), positive=True):
            errors.append(f"tensor fragment {key}: physical bytes required")
        covered[key].append((a, b))
        if key not in tensor_specs:
            errors.append(f"tensor fragment {key}: absent from tensor_specs")
    for name, spec in tensor_specs.items():
        rows = spec.get("rows") if isinstance(spec, dict) else None
        if not _integer(rows, positive=True):
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
        if not isinstance(op, dict):
            errors.append("operation: object required")
            continue
        oid, kind = op.get("id"), op.get("kind")
        if type(oid) not in (str, int) or oid == "" or oid in by_id:
            errors.append(f"operation {oid}: missing or duplicate id")
            continue
        by_id[oid] = op
        if not isinstance(kind, str) or kind not in KINDS:
            errors.append(f"operation {oid}: unknown kind {kind}")
            continue
        instr = op.get("instruction_id")
        if type(instr) not in (str, int) or instr == "":
            errors.append(f"operation {oid}: instruction binding required")
        else:
            instruction_seen.add(instr)
            if instr not in instruction_ids:
                errors.append(f"operation {oid}: instruction {instr} outside complete program")
        start, end = op.get("start_cycle"), op.get("end_cycle")
        if not _integer(start) or not _integer(end, positive=True) or end <= start:
            errors.append(f"operation {oid}: integer positive interval required")
            continue
        max_end = max(max_end, end)
        ready = op.get("ready_cycle")
        if not _integer(ready) or ready > start:
            errors.append(f"operation {oid}: dependency-ready cycle required")
        else:
            wait_cycles[kind] += start - ready
        if scope in ("full_layer", "full_token") and not isinstance(op.get("stall_reasons"), dict):
            errors.append(f"operation {oid}: measured stall reasons required")
        if not _integer(op.get("die")) or not _integer(op.get("cluster")):
            errors.append(f"operation {oid}: concrete die/cluster required")
        op_die, op_cluster = op.get("die"), op.get("cluster")
        fragment_refs = op.get("tensor_fragment_ids")
        if not isinstance(fragment_refs, list):
            errors.append(f"operation {oid}: tensor fragment binding list required")
            fragment_refs = []
        elif any(not isinstance(t, str) or t not in fragment_ids for t in fragment_refs):
            errors.append(f"operation {oid}: unknown tensor fragment binding")
        elif kind in ("qe_rom", "qe_hbm", "me_rom", "me_hbm", "he_rom", "he_hbm") and not fragment_refs:
            errors.append(f"operation {oid}: weight fragment owner required")
        if kind in ("qe_rom", "me_rom", "he_rom"):
            for fid in fragment_refs:
                f = fragment_by_id.get(fid, {})
                if (f.get("owner_die"), f.get("owner_cluster")) != (op_die, op_cluster):
                    errors.append(f"operation {oid}: ROM fragment {fid} is not local to compute cluster")
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
        if kind in ("qe_rom", "me_rom", "he_rom", "qe_hbm", "me_hbm", "he_hbm"):
            source_class = "weight_rom" if kind.endswith("rom") else "weight_hbm"
            physical_bytes = sum(f["physical_bytes"] for fid in fragment_refs
                                 if (f := fragment_by_id.get(fid)) and isinstance(f.get("physical_bytes"), int))
            if demands.get(source_class, 0) < physical_bytes:
                errors.append(f"operation {oid}: physical weight bytes exceed reserved source demand")
        for cls, amount in demands.items():
            if not _number(amount, positive=True):
                errors.append(f"operation {oid}: positive demand required for {cls}")
        reservations = op.get("reservations")
        if not isinstance(reservations, list):
            errors.append(f"operation {oid}: reservations required")
            continue
        delivered = defaultdict(float)
        for q in reservations:
            if not isinstance(q, dict):
                errors.append(f"operation {oid}: reservation object required")
                continue
            rn, cls = q.get("resource"), q.get("class")
            rs, re, rate = q.get("start_cycle"), q.get("end_cycle"), q.get("rate")
            if not isinstance(rn, str) or not isinstance(cls, str):
                errors.append(f"operation {oid}: string resource and class required")
                continue
            r = resources.get(rn)
            if (not isinstance(r, dict) or not isinstance(r.get("physical_id"), str) or
                    not isinstance(r.get("classes"), list) or
                    cls not in r["classes"] or
                    r.get("physical_id") not in phys):
                errors.append(f"operation {oid}: unbound class/resource {cls}/{rn}")
                continue
            owner_die = r.get("owner_die")
            serves = r.get("serves_clusters")
            if owner_die is not None and owner_die != op_die:
                errors.append(f"operation {oid}: resource {rn} belongs to another die")
            if serves is not None and (not isinstance(serves, list) or op_cluster not in serves):
                errors.append(f"operation {oid}: resource {rn} cannot serve cluster {op_cluster}")
            allowed_experts = r.get("served_expert_ids")
            if allowed_experts is not None and cls in ("quant_mac", "bf16_mac", "weight_rom"):
                if not isinstance(allowed_experts, list):
                    errors.append(f"operation {oid}: resource {rn} expert locality list required")
                    allowed_experts = []
                for fid in fragment_refs:
                    expert = fragment_by_id.get(fid, {}).get("expert_id")
                    if expert is not None and expert not in allowed_experts:
                        errors.append(f"operation {oid}: expert {expert} outside resource {rn} locality")
            if (not _integer(rs) or not _integer(re, positive=True) or
                    not _number(rate, positive=True) or rs < start or re > end or re <= rs):
                errors.append(f"operation {oid}: invalid reservation {rn}")
                continue
            delivered[cls] += rate * (re - rs)
            pid = r["physical_id"]
            events[pid].extend(((rs, rate), (re, -rate)))
            used[pid] += rate * (re - rs)
        for cls, amount in demands.items():
            if _number(amount, positive=True) and delivered[cls] < amount:
                errors.append(f"operation {oid}: under-reserved {cls}: {delivered[cls]} < {amount}")
            if _number(amount, positive=True):
                useful[cls] += amount
        if kind == "verified_collective_stage":
            proof = op.get("exact_stage_record")
            if (not isinstance(proof, dict) or not isinstance(proof.get("path"), str) or
                    proof.get("path") not in pins or proof.get("case") not in ("act", "y") or
                    not _integer(proof.get("input_words"), positive=True) or
                    not _integer(proof.get("output_words"), positive=True) or
                    not _integer(proof.get("tail_cycles"))):
                errors.append(f"operation {oid}: pinned exact stage case required")
            else:
                try:
                    rec = json.loads((root / proof["path"]).read_text())
                    if not isinstance(rec, dict):
                        raise ValueError("record must be an object")
                except (OSError, ValueError, TypeError):
                    errors.append(f"operation {oid}: exact stage record unreadable or malformed")
                    continue
                summary = rec.get("summary")
                case = summary.get(proof["case"], {}) if isinstance(summary, dict) else {}
                if not isinstance(case, dict):
                    case = {}
                source_pins = rec.get("source_sha256")
                if not isinstance(source_pins, dict) or not source_pins:
                    errors.append(f"operation {oid}: exact stage source pins required")
                    source_pins = {}
                for path, digest in source_pins.items():
                    if not isinstance(path, str) or not isinstance(digest, str):
                        errors.append(f"operation {oid}: malformed exact stage source pin")
                        continue
                    f = root / path
                    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest() != digest:
                        errors.append(f"operation {oid}: exact stage source mismatch {path}")
                cases = rec.get("cases")
                selected = [x for x in cases if isinstance(x, dict) and
                            x.get("case") == proof["case"] + "_d128_q2_blocked_pairwise"] if isinstance(cases, list) else []
                exact_case = selected[0] if len(selected) == 1 else {}
                faults = exact_case.get("faults")
                if (len(selected) != 1 or exact_case.get("passed") is not True or
                        exact_case.get("mismatches") != 0 or
                        not isinstance(faults, list) or len(faults) != 4 or any(x != 0 for x in faults)):
                    errors.append(f"operation {oid}: exact selected stage has no passing case")
                if (case.get("selected_tail_cycles") != proof.get("tail_cycles") or
                    case.get("input_words_per_die") != proof.get("input_words") or
                    case.get("output_words_per_die") != proof.get("output_words") or
                    exact_case.get("exposed_tail_cycles") != proof.get("tail_cycles") or
                    exact_case.get("words_per_die") != proof.get("input_words") or
                    exact_case.get("link_bytes_per_word") != 64 or
                    exact_case.get("rx_depth_words") != 128 or
                    end - start < proof["input_words"] + proof["tail_cycles"]):
                    errors.append(f"operation {oid}: stage interval or measured case mismatch")
    missing = set(instruction_ids) - instruction_seen
    if missing:
        errors.append(f"program instructions not scheduled: {sorted(missing, key=str)[:8]}")
    for oid, op in by_id.items():
        for dep in op.get("deps") if isinstance(op.get("deps"), list) else []:
            dep_end = by_id[dep].get("end_cycle") if type(dep) in (str, int) and dep in by_id else None
            start = op.get("start_cycle")
            if (not _integer(dep_end, positive=True) or not _integer(start) or
                    dep_end > start):
                errors.append(f"operation {oid}: unmet dependency {dep}")
    peak = {}
    power_events = defaultdict(list)
    for pid, steps in events.items():
        occ = 0
        for cycle, delta in sorted(steps, key=lambda x: (x[0], x[1])):
            occ += delta
            peak[pid] = max(peak.get(pid, 0), occ)
            if occ > phys.get(pid, (0, None))[0] + 1e-9:
                errors.append(f"physical resource {pid}: over capacity at cycle {cycle}")
                break
            if pid in phys_meta:
                die, _area, _idle, active = phys_meta[pid]
                power_events[die].append((cycle, pid, occ > 0, active))
    die_area = defaultdict(float)
    die_peak_power = defaultdict(float)
    if scope in ("full_layer", "full_token"):
        area_limits = contract.get("area_limit_mm2_by_die")
        power_limits = contract.get("power_limit_w_by_die")
        fixed_areas = contract.get("fixed_area_mm2_by_die")
        fixed_powers = contract.get("fixed_power_w_by_die")
        if not all(isinstance(x, dict) for x in (area_limits, power_limits, fixed_areas, fixed_powers)):
            errors.append("contract: die area/power limits and fixed overheads required")
        else:
            for die, area, idle, _active in phys_meta.values():
                die_area[die] += area
            for die in set(d for d, *_ in phys_meta.values()):
                key = str(die)
                vals = [x.get(key) for x in (area_limits, power_limits, fixed_areas, fixed_powers)]
                if any(not _number(v) for v in vals):
                    errors.append(f"die {die}: concrete nonnegative area/power contract required")
                    continue
                die_area[die] += fixed_areas[key]
                if die_area[die] > area_limits[key] + 1e-9:
                    errors.append(f"die {die}: physical area exceeds limit")
                static_power = fixed_powers[key] + sum(meta[2] for meta in phys_meta.values() if meta[0] == die)
                active_by_pid = {}
                die_peak_power[die] = static_power
                for _cycle, pid, active_flag, active_w in sorted(power_events[die], key=lambda e: (e[0], e[2])):
                    active_by_pid[pid] = active_w if active_flag else 0.0
                    total = static_power + sum(active_by_pid.values())
                    die_peak_power[die] = max(die_peak_power[die], total)
                    if total > power_limits[key] + 1e-9:
                        errors.append(f"die {die}: simultaneous power exceeds cooling limit")
                        break
    queues = m.get("queues")
    if not isinstance(queues, dict):
        errors.append("queues: explicit queue ledger required")
        queues = {}
    for name, q in queues.items():
        if (not isinstance(q, dict) or not _integer(q.get("depth"), positive=True) or
                not isinstance(q.get("events"), list)):
            errors.append(f"queue {name}: depth and events required")
            continue
        occ = 0
        valid_events = []
        for ev in q["events"]:
            if not isinstance(ev, dict) or not _integer(ev.get("cycle")) or not isinstance(ev.get("delta"), int) or type(ev.get("delta")) is bool or ev["delta"] == 0:
                errors.append(f"queue {name}: cycle and nonzero integer delta required")
                continue
            oid = ev.get("op")
            declared = by_id[oid].get("queue_ids") if type(oid) in (str, int) and oid in by_id else None
            if (type(oid) not in (str, int) or oid not in by_id or
                    not isinstance(declared, list) or name not in declared):
                errors.append(f"queue {name}: event not bound to a queue-using operation")
                continue
            op = by_id[oid]
            start, end = op.get("start_cycle"), op.get("end_cycle")
            if not _integer(start) or not _integer(end, positive=True) or not (start <= ev["cycle"] <= end):
                errors.append(f"queue {name}: event outside operation interval")
                continue
            valid_events.append(ev)
        for ev in sorted(valid_events, key=lambda e: (e["cycle"], e["delta"])):
            occ += ev["delta"]
            if occ < 0 or occ > q["depth"]:
                errors.append(f"queue {name}: underflow/overflow at cycle {ev.get('cycle')}")
        if occ != 0:
            errors.append(f"queue {name}: nonempty at completion")
    for oid, op in by_id.items():
        queue_ids = op.get("queue_ids")
        if queue_ids is None:
            queue_ids = []
        elif not isinstance(queue_ids, list):
            errors.append(f"operation {oid}: queue_ids must be a list")
            continue
        for queue_id in queue_ids:
            if type(queue_id) not in (str, int) or queue_id not in queues:
                errors.append(f"operation {oid}: missing shared-service queue {queue_id}")
            elif scope in ("full_layer", "full_token"):
                queue = queues[queue_id]
                events_for_queue = queue.get("events", []) if isinstance(queue, dict) else []
                if not any(isinstance(ev, dict) and ev.get("op") == oid for ev in events_for_queue):
                    errors.append(f"operation {oid}: queue {queue_id} has no bound events")
    return {
        "status": "pass_resource_witness" if not errors else "blocked",
        "errors": errors,
        "scope": scope,
        "makespan_cycles": max_end if not errors else None,
        "physical_peak_per_cycle": peak,
        "physical_reserved_fraction": {k: used[k] / (max_end * phys[k][0]) for k in used} if max_end else {},
        "useful_demand_by_class": dict(useful),
        "wait_cycles_by_kind": dict(wait_cycles),
        "die_area_mm2": dict(die_area),
        "die_peak_power_w": dict(die_peak_power),
        "claim_boundary": "A passing operator subset cannot establish full-layer/token rate; no physical timing or power is inferred.",
    }


def main():
    manifest = Path(sys.argv[1])
    result = audit(json.loads(manifest.read_text()))
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "pass_resource_witness" else 1)


if __name__ == "__main__":
    main()
