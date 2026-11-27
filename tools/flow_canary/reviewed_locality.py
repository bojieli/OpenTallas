"""Run a reviewed canary from its retained hub workspace on a permitted worker."""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import placement_review as review

SCRATCH = Path("/srv/opentallas-scratch2/claude")
WARM_REPO = SCRATCH / "warm" / "OpenTallas.git"
HUB_REPO = "/srv/opentallas-scratch2/git/OpenTallas.git"
WORKER_SETUP = SCRATCH / "rt" / "current" / "tools" / "flow_canary" / "reviewed_locality.py"
OT_RUN = Path.home() / ".local/bin/ot-run"
SOURCE_DISK_GB = 12
WORK_DISK_GB = 20


def command_output(argv):
    return subprocess.check_output(argv, text=True).strip()


def source_head(source):
    return command_output(["git", "-C", str(source), "rev-parse", "HEAD"])


def prepare_source(root, sha):
    """Build the stock pinned source worktree once on the selected worker."""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("invalid source revision")
    import trigger
    source = trigger.snapshot_path(root, sha)
    source.parent.mkdir(parents=True, exist_ok=True)
    with (source.parent / f".{sha[:12]}.canary-source.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ready = source.with_name(f".{source.name}.canary-source-ready")
        if ready.is_file() and ready.read_text().strip() == sha and source_head(source) == sha:
            return 0
        git = ["git", f"--git-dir={WARM_REPO}"]
        if subprocess.run([*git, "cat-file", "-e", f"{sha}^{{commit}}"], capture_output=True).returncode:
            hub = os.environ.get("OT_HUB_NAME", "intel2")
            subprocess.run([*git, "fetch", "--no-tags", "--no-write-fetch-head", f"{hub}:{HUB_REPO}", sha],
                           check=True)
        trigger.source_snapshot(WARM_REPO, sha, root)
        if source_head(source) != sha:
            raise ValueError("worker source revision differs from reviewed source")
        subprocess.run(["git", "-C", str(source), "diff-index", "--quiet", "HEAD", "--"], check=True)
        ready.write_text(sha + "\n")
    return 0


def write_metadata(path, meta):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".canary-meta-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(meta, indent=1) + "\n").encode())
            os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def strict_pick(spec):
    hosts = review.ADMISSION_HOSTS
    worker = command_output([str(OT_RUN), "--hosts", hosts, "--strict-host", "--no-spill",
                             "--dir", str(SCRATCH), "--mem", str(spec["mem_gb"]),
                             "--threads", str(spec.get("threads", 8)),
                             "--disk", str(SOURCE_DISK_GB + WORK_DISK_GB),
                             "--max-wait", "1", "--pick"])
    if worker not in hosts.split(","):
        raise ValueError("stock picker did not return a permitted canary worker")
    return worker


def stage_worker_source(worker, run, sha):
    log = run / "worker-source.log"
    with log.open("a") as output:
        result = subprocess.run([str(OT_RUN), "--hosts", worker, "--strict-host", "--no-spill",
                                 "--dir", str(SCRATCH), "--mem", "8", "--threads", "4",
                                 "--disk", str(SOURCE_DISK_GB), "--", "python3", "-I", "-B",
                                 str(WORKER_SETUP), "prepare", str(run.parent), sha],
                                stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        raise ValueError(f"source setup on {worker} exited {result.returncode} (see {log})")


def run_on_worker(run, worker, spec, command, max_wait=None):
    """Use the stock transfer, admission and output-copyback path on one allowed host."""
    if worker not in review.ADMISSION_HOSTS.split(","):
        raise ValueError("canary worker is outside the permitted pool")
    tools = HERE.parent / "fleet"
    sys.path.insert(0, str(tools))
    stock = SourceFileLoader("_canary_stock_ot_run", str(tools / "ot-run")).load_module()
    stock.HOSTS[:] = stock.canon_hosts(stock.HOSTS)
    stock.STAGE[:] = [str(run)]
    stock.SPILL_ONLY_HOSTS.clear()
    stock.SPILL_ONLY_HOSTS.add(worker)
    mem, threads = spec["mem_gb"], spec.get("threads", 8)
    os.environ["OT_RUN_THREADS"] = str(threads)
    plan, why, _ = stock.spill_plan("localhost", str(run), command, mem, threads, False, WORK_DISK_GB,
                                    stock.held_hosts(), print)
    if not plan or plan[0] != worker or set(plan[1]) != {str(run)}:
        raise ValueError(f"stock worker staging refused: {why}")
    status = stock.spill_run("localhost", *plan, mem, command, str(run), max_wait, print, disk=WORK_DISK_GB)
    if status is None:
        raise ValueError("stock stage or admission did not start a worker")
    return status


def run_stage(run, stage):
    meta_path = run / "canary_meta.json"
    meta = json.loads(meta_path.read_text())
    spec = meta["spec"]
    if not meta.get("review_before_route") or not review.supported(spec):
        raise ValueError("not a reviewed type canary")
    if stage == "place":
        sha = source_head(meta["src"])
        source = Path(meta["src"])
        if not sha.startswith(meta["src_commit"]) or source != run.parent.parent / "sources" / sha[:12]:
            raise ValueError("canary source changed before stage")
        worker = strict_pick(spec)
        stage_worker_source(worker, run, sha)
        import pre_submit_review
        hold = pre_submit_review.hold(spec, source, sha, run.parent, meta.get("image", "openroad/orfs:asap7lock"),
                                      pre_submit_review.ledger(), staged=True)
        if hold:
            raise ValueError(hold)
        meta["placement_host"] = worker
        write_metadata(meta_path, meta)
        command = ["bash", "-c", "set -e; bash ./job.sh; test -f GENERATED; bash ./harness/place.sh"]
        status = run_on_worker(run, worker, spec, command)
        if status == 0:
            try:
                document = review.read_receipt(run)
                review.validate_placement(Path(meta["kit"]), review.receipt_path(run), document)
            except (KeyError, OSError, ValueError) as error:
                print(f"CANARY PLACEMENT RECEIPT FAILED after worker return: {error}", file=sys.stderr)
                return 3
        return status
    if not (run / "harness/route_approval.json").is_file():
        raise ValueError("exact route approval is absent")
    return run_on_worker(run, meta["placement_host"], spec, ["bash", "./harness/route_canary.sh"],
                         max_wait=review.MAX_ROUTE_WAIT_S)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("prepare", "place", "route"))
    parser.add_argument("path", type=Path)
    parser.add_argument("sha", nargs="?")
    args = parser.parse_args()
    path = args.path.resolve()
    try:
        if not args.path.is_absolute() or not path.is_relative_to(SCRATCH / "flow-canary"):
            raise ValueError("canary path is outside its dedicated scratch root")
        if args.stage == "prepare":
            return prepare_source(path, args.sha or "")
        return run_stage(path, args.stage)
    except (KeyError, OSError, subprocess.SubprocessError, ValueError) as error:
        print(f"ot-run: NOT RUN: canary locality setup: {error}", file=sys.stderr)
        return 96


if __name__ == "__main__":
    sys.exit(main())
