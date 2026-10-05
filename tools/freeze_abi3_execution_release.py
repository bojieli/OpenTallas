#!/usr/bin/env python3
"""Create or verify one immutable ABI 3.0 execution-release lock.

The lock is deliberately outside the ABI wire format.  It joins the committed
software tree to already locked comparison contracts, checkpoint/source locks,
and one create-once result namespace.  A production token or TPOT campaign can
therefore prove that it used exactly the same model, workload, oracle, neutral
IR, deployment, topology, process/PVT view, and TPOT budget.

``freeze`` only succeeds from a clean tracked worktree and only when every
comparison contract is source-current, fully locked, and carries an explicit
TPOT budget.  ``verify`` repeats those checks and additionally requires the
current checkout to be the frozen commit.  Neither command creates execution
state, checkpoints, retries, or rollback data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator


REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    publish_bytes_atomic_no_replace,
)
from runtime.abi3.capability import digest_of  # noqa: E402
from tools.abi3_comparison_boundary import (  # noqa: E402
    BoundaryError,
    load_comparison_contract,
)


SCHEMA = "opentallas.abi3.execution_release_lock.v1"
SCHEMA_PATH = REPO / "schemas/abi3/execution_release_lock_v1.schema.json"
ABI_VERSION = "3.0"
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,191}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReleaseLockError(ValueError):
    """The requested release cannot be frozen or revalidated."""


def _strict_json_loads(payload: str | bytes, *, source: object) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        body: dict[str, Any] = {}
        for key, value in pairs:
            if key in body:
                raise ReleaseLockError(f"duplicate JSON key {key!r} in {source}")
            body[key] = value
        return body

    def reject_constant(value: str) -> None:
        raise ReleaseLockError(f"non-finite JSON number {value!r} in {source}")

    try:
        return json.loads(
            payload,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ReleaseLockError(f"malformed JSON in {source}: {exc}") from exc


def _load_object(path: Path) -> dict[str, Any]:
    body = _strict_json_loads(path.read_bytes(), source=path)
    if not isinstance(body, dict):
        raise ReleaseLockError(f"{path} is not a JSON object")
    return body


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo: Path, *arguments: str, text: bool = True) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=text,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"")
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        raise ReleaseLockError(
            f"git {' '.join(arguments)} failed: {str(detail).strip()}"
        ) from exc
    return result.stdout.strip() if text else result.stdout


def _repo_relative(repo: Path, raw: Path | str, *, must_exist: bool) -> tuple[Path, str]:
    path = Path(raw)
    unresolved = path if path.is_absolute() else repo / path
    if unresolved.is_symlink():
        raise ReleaseLockError(f"release paths may not be symlinks: {raw}")
    resolved = unresolved.resolve()
    root = repo.resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ReleaseLockError(f"path escapes the repository: {raw}") from exc
    if not relative or relative == "." or ".." in Path(relative).parts:
        raise ReleaseLockError(f"path is not a canonical repository member: {raw}")
    if must_exist and not resolved.is_file():
        raise ReleaseLockError(f"required release file is unavailable: {relative}")
    return resolved, relative


def _tracked_source(repo: Path) -> dict[str, Any]:
    status = str(_git(repo, "status", "--porcelain=v1", "--untracked-files=no"))
    if status:
        raise ReleaseLockError(
            "tracked worktree is not clean; freeze from one committed source snapshot"
        )
    commit = str(_git(repo, "rev-parse", "--verify", "HEAD^{commit}"))
    tree = str(_git(repo, "rev-parse", "HEAD^{tree}"))
    if not SHA256.fullmatch(commit) and len(commit) != 40:
        raise ReleaseLockError("HEAD is not a full Git object ID")
    if not SHA256.fullmatch(tree) and len(tree) != 40:
        raise ReleaseLockError("HEAD tree is not a full Git object ID")
    payload = _git(repo, "ls-files", "-s", "-z", text=False)
    assert isinstance(payload, bytes)
    rows: list[dict[str, Any]] = []
    for entry in payload.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, raw_path = entry.split(b"\t", 1)
            mode, blob, stage = metadata.decode("ascii").split()
            path = raw_path.decode("utf-8")
        except (UnicodeError, ValueError) as exc:
            raise ReleaseLockError("git index contains an unparseable entry") from exc
        if stage != "0":
            raise ReleaseLockError(f"git index has an unmerged entry: {path}")
        rows.append({"blob": blob, "mode": mode, "path": path})
    rows.sort(key=lambda row: str(row["path"]))
    if not rows:
        raise ReleaseLockError("tracked source map is empty")
    return {
        "commit": commit,
        "tree": tree,
        "tracked_file_count": len(rows),
        "tracked_source_map": rows,
        "tracked_source_map_sha256": digest_of(rows),
        "tracked_worktree_clean": True,
    }


def _contract_record(repo: Path, raw_path: Path | str) -> dict[str, Any]:
    path, relative = _repo_relative(repo, raw_path, must_exist=True)
    contract = _load_object(path)
    comparison_id = contract.get("comparison_id")
    if not isinstance(comparison_id, str):
        raise ReleaseLockError(f"comparison contract has no ID: {relative}")
    try:
        loaded, validation, registered_path = load_comparison_contract(
            comparison_id,
            repo=repo,
            path=path,
            require_ready=True,
        )
    except BoundaryError as exc:
        raise ReleaseLockError(
            f"comparison contract is not release-ready: {relative}: {exc}"
        ) from exc
    if registered_path.resolve() != path:
        raise ReleaseLockError(f"comparison contract path is not registered: {relative}")
    execution = loaded.get("execution")
    budget = execution.get("tpot_acceptance") if isinstance(execution, dict) else None
    if not isinstance(budget, dict):
        raise ReleaseLockError(
            f"comparison contract has no explicit TPOT acceptance budget: {relative}"
        )
    if budget.get("batch_size") != execution.get("batch"):
        raise ReleaseLockError(
            f"comparison contract TPOT budget batch differs from execution: {relative}"
        )
    targets = loaded.get("targets")
    target_rows: list[dict[str, Any]] = []
    if isinstance(targets, dict):
        for role, raw in sorted(targets.items()):
            target = raw if isinstance(raw, dict) else {}
            target_rows.append(
                {
                    "backend": target.get("backend"),
                    "node_count": target.get("node_count"),
                    "role": role,
                    "target_id": target.get("target_id"),
                    "topology_class": target.get("topology_class"),
                }
            )
    model = loaded.get("model") if isinstance(loaded.get("model"), dict) else {}
    workload = (
        loaded.get("workload") if isinstance(loaded.get("workload"), dict) else {}
    )
    policy = loaded.get("policy") if isinstance(loaded.get("policy"), dict) else {}
    return {
        "batch_size": execution.get("batch"),
        "comparison_id": comparison_id,
        "context_tokens": execution.get("context_tokens"),
        "model_id": model.get("model_id"),
        "path": relative,
        "process_view": policy.get("technology_view"),
        "semantic_sha256": validation.get("contract_sha256"),
        "source_sha256": _sha256(path),
        "targets": target_rows,
        "tpot_acceptance_sha256": digest_of(budget),
        "workload_id": workload.get("workload_id"),
    }


def _named_lock(repo: Path, name: str, raw_path: Path | str) -> dict[str, Any]:
    if not IDENTIFIER.fullmatch(name):
        raise ReleaseLockError(f"external lock name is not an identifier: {name!r}")
    path, relative = _repo_relative(repo, raw_path, must_exist=True)
    body = _load_object(path)
    return {
        "name": name,
        "path": relative,
        "semantic_sha256": digest_of(body),
        "source_sha256": _sha256(path),
    }


def release_digest(body: Mapping[str, Any]) -> str:
    payload = dict(body)
    payload.pop("release_sha256", None)
    return digest_of(payload)


def build_release_lock(
    *,
    repo: Path,
    release_id: str,
    comparison_contracts: Sequence[Path | str],
    external_locks: Mapping[str, Path | str],
    result_namespace: Path | str,
) -> dict[str, Any]:
    if not IDENTIFIER.fullmatch(release_id):
        raise ReleaseLockError("release_id is not a canonical identifier")
    if not comparison_contracts:
        raise ReleaseLockError("at least one comparison contract is required")
    if not external_locks:
        raise ReleaseLockError("at least one checkpoint/source lock is required")
    namespace, namespace_relative = _repo_relative(
        repo, result_namespace, must_exist=False
    )
    if namespace.exists() or namespace.is_symlink():
        raise ReleaseLockError(
            "result namespace already exists; release output must be create-once"
        )
    contracts = [_contract_record(repo, path) for path in comparison_contracts]
    if len({row["comparison_id"] for row in contracts}) != len(contracts):
        raise ReleaseLockError("comparison contract IDs are not unique")
    locks = [
        _named_lock(repo, name, path)
        for name, path in sorted(external_locks.items())
    ]
    document: dict[str, Any] = {
        "abi_version": ABI_VERSION,
        "comparison_contracts": sorted(
            contracts, key=lambda row: str(row["comparison_id"])
        ),
        "external_locks": locks,
        "release_id": release_id,
        "result_namespace": {
            "create_once": True,
            "path": namespace_relative,
        },
        "schema": SCHEMA,
        "source": _tracked_source(repo),
    }
    document["release_sha256"] = release_digest(document)
    return document


def _schema_problems(body: object) -> list[str]:
    schema = _load_object(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    return [
        f"schema violation at {error.json_path}: {error.message}"
        for error in sorted(
            Draft202012Validator(schema).iter_errors(body),
            key=lambda error: (
                tuple(str(part) for part in error.absolute_path),
                error.message,
            ),
        )
    ]


def validate_release_lock(body: Mapping[str, Any] | object, *, repo: Path) -> list[str]:
    if not isinstance(body, dict):
        return ["release lock is not a JSON object"]
    problems = _schema_problems(body)
    if body.get("release_sha256") != release_digest(body):
        problems.append("release_sha256 is inconsistent")
    try:
        current_source = _tracked_source(repo)
    except ReleaseLockError as exc:
        problems.append(str(exc))
        current_source = {}
    if body.get("source") != current_source:
        problems.append("current committed source differs from the frozen release")

    observed_contracts: list[dict[str, Any]] = []
    for row in body.get("comparison_contracts", []):
        if not isinstance(row, dict):
            continue
        try:
            observed_contracts.append(_contract_record(repo, row.get("path", "")))
        except (OSError, ReleaseLockError) as exc:
            problems.append(f"cannot revalidate comparison contract: {exc}")
    observed_contracts.sort(key=lambda row: str(row["comparison_id"]))
    if body.get("comparison_contracts") != observed_contracts:
        problems.append("comparison contracts differ from the frozen release")

    observed_locks: list[dict[str, Any]] = []
    for row in body.get("external_locks", []):
        if not isinstance(row, dict):
            continue
        try:
            observed_locks.append(
                _named_lock(repo, str(row.get("name", "")), row.get("path", ""))
            )
        except (OSError, ReleaseLockError) as exc:
            problems.append(f"cannot revalidate external lock: {exc}")
    observed_locks.sort(key=lambda row: str(row["name"]))
    if body.get("external_locks") != observed_locks:
        problems.append("checkpoint/source locks differ from the frozen release")

    namespace_record = body.get("result_namespace")
    if isinstance(namespace_record, dict):
        try:
            namespace, _ = _repo_relative(
                repo, namespace_record.get("path", ""), must_exist=False
            )
            if namespace.exists() and (not namespace.is_dir() or namespace.is_symlink()):
                problems.append("result namespace exists but is not a real directory")
        except ReleaseLockError as exc:
            problems.append(str(exc))
    return sorted(set(problems))


def _parse_named_locks(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not name or not path:
            raise ReleaseLockError("--external-lock must use NAME=PATH")
        if name in result:
            raise ReleaseLockError(f"duplicate external lock name: {name}")
        result[name] = Path(path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze = subparsers.add_parser("freeze", help="publish one create-once lock")
    freeze.add_argument("--release-id", required=True)
    freeze.add_argument(
        "--comparison-contract", action="append", type=Path, required=True
    )
    freeze.add_argument(
        "--external-lock",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="checkpoint or other external source lock (repeatable)",
    )
    freeze.add_argument("--result-namespace", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)
    verify = subparsers.add_parser("verify", help="revalidate a frozen lock")
    verify.add_argument("lock", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "freeze":
            output, _ = _repo_relative(REPO, args.output, must_exist=False)
            namespace, _ = _repo_relative(
                REPO, args.result_namespace, must_exist=False
            )
            try:
                output.relative_to(namespace)
            except ValueError:
                pass
            else:
                raise ReleaseLockError(
                    "release-lock output must be outside its result namespace"
                )
            document = build_release_lock(
                repo=REPO,
                release_id=args.release_id,
                comparison_contracts=args.comparison_contract,
                external_locks=_parse_named_locks(args.external_lock),
                result_namespace=args.result_namespace,
            )
            schema_problems = _schema_problems(document)
            if schema_problems:
                raise ReleaseLockError("; ".join(schema_problems))
            output.parent.mkdir(parents=True, exist_ok=True)
            publish_bytes_atomic_no_replace(output, canonical_json_bytes(document))
            print(f"frozen ABI 3.0 execution release {args.release_id}: {output}")
            return 0

        lock, _ = _repo_relative(REPO, args.lock, must_exist=True)
        document = _load_object(lock)
        problems = validate_release_lock(document, repo=REPO)
        for problem in problems:
            print(f"PROBLEM {problem}")
        print(f"ABI 3.0 execution release: {'valid' if not problems else 'invalid'}")
        return 0 if not problems else 1
    except (OSError, ReleaseLockError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
