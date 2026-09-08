#!/usr/bin/env python3
"""Attribute the head span's LAST TWO refusals, by measurement, one field at a time.

``results/rtl/abi3_g1d_head_span_probe.json`` took the G1d head span --
entry 65, PCs 66/68/69/70, ending in ``SELECTION.ARGMAX`` -- as far as an
object placement table can take it.  Its ladder ends with the final norm and
the gather launching and the refusal standing at **PC 69**, the LM head's
``TENSOR.MATMUL``, and it records that this last refusal is NOT placement
(``attribution.the_final_refusal_is_not_placement``).  What it does not do is
say what the refusal IS, and it could not have reached the question its own
span ends on.  This campaign closes both gaps, and each is a measurement of
the design rather than a reading of its source.

**The first gap: what refuses PC 69.**  ``TRAP_DESCRIPTOR`` is a class, not an
attribution -- the same class is raised by every operand and result view
predicate in ``rtl/abi3/ot_a3_engine_issue_bridge.sv``.  The bracket here
changes ONE field of ONE descriptor of the retained image, the LM head weight
view's ``dim0``, and re-runs the identical binary on the identical span with
the identical placement table.  A refusal that disappears when that one number
falls, and returns when it rises by one, is attributable to that number and to
nothing else in the vehicle.  The output view's ``dim1``/``stride0`` move with
it because a weight view of R rows and an output view of 151,936 are not the
same operator; they are the same three fields
``tools/build_abi3_row_shard_vectors.py`` rewrites for a row shard, and this
campaign rewrites no others.

**The second gap: whether the argmax is reachable at all.**  It was not, and
the reason was in the bench rather than in the design.  The harness's entry
probe path configured the object placement table and never configured
``cfg_extended_placement_valid`` -- the flag that says an instantiation admits
the six mapped families, of which ``SELECTION.ARGMAX`` is one -- while the
campaign path drove it from the case record's own word.  So every probe ever
run measured a machine whose six mapped families were gated off no matter what
its vector set said, and a span that ENDS in ``SELECTION.ARGMAX`` could not
have reached an admission decision about it.  That path now drives the same
word through the same guard, and this campaign measures both settings of it on
one elaborated binary, which is what makes the argmax's verdict attributable
to the gate rather than to the vehicle.

WHAT NO ARM OF THIS CAMPAIGN ESTABLISHES, stated so nobody has to infer it:

* **No numeric claim, and no token id.**  An arm binds an added object at a
  declared base with nothing staged there, and enters mid-program on a result
  memory that holds its initialisation pattern.  Whatever an admitted engine
  writes is not what the checkpoint implies, and whatever an admitted argmax
  selects is not the workload's token.  No arm compares a word against golden,
  and the selected token is reported ONLY as evidence that a selection
  happened, never as a token id.  ``results/rtl/abi3_g1d_token.json`` must not
  read one from here.
* **It is not gate G1d, and it does not move a field of it.**  G1d asks for
  the head to execute on the COMPOSED TRUNK OUTPUT with its logits compared.
  No trunk has run in this vehicle.
* **It is not a proposal for the shipped vector set.**  The rewritten
  descriptor is not the governed program's; the governed program's LM head is
  151,936 rows and stays refused.  What the bracket measures is the bound.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    Attention,
    Dma,
    Major,
    Selection,
    Tensor,
    Vector,
)
from runtime.abi3.descriptors import (  # noqa: E402
    Descriptor,
    ExtendedDescriptorType,
)
from tools import rtl_abi3_shipped_prefix_campaign as prefix  # noqa: E402
from tools import build_abi3_vehicle_reachability as reach  # noqa: E402
from tools import build_a3_qwen_kv_scatter_vectors as scatter  # noqa: E402
from tools.build_a3_operator_admission_vectors import build_table  # noqa: E402
from tools.build_abi3_shipped_prefix_vectors import (  # noqa: E402
    CASE_STRIDE,
    TARGETS,
    _deployment_vectors,
)
from tools.rtl_abi3_g1d_head_span_probe import (  # noqa: E402
    Bench as ProbeBench,
    MARKER,
    NO_ID,
    PLACE_TABLE_ENTRIES,
    PLACE_TABLE_WORD,
    PROBE_BASE,
    PROBE_RE,
    TRAP_DESCRIPTOR,
    _elaborate,
    _git_state,
    _read_hex,
    _span,
    _views_of,
    _write_hex,
)

SCHEMA = "opentallas.rtl.abi3_g1d_head_admission.v1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_g1d_head_admission.json"
MAPPED_FAMILIES_WORD = 59
MAP_CONTEXT_WORD = 124
MAP_PLANE_ROWS_WORD = 125
MAP_POLICY_WORD = 126
MAP_MAX_NEW_WORD = 127
MAP_GENERATED_WORD = 128
DESCRIPTOR_IMAGE = "a3_descriptor.hex"
DESC_BASE_WORD = 2
DESC_COUNT_WORD = 3
TRAP_CAPABILITY = 4
# The six families ``cfg_extended_placement_valid`` gates.  A missing base for
# ONE OF THESE is a TRAP_CAPABILITY rather than a TRAP_DESCRIPTOR, and that is
# the design's own decision, stated in ot_a3_engine_issue_bridge.sv where it
# refuses on ``mapped_bases_found``: "A missing bank is a capability this
# instance does not have, not a malformed descriptor."  A ladder that added
# objects only on TRAP_DESCRIPTOR would therefore read a placement shortfall
# in one of these six as an opcode the design cannot execute, which is a
# different and much stronger claim.  This campaign measured that mistake
# before it fixed it.
MAPPED_FAMILY_OPCODES = frozenset(
    {
        (int(Major.VECTOR), int(Vector.ADD)),
        (int(Major.VECTOR), int(Vector.SILU_MUL)),
        (int(Major.DMA), int(Dma.SCATTER)),
        (int(Major.ATTENTION), int(Attention.GQA)),
        (int(Major.SELECTION), int(Selection.ARGMAX)),
        (int(Major.SELECTION), int(Selection.TOKEN_APPEND)),
    }
)
# The bridge's admitted MATMUL weight bound, as ``dim0 <= EMBEDDING_WIDTH``.
# It is NOT read from the source here: it is the value the bracket brackets,
# and the campaign refuses to publish it unless the arm at the value launches
# and the arm one row above it refuses.
BRACKET_ROWS = 4096
BRACKET_OVER_ROWS = BRACKET_ROWS + 1
# The width the argmax arms rewrite the head to.  It is NOT the bracket: the
# bracket's job is the bound and it costs 16.8 x 10^6 multiply-accumulates a
# store, while the argmax's job is admission, which does not depend on how
# many rows the MATMUL before it wrote.  Running the argmax ladder at the
# bracket would spend forty minutes re-measuring a number the bracket already
# has.  The two are reported separately and neither is presented as the other.
ARGMAX_HEAD_ROWS = 128
PROBEMAPPED_RE = re.compile(
    r"^PROBEMAPPED case=(?P<case>\d+) admitted=(?P<admitted>\d+) "
    r"vector_add=(?P<vector_add>\d+) vector_silu_mul=(?P<vector_silu_mul>\d+) "
    r"dma_scatter=(?P<dma_scatter>\d+) attention_gqa=(?P<attention_gqa>\d+) "
    r"selection_argmax=(?P<selection_argmax>\d+) "
    r"selection_token_append=(?P<selection_token_append>\d+) "
    r"matmul=(?P<matmul>\d+) rms_norm=(?P<rms_norm>\d+) "
    r"dma_gather=(?P<dma_gather>\d+) token=(?P<token>\d+) tie=(?P<tie>\d+) "
    r"eos=(?P<eos>\d+)$",
    re.MULTILINE,
)


class Bench(ProbeBench):
    """The probe's bench, plus the two surfaces this campaign varies.

    ``ProbeBench`` drives one thing per arm: the object placement table.  This
    adds the two the head span's last refusals turn on -- the case record's
    mapped-families word, and one descriptor of the retained image -- and
    restores both after every arm so an arm is never contaminated by the one
    before it.
    """

    def __init__(self, build: Path, vectors: dict[str, Any]) -> None:
        super().__init__(build, vectors)
        self.base_descriptor_text = (build / DESCRIPTOR_IMAGE).read_text(
            encoding="utf-8"
        )
        self.descriptor_words = [
            int(line, 16)
            for line in self.base_descriptor_text.split()
        ]

    def case_record(self, case_index: int) -> list[int]:
        return self.base_case_words[
            case_index * self.stride : (case_index + 1) * self.stride
        ]

    def rewrite_view(
        self, case_index: int, descriptor_id: int, fields: dict[str, int]
    ) -> dict[str, Any]:
        """Rewrite named payload fields of one TENSOR_VIEW of the retained image.

        Returns the before/after of every field it touched.  A field whose
        value it would not change, a descriptor that is not a TENSOR_VIEW and
        a record whose re-encoding is not the same length are all refusals:
        this campaign changes what it says it changes and nothing else.
        """
        record = self.case_record(case_index)
        base = record[DESC_BASE_WORD]
        count = record[DESC_COUNT_WORD]
        if descriptor_id >= count:
            raise SystemExit(
                f"descriptor {descriptor_id} is past this case's own "
                f"{count}-descriptor table"
            )
        beat = self.descriptor_words[base + descriptor_id].to_bytes(
            scatter.DESCRIPTOR_BYTES, "little"
        )
        table, _ = build_table(self.descriptor_words, base, count)
        view = table.get(descriptor_id)
        if int(view.descriptor_type) != int(ExtendedDescriptorType.TENSOR_VIEW):
            raise SystemExit(
                f"descriptor {descriptor_id} is not a TENSOR_VIEW"
            )
        payload = dict(view.payload)
        moved: dict[str, list[int]] = {}
        for name, value in fields.items():
            if name not in payload:
                raise SystemExit(f"TENSOR_VIEW has no field {name!r}")
            if int(payload[name]) == int(value):
                raise SystemExit(
                    f"{name} is already {value}: this bracket rewrites a "
                    "field or it does not run"
                )
            moved[name] = [int(payload[name]), int(value)]
            payload[name] = int(value)
        rewritten = Descriptor(
            descriptor_id=view.descriptor_id,
            descriptor_type=view.descriptor_type,
            payload=payload,
            flags=view.flags,
            primary_object_id=view.primary_object_id,
            secondary_object_id=view.secondary_object_id,
            numeric_profile_id=view.numeric_profile_id,
            schedule_id=view.schedule_id,
            permissions=view.permissions,
            owner_scope_id=view.owner_scope_id,
        ).encode()
        if len(rewritten) != len(beat.rstrip(b"\x00")) and len(
            rewritten
        ) > scatter.DESCRIPTOR_BYTES:
            raise SystemExit("the rewritten record does not fit the beat")
        return {
            "descriptor_id": descriptor_id,
            "image_index": base + descriptor_id,
            "fields": moved,
            "record": rewritten,
        }

    def run_arm(
        self,
        *,
        tables: dict[int, list[tuple[int, int]]],
        mapped: dict[int, dict[str, int] | None],
        rewrites: list[dict[str, Any]],
        plan: list[tuple[int, int, int]],
    ) -> dict[str, Any]:
        words = list(self.base_case_words)
        for case_index, entries in tables.items():
            if len(entries) > PLACE_TABLE_ENTRIES:
                raise SystemExit(
                    f"case {case_index}: {len(entries)} entries exceed the "
                    f"{PLACE_TABLE_ENTRIES}-entry table the record carries"
                )
            objects = [entry[0] for entry in entries]
            if len(set(objects)) != len(objects):
                raise SystemExit(
                    f"case {case_index}: an object is bound twice, which the "
                    "bridge refuses before anything is fetched"
                )
            padded = list(entries) + [(NO_ID, 0)] * (
                PLACE_TABLE_ENTRIES - len(entries)
            )
            offset = case_index * self.stride + PLACE_TABLE_WORD
            for slot, (object_id, base) in enumerate(padded):
                words[offset + 2 * slot] = object_id
                words[offset + 2 * slot + 1] = base
        for case_index, config in mapped.items():
            offset = case_index * self.stride
            words[offset + MAPPED_FAMILIES_WORD] = 0 if config is None else 1
            if config is not None:
                words[offset + MAP_CONTEXT_WORD] = config["context_length"]
                words[offset + MAP_PLANE_ROWS_WORD] = config["kv_plane_rows"]
                words[offset + MAP_POLICY_WORD] = config["generation_policy_id"]
                words[offset + MAP_MAX_NEW_WORD] = config["max_new_tokens"]
                words[offset + MAP_GENERATED_WORD] = config["generated_before"]
        _write_hex(self.build / "p3_case.hex", words)
        image = list(self.descriptor_words)
        for rewrite in rewrites:
            image[rewrite["image_index"]] = int.from_bytes(
                scatter.padded_record(rewrite["record"]), "little"
            )
        if rewrites:
            (self.build / DESCRIPTOR_IMAGE).write_text(
                scatter.hex_lines(image, 1536), encoding="ascii"
            )
        (self.build / "arm_plan.txt").write_text(
            "".join(f"{case} {entry} {bound}\n" for case, entry, bound in plan),
            encoding="utf-8",
        )
        environment = dict(os.environ)
        environment["OT_A3_ENTRY_PROBE"] = "arm_plan.txt"
        started = time.time()
        result = subprocess.run(
            ["./obj_probe/Vot_a3_shipped_prefix_top"],
            cwd=self.build,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=environment,
            timeout=21600,
        )
        _write_hex(self.build / "p3_case.hex", self.base_case_words)
        (self.build / DESCRIPTOR_IMAGE).write_text(
            self.base_descriptor_text, encoding="utf-8"
        )
        rows = [
            {key: int(value) for key, value in match.groupdict().items()}
            for match in PROBE_RE.finditer(result.stdout)
        ]
        mapped_rows = [
            {key: int(value) for key, value in match.groupdict().items()}
            for match in PROBEMAPPED_RE.finditer(result.stdout)
        ]
        if mapped_rows and len(mapped_rows) != len(rows):
            raise SystemExit(
                "the harness printed a different number of PROBE and "
                "PROBEMAPPED lines"
            )
        return {
            "returncode": result.returncode,
            "marker_present": MARKER in result.stdout,
            "wall_seconds": round(time.time() - started, 3),
            "rows": rows,
            "mapped_rows": mapped_rows,
            "log_tail": prefix.canonical(result.stdout[-2000:], self.build),
        }


def _head_matmul(program: reach.Program, span: dict[str, Any]) -> dict[str, Any]:
    """The span's LM head MATMUL and the two views a row shard rewrites.

    Found by opcode, never by position: the one ``TENSOR.MATMUL`` the head
    span issues.  Two of them, or none, is a refusal rather than a choice.
    """
    matmul_pcs = [
        pc
        for pc in span["issued_pcs"]
        if int(program.instructions[pc].major) == int(Major.TENSOR)
        and int(program.instructions[pc].sub) == int(Tensor.MATMUL)
    ]
    if len(matmul_pcs) != 1:
        raise SystemExit(
            f"{program.target.key}: the head span issues {len(matmul_pcs)} "
            "TENSOR.MATMUL instructions, expected exactly one"
        )
    matmul_pc = matmul_pcs[0]
    views = {view["role"]: view for view in _views_of(program, matmul_pc)}
    weight = views["input_view_1"]
    if weight["rank"] != 2 or weight["dims"][0] <= BRACKET_ROWS:
        raise SystemExit(
            f"{program.target.key}: the head MATMUL's weight view is "
            f"{weight['dims'][:2]}, which this bracket has nothing to say about"
        )
    return {
        "pc": matmul_pc,
        "weight_view": weight,
        "output_view": views["output_view_0"],
    }


def _generation_policy(program: reach.Program) -> int:
    ids = [
        descriptor_id
        for descriptor_id in program.table.ids_of_type(
            ExtendedDescriptorType.GENERATION_POLICY
        )
    ]
    if len(ids) != 1:
        raise SystemExit(
            f"{program.target.key}: expected one GENERATION_POLICY descriptor, "
            f"found {len(ids)}"
        )
    return int(ids[0])


def _refusal_is_attributable_to_placement(
    program: reach.Program, row: dict[str, Any], mapped: bool
) -> bool:
    """Whether this refusal is one an added table entry could move.

    ``TRAP_DESCRIPTOR`` always is.  ``TRAP_CAPABILITY`` is too, but only for
    one of the six gated families and only with the gate on: the bridge
    answers that class both for an opcode it does not admit at all and for a
    mapped family whose object the table does not name, and the two are told
    apart by the opcode, never by the class.
    """
    if row is None:
        return False
    if int(row["trap"]) == TRAP_DESCRIPTOR:
        return True
    if int(row["trap"]) != TRAP_CAPABILITY or not mapped:
        return False
    pc = int(row["fault"])
    if pc >= len(program.instructions):
        return False
    instruction = program.instructions[pc]
    return (
        int(instruction.major),
        int(instruction.sub),
    ) in MAPPED_FAMILY_OPCODES


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-root", type=Path, default=None)
    args = parser.parse_args(argv)

    deployment_vectors, _ = _deployment_vectors()
    shipped = {case["name"]: case for case in deployment_vectors["cases"]}
    qwen = [target for target in TARGETS if target.key.startswith("qwen3-8b-")]

    with tempfile.TemporaryDirectory(prefix="opentallas-a3-head-admit-") as raw:
        build_dir = Path(args.build_root) if args.build_root else Path(raw)
        build_dir.mkdir(parents=True, exist_ok=True)
        elaboration = _elaborate(build_dir, prefix.VECTOR_DIR)
        vectors = elaboration["vectors"]
        case_index = {
            case["name"].split("/")[0]: index
            for index, case in enumerate(vectors["cases"])
        }
        bench = Bench(build_dir, vectors)

        programs: dict[str, reach.Program] = {}
        spans: dict[str, dict[str, Any]] = {}
        heads: dict[str, dict[str, Any]] = {}
        for target in qwen:
            case = shipped.get(f"{target.key}/decode")
            if case is None:
                raise SystemExit(f"no shipped decode case for {target.key}")
            symbols = {int(k): int(v) for k, v in case["symbols"].items()}
            program = reach.Program(target, symbols)
            programs[target.key] = program
            spans[target.key] = _span(program)
            heads[target.key] = _head_matmul(program, spans[target.key])

        plan = [
            (
                case_index[t.key],
                spans[t.key]["entry_pc"],
                spans[t.key]["instruction_count"],
            )
            for t in qwen
        ]
        mapped_config = {
            t.key: {
                "context_length": 0,
                "kv_plane_rows": 0,
                "generation_policy_id": _generation_policy(programs[t.key]),
                "max_new_tokens": 0,
                "generated_before": 0,
                "note": (
                    "only the admission flag and the placement bases decide a "
                    "SELECTION.ARGMAX: the bridge reads the policy id on "
                    "SELECTION.TOKEN_APPEND and the KV terms on DMA.SCATTER "
                    "and ATTENTION.GQA, neither of which this span reaches.  "
                    "The policy id is the deployment's own so no arm runs a "
                    "configuration the deployment does not have"
                ),
            }
            for t in qwen
        }

        def measure(
            kind: str,
            tables: dict[str, list[tuple[int, int]]],
            *,
            mapped: bool,
            rewrite_rows: int | None,
        ) -> dict[str, Any]:
            rewrites: list[dict[str, Any]] = []
            rewritten_record: dict[str, Any] = {}
            if rewrite_rows is not None:
                for target in qwen:
                    head = heads[target.key]
                    index = case_index[target.key]
                    weight = bench.rewrite_view(
                        index,
                        head["weight_view"]["view_descriptor_id"],
                        {"dim0": rewrite_rows},
                    )
                    output = bench.rewrite_view(
                        index,
                        head["output_view"]["view_descriptor_id"],
                        {"dim1": rewrite_rows, "stride0": rewrite_rows},
                    )
                    rewrites.extend([weight, output])
                    rewritten_record[target.key] = {
                        "weight_view": {
                            "descriptor_id": weight["descriptor_id"],
                            "fields": weight["fields"],
                        },
                        "output_view": {
                            "descriptor_id": output["descriptor_id"],
                            "fields": output["fields"],
                        },
                    }
            measured = bench.run_arm(
                tables={case_index[t.key]: tables[t.key] for t in qwen},
                mapped={
                    case_index[t.key]: (
                        {
                            key: value
                            for key, value in mapped_config[t.key].items()
                            if key != "note"
                        }
                        if mapped
                        else None
                    )
                    for t in qwen
                },
                rewrites=rewrites,
                plan=plan,
            )
            per_target = {}
            for index, target in enumerate(qwen):
                row = measured["rows"][index] if index < len(measured["rows"]) else None
                mapped_row = (
                    measured["mapped_rows"][index]
                    if index < len(measured["mapped_rows"])
                    else None
                )
                per_target[target.key] = {
                    "placement_table_entry_count": len(tables[target.key]),
                    "measured": row,
                    "mapped_families": mapped_row,
                    "refused_instruction_views": (
                        _views_of(programs[target.key], row["fault"])
                        if row is not None
                        and row["fault"] < len(programs[target.key].instructions)
                        else []
                    ),
                }
            return {
                "kind": kind,
                "mapped_families_admitted": mapped,
                "lm_head_weight_rows_rewritten_to": rewrite_rows,
                "rewritten_descriptor_fields": rewritten_record or None,
                "returncode": measured["returncode"],
                "marker_present": measured["marker_present"],
                "wall_seconds": measured["wall_seconds"],
                "targets": per_target,
            }

        # -- the table the probe's ladder ended with -------------------------
        # Re-derived here rather than copied from that artifact: the ladder is
        # cheap, and a table read out of a file is a table this campaign did
        # not measure.  Each step adds only the refused instruction's own
        # objects that the table does not already name.
        tables = {
            t.key: list(bench.committed_table(case_index[t.key])) for t in qwen
        }
        ladder: list[dict[str, Any]] = []
        previous: dict[str, int | None] = {t.key: None for t in qwen}
        for step in range(10):
            arm = measure(
                "ladder" if step else "baseline",
                tables,
                mapped=False,
                rewrite_rows=None,
            )
            arm["step"] = step
            ladder.append(arm)
            moved = False
            additions: dict[str, list[dict[str, Any]]] = {}
            for target in qwen:
                row = arm["targets"][target.key]["measured"]
                if row is None:
                    continue
                if previous[target.key] != row["fault"]:
                    moved = True
                previous[target.key] = row["fault"]
                bound_objects = {o for o, _ in tables[target.key]}
                unplaced = []
                if _refusal_is_attributable_to_placement(
                    programs[target.key], row, arm["mapped_families_admitted"]
                ):
                    for view in arm["targets"][target.key][
                        "refused_instruction_views"
                    ]:
                        if view["object_id"] not in bound_objects and not any(
                            entry["object_id"] == view["object_id"]
                            for entry in unplaced
                        ):
                            unplaced.append(view)
                additions[target.key] = unplaced
            if step and not moved:
                break
            if not any(additions.get(t.key) for t in qwen):
                break
            for target in qwen:
                for view in additions.get(target.key, []):
                    tables[target.key].append((view["object_id"], PROBE_BASE))

        arms = {"ladder": ladder}

        # -- the bracket: one descriptor field, three values -----------------
        arms["placement_bound_mapped_off"] = ladder[-1]
        arms["placement_bound_mapped_on"] = measure(
            "the same table and span, with the six mapped families admitted",
            tables,
            mapped=True,
            rewrite_rows=None,
        )
        arms["weight_rows_one_over_the_bound"] = measure(
            "the LM head weight view rewritten to one row over the bracket",
            tables,
            mapped=True,
            rewrite_rows=BRACKET_OVER_ROWS,
        )
        arms["weight_rows_at_the_bound"] = measure(
            "the LM head weight view rewritten to the bracket itself",
            tables,
            mapped=True,
            rewrite_rows=BRACKET_ROWS,
        )
        arms["weight_rows_for_the_argmax_arms"] = measure(
            "the LM head weight view rewritten to the cheap admitted width "
            "the argmax arms use",
            tables,
            mapped=True,
            rewrite_rows=ARGMAX_HEAD_ROWS,
        )
        # After the bracket admits PC 69 the span may refuse further on at PC
        # 70 for the ordinary reason -- an object of the argmax that the table
        # does not name.  The ladder is continued from there, on the SAME
        # rewrite, so the argmax's verdict is not confounded with placement.
        argmax_ladder: list[dict[str, Any]] = []
        arm = arms["weight_rows_for_the_argmax_arms"]
        for step in range(6):
            additions: dict[str, list[dict[str, Any]]] = {}
            for target in qwen:
                row = arm["targets"][target.key]["measured"]
                if row is None:
                    continue
                bound_objects = {o for o, _ in tables[target.key]}
                unplaced = []
                if _refusal_is_attributable_to_placement(
                    programs[target.key], row, arm["mapped_families_admitted"]
                ):
                    for view in arm["targets"][target.key][
                        "refused_instruction_views"
                    ]:
                        if view["object_id"] not in bound_objects and not any(
                            entry["object_id"] == view["object_id"]
                            for entry in unplaced
                        ):
                            unplaced.append(view)
                additions[target.key] = unplaced
            if not any(additions.get(t.key) for t in qwen):
                break
            for target in qwen:
                for view in additions.get(target.key, []):
                    tables[target.key].append((view["object_id"], PROBE_BASE))
            arm = measure(
                "an admitted head width, with the refusal's own unplaced "
                "objects added",
                tables,
                mapped=True,
                rewrite_rows=ARGMAX_HEAD_ROWS,
            )
            arm["step"] = step
            argmax_ladder.append(arm)
        arms["argmax_ladder"] = argmax_ladder
        final = (
            argmax_ladder[-1]
            if argmax_ladder
            else arms["weight_rows_for_the_argmax_arms"]
        )
        arms["final"] = final
        # The control that makes the argmax's admission attributable to the
        # gate: the SAME table, the SAME rewrite, the SAME span, with the
        # mapped-families word back to what the shipped vector set carries.
        arms["negative_control_mapped_off"] = measure(
            "the final arm with the mapped-families word back to the shipped 0",
            tables,
            mapped=False,
            rewrite_rows=ARGMAX_HEAD_ROWS,
        )

        def launches(arm: dict[str, Any], target: str, family: str) -> int | None:
            row = arm["targets"][target].get("mapped_families")
            return None if row is None else row[family]

        findings = {}
        for target in qwen:
            key = target.key
            over = arms["weight_rows_one_over_the_bound"]["targets"][key]["measured"]
            at = arms["weight_rows_at_the_bound"]["targets"][key]["measured"]
            off = arms["placement_bound_mapped_off"]["targets"][key]["measured"]
            head_pc = heads[key]["pc"]
            findings[key] = {
                "lm_head_pc": head_pc,
                "shipped_weight_rows": heads[key]["weight_view"]["dims"][0],
                "refusal_is_the_weight_row_count": bool(
                    off is not None
                    and off["trap"] == TRAP_DESCRIPTOR
                    and off["fault"] == head_pc
                    and over is not None
                    and over["trap"] == TRAP_DESCRIPTOR
                    and over["fault"] == head_pc
                    and at is not None
                    and at["fault"] != head_pc
                ),
                "largest_weight_rows_measured_to_launch": (
                    BRACKET_ROWS if at is not None and at["fault"] != head_pc else None
                ),
                "smallest_weight_rows_measured_to_refuse": (
                    BRACKET_OVER_ROWS
                    if over is not None and over["fault"] == head_pc
                    else None
                ),
                "argmax_site_pc": spans[key]["site_pc"],
                "head_rows_the_argmax_arms_ran_at": ARGMAX_HEAD_ROWS,
                "argmax_launches_with_the_gate_on": launches(
                    final, key, "selection_argmax"
                ),
                "argmax_launches_with_the_gate_off": launches(
                    arms["negative_control_mapped_off"], key, "selection_argmax"
                ),
                "final_trap_class": (
                    final["targets"][key]["measured"]["trap"]
                    if final["targets"][key]["measured"]
                    else None
                ),
                "final_fault_pc": (
                    final["targets"][key]["measured"]["fault"]
                    if final["targets"][key]["measured"]
                    else None
                ),
                "final_placement_table_entry_count": len(tables[key]),
                "final_placement_table_objects": [o for o, _ in tables[key]],
                "objects_added_after_the_bracket": [
                    o
                    for o, _ in tables[key][
                        arms["weight_rows_for_the_argmax_arms"]["targets"][
                            key
                        ]["placement_table_entry_count"] :
                    ]
                ],
                "argmax_launched": bool(
                    launches(final, key, "selection_argmax")
                ),
                "argmax_refusal_class_when_its_own_object_was_unplaced": (
                    arms["weight_rows_for_the_argmax_arms"]["targets"][key][
                        "measured"
                    ]["trap"]
                    if arms["weight_rows_for_the_argmax_arms"]["targets"][key][
                        "measured"
                    ]
                    else None
                ),
            }

        record = {
            "schema": SCHEMA,
            "gate": "G1d (configs/gates/redesign_gates.json)",
            "what_this_measures": (
                "what refuses the LM head at the end of the G1d head span, "
                "and whether the span's SELECTION.ARGMAX is admitted once it "
                "is reached -- attributed by changing one field per arm on "
                "one elaborated binary"
            ),
            "evidence_class": "public_open_tool_rtl_simulation",
            "simulator": "verilator_cpp_executable",
            "vehicle": "rtl/test/a3_shipped_prefix_top.sv",
            "one_elaboration_for_every_arm": True,
            "compile_returncode": elaboration["compile"]["returncode"],
            "tools": elaboration["tools"],
            "vector_set": {
                "directory": str(prefix.VECTOR_DIR.relative_to(ROOT)),
                "committed": True,
                "case_record_stride": CASE_STRIDE,
                "mapped_families_word_in_the_committed_set": {
                    t.key: bench.case_record(case_index[t.key])[
                        MAPPED_FAMILIES_WORD
                    ]
                    for t in qwen
                },
            },
            "spans": spans,
            "head_matmul": {
                t.key: {
                    "pc": heads[t.key]["pc"],
                    "weight_view_descriptor_id": heads[t.key]["weight_view"][
                        "view_descriptor_id"
                    ],
                    "weight_view_dims": heads[t.key]["weight_view"]["dims"][:2],
                    "output_view_descriptor_id": heads[t.key]["output_view"][
                        "view_descriptor_id"
                    ],
                    "output_view_dims": heads[t.key]["output_view"]["dims"][:2],
                }
                for t in qwen
            },
            "mapped_configuration": mapped_config,
            "arms": arms,
            "findings": findings,
            "does_not_establish": [
                "gate G1d: no arm runs the head on the composed trunk output "
                "and no arm compares a logit against golden",
                "any token id: an arm enters mid-program on an initialised "
                "result memory and binds objects at a base with nothing "
                "staged there, so a selected token is evidence that a "
                "selection happened and is not a token id",
                "that the governed program's LM head is admissible: it is "
                "151,936 rows and every arm at that width refuses",
                "any numeric result of the rewritten operator",
            ],
            "git": _git_state(),
        }
        record["simulated_cycles"] = sum(
            row["cycles"]
            for arm in [*ladder, *argmax_ladder, arms["placement_bound_mapped_on"],
                        arms["weight_rows_one_over_the_bound"],
                        arms["weight_rows_at_the_bound"],
                        arms["weight_rows_for_the_argmax_arms"],
                        arms["negative_control_mapped_off"]]
            for row in (arm["rows"] if "rows" in arm else [])
        ) or sum(
            target["measured"]["cycles"]
            for arm in [*ladder, *argmax_ladder, arms["placement_bound_mapped_on"],
                        arms["weight_rows_one_over_the_bound"],
                        arms["weight_rows_at_the_bound"],
                        arms["weight_rows_for_the_argmax_arms"],
                        arms["negative_control_mapped_off"]]
            for target in arm["targets"].values()
            if target["measured"] is not None
        )
        record["status"] = (
            "pass"
            if all(
                arm["marker_present"] and arm["returncode"] == 0
                for arm in [*ladder, *argmax_ladder,
                            arms["placement_bound_mapped_on"],
                            arms["weight_rows_one_over_the_bound"],
                            arms["weight_rows_at_the_bound"],
                            arms["weight_rows_for_the_argmax_arms"],
                            arms["negative_control_mapped_off"]]
            )
            else "fail"
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(record["findings"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
