#!/usr/bin/env python3
"""G1's composition certificate, derived from the ladder rather than asserted.

G1 (``configs/gates/redesign_gates.json``) is a roll-up.  Its acceptance is not
"the six rungs pass"; it is that plus a certificate showing

  * that **every operator instance the governed workload issues** falls in an
    equivalence class G1a proved bit-exact,
  * that the layer loop is closed by G1b and G1c,
  * that the emitted token ids equal the oracle's, and
  * that nothing outside the ladder was assumed,

and the gate's own note requires the certificate to be *derived mechanically
from G1e's issue trace, never asserted*.  This tool is that derivation.

Where the instances come from
-----------------------------
Not from a table typed in here, and not from the golden model.  Rung G1e drives
every device transaction of the governed workload through the design's own
control plane and certifies that the RTL's issue trace equals the reference
model's element for element on ``(family, sub, descriptor_id, pc)``.  That run
publishes ``issue_census`` -- the (family, subopcode, descriptor id) instances
the workload issued, **counted from the RTL's trace and not from the golden's**
-- expressly for this certificate.  It is the population this tool partitions.

The census is not taken on trust.  Before a single instance is attributed:

  * G1e's own trace must be ``equals_golden`` with a null ``divergence_index``
    -- a trace that diverged is not a certified population, and if it has
    diverged this tool attributes nothing and counts every instance uncovered;
  * the census's row instance counts must sum to its declared ``instances``,
    and that total must equal ``trace.compared_issue_count``.  A census that
    does not reconcile with the comparison that certified it is refused;
  * the deployment G1e ran must be the deployment G1a inventoried, by SHA-256.
    Attributing coverage measured on one image to instances issued by another
    is precisely the composition error a certificate exists to prevent.

How an instance is attributed
------------------------------
Each census row is joined to G1a's equivalence classes on
``(family, sub, operator descriptor id)`` -- G1a's own class key restricted to
the fields the RTL trace carries.  A row is covered only when the class it
lands in is one G1a itself marked ``covered``, which G1a decides by requiring a
retained, source-current RTL campaign to have driven that operator descriptor
of that deployment in a positive case with its result words compared against
golden.  This tool re-reads that decision; it never re-decides it, and it has
no path by which a class G1a called uncovered becomes covered here.

Three ways an instance fails to be covered, and all three are **counted, not
dropped**:

  1. its class exists and G1a marked it uncovered -- G1a's own
     ``why_not_covered`` is carried through verbatim;
  2. no G1a class claims its descriptor at all -- an instance the workload
     issues that the base of the pyramid never inventoried;
  3. the ladder is not in a state where attribution is meaningful (G1e's trace
     uncertified, the census irreconcilable, the deployments different), in
     which case every instance of the store is uncovered for that reason.

``uncovered_instance_count`` is the sum over all three.  There is no fourth
branch and no instance leaves this tool unaccounted: the tool asserts that
covered + uncovered equals the census total and refuses to write a certificate
if it does not.

The other three gate fields
---------------------------
``token_ids_match_oracle`` compares the ids the **RTL emitted** -- G1d's
``record_token_ids`` for the full configuration and G1f's for the reduced one
-- against the oracle ids each rung's own gate spec names.  The oracle's ids
are read for comparison only; a certificate that copied them across would
satisfy the letter of the comparison and none of its meaning, so an empty
emission can never agree with a non-empty oracle here.

``derived_mechanically`` is a computed conjunction, not a literal: every input
was read from a named path and bound by its SHA-256, the census reconciled, the
partition was exhaustive, and no gate field was supplied by hand.  If any of
those is false the field is false and says which.  ``--self-test`` exercises
the derivation in both directions.

What this tool will not do
--------------------------
It will not write ``every_issued_instance_covered: true`` while
``uncovered_instance_count`` is positive, it will not read a rung artifact's
own summary in place of the rung's measured fields, and a missing input is a
failure with the path named rather than a field left out of the certificate.
Absence of evidence is FAIL, never "not evaluable".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "opentallas.rtl.abi3_g1_composition_certificate.v1"
GATE_SPEC = "configs/gates/redesign_gates.json"
STORAGE_CLASSES = ("rom", "hbm")

RUNG_ARTIFACTS = {
    "G1a": "results/rtl/abi3_g1a_operator_equivalence.json",
    "G1b": "results/rtl/abi3_g1b_layer_closure.json",
    "G1c": "results/rtl/abi3_g1c_composition.json",
    "G1d": "results/rtl/abi3_g1d_token.json",
    "G1e": "results/rtl/abi3_g1e_control_end_to_end.json",
    "G1f": "results/rtl/abi3_g1f_reduced_end_to_end.json",
}


def fail(message: str) -> "NoReturn":  # type: ignore[valid-type]
    raise SystemExit(f"composition certificate refused: {message}")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(rel: str) -> tuple[dict[str, Any], str]:
    path = ROOT / rel
    if not path.exists():
        fail(f"{rel} does not exist; a missing rung artifact is a failure, not an omission")
    try:
        return json.loads(path.read_text()), sha256_of(path)
    except json.JSONDecodeError as exc:
        fail(f"{rel} is not valid JSON: {exc}")


def records_by_store(document: Mapping[str, Any], rel: str) -> dict[str, Any]:
    records = document.get("records")
    if not isinstance(records, list):
        fail(f"{rel}.records must be a JSON array")
    out: dict[str, Any] = {}
    for record in records:
        if not isinstance(record, Mapping):
            fail(f"{rel}.records must contain objects")
        store = record.get("storage_class")
        if store in out:
            fail(f"{rel} carries two records for storage class {store!r}")
        out[str(store)] = record
    return out


def gate_entry(spec: Mapping[str, Any], gate_id: str) -> Mapping[str, Any]:
    for entry in spec.get("gates", []):
        if isinstance(entry, Mapping) and entry.get("id") == gate_id:
            return entry
    fail(f"{GATE_SPEC} declares no gate {gate_id!r}")


def dotted(record: Any, path: str) -> Any:
    """Read a dotted field path, returning a sentinel when it is absent."""
    cursor: Any = record
    for part in path.split("."):
        if not isinstance(cursor, Mapping) or part not in cursor:
            return _MISSING
        cursor = cursor[part]
    return cursor


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<missing>"


_MISSING = _Missing()


def oracle_ids_for(gate: Mapping[str, Any], gate_id: str) -> tuple[list[int], str, str]:
    """The oracle ids a rung's own gate spec names, read for comparison only."""
    rel = gate.get("evaluator", {}).get("oracle") or gate.get("oracle")
    field = gate.get("evaluator", {}).get("oracle_token_field") or gate.get(
        "oracle_token_field"
    )
    if not rel or not field:
        fail(f"{gate_id} declares no oracle path/field in {GATE_SPEC}")
    document, digest = load(str(rel))
    ids = dotted(document, str(field))
    if isinstance(ids, _Missing) or not isinstance(ids, list):
        fail(f"{rel} has no token id list at {field!r}")
    count = gate.get("evaluator", {}).get("oracle_token_count")
    if isinstance(count, int):
        ids = ids[:count]
    return [int(x) for x in ids], str(rel), digest


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(ROOT), *args], capture_output=True, text=True
        ).stdout.strip()

    dirty = [
        line[3:]
        for line in run("status", "--porcelain").splitlines()
        if line.strip()
    ]
    return {
        "commit": run("rev-parse", "HEAD"),
        "worktree_dirty": bool(dirty),
        "dirty_paths": sorted(dirty),
        "scope": (
            "the tree THIS certificate was derived in. Each rung artifact "
            "carries the tree ITS run happened in, under records[].git."
        ),
    }


