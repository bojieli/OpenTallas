#!/usr/bin/env python3
"""Join genuine lowered SU words to actual shared-VM arrival phases.

This is a source/schedule guard, not a simulation or a transport-pad generator.
The native bank takes row/bank authority from lane0; waiting for a later command
cannot repair an unequal phase within one eight-lane write group.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import dv_lower as D


def selected_word(path, stage, slice_id, user, pidx):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    st = next(x for x in data["stages"] if x["stage"] == stage)
    sl = next(x for x in st["slices"] if x["slice"] == slice_id)
    row = next(x for x in sl["prog_users"][user] if x["addr"] == pidx // 2)
    word = (int(row["payload_hex"], 16) >> (512 * (pidx % 2))) & ((1 << 457) - 1)
    return D.su_unpack(word), {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                              "stage": stage, "slice": slice_id, "user": user, "pidx": pidx,
                              "su_word_hex": format(word, "0115x")}


def compose(word, phases):
    if len(phases) != 8 or any(type(v) is not int or v < 0 for v in phases):
        raise ValueError("actual command-metadata plus normal-write phases need eight nonnegative integers")
    if word["dst"] != 1 or word["d"] >> 22 != 0:
        raise ValueError("descriptor is not a normal window00 VM writer")
    if word["nin"] < 1 or word["nout"] < 1:
        raise ValueError("empty native vector descriptor")
    if word["red"] or word["redsq"]:
        raise ValueError("reduction publication requires the separately selected RED/CTL path")
    groups = []
    violations = []
    for row in range(word["nout"]):
        for v in range((word["nin"] + 7) // 8):
            active = [lane for lane in range(8) if (v << 3) + lane < word["nin"]]
            addresses = {lane: word["d"] + row * word["dso"] + ((v << 3) + lane) * word["dsi"] for lane in active}
            same_bank_row = all(addr >> 3 == addresses[0] >> 3 for addr in addresses.values())
            same_phase = len({phases[lane] for lane in active}) == 1
            if not same_bank_row or not same_phase:
                violations.append({"row": row, "vector_group": v, "same_bank_row": same_bank_row,
                                   "same_arrival_phase": same_phase})
            groups.append({"row": row, "vector_group": v, "active_lanes": active,
                           "addresses": addresses, "arrival_phases": [phases[lane] for lane in active]})
    target = max(phases)
    return {"schema": "opentallas.qwen.native-vm-write-phase-join.v1",
            "status": "PASS_STATIC_SOURCE_JOIN" if not violations else "FAIL_SHARED_BANK_PHASE",
            "native_live_law": "((v << 3) + gl < nin_r), LS3/SW8",
            "native_bank_law": "lane0 must be active; every enabled lane address[23:3] equals lane0",
            "word": word, "actual_command_plus_write_phases": phases,
            "groups": groups, "violations": violations,
            "required_coherent_tuple_pad": [target - phase for phase in phases],
            "pad_scope": "enable/address/data together on every actual VM replica; computed demand only, not applied source",
            "compiler_wait_repairs_phase": False,
            "native_lrly_edges_already_in_measured_ages": 3,
            "native_mif1_commit_suffix_after_lrly_receiver": 5,
            "native_compiler_margin": 8,
            "publication_note": "Do not add LRLY3 again or blindly add suffix5 atop existing margin8. Consumer request path and actual normal/reduction endpoints must compose separately.",
            "qualification": "Static actual-descriptor/source join only. A positive does not replace native bank exactness, emitted tuple-pad identity, final physical transport, or programme gates."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tables", type=Path, required=True)
    parser.add_argument("--stage", type=int, required=True)
    parser.add_argument("--slice", type=int, required=True)
    parser.add_argument("--user", type=int, default=0)
    parser.add_argument("--pidx", type=int, required=True)
    parser.add_argument("--phases", required=True, help="eight actual command+write phases, comma separated")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError("output exists: preserve earlier verdict")
        word, source = selected_word(args.tables, args.stage, args.slice, args.user, args.pidx)
        result = compose(word, [int(x) for x in args.phases.split(",")])
        result["selected_programme"] = source
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": result["status"], "groups": len(result["groups"]),
                          "violations": len(result["violations"]), "required_tuple_pad": result["required_coherent_tuple_pad"]}))
        return 0 if not result["violations"] else 2
    except (ValueError, KeyError, StopIteration, IndexError, OSError) as error:
        parser.exit(2, "VM write phase join refused: " + str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
