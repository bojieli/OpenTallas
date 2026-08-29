"""OpenTallas compiler command line."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys

from compiler.build import BuildError, build_deployment
from compiler.canonical import (
    CanonicalApplicationError,
    CanonicalTransformError,
    apply_official_canonical_plan,
    build_official_canonical_plan,
)
from compiler.checking.deepseek_v4_application import (
    DeepSeekV4ApplicationCheckError,
    VERIFICATION_FILENAME,
    verify_canonical_application,
)
from compiler.checking.deepseek_v4_fp8_linear_execution import (
    DeepSeekV4FP8LinearDifferentialError,
    verify_deepseek_v4_fp8_linear_execution,
)
from compiler.checking.deepseek_v4_lookup_execution import (
    DeepSeekV4LookupDifferentialError,
    verify_deepseek_v4_lookup_execution,
)
from compiler.checking.inverse import InverseCheckError
from compiler.frontend.checkpoint import (
    CheckpointError,
    build_checkpoint_lock,
    load_checkpoint_lock,
    load_checkpoint_source,
    verify_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import (
    DeepSeekV4AdapterError,
    build_expected_tensor_contract,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.frontend.deepseek_v4_graph import (
    DeepSeekV4GraphError,
    build_official_graph_contract,
)
from compiler.frontend.deepseek_v4_tokenizer import (
    DeepSeekV4TokenizerError,
    load_verified_deepseek_v4_tokenizer,
)
from compiler.frontend.deepseek_v4_generation import (
    DeepSeekV4GenerationError,
    replay_generation_control,
)
from compiler.image.rom import RomImageError
from compiler.ir.model import IRValidationError, canonical_json_bytes, load_strict_json
from compiler.microcode.isa import MicrocodeError
from compiler.vertical_slice.deepseek_v4_fp8_linear import (
    DEFAULT_OUTPUT_ROWS,
    DeepSeekV4FP8LinearBuildError,
    build_deepseek_v4_fp8_linear_deployment,
    build_deepseek_v4_fp8_linear_full_deployment,
)
from compiler.vertical_slice.deepseek_v4_hc_pre import (
    DeepSeekV4HCPreBuildError,
    build_deepseek_v4_hc_pre_deployment,
)
from compiler.vertical_slice.deepseek_v4_hc_pre_executable import (
    DeepSeekV4HCPreExecutableBuildError,
    build_deepseek_v4_hc_pre_executable_deployment,
)
from compiler.vertical_slice.deepseek_v4_hc_pre_input import (
    DeepSeekV4HCPreInputBuildError,
    build_deepseek_v4_hc_pre_input_request,
)
from compiler.vertical_slice.deepseek_v4_lookup import (
    DeepSeekV4LookupBuildError,
    build_deepseek_v4_lookup_deployment,
)
from runtime.reference.deepseek_v4_hc_pre_execution_check import (
    DeepSeekV4HCPreExecutionCheckError,
    verify_deepseek_v4_hc_pre_execution,
)
from runtime.service_engine.deepseek_v4_hc_pre_executable import (
    DeepSeekV4HCPreExecutableServiceError,
    execute_deepseek_v4_hc_pre_executable_deployment,
)


_MAX_SOURCE_TEXT_FILE_BYTES = 1024 * 1024
_SOURCE_READ_CHUNK_BYTES = 1024 * 1024


def _stat_fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="python3 -m compiler.cli",
        description="Build deterministic OpenTallas executable-system artifacts.",
    )
    subparsers = result.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser(
        "compile", help="compile one strict semantic IR deployment"
    )
    compile_parser.add_argument("--model", required=True, type=Path)
    compile_parser.add_argument("--output", required=True, type=Path)
    lock_parser = subparsers.add_parser(
        "lock-checkpoint",
        help="stream and content-lock a complete local safetensors checkpoint",
    )
    lock_parser.add_argument("--source", required=True, type=Path)
    lock_parser.add_argument("--snapshot", required=True, type=Path)
    lock_parser.add_argument("--output", required=True, type=Path)
    verify_parser = subparsers.add_parser(
        "verify-checkpoint",
        help="replay a checkpoint lock against every local checkpoint byte",
    )
    verify_parser.add_argument("--lock", required=True, type=Path)
    verify_parser.add_argument("--snapshot", required=True, type=Path)
    contract_parser = subparsers.add_parser(
        "describe-deepseek-v4",
        help="emit the exact official DeepSeek V4 Flash tensor-role contract",
    )
    contract_parser.add_argument("--output", required=True, type=Path)
    validate_deepseek_parser = subparsers.add_parser(
        "validate-deepseek-v4",
        help="bind a complete checkpoint lock to the official V4 tensor contract",
    )
    validate_deepseek_parser.add_argument("--lock", required=True, type=Path)
    validate_deepseek_parser.add_argument("--output", required=True, type=Path)
    graph_parser = subparsers.add_parser(
        "describe-deepseek-v4-graph",
        help="emit the source-mapped V4 operator graph and open coverage ledger",
    )
    graph_parser.add_argument("--output", required=True, type=Path)
    tokenizer_parser = subparsers.add_parser(
        "validate-deepseek-v4-tokenizer",
        help="validate and load the exact local-only V4 tokenizer",
    )
    tokenizer_parser.add_argument("--snapshot", required=True, type=Path)
    tokenizer_parser.add_argument("--output", required=True, type=Path)
    generation_parser = subparsers.add_parser(
        "replay-deepseek-v4-generation",
        help="replay target-only V4 generation and executor state commits",
    )
    generation_parser.add_argument("--request", required=True, type=Path)
    generation_parser.add_argument("--output", required=True, type=Path)
    canonical_parser = subparsers.add_parser(
        "describe-deepseek-v4-canonical-plan",
        help="emit the complete V4 checkpoint transform and rank-assignment plan",
    )
    canonical_parser.add_argument("--model-parallel", default=4, type=int)
    canonical_parser.add_argument("--output", required=True, type=Path)
    apply_canonical_parser = subparsers.add_parser(
        "apply-deepseek-v4-canonical-plan",
        help="apply an exact V4 plan to a full official hash-locked snapshot",
    )
    apply_canonical_parser.add_argument("--snapshot", required=True, type=Path)
    apply_canonical_parser.add_argument("--lock", required=True, type=Path)
    apply_canonical_parser.add_argument("--plan", required=True, type=Path)
    apply_canonical_parser.add_argument("--output", required=True, type=Path)
    apply_canonical_parser.add_argument(
        "--tensor",
        action="append",
        dest="tensors",
        help=(
            "materialize one named input plus required scale dependencies; "
            "repeatable and explicitly partial"
        ),
    )
    check_canonical_parser = subparsers.add_parser(
        "verify-canonical-application",
        help="independently replay every source and output byte in an application",
    )
    check_canonical_parser.add_argument("--snapshot", required=True, type=Path)
    check_canonical_parser.add_argument("--lock", required=True, type=Path)
    check_canonical_parser.add_argument("--application", required=True, type=Path)
    check_canonical_parser.add_argument("--output", required=True, type=Path)
    lookup_parser = subparsers.add_parser(
        "compile-deepseek-v4-lookup-slice",
        help="compile verified canonical V4 lookup tensors into an executable slice",
    )
    lookup_parser.add_argument("--snapshot", required=True, type=Path)
    lookup_parser.add_argument("--lock", required=True, type=Path)
    lookup_parser.add_argument("--application", required=True, type=Path)
    lookup_parser.add_argument("--output", required=True, type=Path)
    lookup_check_parser = subparsers.add_parser(
        "verify-deepseek-v4-lookup-execution",
        help="compare lookup service outputs directly with locked checkpoint rows",
    )
    lookup_check_parser.add_argument("--snapshot", required=True, type=Path)
    lookup_check_parser.add_argument("--lock", required=True, type=Path)
    lookup_check_parser.add_argument("--deployment", required=True, type=Path)
    lookup_check_parser.add_argument("--request", required=True, type=Path)
    lookup_check_parser.add_argument("--result", required=True, type=Path)
    lookup_check_parser.add_argument("--output", required=True, type=Path)
    fp8_parser = subparsers.add_parser(
        "compile-deepseek-v4-fp8-linear-slice",
        help="compile verified query-A tensors into a selected-row FP8 arithmetic slice",
    )
    fp8_parser.add_argument("--snapshot", required=True, type=Path)
    fp8_parser.add_argument("--lock", required=True, type=Path)
    fp8_parser.add_argument("--application", required=True, type=Path)
    fp8_parser.add_argument("--output", required=True, type=Path)
    fp8_parser.add_argument(
        "--output-row",
        action="append",
        dest="output_rows",
        type=int,
        help=(
            "selected logical query-A output row; repeatable and defaults to "
            "0,127,128,1023"
        ),
    )
    fp8_full_parser = subparsers.add_parser(
        "compile-deepseek-v4-fp8-linear",
        help="compile verified query-A tensors into a complete-output FP8 operator",
    )
    fp8_full_parser.add_argument("--snapshot", required=True, type=Path)
    fp8_full_parser.add_argument("--lock", required=True, type=Path)
    fp8_full_parser.add_argument("--application", required=True, type=Path)
    fp8_full_parser.add_argument("--output", required=True, type=Path)
    fp8_check_parser = subparsers.add_parser(
        "verify-deepseek-v4-fp8-linear-execution",
        help="compare FP8 linear outputs directly with locked checkpoint arithmetic",
    )
    fp8_check_parser.add_argument("--snapshot", required=True, type=Path)
    fp8_check_parser.add_argument("--lock", required=True, type=Path)
    fp8_check_parser.add_argument("--deployment", required=True, type=Path)
    fp8_check_parser.add_argument("--request", required=True, type=Path)
    fp8_check_parser.add_argument("--result", required=True, type=Path)
    fp8_check_parser.add_argument("--output", required=True, type=Path)
    hc_pre_parser = subparsers.add_parser(
        "package-deepseek-v4-hc-pre-parameters",
        help=(
            "package all learned parameters and the frozen numeric contract for "
            "one verified V4 layer-0 attention HC_PRE site"
        ),
    )
    hc_pre_parser.add_argument("--snapshot", required=True, type=Path)
    hc_pre_parser.add_argument("--lock", required=True, type=Path)
    hc_pre_parser.add_argument("--application", required=True, type=Path)
    hc_pre_parser.add_argument("--output", required=True, type=Path)
    hc_pre_executable_parser = subparsers.add_parser(
        "package-deepseek-v4-hc-pre-executable",
        help=(
            "package the exact V4 layer-0 attention HC_PRE program, logical "
            "schedule, interfaces, and verified learned parameters"
        ),
    )
    hc_pre_executable_parser.add_argument("--snapshot", required=True, type=Path)
    hc_pre_executable_parser.add_argument("--lock", required=True, type=Path)
    hc_pre_executable_parser.add_argument("--application", required=True, type=Path)
    hc_pre_executable_parser.add_argument("--output", required=True, type=Path)
    hc_pre_input_parser = subparsers.add_parser(
        "compose-deepseek-v4-hc-pre-input",
        help=(
            "compose a V4 HC_PRE request from verified tokenizer, lookup, "
            "checkpoint, and executable artifacts"
        ),
    )
    hc_pre_input_parser.add_argument("--snapshot", required=True, type=Path)
    hc_pre_input_parser.add_argument("--lock", required=True, type=Path)
    hc_pre_input_parser.add_argument("--lookup-deployment", required=True, type=Path)
    hc_pre_input_parser.add_argument("--lookup-request", required=True, type=Path)
    hc_pre_input_parser.add_argument("--lookup-result", required=True, type=Path)
    hc_pre_input_parser.add_argument("--lookup-differential", required=True, type=Path)
    hc_pre_input_parser.add_argument(
        "--executable-deployment", required=True, type=Path
    )
    hc_pre_input_parser.add_argument(
        "--executable-application", required=True, type=Path
    )
    hc_pre_input_parser.add_argument(
        "--source-text-file",
        action="append",
        dest="source_text_files",
        required=True,
        type=Path,
        help=(
            "UTF-8 source text for one batch row; repeat once per batch row "
            "without trimming or newline normalization"
        ),
    )
    hc_pre_input_parser.add_argument("--output", required=True, type=Path)
    hc_pre_input_parser.add_argument("--report-output", required=True, type=Path)
    hc_pre_execute_parser = subparsers.add_parser(
        "execute-deepseek-v4-hc-pre",
        help="execute the exact packaged V4 HC_PRE program on one closed request",
    )
    hc_pre_execute_parser.add_argument("--deployment", required=True, type=Path)
    hc_pre_execute_parser.add_argument("--request", required=True, type=Path)
    hc_pre_execute_parser.add_argument("--output", required=True, type=Path)
    hc_pre_verify_parser = subparsers.add_parser(
        "verify-deepseek-v4-hc-pre-execution",
        help=(
            "compare a persisted HC_PRE result with an independent locked-"
            "checkpoint recomputation"
        ),
    )
    hc_pre_verify_parser.add_argument("--snapshot", required=True, type=Path)
    hc_pre_verify_parser.add_argument("--lock", required=True, type=Path)
    hc_pre_verify_parser.add_argument("--application", required=True, type=Path)
    hc_pre_verify_parser.add_argument("--deployment", required=True, type=Path)
    hc_pre_verify_parser.add_argument("--request", required=True, type=Path)
    hc_pre_verify_parser.add_argument("--result", required=True, type=Path)
    hc_pre_verify_parser.add_argument("--output", required=True, type=Path)
    return result


def _write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(canonical_json_bytes(value))
    except FileExistsError as exc:
        raise CheckpointError(f"output already exists: {path}") from exc


def _read_source_text_file(path: Path) -> str:
    """Read one exact bounded UTF-8 prompt without following the final symlink."""

    if (
        not hasattr(os, "O_NOFOLLOW")
        or not hasattr(os, "O_NONBLOCK")
        or not hasattr(os, "O_CLOEXEC")
        or not hasattr(os, "pread")
    ):
        raise DeepSeekV4HCPreInputBuildError(
            "platform lacks bounded no-follow source-text reads"
        )
    source = Path(path).absolute()
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        descriptor = os.open(source, flags)
    except OSError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot open source text {source} without following symlinks: {exc}"
        ) from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise DeepSeekV4HCPreInputBuildError(
                f"source text {source} is not a regular file"
            )
        if before.st_size > _MAX_SOURCE_TEXT_FILE_BYTES:
            raise DeepSeekV4HCPreInputBuildError(
                f"source text {source} exceeds the "
                f"{_MAX_SOURCE_TEXT_FILE_BYTES}-byte bound"
            )
        payload = bytearray()
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(
                descriptor,
                min(_SOURCE_READ_CHUNK_BYTES, before.st_size - offset),
                offset,
            )
            if not chunk:
                break
            payload.extend(chunk)
            offset += len(chunk)
        after = os.fstat(descriptor)
        try:
            current_descriptor = os.open(source, flags)
        except OSError as exc:
            raise DeepSeekV4HCPreInputBuildError(
                f"cannot reopen source text {source} after reading: {exc}"
            ) from exc
        try:
            current = os.fstat(current_descriptor)
        finally:
            os.close(current_descriptor)
        if (
            len(payload) != before.st_size
            or _stat_fingerprint(after) != _stat_fingerprint(before)
            or _stat_fingerprint(current) != _stat_fingerprint(before)
        ):
            raise DeepSeekV4HCPreInputBuildError(
                f"source text {source} changed or was replaced while it was read"
            )
    except OSError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"cannot read source text {source}: {exc}"
        ) from exc
    finally:
        os.close(descriptor)
    try:
        return bytes(payload).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise DeepSeekV4HCPreInputBuildError(
            f"source text {source} is not valid UTF-8"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "compile":
            manifest = build_deployment(arguments.model, arguments.output)
            print(
                f"built {manifest['model_id']} deployment {manifest['build_id']} "
                f"at {arguments.output.resolve()}"
            )
            return 0
        if arguments.command == "lock-checkpoint":
            source = load_checkpoint_source(arguments.source)
            lock = build_checkpoint_lock(arguments.snapshot, source)
            _write_new_json(arguments.output, lock)
            summary = lock["checkpoint"]
            print(
                f"locked {summary['tensor_count']} tensors in "
                f"{summary['shard_count']} shards ({summary['payload_bytes']} bytes); "
                f"lock {lock['lock_id']}"
            )
            return 0
        if arguments.command == "verify-checkpoint":
            lock = load_checkpoint_lock(arguments.lock)
            verify_checkpoint_lock(arguments.snapshot, lock)
            print(f"verified checkpoint lock {lock['lock_id']}")
            return 0
        if arguments.command == "describe-deepseek-v4":
            contract = build_expected_tensor_contract(load_official_config())
            _write_new_json(arguments.output, contract)
            coverage = contract["coverage"]
            print(
                f"described {coverage['expected_tensor_count']} official tensors "
                f"({coverage['expected_payload_bytes']} bytes); contract "
                f"{contract['contract_id']}"
            )
            return 0
        if arguments.command == "validate-deepseek-v4":
            lock = load_checkpoint_lock(arguments.lock)
            validation = validate_official_checkpoint_lock(lock, load_official_config())
            _write_new_json(arguments.output, validation)
            print(
                f"validated {validation['tensor_count']} official tensors "
                f"({validation['payload_bytes']} bytes) against checkpoint lock "
                f"{validation['checkpoint_lock_id']}"
            )
            return 0
        if arguments.command == "describe-deepseek-v4-graph":
            graph = build_official_graph_contract()
            _write_new_json(arguments.output, graph)
            coverage = graph["coverage"]
            print(
                f"described {coverage['node_count']} nodes across "
                f"{coverage['catalog_kind_count']} operator kinds; graph contract "
                f"{graph['graph_contract_id']} ({coverage['execution_status']})"
            )
            return 0
        if arguments.command == "validate-deepseek-v4-tokenizer":
            tokenizer = load_verified_deepseek_v4_tokenizer(arguments.snapshot)
            report = tokenizer.validation_report
            _write_new_json(arguments.output, report)
            print(
                f"validated official tokenizer {report['validation_id']} "
                f"with {report['contract']['total_vocab_size']} tokens "
                f"using local-only {report['runtime']['implementation']} "
                f"{report['runtime']['version']}"
            )
            return 0
        if arguments.command == "replay-deepseek-v4-generation":
            try:
                request = load_strict_json(arguments.request)
            except (OSError, ValueError) as exc:
                raise DeepSeekV4GenerationError(
                    f"cannot load generation replay {arguments.request}: {exc}"
                ) from exc
            trace = replay_generation_control(request)
            _write_new_json(arguments.output, trace)
            print(
                f"replayed {len(trace['trace'])} target-only model calls for "
                f"{len(trace['sessions'])} session(s); trace {trace['trace_id']} "
                f"({trace['control_scope']['execution_status']})"
            )
            return 0
        if arguments.command == "describe-deepseek-v4-canonical-plan":
            plan = build_official_canonical_plan(
                model_parallel=arguments.model_parallel
            )
            _write_new_json(arguments.output, plan)
            coverage = plan["coverage"]
            print(
                f"planned {coverage['input_tensor_count']} official tensors into "
                f"{coverage['output_assignment_count']} assignments across "
                f"{plan['profile']['model_parallel']} ranks; plan {plan['plan_id']} "
                f"({plan['status']})"
            )
            return 0
        if arguments.command == "apply-deepseek-v4-canonical-plan":
            lock = load_checkpoint_lock(arguments.lock)
            try:
                plan = load_strict_json(arguments.plan)
            except (OSError, ValueError) as exc:
                raise CanonicalApplicationError(
                    f"cannot load canonical plan {arguments.plan}: {exc}"
                ) from exc
            result = apply_official_canonical_plan(
                snapshot=arguments.snapshot,
                lock=lock,
                plan=plan,
                output=arguments.output,
                requested_names=arguments.tensors,
            )
            manifest = result["manifest"]
            print(
                f"applied {manifest['coverage']['consumed_input_count']} locked "
                f"inputs into {manifest['coverage']['output_assignment_count']} "
                f"canonical assignments; application {manifest['application_id']} "
                f"({manifest['status']})"
            )
            return 0
        if arguments.command == "verify-canonical-application":
            lock = load_checkpoint_lock(arguments.lock)
            report = verify_canonical_application(
                arguments.application, arguments.snapshot, lock
            )
            retained_path = arguments.application / VERIFICATION_FILENAME
            if retained_path.is_file():
                try:
                    retained = load_strict_json(retained_path)
                except (OSError, ValueError) as exc:
                    raise DeepSeekV4ApplicationCheckError(
                        f"cannot load retained verification report: {exc}"
                    ) from exc
                if retained != report:
                    raise DeepSeekV4ApplicationCheckError(
                        "retained verification report differs from independent replay"
                    )
            _write_new_json(arguments.output, report)
            print(
                f"verified {report['coverage']['checked_assignment_count']} "
                f"canonical assignments from "
                f"{report['coverage']['checked_input_count']} locked inputs; "
                f"verification {report['verification_id']}"
            )
            return 0
        if arguments.command == "compile-deepseek-v4-lookup-slice":
            lock = load_checkpoint_lock(arguments.lock)
            deployment = build_deepseek_v4_lookup_deployment(
                snapshot=arguments.snapshot,
                lock=lock,
                application_root=arguments.application,
                output=arguments.output,
            )
            print(
                f"built three-operator V4 lookup deployment "
                f"{deployment['build_id']} at {arguments.output.resolve()} "
                f"({deployment['status']})"
            )
            return 0
        if arguments.command == "verify-deepseek-v4-lookup-execution":
            lock = load_checkpoint_lock(arguments.lock)
            report = verify_deepseek_v4_lookup_execution(
                snapshot=arguments.snapshot,
                lock=lock,
                deployment_root=arguments.deployment,
                request_path=arguments.request,
                result_path=arguments.result,
            )
            _write_new_json(arguments.output, report)
            print(
                f"verified {report['token_count']} token rows across "
                f"{len(report['comparisons'])} lookup outputs; differential "
                f"{report['differential_id']} ({report['status']})"
            )
            return 0
        if arguments.command == "compile-deepseek-v4-fp8-linear-slice":
            lock = load_checkpoint_lock(arguments.lock)
            deployment = build_deepseek_v4_fp8_linear_deployment(
                snapshot=arguments.snapshot,
                lock=lock,
                application_root=arguments.application,
                output=arguments.output,
                output_rows=(
                    tuple(arguments.output_rows)
                    if arguments.output_rows is not None
                    else DEFAULT_OUTPUT_ROWS
                ),
            )
            print(
                f"built selected-row V4 FP8 linear deployment "
                f"{deployment['build_id']} at {arguments.output.resolve()} "
                f"({deployment['status']})"
            )
            return 0
        if arguments.command == "compile-deepseek-v4-fp8-linear":
            lock = load_checkpoint_lock(arguments.lock)
            deployment = build_deepseek_v4_fp8_linear_full_deployment(
                snapshot=arguments.snapshot,
                lock=lock,
                application_root=arguments.application,
                output=arguments.output,
            )
            print(
                f"built complete-output V4 FP8 linear deployment "
                f"{deployment['build_id']} at {arguments.output.resolve()} "
                f"({deployment['status']})"
            )
            return 0
        if arguments.command == "verify-deepseek-v4-fp8-linear-execution":
            lock = load_checkpoint_lock(arguments.lock)
            report = verify_deepseek_v4_fp8_linear_execution(
                snapshot=arguments.snapshot,
                lock=lock,
                deployment_root=arguments.deployment,
                request_path=arguments.request,
                result_path=arguments.result,
            )
            _write_new_json(arguments.output, report)
            if "selected_output_rows" in report:
                output_scope = (
                    f"{len(report['selected_output_rows'])} selected FP8 outputs"
                )
            else:
                output_scope = f"{report['output_row_count']} FP8 outputs"
            print(
                f"verified {report['input_row_count']} input row(s) across "
                f"{output_scope}; "
                f"differential {report['differential_id']} ({report['status']})"
            )
            return 0
        if arguments.command == "package-deepseek-v4-hc-pre-parameters":
            lock = load_checkpoint_lock(arguments.lock)
            deployment = build_deepseek_v4_hc_pre_deployment(
                snapshot=arguments.snapshot,
                lock=lock,
                application_root=arguments.application,
                output=arguments.output,
            )
            print(
                "built complete-parameter V4 HC_PRE package "
                f"{deployment['build_id']} at {arguments.output.resolve()} "
                f"({deployment['status']})"
            )
            return 0
        if arguments.command == "package-deepseek-v4-hc-pre-executable":
            lock = load_checkpoint_lock(arguments.lock)
            deployment = build_deepseek_v4_hc_pre_executable_deployment(
                snapshot=arguments.snapshot,
                lock=lock,
                application_root=arguments.application,
                output=arguments.output,
            )
            print(
                "built executable V4 HC_PRE package "
                f"{deployment['build_id']} at {arguments.output.resolve()} "
                f"({deployment['status']})"
            )
            return 0
        if arguments.command == "compose-deepseek-v4-hc-pre-input":
            lock = load_checkpoint_lock(arguments.lock)
            source_texts = tuple(
                _read_source_text_file(path) for path in arguments.source_text_files
            )
            report = build_deepseek_v4_hc_pre_input_request(
                snapshot=arguments.snapshot,
                lock=lock,
                lookup_deployment_root=arguments.lookup_deployment,
                lookup_request_path=arguments.lookup_request,
                lookup_result_path=arguments.lookup_result,
                lookup_differential_path=arguments.lookup_differential,
                executable_deployment_root=arguments.executable_deployment,
                executable_application_root=arguments.executable_application,
                source_texts=source_texts,
                output=arguments.output,
                report_output=arguments.report_output,
            )
            print(
                f"composed {report['request']['shape'][0]}x"
                f"{report['request']['shape'][1]} V4 HC_PRE input "
                f"{report['composition_id']} at {arguments.output.resolve()} "
                f"({report['status']})"
            )
            return 0
        if arguments.command == "execute-deepseek-v4-hc-pre":
            result = execute_deepseek_v4_hc_pre_executable_deployment(
                arguments.deployment,
                arguments.request / "request_manifest.json",
                arguments.output,
            )
            print(
                f"executed {result.token_count} token(s) through packaged V4 "
                f"HC_PRE {result.build_id}; request {result.request_sha256} at "
                f"{arguments.output.resolve()} ({result.status})"
            )
            return 0
        if arguments.command == "verify-deepseek-v4-hc-pre-execution":
            lock = load_checkpoint_lock(arguments.lock)
            report = verify_deepseek_v4_hc_pre_execution(
                snapshot=arguments.snapshot,
                lock=lock,
                application_root=arguments.application,
                deployment_root=arguments.deployment,
                request_root=arguments.request,
                result_root=arguments.result,
                report_path=arguments.output,
            )
            print(
                f"verified {len(report['comparisons'])} HC_PRE payloads and "
                f"{len(report['logical_counters'])} counters; differential "
                f"{report['differential_id']} ({report['status']})"
            )
            return 0
    except (
        BuildError,
        IRValidationError,
        RomImageError,
        MicrocodeError,
        InverseCheckError,
        CheckpointError,
        DeepSeekV4AdapterError,
        DeepSeekV4GraphError,
        DeepSeekV4GenerationError,
        DeepSeekV4TokenizerError,
        CanonicalApplicationError,
        CanonicalTransformError,
        DeepSeekV4ApplicationCheckError,
        DeepSeekV4FP8LinearDifferentialError,
        DeepSeekV4FP8LinearBuildError,
        DeepSeekV4HCPreBuildError,
        DeepSeekV4HCPreExecutableBuildError,
        DeepSeekV4HCPreExecutableServiceError,
        DeepSeekV4HCPreExecutionCheckError,
        DeepSeekV4HCPreInputBuildError,
        DeepSeekV4LookupDifferentialError,
        DeepSeekV4LookupBuildError,
        OSError,
    ) as exc:
        print(f"compiler error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError("argparse accepted an unknown command")