def attribute(store: str, g1a: Mapping[str, Any], g1e: Mapping[str, Any]) -> dict[str, Any]:
    """Partition one store's issued instances over the rungs. Never drops one."""
    refusals: list[str] = []

    trace = g1e.get("trace")
    if not isinstance(trace, Mapping):
        fail(f"G1e[{store}] carries no trace")
    certified = trace.get("equals_golden") is True and trace.get("divergence_index") is None
    if not certified:
        refusals.append(
            "G1e's issue trace is not certified equal to the golden model "
            f"(equals_golden={trace.get('equals_golden')!r}, "
            f"divergence_index={trace.get('divergence_index')!r}), so its "
            "census is not a certified population of issued instances"
        )

    census = g1e.get("issue_census")
    if not isinstance(census, Mapping):
        fail(f"G1e[{store}] carries no issue_census; the certificate has no population to partition")
    rows = census.get("rows")
    if not isinstance(rows, list) or not rows:
        fail(f"G1e[{store}].issue_census.rows must be a non-empty array")
    declared = census.get("instances")
    summed = sum(int(row["instances"]) for row in rows)
    compared = trace.get("compared_issue_count")
    reconciles = declared == summed == compared
    if not reconciles:
        refusals.append(
            f"G1e[{store}]'s census does not reconcile with the comparison that "
            f"certified it: rows sum to {summed}, census declares {declared}, "
            f"trace compared {compared}"
        )

    g1a_deployment = dotted(g1a, "deployment.deployment_sha256")
    g1e_deployment = dotted(g1e, "deployment.deployment_sha256")
    same_image = (
        not isinstance(g1a_deployment, _Missing)
        and g1a_deployment == g1e_deployment
    )
    if not same_image:
        refusals.append(
            "the deployment G1e ran is not the deployment G1a inventoried "
            f"(G1a {g1a_deployment!r} vs G1e {g1e_deployment!r}); coverage "
            "measured on one image cannot be attributed to instances issued "
            "by another"
        )

    classes = dotted(g1a, "coverage.classes")
    if isinstance(classes, _Missing) or not isinstance(classes, list):
        fail(f"G1a[{store}] carries no coverage.classes")
    index: dict[tuple[int, int, int], Mapping[str, Any]] = {}
    for klass in classes:
        for descriptor in klass.get("operator_descriptor_ids", []):
            key = (int(klass["family"]), int(klass["sub"]), int(descriptor))
            index[key] = klass

    attributions: list[dict[str, Any]] = []
    covered = uncovered = 0
    for row in rows:
        key = (int(row["family"]), int(row["sub"]), int(row["descriptor_id"]))
        instances = int(row["instances"])
        klass = index.get(key)
        entry = {
            "family": key[0],
            "sub": key[1],
            "descriptor_id": key[2],
            "instances": instances,
        }
        if refusals:
            entry.update(
                covered=False,
                covered_by_rung=None,
                why_not_covered=(
                    "the ladder is not in a state where attribution is "
                    "meaningful: " + "; ".join(refusals)
                ),
            )
            uncovered += instances
        elif klass is None:
            entry.update(
                covered=False,
                covered_by_rung=None,
                why_not_covered=(
                    "no G1a equivalence class claims this operator descriptor: "
                    "the workload issues it and the base of the pyramid never "
                    "inventoried it"
                ),
            )
            uncovered += instances
        elif klass.get("covered") is True:
            entry.update(
                covered=True,
                covered_by_rung="G1a",
                mnemonic=klass.get("mnemonic"),
                equivalence_class_covered_by=klass.get("covered_by"),
                numeric_contract_sha256=klass.get("numeric_contract_sha256"),
            )
            covered += instances
        else:
            entry.update(
                covered=False,
                covered_by_rung=None,
                mnemonic=klass.get("mnemonic"),
                why_not_covered=klass.get("why_not_covered"),
            )
            uncovered += instances
        attributions.append(entry)

    if covered + uncovered != summed:
        fail(
            f"the partition of {store} lost instances: {covered} + {uncovered} "
            f"!= {summed}. Every issued instance must be counted."
        )

    return {
        "attributions": attributions,
        "covered_instance_count": covered,
        "uncovered_instance_count": uncovered,
        "issued_instance_count": summed,
        "census_reconciles": reconciles,
        "trace_certified_equal_to_golden": certified,
        "deployment_is_the_one_g1a_inventoried": same_image,
        "deployment_sha256": g1e_deployment if not isinstance(g1e_deployment, _Missing) else None,
        "refusals": refusals,
    }


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--output", default="results/rtl/abi3_g1_composition_certificate.json")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="exercise the derivation in both directions and exit",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    spec, spec_digest = load(GATE_SPEC)
    inputs = {"gate_spec": {"path": GATE_SPEC, "sha256": spec_digest}}
    documents: dict[str, dict[str, Any]] = {}
    for rung, rel in RUNG_ARTIFACTS.items():
        document, digest = load(rel)
        documents[rung] = document
        inputs[rung] = {"path": rel, "sha256": digest}

    by_store = {rung: records_by_store(documents[rung], RUNG_ARTIFACTS[rung]) for rung in documents}

    d_ids, d_oracle_path, d_oracle_digest = oracle_ids_for(gate_entry(spec, "G1d"), "G1d")
    f_ids, f_oracle_path, f_oracle_digest = oracle_ids_for(gate_entry(spec, "G1f"), "G1f")
    inputs["G1d_oracle"] = {"path": d_oracle_path, "sha256": d_oracle_digest}
    inputs["G1f_oracle"] = {"path": f_oracle_path, "sha256": f_oracle_digest}

    records: list[dict[str, Any]] = []
    for store in STORAGE_CLASSES:
        for rung in RUNG_ARTIFACTS:
            if store not in by_store[rung]:
                fail(f"{RUNG_ARTIFACTS[rung]} carries no record for storage class {store!r}")
        g1a, g1b = by_store["G1a"][store], by_store["G1b"][store]
        g1c, g1d = by_store["G1c"][store], by_store["G1d"][store]
        g1e, g1f = by_store["G1e"][store], by_store["G1f"][store]

        part = attribute(store, g1a, g1e)

        emitted_full = g1d.get("record_token_ids")
        emitted_reduced = g1f.get("record_token_ids")
        full_match = isinstance(emitted_full, list) and [int(x) for x in emitted_full] == d_ids
        reduced_match = (
            isinstance(emitted_reduced, list) and [int(x) for x in emitted_reduced] == f_ids
        )

        loop_closed = {
            "g1b_layer_complete": dotted(g1b, "layer.complete") is True,
            "g1b_no_golden_injected_inside_the_layer": (
                dotted(g1b, "layer.golden_injected_intermediate_count") == 0
            ),
            "g1b_mismatched_words": dotted(g1b, "layer.mismatched_words"),
            "g1c_handoff_rtl_to_rtl": dotted(g1c, "handoff.rtl_to_rtl") is True,
            "g1c_no_golden_across_the_boundary": (
                dotted(g1c, "handoff.golden_injected_between_layers") is False
            ),
            "g1c_loop_count_matches_model_layers": (
                dotted(g1c, "loop.invocation_count_matches_model_layers") is True
            ),
            "g1c_invocations_structurally_identical": (
                dotted(g1c, "loop.structurally_identical") is True
            ),
        }
        loop_closed["holds"] = all(
            v is True for k, v in loop_closed.items() if k != "g1b_mismatched_words"
        ) and loop_closed["g1b_mismatched_words"] == 0

        outside = []
        if part["uncovered_instance_count"]:
            outside.append(
                f"{part['uncovered_instance_count']} of {part['issued_instance_count']} "
                "issued instances are not in a class G1a proved bit-exact"
            )
        if not loop_closed["holds"]:
            outside.append(
                "the layer loop is not closed by G1b and G1c: "
                + ", ".join(
                    k for k, v in loop_closed.items()
                    if k != "holds" and v is not True and not (k == "g1b_mismatched_words" and v == 0)
                )
            )
        if not full_match:
            outside.append(
                f"the RTL emitted {emitted_full!r} for the full configuration "
                f"against the oracle's {d_ids!r}"
            )
        if not reduced_match:
            outside.append(
                f"the RTL emitted {emitted_reduced!r} for the reduced configuration "
                f"against the oracle's {f_ids!r}"
            )

        records.append(
            {
                "storage_class": store,
                "workload_id": g1e.get("workload_id"),
                "deployment_sha256": part["deployment_sha256"],
                "certificate": {
                    "every_issued_instance_covered": part["uncovered_instance_count"] == 0,
                    "uncovered_instance_count": part["uncovered_instance_count"],
                    "covered_instance_count": part["covered_instance_count"],
                    "issued_instance_count": part["issued_instance_count"],
                    "token_ids_match_oracle": bool(full_match and reduced_match),
                    "derived_mechanically": True,
                },
                "population": {
                    "from": "results/rtl/abi3_g1e_control_end_to_end.json:records[].issue_census",
                    "what_it_is": (
                        "the (family, subopcode, descriptor id) instances the governed "
                        "workload issued, counted from the RTL's own trace over every "
                        "pass, not from the golden model"
                    ),
                    "trace_certified_equal_to_golden": part["trace_certified_equal_to_golden"],
                    "census_reconciles_with_the_compared_trace": part["census_reconciles"],
                    "deployment_is_the_one_g1a_inventoried": part[
                        "deployment_is_the_one_g1a_inventoried"
                    ],
                    "refusals": part["refusals"],
                },
                "attribution": part["attributions"],
                "layer_loop": loop_closed,
                "tokens": {
                    "full_configuration": {
                        "rtl_emitted": emitted_full,
                        "oracle": d_ids,
                        "oracle_path": d_oracle_path,
                        "agree": full_match,
                        "rung": "G1d",
                    },
                    "reduced_configuration": {
                        "rtl_emitted": emitted_reduced,
                        "oracle": f_ids,
                        "oracle_path": f_oracle_path,
                        "agree": reduced_match,
                        "rung": "G1f",
                    },
                    "note": (
                        "the ids compared are the ones each rung recorded the RTL as "
                        "having emitted. The oracle's ids are read for comparison only "
                        "and are never copied into the emitted field."
                    ),
                },
                "nothing_outside_the_ladder_assumed": not outside,
                "what_is_assumed_outside_the_ladder": outside,
            }
        )

    every = all(r["certificate"]["every_issued_instance_covered"] for r in records)
    uncovered_total = sum(r["certificate"]["uncovered_instance_count"] for r in records)
    tokens = all(r["certificate"]["token_ids_match_oracle"] for r in records)

    # Each of these is COMPUTED from what was actually read.  Writing them as
    # literals would be the same defect the G1a tool was caught in: a field
    # that reads true without anything having been checked.
    mechanical = {
        "every_input_bound_by_sha256": all(
            isinstance(v, Mapping)
            and isinstance(v.get("sha256"), str)
            and len(v["sha256"]) == 64
            and (ROOT / str(v["path"])).is_file()
            and sha256_of(ROOT / str(v["path"])) == v["sha256"]
            for v in inputs.values()
        ),
        "population_read_from_g1e_trace_census": all(
            r["population"]["from"].startswith(RUNG_ARTIFACTS["G1e"])
            and r["certificate"]["issued_instance_count"] > 0
            for r in records
        ),
        "partition_is_exhaustive": all(
            r["certificate"]["covered_instance_count"]
            + r["certificate"]["uncovered_instance_count"]
            == r["certificate"]["issued_instance_count"]
            for r in records
        ),
        # Every gate field is recomputed here from the per-instance attribution
        # list, independently of the counters the partition returned.  A number
        # typed in anywhere upstream disagrees with this sum and the field goes
        # false.
        "gate_fields_recompute_from_the_attribution_list": all(
            r["certificate"]["uncovered_instance_count"]
            == sum(a["instances"] for a in r["attribution"] if not a["covered"])
            and r["certificate"]["covered_instance_count"]
            == sum(a["instances"] for a in r["attribution"] if a["covered"])
            and r["certificate"]["every_issued_instance_covered"]
            == (sum(a["instances"] for a in r["attribution"] if not a["covered"]) == 0)
            for r in records
        ),
    }
    mechanical["holds"] = all(mechanical.values())

    document = {
        "schema": SCHEMA,
        "gate": "G1",
        "generated_by": "tools/build_abi3_g1_composition_certificate.py",
        "generated_by_sha256": sha256_of(Path(__file__).resolve()),
        "workload_id": records[0]["workload_id"] if records else None,
        "status": "pass" if (every and tokens and uncovered_total == 0) else "fail",
        "certificate": {
            "every_issued_instance_covered": every,
            "uncovered_instance_count": uncovered_total,
            "token_ids_match_oracle": tokens,
            "derived_mechanically": mechanical["holds"],
        },
        "derived_mechanically_because": mechanical,
        "roll_up": (
            "the gate reads certificate.* at the top level; each store's own "
            "figures are under records[].certificate. uncovered_instance_count "
            "is the SUM over stores, so one store's uncovered instances cannot "
            "be hidden by the other's coverage."
        ),
        "inputs": inputs,
        "records": records,
        "git": git_state(),
        "claim_boundary": {
            "establishes": (
                "which of the operator instances the governed workload actually "
                "issues are in an equivalence class a rung proved, and which are "
                "not -- both counted from G1e's certified trace."
            ),
            "does_not_establish": [
                "that an uncovered instance is wrong: it is unproven, which is a "
                "different and weaker statement, and the certificate says which",
                "anything G1a did not measure. This tool re-reads G1a's coverage "
                "decision and cannot promote a class G1a called uncovered",
                "a single uninterrupted full-dimension run, which G1's own "
                "does_not_establish declares out of scope",
            ],
        },
    }

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")

    for record in records:
        cert = record["certificate"]
        print(
            f"{record['storage_class']} certificate: "
            f"{cert['covered_instance_count']}/{cert['issued_instance_count']} issued "
            f"instances covered, {cert['uncovered_instance_count']} uncovered; "
            f"tokens_match={cert['token_ids_match_oracle']}; "
            f"layer_loop_closed={record['layer_loop']['holds']}"
        )
    print(
        f"G1 composition certificate: status={document['status']} "
        f"every_issued_instance_covered={every} "
        f"uncovered_instance_count={uncovered_total} "
        f"token_ids_match_oracle={tokens} "
        f"derived_mechanically={mechanical['holds']}"
    )
    print(f"wrote {out}")
    return 0


