"""Read-only CLI presentation; historical job state remains intact."""
from collections import Counter
import datetime as dt
import json
import math


def nonnegative_int(value):
    import argparse
    try:
        result = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    if result < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return result


def nonnegative_hours(value):
    import argparse
    try:
        result = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a finite nonnegative number")
    if not math.isfinite(result) or result < 0:
        raise argparse.ArgumentTypeError("must be a finite nonnegative number")
    return result


def add_arguments(parser):
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="show every saved job, including historical results")
    mode.add_argument("--active", action="store_true", help="show only nonterminal jobs")
    parser.add_argument("--recent-hours", type=nonnegative_hours, default=24,
                        help="recent result window in hours (default: 24; active jobs always shown)")
    parser.add_argument("--limit", type=nonnegative_int, default=20,
                        help="maximum recent results (default: 20; active jobs are never limited)")
    parser.add_argument("--filter", default="", metavar="TEXT",
                        help="case-insensitive match on job name, block, or owner")


def timestamp(job, *fields):
    for field in fields:
        try:
            value = dt.datetime.fromisoformat(str(job.get(field, "")).replace("Z", "+00:00"))
            if value.tzinfo is None:
                value = value.replace(tzinfo=dt.timezone.utc)
            return value.timestamp()
        except (ValueError, OverflowError):
            continue
    return 0.0


def block_key(job):
    spec = job.get("spec", {})
    # Do not conflate explicit parameter variants. Jobs without a block are
    # distinct rather than collapsing into one unnamed history entry.
    return (spec.get("block") or job["name"],
            json.dumps(spec.get("params", spec.get("parameters", {})), sort_keys=True))


def select_jobs(jobs, args, terminal, now=None):
    now = dt.datetime.now(dt.timezone.utc).timestamp() if now is None else now
    query = args.filter.casefold()
    matched = [j for j in jobs if query in " ".join(str(x) for x in
               (j["name"], j.get("spec", {}).get("block", ""), j.get("spec", {}).get("owner", ""))).casefold()]
    if args.all:
        return matched, [], matched
    active = sorted((j for j in matched if j["status"] not in terminal), key=lambda j: j["name"])
    if args.active:
        return active, [], matched
    latest = {}
    for job in matched:
        # Cancelled/invalid attempts are housekeeping, not current results.
        if job["status"] in {"CANCELLED", "INVALID"}:
            continue
        key = block_key(job)
        order = (timestamp(job, "created", "finished_at", "updated"), job["name"])
        if key not in latest or order > latest[key][0]:
            latest[key] = (order, job)
    recent = [job for _, job in latest.values() if job["status"] in terminal and
              timestamp(job, "finished_at", "updated", "created") >= now - args.recent_hours * 3600]
    recent.sort(key=lambda j: (timestamp(j, "finished_at", "updated", "created"), j["name"]), reverse=True)
    return active, recent[:args.limit], matched


def print_status(jobs, args, terminal, host_label):
    active, recent, matched = select_jobs(jobs, args, terminal)
    counts = Counter(j["status"] for j in matched)
    print(f"Jobs: {len(matched)} saved; {sum(n for s, n in counts.items() if s not in terminal)} active; "
          + ", ".join(f"{s} {n}" for s, n in sorted(counts.items()) if s in terminal))

    def rows(items):
        print(f"{'JOB':40s} {'STATUS':12s} {'STAGE':16s} {'HOST':8s} REASON / WAIT")
        for job in items:
            reason = " ".join(str(job.get("reason") or job.get("wait") or "").split())
            print(f"{job['name']:40s} {job['status']:12s} {job.get('stage_key', '-'):16s} "
                  f"{host_label(job.get('host')):8s} {reason[:90]}")

    if args.all:
        rows(active)
        return
    print(f"\nActive jobs ({len(active)}):")
    if active:
        rows(active)
    else:
        print("  none")
    if not args.active:
        print(f"\nRecent results ({len(recent)}, last {args.recent_hours:g}h, latest attempt per block):")
        if recent:
            rows(recent)
        else:
            print("  none")
    print(f"\nHidden: {len(matched) - len(active) - len(recent)} saved jobs. "
          "Use status --all [--filter TEXT] for history.")
