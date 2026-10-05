#!/usr/bin/env python3
"""Check a model profile's KV traffic against a reference engine that ran it.

The KV term decides the ROM argument at long context, and for a sparse model it
is the hardest part of a profile to get right: the read set is not the context,
it is whatever the model's own routing selected. Reading the released
implementation and writing down what it *appears* to do is not the same as
running it and counting, and this tool exists because those two disagreed.

It compares three things per rung, because they fail differently:

  positions   the (layer, position) pairs each attention kind visited, which
              catches a wrong sparsity structure -- a window modelled where a
              compressed full-context scan belongs, or the reverse
  entry size  bytes per visited pair, which catches a KV row read at the wrong
              precision or width
  total       the product, which is what a roofline actually divides by
              bandwidth

A structural error and an entry-size error look identical in the total and have
completely different fixes, so the total alone is not a diagnosis.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "src"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from opentallas.schema import ModelProfile  # noqa: E402
from opentallas.workload import kv_traffic  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402

#: The KV term carries no scales or index tables riding along, so unlike weight
#: traffic it is expected to agree closely.  A rung outside this is a defect in
#: the profile, not a tolerance to widen.
TOLERANCE = 0.01


def _measured_rungs(body: dict[str, Any]) -> list[dict[str, Any]]:
    rungs = []
    for name, rung in sorted(body.get("results", {}).items()):
        steps = (rung.get("kv_measurement") or {}).get("decode_steps") or []
        if not steps:
            continue
        step = steps[0]
        by_kind: dict[str, dict[str, float]] = defaultdict(
            lambda: {"layers": 0, "pairs": 0, "bytes": 0}
        )
        for layer in step.get("per_layer", {}).values():
            entry = by_kind[layer["kind"]]
            entry["layers"] += 1
            entry["pairs"] += layer.get("main_pairs", 0) + layer.get("index_pairs", 0)
            entry["bytes"] += layer.get("main_bytes", 0) + layer.get("index_bytes", 0)
        rungs.append(
            {
                "workload_id": name,
                "context_tokens": int(step["context_tokens"]),
                "measured_bytes": int(step["measured"]["total_kv_bytes_read"]),
                "by_kind": {k: dict(v) for k, v in sorted(by_kind.items())},
            }
        )
    return rungs


#: The roles the V4.1 reference-oracle probe measures, and the
#: :class:`AttentionGroup` field each one prices.  A ``window`` group charges its
#: window entry in ``entry_bytes``; a ``compressed_sparse`` group charges the
#: compressed main entry there and its window in ``window_entry_bytes``.
_WIDTH_FIELD_BY_ROLE = {
    "main": "entry_bytes",
    "index": "index_entry_bytes",
    "window": "window_entry_bytes",
}


def _measured_widths(probe: dict[str, Any]) -> dict[str, int]:
    """Lift the executed entry widths out of a reference-oracle probe.

    Refuses anything that is not a completed probe carrying widths at grade
    ``executed``: a width read from a refused or partial run is not a
    measurement, and writing it back would launder a failure into a profile.
    """
    if probe.get("schema") != "opentallas.abi3.reference_oracle.v1":
        raise SystemExit(
            f"{probe.get('schema')!r} is not opentallas.abi3.reference_oracle.v1"
        )
    if probe.get("status") != "completed":
        raise SystemExit(
            f"the probe status is {probe.get('status')!r}; only a completed run "
            "carries a measurement"
        )
    entry_widths = probe.get("entry_widths") or {}
    measured = entry_widths.get("measured") or {}
    if measured.get("grade") != "executed":
        raise SystemExit(
            f"the probe's widths are graded {measured.get('grade')!r}, not 'executed'"
        )
    widths = measured.get("measured_entry_bytes") or {}
    missing = sorted(set(_WIDTH_FIELD_BY_ROLE) - set(widths))
    if missing:
        raise SystemExit(
            "the probe measured no width for: " + ", ".join(missing)
        )
    for role, value in widths.items():
        if not isinstance(value, int) or value <= 0:
            raise SystemExit(f"the measured {role} width {value!r} is not a positive int")
    return {role: int(widths[role]) for role in _WIDTH_FIELD_BY_ROLE}


def write_measured_widths(
    probe_path: Path,
    model_path: Path,
    profile_out: Path,
    report_out: Path,
    *,
    force: bool,
) -> tuple[int, dict[str, Any]]:
    """Write the probe's measured entry widths into a COPY of the profile.

    Gate DS41-X4 asks for "the measured main, index and window entry widths
    written into the profile with grade ``executed``, replacing the read-off
    widths".  This does exactly that -- and writes the result to a NEW path,
    never over the input profile, because the substitution is not a correction
    and the difference matters:

    * the RECIPE width is the serving format the model card and technical report
      describe, and it is what the roofline currently divides by;
    * the MEASURED width is what the pinned reference implementation's own cache
      holds, which for V4.1 is bfloat16 throughout, because
      ``fp4_act_quant(inplace=True)`` and ``act_quant(inplace=True)`` write
      DEQUANTIZED values back at the input dtype.

    Substituting one for the other changes every roofline number derived from the
    profile, so this emits a PROPOSAL plus a side-by-side record and leaves the
    adoption decision to whoever owns the profile.  The V4 program did not
    substitute: it kept both and reported ``format_normalised_byte_ratio``.  That
    disagreement with the gate's wording is recorded in the report rather than
    resolved here.

    ``evidence`` is the profile's own grade field, so each touched group's
    evidence string is rewritten to name the executed record.
    """
    for path, label in ((profile_out, "profile"), (report_out, "report")):
        if path.exists() and not force:
            raise SystemExit(f"refusing to overwrite the {label} {path}; pass --force")
    if profile_out.resolve() == model_path.resolve():
        raise SystemExit(
            "the proposed profile must not be written over the input profile: the "
            "measured width is a different quantity from the recipe width, not a "
            "correction of it"
        )

    probe = json.loads(probe_path.read_text())
    widths = _measured_widths(probe)
    document = json.loads(model_path.read_text())
    groups = document.get("attention_groups")
    if not isinstance(groups, list) or not groups:
        raise SystemExit(f"{model_path} carries no attention_groups")

    provenance = (
        "measured by executing the pinned vendor modules at the released "
        f"geometry; see {probe_path.as_posix()} entry_widths.measured "
        "(grade executed)"
    )
    rows: list[dict[str, Any]] = []
    for index, group in enumerate(groups):
        label = group.get("label") or group.get("kind")
        changes: list[dict[str, Any]] = []
        #: A window group prices its window entry in entry_bytes; a compressed
        #: group prices the main entry there.  The mapping follows the group's
        #: own kind rather than its label, so a renamed group still maps.
        roles = (
            {"window": "entry_bytes"}
            if group.get("kind") == "window"
            else dict(_WIDTH_FIELD_BY_ROLE)
        )
        for role, field in sorted(roles.items()):
            if field not in group:
                continue
            recipe = group[field]
            #: A group that charges nothing for a role does not have that role.
            #: Writing a width into it would invent traffic it never had.
            if not recipe:
                continue
            measured = widths[role]
            group[field] = float(measured)
            changes.append(
                {
                    "role": role,
                    "field": field,
                    "recipe_entry_bytes": float(recipe),
                    "measured_entry_bytes": measured,
                    "measured_over_recipe": measured / float(recipe),
                }
            )
        if changes:
            group["evidence"] = provenance
            rows.append(
                {
                    "group_index": index,
                    "label": label,
                    "kind": group.get("kind"),
                    "count": group.get("count"),
                    "changes": changes,
                }
            )

    if not rows:
        raise SystemExit("no attention group priced any of the measured roles")

    report = {
        "schema": "opentallas.roofline.kv_measured_widths.v1",
        "grade": "executed",
        "probe": probe_path.as_posix(),
        "probe_revision": probe.get("revision"),
        "input_profile": model_path.as_posix(),
        "proposed_profile": profile_out.as_posix(),
        "adopted": False,
        "measured_entry_bytes": widths,
        "measured_provenance": (
            probe.get("entry_widths", {}).get("measured", {}).get("method")
        ),
        "groups": rows,
        "why_this_is_a_proposal_and_not_an_edit": [
            "the recipe width is the serving format the release describes; the "
            "measured width is what the pinned reference implementation's cache "
            "holds, and for V4.1 those differ because both in-place quantizers "
            "write dequantized values back at the input dtype",
            "substituting one for the other changes every roofline number derived "
            "from this profile",
            "the V4 program kept both and reported format_normalised_byte_ratio "
            "rather than substituting; gate DS41-X4's wording says replace, and "
            "that disagreement is recorded here rather than resolved",
        ],
        "not_established": [
            "that the accelerator should store KV at the measured width",
            "any KV traffic total: no decode step was measured, because the token "
            "ladder did not run",
        ],
    }
    profile_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.parent.mkdir(parents=True, exist_ok=True)
    profile_out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    report_out.write_bytes(canonical_json(report))

    #: The proposal must still load: a profile the loader rejects is not a
    #: proposal, it is a broken file.
    reloaded = ModelProfile.load(profile_out)
    report["proposed_profile_loads"] = True
    report["proposed_profile_layers"] = reloaded.num_layers
    report_out.write_bytes(canonical_json(report))

    print(f"measured entry widths from {probe_path}")
    for role in sorted(widths):
        print(f"  {role:>6}: {widths[role]:>6,} B  (grade executed)")
    for row in rows:
        print(f"  group {row['label']} x{row['count']}")
        for change in row["changes"]:
            print(
                f"      {change['role']:>6} {change['field']:<20} "
                f"recipe {change['recipe_entry_bytes']:>8,.1f} -> measured "
                f"{change['measured_entry_bytes']:>6,} B "
                f"({change['measured_over_recipe']:.4f}x)"
            )
    print(f"  proposed profile -> {profile_out} (loads, {reloaded.num_layers} layers)")
    print(f"  record           -> {report_out}")
    print("  adopted: NO. This is a proposal; see why_this_is_a_proposal_and_not_an_edit")
    return 0, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--write-measured-widths",
        type=Path,
        metavar="PROPOSED_PROFILE",
        help=(
            "instead of the traffic comparison, write the probe's measured entry "
            "widths into a COPY of the profile at this path, with grade "
            "'executed', and emit the side-by-side record to --output. Never "
            "writes over --model"
        ),
    )
    args = parser.parse_args()

    if args.write_measured_widths is not None:
        code, _ = write_measured_widths(
            args.oracle,
            args.model,
            args.write_measured_widths,
            args.output,
            force=args.force,
        )
        return code

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force")
        return 1

    model = ModelProfile.load(args.model)
    rungs = _measured_rungs(json.loads(args.oracle.read_text()))
    if not rungs:
        print("the oracle artifact carries no KV measurement; nothing to check")
        return 1

    results, problems = [], []
    for rung in rungs:
        predicted = kv_traffic(model, rung["context_tokens"]).read_bytes
        ratio = rung["measured_bytes"] / predicted if predicted else 0.0
        rung["predicted_bytes"] = predicted
        rung["ratio"] = ratio
        rung["bytes_per_pair_by_kind"] = {
            kind: (v["bytes"] / v["pairs"] if v["pairs"] else 0.0)
            for kind, v in rung["by_kind"].items()
        }
        if abs(ratio - 1.0) > TOLERANCE:
            problems.append(
                f"{rung['workload_id']} at {rung['context_tokens']:,} tokens: the profile "
                f"predicts {predicted:,.0f} KV bytes per step where the engine read "
                f"{rung['measured_bytes']:,} ({ratio:.3f}x)"
            )
        results.append(rung)

    out = {
        "schema": "opentallas.roofline.kv_model_validation.v1",
        "status": "pass" if not problems else "fail",
        "model": model.name,
        "oracle": str(args.oracle),
        "tolerance": TOLERANCE,
        "rungs": results,
        "problems": problems,
        "scope": [
            "Validates the KV read traffic a profile predicts against the traffic the"
            " released implementation performed. Does not validate weights, arithmetic"
            " or time.",
            "Per-kind bytes-per-pair are reported so a structural error and an entry-size"
            " error can be told apart; they look identical in the total.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(out))

    print(f"{model.name} KV model vs the engine that ran it")
    for rung in results:
        print(f"  {rung['context_tokens']:>9,} tokens  measured {rung['measured_bytes']:>15,}"
              f"  predicted {rung['predicted_bytes']:>15,.0f}  ratio {rung['ratio']:.4f}")
        for kind, per in sorted(rung["bytes_per_pair_by_kind"].items()):
            k = rung["by_kind"][kind]
            print(f"      {kind:<8} {k['layers']:>3.0f} layers  {k['pairs']:>10,.0f} pairs"
                  f"  {per:>7,.0f} B/pair")
    print(f"  status {out['status']} -> {args.output}")
    for problem in problems:
        print(f"  PROBLEM {problem}")
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