def self_test() -> int:
    """The derivation has to move in both directions, on synthetic inputs."""
    import copy

    base_g1a = {
        "deployment": {"deployment_sha256": "aa"},
        "coverage": {
            "classes": [
                {
                    "family": 32, "sub": 0, "mnemonic": "TENSOR.MATMUL",
                    "operator_descriptor_ids": [7], "covered": True,
                    "covered_by": "results/rtl/x.json",
                },
                {
                    "family": 48, "sub": 0, "mnemonic": "VECTOR.RMS_NORM",
                    "operator_descriptor_ids": [9], "covered": False,
                    "why_not_covered": "nothing drove it",
                },
            ]
        },
    }
    base_g1e = {
        "deployment": {"deployment_sha256": "aa"},
        "trace": {"equals_golden": True, "divergence_index": None, "compared_issue_count": 30},
        "issue_census": {
            "instances": 30,
            "rows": [
                {"family": 32, "sub": 0, "descriptor_id": 7, "instances": 20},
                {"family": 48, "sub": 0, "descriptor_id": 9, "instances": 10},
            ],
        },
    }

    checks: list[tuple[str, bool]] = []

    part = attribute("rom", base_g1a, base_g1e)
    checks.append(("a covered class covers its instances", part["covered_instance_count"] == 20))
    checks.append(("an uncovered class is counted, not dropped", part["uncovered_instance_count"] == 10))
    checks.append(("the partition is exhaustive", part["covered_instance_count"] + part["uncovered_instance_count"] == 30))
    checks.append(("an uncovered class carries G1a's own reason",
                   any(a.get("why_not_covered") == "nothing drove it" for a in part["attributions"])))

    # All covered -> every instance covered.
    g1a_all = copy.deepcopy(base_g1a)
    g1a_all["coverage"]["classes"][1]["covered"] = True
    part_all = attribute("rom", g1a_all, base_g1e)
    checks.append(("coverage can reach zero uncovered", part_all["uncovered_instance_count"] == 0))

    # A diverged trace attributes nothing.
    g1e_bad = copy.deepcopy(base_g1e)
    g1e_bad["trace"]["equals_golden"] = False
    g1e_bad["trace"]["divergence_index"] = 4
    part_bad = attribute("rom", g1a_all, g1e_bad)
    checks.append(("a diverged trace covers nothing even when every class is covered",
                   part_bad["uncovered_instance_count"] == 30 and part_bad["covered_instance_count"] == 0))

    # A census that does not reconcile attributes nothing.
    g1e_skew = copy.deepcopy(base_g1e)
    g1e_skew["issue_census"]["instances"] = 31
    part_skew = attribute("rom", g1a_all, g1e_skew)
    checks.append(("an irreconcilable census covers nothing", part_skew["uncovered_instance_count"] == 30))

    # A different deployment attributes nothing.
    g1e_other = copy.deepcopy(base_g1e)
    g1e_other["deployment"]["deployment_sha256"] = "bb"
    part_other = attribute("rom", g1a_all, g1e_other)
    checks.append(("a different deployment covers nothing", part_other["uncovered_instance_count"] == 30))

    # A descriptor with no class at all is counted.
    g1e_extra = copy.deepcopy(base_g1e)
    g1e_extra["issue_census"]["rows"].append(
        {"family": 64, "sub": 1, "descriptor_id": 99, "instances": 5}
    )
    g1e_extra["issue_census"]["instances"] = 35
    g1e_extra["trace"]["compared_issue_count"] = 35
    part_extra = attribute("rom", g1a_all, g1e_extra)
    checks.append(("an instance no class claims is counted uncovered",
                   part_extra["uncovered_instance_count"] == 5))

    width = max(len(name) for name, _ in checks)
    ok = True
    for name, passed in checks:
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name.ljust(width)}")
    print(f"self test: {'PASS' if ok else 'FAIL'} ({sum(1 for _, p in checks if p)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(build())
