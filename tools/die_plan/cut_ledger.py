#!/usr/bin/env python3
"""CUT-LEDGER-R1 (FABLE-FLOW-0600 class K1): a die plan cut never drops a row silently.

Generic form of the hand-run d28_compose.py.  `compose` applies owner row scripts in manifest order on a base plan and writes
  <ledger-dir>/CUT-LEDGER-<die>-<event>.tsv   one line per input row: APPLIED / PARTIAL / NOOP / DROPPED / REFUSED / UNLISTED
and posts one DROPPED line to the row owner for every row that did not apply cleanly.  `seal` refuses (exit 5) while any such row
has no owner ACK, unless `--allow-drop ROW` names it.

Input rows = (a) every ROWS_*.py found in --rows-dir (a glob, never only the manifest) and (b) every manifest entry.  A file in the
directory that the manifest does not name is UNLISTED: reported and posted, never skipped.  A manifest entry whose script is missing
is DROPPED.  Row script contract (as d28_compose.py): `python3 -I SCRIPT PLAN_IN PLAN_OUT`; manifest
[{"owner","script","types","allow_top"?,"problem"?}].  The open problem a row was written for is the manifest "problem" or a
`# PROBLEM: ...` line in the script; the DROPPED post names it.

Statuses: APPLIED clean; PARTIAL applied but the script printed a "matched no ..." / "skipped" / "dropped" line (some ops lost);
NOOP applied but changed none of its named types; DROPPED script missing or failed; REFUSED stable-key breach (unnamed type or top
key changed); UNLISTED file not in the manifest.  ACK file: <ledger-dir>/CUT-ACK-<die>-<event>.tsv, lines `ROW<TAB>OWNER<TAB>note`.
usage:
  cut_ledger.py compose --die KV --event D28 --base BASE.json --out OUT_DIR --manifest rows.json --rows-dir DIR [--ledger-dir D] [--no-post]
  cut_ledger.py seal    --die KV --event D28 [--ledger-dir D] [--allow-drop ROW ...]
exit: compose 0 all APPLIED, 1 otherwise (plan still written); seal 0 ok, 5 unacknowledged drops."""
import argparse, glob, hashlib, json, os, re, subprocess, sys
from pathlib import Path

BAD = ("DROPPED", "REFUSED", "UNLISTED", "PARTIAL", "NOOP")
PARTIAL_RE = re.compile(r"matched no|no sink|skipped|dropped|not applied|ignored", re.I)
HEAD = ["row", "owner", "status", "reason", "problem", "types_named", "types_changed", "file", "sha12"]


