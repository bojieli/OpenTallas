"""Fresh native PG-terminal admission; a saved receipt is never admission authority.

This predicate qualifies native master POWER/GROUND terminal bindings only.
It does not establish routed conductor connectivity, shorts, or timing closure.
"""
from __future__ import annotations

import argparse
import hashlib
import gzip
import shlex
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SCHEMA = "opentallas.native_pg_receipt.v1"
SCOPE = "native_master_pg_terminal_binding_only"


class PGRefused(RuntimeError):
    pass


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _default_collector() -> Path:
    here = Path(__file__).resolve().parent
    flat = here / "audit_native_pg.tcl"
    return flat if flat.is_file() else here.parent.parent / "physical/common_flow/audit_native_pg.tcl"


def _validate_audit(audit: dict) -> None:
    if audit.get("schema") != "native_pg_audit.v1":
        raise PGRefused("native audit schema mismatch")
    if audit.get("mapping_error"):
        raise PGRefused("native domain mapping refused: " + str(audit["mapping_error"]))
    counts = (audit.get("checked"), audit.get("instance_count"), audit.get("pg_master_count"))
    if any(type(n) is not int or n <= 0 for n in counts):
        raise PGRefused("native audit lacks nonzero master/instance/terminal coverage")
    roles = audit.get("roles")
    if not isinstance(roles, dict) or set(roles) != {"POWER", "GROUND"}:
        raise PGRefused("native audit lacks exact POWER/GROUND counts")
    if any(type(n) is not int or n <= 0 for n in roles.values()) or sum(roles.values()) != audit["checked"]:
        raise PGRefused("native audit coverage counts disagree")
    failures = audit.get("failures")
    if not isinstance(failures, list) or type(audit.get("failure_count")) is not int:
        raise PGRefused("native audit lacks failure inventory")
    if len(failures) != audit["failure_count"] or failures or audit.get("status") != "PASS":
        raise PGRefused("native PG terminal binding FAIL")
    rules = audit.get("domain_rules")
    if not isinstance(rules, list) or not rules or not isinstance(audit.get("regions"), list):
        raise PGRefused("native audit lacks domain rules/regions")
    for rule in rules:
        if not isinstance(rule, dict) or set(rule) != {"inst_pattern", "pin_pattern", "net", "role", "region"}:
            raise PGRefused("malformed native rule snapshot")
        if rule["role"] not in roles or not rule["net"]:
            raise PGRefused("native rule lacks supply role/net")


def _spef_design(path: Path) -> str:
    with path.open("rb") as f:
        compressed = f.read(2) == b"\x1f\x8b"
    opener = gzip.open if compressed else open
    with opener(path, "rt", encoding="utf-8", errors="strict") as f:
        for line in f:
            if line.startswith("*DESIGN "):
                fields = shlex.split(line)
                if len(fields) == 2 and fields[1]:
                    return fields[1]
                break
            if line.startswith("*NAME_MAP") or line.startswith("*D_NET"):
                break
    raise PGRefused("SPEF lacks unambiguous DESIGN header")


