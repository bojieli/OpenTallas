"""Retain and verify an exact placed Flow Canary kit before routing it."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import time
from zoneinfo import ZoneInfo

TYPE_ROUTE = "bash {gen}/run_kit.sh {kit} route {mem} {cpus}"
ACCEPT = {"GOOD", "OK", "ISSUES-ACCEPT"}
REJECT = {"BAD", "ISSUES"}
IMAGES = ("floorplan.png", "density.png")
HUB_TZ = ZoneInfo("America/Los_Angeles")
MAX_ROUTE_WAIT_S = 30 * 60
REVIEW_KEEP_S = 12 * 3600
ADMISSION_HOSTS = "intel1,epyc7,epyc8,epyc10,epyc11"
REVIEW_FILES = (
    "autopilot/render_review.sh", "autopilot/render_review.py",
    "ref_tile/layout_dump.tcl", "ref_tile/layout_png.py", "ref_tile/layout_review.tcl",
)
HEAD = re.compile(r"GEOM VERDICT \[([^\]]*)\] (\S+)/(\S+) (?:attempt_|a)(\d+)\b")
STAMP = re.compile(r"^-\s+(\d{4}-\d\d-\d\d \d\d:\d\d)")
KIT = re.compile(r"(?:^|\s)kit=([^\s`]+)")
VERDICT = re.compile(r"\s*(ISSUES-ACCEPT|GOOD|OK|BAD|ISSUES)\b")


def supported(spec):
    return spec.get("flow") == "type" and spec.get("run") == TYPE_ROUTE


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_json(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    temp.replace(path)


def receipt_path(run):
    return Path(run) / "gen" / "placement_review" / "placed.json"


def read_receipt(run):
    return json.loads(receipt_path(run).read_text())


def checkpoint(kit):
    bases = list(kit.glob("run/results/asap7/*/base"))
    if len(bases) != 1:
        raise ValueError("expected one placed results directory")
    odb = bases[0] / "3_place.odb"
    if not odb.is_file() or not odb.stat().st_size:
        raise ValueError("3_place.odb is missing or empty")
    if any(bases[0].glob("[456]_*.odb")):
        raise ValueError("kit already contains post-placement checkpoints")
    return odb


def render(a):
    kit, out = Path(a.kit), Path(a.out)
    odb = checkpoint(kit)
    placed_sha = digest(odb)
    out.mkdir(parents=True, exist_ok=True)
    tools = out / "tools"
    tools.mkdir(exist_ok=True)
    for path in Path(a.tools).iterdir():
        (tools / path.name).write_bytes(path.read_bytes())
    summary = out / "placement_only.json"
    write_json(summary, {"verdict": "PLACEMENT REVIEW", "reasons": []})
    write_json(out / "review.json", {"kit": str(kit), "odb": str(odb), "signoff": str(summary),
                                    "image": a.image, "id": out.parent.parent.name[-55:],
                                    "title": f"Flow Canary {a.die}/{a.item} exact placement"})
    for name in IMAGES:
        (out / name).unlink(missing_ok=True)
    subprocess.run(["bash", str(tools / "render_review.sh"), str(out)], check=True)
    if digest(checkpoint(kit)) != placed_sha:
        raise ValueError("placement checkpoint changed during rendering")
    doc = {"die": a.die, "item": a.item, "attempt": 1, "src_commit": a.src_commit,
           "kit": str(kit), "kit_location": f"{a.host}:{kit}", "odb": str(odb),
           "odb_sha256": placed_sha, "runner_sha256": digest(kit.parent / "run_kit.sh"), "ready_at": time.time(),
           "images": {name: digest(out / name) for name in IMAGES}}
    certificate = getattr(a, "input_certificate", None)
    if certificate:
        path = Path(certificate)
        if path.is_file() and not path.is_symlink():
            doc["placement_inputs_file_sha256"] = digest(path)
    write_json(out / "placed.json", doc)
    print(f"CANARY WAIT-VISUAL {a.die}/{a.item} attempt_1 kit={doc['kit_location']} "
          f"odb_sha256={placed_sha} views={out}/{','.join(IMAGES)}")


def line_verdict(tail):
    depth = 0
    for i, char in enumerate(tail):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ":" and not depth and (m := VERDICT.match(tail, i + 1)):
            return m[1]
    return None


def latest_decision(doc, log):
    """Return the last current human verdict and line identity for this exact kit."""
    row = doc["die"], doc["item"], str(doc["attempt"])
    ready_minute = int(doc["ready_at"]) // 60 * 60
    verdict = None
    for line in log.splitlines():
        h, ts, kit = HEAD.search(line), STAMP.match(line), KIT.search(line)
        if not h or not ts or not kit or h.group(2, 3, 4) != row or kit[1] != doc["kit_location"]:
            continue
        if h[1].startswith("AUTO-VISUAL-REVIEW") or not re.search(r"\bviewed\b", h[1], re.I):
            continue
        try:
            reviewed = datetime.strptime(ts[1], "%Y-%m-%d %H:%M").replace(tzinfo=HUB_TZ).timestamp()
        except ValueError:
            continue
        if ready_minute <= reviewed <= time.time():
            parsed = line_verdict(line[h.end():])
            verdict = (parsed, hashlib.sha256(line.encode()).hexdigest()) if parsed else None
    return verdict


def latest_viewed(doc, log):
    decision = latest_decision(doc, log)
    return decision[0] if decision else None


def canonical_review_log():
    coord = Path.home() / "coord"
    for path in (coord / "lanes/GEOM-REVIEW.md", coord / "GEOM-REVIEW.md"):
        if path.is_file():
            return path.read_text(errors="replace")
    return ""


def worker_review_log(doc):
    """Read the latest exact lines from the canonical hub at worker entry."""
    hub = doc["kit_location"].partition(":")[0]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", hub):
        raise ValueError("invalid review hub")
    cmd = ('f="$HOME/coord/lanes/GEOM-REVIEW.md"; '
           'if [ ! -f "$f" ]; then f="$HOME/coord/GEOM-REVIEW.md"; fi; '
           f'grep -F -- {shlex.quote(doc["kit_location"])} "$f"')
    result = subprocess.run(["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none",
                             "-o", "ConnectTimeout=10", hub, "bash -c " + shlex.quote(cmd)],
                            capture_output=True, text=True, timeout=15)
    if result.returncode not in (0, 1):
        raise ValueError("cannot refresh canonical viewed approval")
    return result.stdout


def keep_text(run):
    return f"Flow Canary retained placement pending viewed route review: {run.name}\n"


def release_owned_keep(run, evidence, now=None):
    """Retain evidence through the ordinary probe review window."""
    try:
        lease = run / ".keep"
        oldest = (time.time() if now is None else now) - REVIEW_KEEP_S
        if evidence.stat().st_mtime <= oldest and not lease.is_symlink() and lease.read_text() == keep_text(run):
            lease.unlink()
    except OSError:
        return


def definitely_not_started(log):
    """Permit retry only on positive evidence that the route script never started CAD."""
    if any(marker in log for marker in ("CANARY_ROUTE_STARTED", "CANARY_FLOW_RC ", "STILL RUNNING", "NOT COMPLETED")):
        return False
    if "CANARY PREPARE-ROUTE REFUSED" in log:
        return True
    return "ot-run: NOT RUN" in log and not any(
        marker in log for marker in ("ot-heavy: admitted on", "ot-run: RAN on")
    )


def validate_placement(kit, receipt, doc):
    if doc["kit"] != str(kit) or doc["odb"] != str(checkpoint(kit)):
        raise ValueError("placement receipt does not name this kit's checkpoint")
    if doc["odb_sha256"] != digest(doc["odb"]):
        raise ValueError("reviewed placement checkpoint bytes changed")
    if doc["runner_sha256"] != digest(kit.parent / "run_kit.sh"):
        raise ValueError("kit runner changed since placement")
    if set(doc["images"]) != set(IMAGES) or any(
        digest(receipt.parent / name) != doc["images"][name] for name in IMAGES
    ):
        raise ValueError("exact placement review images missing or changed")


def prepare_route(a):
    receipt = Path(a.receipt)
    doc = json.loads(receipt.read_text())
    approval = json.loads(Path(a.approval).read_text())
    if approval["placement_sha256"] != digest(receipt) or approval["verdict"] not in ACCEPT:
        raise ValueError("route request does not approve this exact placement receipt")
    waited = time.time() - approval["requested_at"]
    if not 0 <= waited <= MAX_ROUTE_WAIT_S:
        raise ValueError("viewed route request expired while waiting for admission")
    expected = approval["verdict"], approval["review_line_sha256"]
    if latest_decision(doc, worker_review_log(doc)) != expected:
        raise ValueError("canonical viewed verdict is absent, changed or revoked")
    kit, runner = Path(a.kit), Path(a.runner)
    validate_placement(kit, receipt, doc)
    if runner != kit.parent / "run_kit.sh":
        raise ValueError("route runner does not belong to the reviewed kit")
    kr = importlib.util.spec_from_file_location("kit_resume", kit / "kit_resume.py")
    if not kr or not kr.loader or "OT_STAGE_RESUME_V1" not in runner.read_text():
        raise ValueError("kit runner does not support the stock stage resume")
    resume = importlib.util.module_from_spec(kr)
    kr.loader.exec_module(resume)
    plan = resume.auto_write(str(kit), "route") or {}
    if plan.get("start") != "cts" or "place" not in plan.get("reused_steps", ()):
        raise ValueError("stock runner cannot resume directly from retained placement")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    placement = sub.add_parser("render")
    for name in ("kit", "out", "tools", "die", "item", "src-commit", "host", "image"):
        placement.add_argument(f"--{name}", required=True)
    placement.add_argument("--input-certificate")
    route = sub.add_parser("prepare-route")
    for name in ("kit", "runner", "receipt", "approval"):
        route.add_argument(f"--{name}", required=True)
    a = cli.parse_args()
    try:
        (render if a.command == "render" else prepare_route)(a)
    except (OSError, TypeError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"CANARY {a.command.upper()} REFUSED [{exc}]")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
