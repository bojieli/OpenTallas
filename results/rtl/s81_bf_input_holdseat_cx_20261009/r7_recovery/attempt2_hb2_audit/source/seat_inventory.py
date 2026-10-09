"""Read-only HB2 inventory audit of immutable, completed OpenDB checkpoints."""
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import re

import odb

MASTER = "HB2xp67_ASAP7_75t_R"
MAPPED = Path(os.environ["OT_H7_MAPPED"])
BASELINE = Path(os.environ["OT_H7_BASELINE"])
CHECKPOINT = Path(os.environ["OT_H7_CHECKPOINT"])
OUT = Path(os.environ["OT_H7_AUDIT_OUT"])
PATTERN = re.compile(r"^g_pin\.u_hs_(control|data)\.g_seat\[(\d+)\]\.g_bit\[(\d+)\]\.u_hb$")


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def normalize(name):
    return name.replace("\\", "").replace("/", ".")


def original_inventory():
    rows = {}
    previous = deque(maxlen=8)
    with MAPPED.open() as stream:
        for line in stream:
            match = re.match(r"\s*(\S+)\s+(\\?\S+)\s+\(", line)
            if match:
                master, raw_name = match.groups()
                name = normalize(raw_name)
                if PATTERN.fullmatch(name):
                    if name in rows:
                        raise RuntimeError(f"Duplicate normalized mapped name: {name}")
                    attribute_lines = []
                    for previous_line in reversed(previous):
                        if not previous_line.lstrip().startswith("(*"):
                            break
                        attribute_lines.append(previous_line)
                    attributes = "".join(reversed(attribute_lines))
                    rows[name] = {
                        "raw_name": raw_name, "master": master,
                        "raw_attributes": attributes.splitlines(),
                        "keep": bool(re.search(r"keep\s*=\s*32'b0*1\s*\*\)", attributes)),
                        "dont_touch": bool(re.search(r"dont_touch\s*=\s*32'b0*1\s*\*\)", attributes)),
                    }
            previous.append(line)
    return rows


def db_inventory(path):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    block = db.getChip().getBlock()
    rows = {}
    for inst in block.getInsts():
        raw_name = inst.getName()
        name = normalize(raw_name)
        if PATTERN.fullmatch(name):
            if name in rows:
                raise RuntimeError(f"Duplicate normalized ODB name: {name}")
            supported = hasattr(inst, "isDoNotTouch")
            rows[name] = {
                "raw_name": raw_name, "master": inst.getMaster().getName(),
                "is_do_not_touch_supported": supported,
                "is_do_not_touch": bool(inst.isDoNotTouch()) if supported else None,
            }
    odb.dbDatabase.destroy(db)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    before = {str(path): digest(path) for path in (MAPPED, BASELINE, CHECKPOINT)}
    original = original_inventory()
    baseline = db_inventory(BASELINE)
    current = db_inventory(CHECKPOINT)
    expected = {
        f"g_pin.u_hs_{family}.g_seat[{seat}].g_bit[{bit}].u_hb"
        for family, width in (("control", 4), ("data", 1668))
        for seat in range(4) for bit in range(width)
    }
    discrepancies = {
        "mapped_missing": sorted(expected - original.keys()),
        "mapped_extra": sorted(original.keys() - expected),
        "baseline_missing": sorted(original.keys() - baseline.keys()),
        "baseline_extra": sorted(baseline.keys() - original),
        "checkpoint_missing": sorted(original.keys() - current.keys()),
        "checkpoint_extra": sorted(current.keys() - original),
        "wrong_masters": [name for name in sorted(original)
                          if original[name]["master"] != MASTER
                          or baseline.get(name, {}).get("master") != MASTER
                          or current.get(name, {}).get("master") != MASTER],
        "missing_mapped_attributes": [name for name in sorted(original)
                                      if not original[name]["keep"] or not original[name]["dont_touch"]],
        "db_protection_lost": [name for name in sorted(original.keys() & baseline.keys() & current.keys())
                               if baseline[name]["is_do_not_touch"] is True
                               and current[name]["is_do_not_touch"] is not True],
    }
    after = {str(path): digest(path) for path in (MAPPED, BASELINE, CHECKPOINT)}
    receipt = {
        "schema": "opentallas.h7.completed_checkpoint_seat_inventory.v1",
        "read_only": True, "expected_master": MASTER, "expected_count": 6688,
        "mapped_count": len(original), "baseline_count": len(baseline),
        "checkpoint_count": len(current),
        "mapped_keep_and_dont_touch_count": sum(r["keep"] and r["dont_touch"] for r in original.values()),
        "baseline_db_do_not_touch_count": sum(r["is_do_not_touch"] is True for r in baseline.values()),
        "checkpoint_db_do_not_touch_count": sum(r["is_do_not_touch"] is True for r in current.values()),
        "checkpoint_db_protection_api_supported_count": sum(r["is_do_not_touch_supported"] for r in current.values()),
        "all_checkpoint_db_protected": len(current) == 6688 and all(r["is_do_not_touch"] is True for r in current.values()),
        "db_protection_changes": [name for name in sorted(original.keys() & baseline.keys() & current.keys())
                                  if baseline[name]["is_do_not_touch"] != current[name]["is_do_not_touch"]
                                  or baseline[name]["is_do_not_touch_supported"] != current[name]["is_do_not_touch_supported"]],
        "discrepancies": discrepancies, "input_sha256_before": before,
        "input_sha256_after": after, "inputs_unchanged": before == after,
        "protection_note": "Mapped keep/dont_touch and actual OpenDB protection flags are separate observations. Retained count alone does not establish protection.",
    }
    receipt["inventory_and_protection_equivalence"] = before == after and not any(discrepancies.values())
    (OUT / "inventory.json").write_text(json.dumps({"mapped": original, "baseline": baseline, "checkpoint": current}, indent=2) + "\n")
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    if not receipt["inventory_and_protection_equivalence"]:
        raise SystemExit(1)


main()