def require_native_pg(odb: Path, *, collector: Path | None = None,
                      openroad: str | None = None, receipt_dir: Path | None = None,
                      spef: Path | None = None, parasitic_model: str = "routed_extracted") -> dict:
    """Execute a fresh read-only native audit of this exact ODB, preserving FAIL.

    Every call uses an exclusive new transaction directory. No caller-provided
    receipt or cached JSON is read, including a receipt next to the active ODB.
    """
    odb = Path(odb).resolve(strict=True)
    if parasitic_model != "routed_extracted":
        raise PGRefused("final publication requires routed_extracted SPEF, not placement RC")
    spef = Path(spef or odb.parent / "6_final.spef").resolve(strict=True)
    spef_before = _sha(spef)
    spef_design = _spef_design(spef)
    collector = Path(collector or os.environ.get("OT_PG_COLLECTOR") or _default_collector()).resolve(strict=True)
    binding = collector.parent / "native_pg_binding.tcl"
    binding = binding.resolve(strict=True)
    program = openroad or os.environ.get("OPENROAD_EXE") or "openroad"
    executable = shutil.which(program)
    image = None
    binary = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
    if not executable and (openroad or os.environ.get("OPENROAD_EXE")):
        raise PGRefused("explicit native OpenROAD executable unavailable: " + program)
    if executable:
        executable = str(Path(executable).resolve(strict=True))
        executable_sha = _sha(Path(executable))
    else:
        if not shutil.which("docker"):
            raise PGRefused("neither native OpenROAD nor Docker is available")
        requested_image = os.environ.get("ORFS_IMAGE", "openroad/orfs:asap7lock")
        # Resolve mutable tags once, then run only the immutable image ID.
        image = subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", requested_image], text=True).strip()
        if not image.startswith("sha256:"):
            raise PGRefused("unresolved native container image")
        executable_sha = subprocess.check_output(["docker", "run", "--rm", "--entrypoint", "sha256sum", image, binary], text=True).split()[0]
        if len(executable_sha) != 64:
            raise PGRefused("native binary hash unavailable")
    dependencies = {str(p): _sha(p) for p in (Path(__file__).resolve(), collector, binding)}
    before = _sha(odb)
    parent = Path(receipt_dir) if receipt_dir else odb.parent / "native_pg_receipts"
    parent.mkdir(parents=True, exist_ok=True)
    parent = parent.resolve(strict=True)
    transaction = Path(tempfile.mkdtemp(prefix="audit-", dir=parent))
    raw = transaction / "native_audit.json"
    log = transaction / "native.log"
    receipt_path = transaction / "receipt.json"
    receipt = {"schema": SCHEMA, "binding_scope": SCOPE, "status": "REFUSED",
               "input_odb": str(odb), "odb_sha256": before,
               "input_spef": str(spef), "spef_sha256": spef_before,
               "spef_design": spef_design, "parasitic_model": parasitic_model,
               "parasitic_qualification": "source_output_pair_hash_binding_not_independent_rc_equivalence",
               "source_dependencies": dependencies, "openroad_sha256": executable_sha, "container_image": image,
               "native_audit": str(raw), "transaction": str(transaction)}
    try:
        env = os.environ.copy()
        env.update(OT_PG_AUDIT_ODB=str(odb), OT_PG_AUDIT_REPORT=str(raw))
        command = [executable, "-exit", str(collector)]
        if image:
            command = ["docker", "run", "--rm", "--entrypoint", binary,
                       "-v", f"{odb}:/input/final.odb:ro",
                       "-v", f"{collector.parent}:/collector:ro",
                       "-v", f"{transaction}:/output",
                       "-e", "OT_PG_AUDIT_ODB=/input/final.odb",
                       "-e", "OT_PG_AUDIT_REPORT=/output/native_audit.json",
                       image, "-exit", "/collector/" + collector.name]
        # Audit is read-only, and intentionally never calls global_connect.
        with log.open("xb") as output:
            result = subprocess.run(command, env=env,
                                    stdout=output, stderr=subprocess.STDOUT, check=False)
        receipt["native_exit"] = result.returncode
        if raw.is_symlink() or not raw.is_file():
            raise PGRefused("native collector produced no fresh regular audit")
        receipt["native_audit_sha256"] = _sha(raw)
        audit = json.loads(raw.read_text())
        # Preserve the raw failure inventory even if exit status/schema refuses.
        receipt["native_result"] = audit
        if _sha(odb) != before:
            raise PGRefused("active ODB changed during native admission")
        if _sha(spef) != spef_before:
            raise PGRefused("active SPEF changed during native admission")
        if audit.get("block") != spef_design:
            raise PGRefused("SPEF DESIGN mismatches active native ODB block")
        if any(_sha(Path(p)) != digest for p, digest in dependencies.items()) or (executable and _sha(Path(executable)) != executable_sha):
            raise PGRefused("executed collector/source changed during native admission")
        _validate_audit(audit)
        if result.returncode:
            raise PGRefused("native collector exited nonzero")
        domain = {"domain_rules": audit["domain_rules"], "regions": audit["regions"]}
        receipt.update(status="PASS", checked=audit["checked"], roles=audit["roles"],
                       failure_count=0, domain_rules_sha256=hashlib.sha256(_json_bytes(domain)).hexdigest())
    except Exception as error:
        receipt["reason"] = str(error)
        with receipt_path.open("x") as f:
            json.dump(receipt, f, sort_keys=True, indent=2)
            f.write("\n")
        raise PGRefused(f"{error}; preserved native receipt {receipt_path}") from error
    with receipt_path.open("x") as f:
        json.dump(receipt, f, sort_keys=True, indent=2)
        f.write("\n")
    receipt["receipt_path"] = str(receipt_path)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify"])
    parser.add_argument("odb", type=Path)
    parser.add_argument("--collector", type=Path)
    parser.add_argument("--openroad")
    parser.add_argument("--receipt-dir", type=Path)
    parser.add_argument("--spef", type=Path)
    parser.add_argument("--parasitic-model", default="routed_extracted")
    args = parser.parse_args()
    try:
        receipt = require_native_pg(args.odb, collector=args.collector, openroad=args.openroad, receipt_dir=args.receipt_dir,
                                    spef=args.spef, parasitic_model=args.parasitic_model)
    except (PGRefused, OSError) as error:
        print("NATIVE_PG_REFUSED", error)
        return 2
    print("NATIVE_PG_PASS", receipt["receipt_path"], receipt["odb_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