def h(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()[:12]


def sha12(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
    except OSError:
        return "-"


def owner_of(path):
    n = Path(path).name
    return re.sub(r"^ROWS_|\.py$", "", n)


def problem_of(path, given=None):
    if given:
        return given
    try:
        for ln in Path(path).read_text(errors="replace").splitlines()[:40]:
            m = re.match(r"#\s*PROBLEM:\s*(.+)", ln)
            if m:
                return m.group(1).strip()
    except OSError:
        pass
    return "not stated (owner: name the open problem this row fixes)"


def collect(manifest, rows_dir):
    """-> ordered list of dict(owner, script, types, allow_top, problem, listed) over manifest + directory glob."""
    out, seen = [], set()
    for r in manifest:
        s = os.path.abspath(r["script"])
        seen.add(s)
        out.append(dict(owner=r["owner"], script=s, types=list(r.get("types", [])), allow_top=list(r.get("allow_top", [])),
                        problem=r.get("problem"), listed=True))
    if rows_dir:
        for f in sorted(glob.glob(os.path.join(rows_dir, "ROWS_*.py"))):
            s = os.path.abspath(f)
            if s not in seen:
                out.append(dict(owner=owner_of(s), script=s, types=[], allow_top=[], problem=None, listed=False))
    return out


def compose(base, out, manifest, rows_dir=None):
    """Apply the rows; return (final_plan, ledger records)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cur = json.load(open(base))
    led = []
    for i, r in enumerate(collect(manifest, rows_dir)):
        rec = dict(row=Path(r["script"]).name, owner=r["owner"], file=r["script"], sha12=sha12(r["script"]),
                   problem=problem_of(r["script"], r["problem"]), types_named=sorted(r["types"]), types_changed=[])
        led.append(rec)
        if not r["listed"]:
            rec.update(status="UNLISTED", reason="file in rows dir is not in the manifest; not applied")
            continue
        if not os.path.isfile(r["script"]):
            rec.update(status="DROPPED", reason="script missing")
            continue
        pin, pout = out / f"step{i:02d}_in.json", out / f"step{i:02d}_out.json"
        json.dump(cur, open(pin, "w"), indent=1, ensure_ascii=False)
        p = subprocess.run([sys.executable, "-I", r["script"], str(pin), str(pout)], capture_output=True, text=True)
        txt = (p.stdout + p.stderr)
        if p.returncode or not pout.is_file():
            rec.update(status="DROPPED", reason=f"script failed rc={p.returncode}: {txt.strip()[-300:]}")
            continue
        new = json.load(open(pout))
        named, allow = set(r["types"]), set(r["allow_top"]) | {"partition_types", "note"}
        a, b = cur["partition_types"], new["partition_types"]
        changed = sorted(t for t in set(a) | set(b) if h(a.get(t)) != h(b.get(t)))
        stray = [t for t in changed if t not in named]
        top = [k for k in set(cur) | set(new) if k not in allow and h(cur.get(k)) != h(new.get(k))]
        rec["types_changed"] = changed
        if stray or top:
            rec.update(status="REFUSED", reason=f"stable-key breach: unnamed types {stray[:10]} top keys {top[:10]}")
            continue
        cur = new
        lost = [ln.strip() for ln in txt.splitlines() if PARTIAL_RE.search(ln)]
        if lost:
            rec.update(status="PARTIAL", reason=f"{len(lost)} line(s) say ops were lost: {lost[0][:200]}")
        elif not changed:
            rec.update(status="NOOP", reason="applied but changed none of its named types")
        else:
            rec.update(status="APPLIED", reason="")
    return cur, led


def paths(ledger_dir, die, event):
    d = Path(ledger_dir)
    return d / f"CUT-LEDGER-{die}-{event}.tsv", d / f"CUT-ACK-{die}-{event}.tsv"


def write_ledger(path, led):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("\t".join(HEAD) + "\n")
        for r in led:
            vals = [r.get(k, "") for k in HEAD]
            f.write("\t".join(",".join(v) if isinstance(v, list) else str(v).replace("\t", " ").replace("\n", " ") for v in vals) + "\n")


def read_ledger(path):
    rows = [ln.rstrip("\n").split("\t") for ln in open(path)]
    return [dict(zip(rows[0], r)) for r in rows[1:]]


def acked(ack_path):
    s = set()
    if Path(ack_path).is_file():
        for ln in open(ack_path):
            if ln.strip() and not ln.startswith("#"):
                s.add(ln.split("\t")[0].strip())
    return s


def post_text(die, event, r, post_lane):
    return (f"DROPPED [{post_lane} -> {r['owner']}; cc COORD] {die} {event} cut: row {r['row']} (sha {r['sha12']}) is {r['status']}: "
            f"{r['reason']}. Open problem it was written for: {r['problem']}. File {r['file']}. Fix and re-hand it, or ACK the drop in "
            f"CUT-ACK-{die}-{event}.tsv (row<TAB>owner<TAB>why); seal is refused until then.")


def post_dropped(die, event, led, post_lane, post_cmd):
    n = 0
    for r in led:
        if r["status"] in BAD:
            subprocess.run([*post_cmd, post_lane, post_text(die, event, r, post_lane)], check=False)
            n += 1
    return n


def seal_check(ledger_path, ack_path, allow=()):
    """-> list of rows that block the seal (bad status, no ACK, not in allow)."""
    ok = acked(ack_path) | set(allow)
    return [r for r in read_ledger(ledger_path) if r["status"] in BAD and r["row"] not in ok and r["owner"] not in ok]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("compose", "seal"):
        s = sub.add_parser(n)
        s.add_argument("--die", required=True)
        s.add_argument("--event", required=True)
        s.add_argument("--ledger-dir", default=os.path.join(os.environ.get("COORD_DIR", os.path.expanduser("~/coord")), "autopilot"))
    c = sub.choices["compose"]
    c.add_argument("--base", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--manifest", required=True)
    c.add_argument("--rows-dir")
    c.add_argument("--post-lane", default="CUT-LEDGER-R1")
    c.add_argument("--post-cmd", default=os.path.join(os.environ.get("COORD_DIR", os.path.expanduser("~/coord")), "bin/post.sh"))
    c.add_argument("--no-post", action="store_true")
    sub.choices["seal"].add_argument("--allow-drop", action="append", default=[])
    a = ap.parse_args(argv)
    lp, ap_ = paths(a.ledger_dir, a.die, a.event)
    if a.cmd == "compose":
        plan, led = compose(a.base, a.out, json.load(open(a.manifest)), a.rows_dir)
        json.dump(plan, open(Path(a.out) / f"plan_{a.event}.json", "w"), indent=1, ensure_ascii=False)
        write_ledger(lp, led)
        bad = [r for r in led if r["status"] in BAD]
        if bad and not a.no_post:
            post_dropped(a.die, a.event, led, a.post_lane, ["bash", a.post_cmd])
        print(json.dumps({"ledger": str(lp), "rows": len(led), "applied": len(led) - len(bad), "not_applied": [(r["row"], r["status"]) for r in bad]}))
        return 1 if bad else 0
    blk = seal_check(lp, ap_, a.allow_drop)
    for r in blk:
        print(f"SEAL REFUSED: {r['row']} ({r['owner']}) {r['status']}: {r['reason']}", file=sys.stderr)
    return 5 if blk else 0


if __name__ == "__main__":
    sys.exit(main())
