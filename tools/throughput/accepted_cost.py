#!/usr/bin/env python3
"""Accepted-cost ledger (owner 2026-10-13, HANDOFF 0e): end-to-end tok/s loss of a unit over its 1.10x limit.

A structurally safe unit that misses measured / price <= 1.10 may be accepted when its end-to-end tokens-per-second
loss is <= 5 % and the design's accepted total stays <= 15 %.  The unit is never re-priced.  The loss here is NOT the
unit ratio: it comes from the committed composition of each design, with the unit's measured cycles put in place of
its price and everything else left at price:

  ROM designs (qwen_rom, s81)   the token-path DAG (results/arch/token_path_20261009/*.json).  The matched operator
                                nodes get measured - price added, the longest path is solved again, and
                                loss = 1 - T_price / T_measured.  An operator that runs N times a token costs N times
                                on the critical path and only its excess over its slack when it is overlapped.
  HBM die (r25gq)               the S2 command-processor schedule of the exact per-die program (the same one
                                tools/throughput_budget/build.py prices), re-scheduled with the op at its measured
                                ratio (--op-delta: with a fixed number of cycles added to every
                                record of the op instead).  An op the schedule overlaps costs 0.
  rate classes                  a credit / link class that moves W words a token at r words a cycle: W / r_measured
                                - W / r_price cycles, added to the token when the class is on the critical path.
  unpriced serial jobs          a job the token path does not hold at all (price 0) that the per-layer die run shows
                                serial on the critical path: --price 0 --node-delta <cycles> on the nodes it delays.
                                The row has no unit ratio (null); it is judged by its end-to-end loss alone and its
                                structural removal is named in the note.

A design with several workloads (s81: ar + mtp, r25gq: ds_ar + qwen_ar) is charged its worst workload per unit.

    python3 tools/throughput/accepted_cost.py compute s81 --unit SU.HC_POST --match 'hc_post$' --price 112.9 --measured 287
    python3 tools/throughput/accepted_cost.py propose s81 --unit ... --evidence <path> [--note ...]
    python3 tools/throughput/accepted_cost.py accept  <design> <unit>     (refused over 5 % / 15 %)
    python3 tools/throughput/accepted_cost.py annotate <design> <unit> --share-basis modelled --append "..."
    python3 tools/throughput/accepted_cost.py table | check

A row's loss is  (measured - price) x (how often the unit sits on the token's critical path).  The first factor is a
measured run; the second is MEASURED only when a per-layer die run (owner 2026-10-13 ROM throughput rule) shows the
unit's jobs serial on the layer's critical path, otherwise it is the token-path model's share.  Row field
"share_basis" says which ("measured" | "modelled"); a row without it has not been stated by its owner (table: "-").
"""
from __future__ import annotations

import argparse
import collections
import datetime
import fnmatch
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
LEDGER = ROOT / "results/arch/accepted_cost_ledger_1013.json"
TP = ROOT / "results/arch/token_path_20261009"

SCHEMA = "opentallas.accepted_cost_ledger.v1"
QUALIFY = 1.10          # measured / price limit of the throughput gate
UNIT_LIMIT = 5.0        # % end-to-end tok/s loss a single acceptance may cost
DESIGN_LIMIT = 15.0     # % total of all acceptances in one design
GRADES = ("committed_bench", "interim_log")
# superseded: the row's unit belongs to a retired design revision (e.g. the S81 hub die replaced by the DV die).  The
# row is KEPT for history with row["superseded"] = {from_status, by (superseding die rev), reason, date} and counts in
# no total, no limit and no table line.
STATUSES = ("proposed", "accepted", "superseded")

DESIGNS = {
    "qwen_rom": dict(kind="rom", workloads={"ar": "qwen_rom"}),
    "s81": dict(kind="rom", workloads={"ar": "ds_rom", "mtp": "ds_rom_mtp"}),
    "r25gq": dict(kind="hbm", workloads={"ds_ar": "ds", "qwen_ar": "qwen"}),
}


class LedgerError(Exception):
    pass


def loss_pct(base, new):
    """tok/s loss in percent when the token goes from base to new cycles (negative = a gain)"""
    return 100.0 * (1.0 - base / new)


# ---------------------------------------------------------------------------------------------------------------
# ROM designs: the token-path DAG
def solve(nodes, edges, delta=None):
    """Longest path of the token-path DAG.  nodes: [{id, cycles, start}], edges: [{src, dst, cycles}], delta: extra
    cycles per node id.  A node with no predecessor keeps its recorded start (a released input).  -> (total, end)"""
    delta = delta or {}
    by = {n["id"]: n for n in nodes}
    pred = collections.defaultdict(list)
    succ = collections.defaultdict(list)
    indeg = collections.Counter()
    for e in edges:
        pred[e["dst"]].append(e)
        succ[e["src"]].append(e["dst"])
        indeg[e["dst"]] += 1
    order = [i for i in by if not indeg[i]]
    end = {}
    k = 0
    while k < len(order):
        i = order[k]
        k += 1
        n = by[i]
        start = max((end[e["src"]] + e.get("cycles", 0) for e in pred[i]), default=n.get("start", 0.0))
        end[i] = start + n["cycles"] + delta.get(i, 0.0)
        for j in succ[i]:
            indeg[j] -= 1
            if not indeg[j]:
                order.append(j)
    if len(end) != len(by):
        raise LedgerError("token path is not a DAG")
    return max(end.values()), end


def rom_loss(path_doc, match, price, measured, tol=0.005, scale=False, node_delta=None):
    """Put `measured` in place of `price` on every node whose id matches `match` and whose own base price is `price`
    (within tol; scale=True instead multiplies every matched node by measured / price; node_delta instead adds that
    many cycles to every matched node, for a node that composes several runs of the unit).  -> dict"""
    nodes, edges = path_doc["nodes"], path_doc["edges"]
    base, _ = solve(nodes, edges)
    rx = re.compile(match)
    delta, crit, skipped = {}, 0, 0
    for n in nodes:
        if not rx.search(n["id"]):
            continue
        if node_delta is not None:
            delta[n["id"]] = node_delta
        elif scale:
            delta[n["id"]] = n["cycles"] * (measured / price - 1.0)
        elif abs(n.get("base_cycles", n["cycles"]) - price) <= tol * price:
            delta[n["id"]] = measured - price
        else:
            skipped += 1
            continue
        crit += bool(n.get("critical"))
    if not delta:
        raise LedgerError(f"no token-path node matches {match!r} at price {price}")
    naive = sum(delta.values())
    # MTP wavefront verify: every further position waits one busy period of the slowest verify stage (wave.busy
    # nodes), so that stage's share of the added cycles is paid once more per wave node
    wave = [n["id"] for n in nodes if n.get("op") == "wave.busy"]
    wave_add = 0.0
    if wave:
        stages = [g for g in path_doc.get("groups", []) if g.get("kind") in ("stage", "layer", "embed")]
        worst = max(stages, key=lambda g: g["cycles"])["id"]
        wave_add = sum(delta.get(n["id"], 0.0) for n in nodes if n.get("group") == worst)
        for i in wave:
            delta[i] = delta.get(i, 0.0) + wave_add
    new, _ = solve(nodes, edges, delta)
    return dict(model="token-path longest path", base_cycles=round(base, 1), cycles=round(new, 1),
                added_cycles=round(new - base, 1), runs_per_token=len(delta) - len(wave), critical_runs=crit,
                overlapped_runs=len(delta) - len(wave) - crit, other_price_nodes_skipped=skipped,
                naive_added_cycles=round(naive, 1), wave_positions=len(wave),
                wave_added_cycles_per_position=round(wave_add, 1), e2e_loss_pct=round(loss_pct(base, new), 3))


def rate_loss(path_doc, words_per_token, rate_price, rate_measured, critical=True):
    """A flow-controlled class: words_per_token words at rate_* words a cycle."""
    base, _ = solve(path_doc["nodes"], path_doc["edges"])
    add = words_per_token * (1.0 / rate_measured - 1.0 / rate_price) if critical else 0.0
    return dict(model="rate class on the token path", base_cycles=round(base, 1), cycles=round(base + add, 1),
                added_cycles=round(add, 1), words_per_token=words_per_token, critical=critical,
                e2e_loss_pct=round(loss_pct(base, base + add), 3))


def load_path(name):
    d = json.loads((TP / f"{name}.json").read_text())
    base, _ = solve(d["nodes"], d["edges"])
    # node cycles are stored rounded to 0.1, so a 2,700-node chain re-solves within ~1e-5 of the published total;
    # base and measured are both taken from this solver, so the rounding cancels in the loss
    if abs(base - d["totals"]["cycles"]) > 1e-4 * base:
        raise LedgerError(f"{name}: the DAG solves to {base:.1f}, the record says {d['totals']['cycles']}")
    return d


# ---------------------------------------------------------------------------------------------------------------
# HBM die: the S2 schedule of the exact per-die program
def op_match(name, op):
    """UNIT.OP of a record against --op: the exact name, or an fnmatch pattern (e.g. COLL.* for a latency every
    record of a unit pays, such as the hard_v5 COLL quadrant's +3 issue edges); 'A|B' = either alternative"""
    if "|" in op:
        return any(op_match(name, o) for o in op.split("|"))
    return name == op or (any(ch in op for ch in "*?[") and fnmatch.fnmatchcase(name, op))


def parse_fmt(specs):
    """--op-fmt [OP:]OPERAND=FMT[/FMT...] -> [(op scope or None, operand, {fmts})]; None when no spec"""
    out = []
    for x in specs or ():
        scope, _, kv = x.rpartition(":")
        k, v = kv.split("=", 1)
        out.append((scope or None, k, set(v.split("/"))))
    return out or None


def fmt_match(r, fmt):
    """--op-fmt operand filter: every term whose op scope matches the record (no scope = every record) needs the record's
    operand descriptor in one of the term's formats (e.g. SM.MATVEC:B=BF16/INT8 = the SM matvecs that run on the BF16
    tc columns -- BF16 weights, and INT8 fmt3 through the BF16 lanes -- not the FP8 / FP4 block-dot ones)"""
    if not fmt:
        return True
    if isinstance(fmt, dict):
        fmt = [(None, k, {v}) for k, v in fmt.items()]
    name = f"{r.unit}.{r.op}"
    desc = getattr(r, "desc", None) or {}
    return all(getattr(desc.get(k), "fmt", None) in vals for sc, k, vals in fmt if sc is None or op_match(name, sc))


def hbm_schedule(model, fmt=None):
    """-> (schedule_with(op or None, factor) -> token cycles, records per op); fmt: --op-fmt operand filter on the op"""
    sys.path.insert(0, str(TOOLS))
    from hgi_sim import timing as T
    if model == "ds":
        from hgi_sim import ds_native_timing as DT
        res = ROOT / "results/arch/hgi_sim_20261010/g25_proof"
        d, recs = DT.load(res / "ds_rank0_program.json")
        recs = T.rebuild_waits(recs)
        rg = {}
        for x in json.loads((res / "ds_full.json").read_text())["results"]:
            for s_ in x.get("row_gather") or []:
                rg[x["layer"]] = s_
        DT.apply_dyn_counts(recs, rg)
        cf, pos = DT.NativeCost(d["ops"], recs, row_gather=rg), DT.POS
    else:
        from hgi_sim import qwen_compiler as QC
        cfg = json.loads((ROOT / "compiler/models/qwen3-8b/config.json").read_text())
        recs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg["num_hidden_layers"])
        cf, pos = T.cost, 8191
    count = collections.Counter(f"{r.unit}.{r.op}" for r in recs if fmt_match(r, fmt))

    def run(op=None, f=1.0, delta=0.0, extra=()):
        """extra: further (op, fmt, fixed cycles) terms applied in the same schedule (a combined row of several fixed
        latencies, e.g. results/token_pass/toksched_1025/hbm_price.py)"""
        def g(r, dyn, L):
            c = cf(r, dyn, L)
            name = f"{r.unit}.{r.op}"
            hit = op is not None and op_match(name, op) and fmt_match(r, fmt)
            x = c[0] * f + delta if hit else c[0]
            x += sum(d for o, fm, d in extra if op_match(name, o) and fmt_match(r, fm))
            return x, c[1], c[2]
        return T.schedule(recs, pos, "S2", cost_fn=g)["total_cycles"]
    return run, count


def hbm_loss(run, count, op, ratio, base=None, delta=None):
    """delta: a FIXED number of cycles added to every record of the op (a latency the op pays once a record whatever
    its length, e.g. the VM8 x-load start-to-dispatch edges before every SM.MATVEC); the op's own cycles stay at price"""
    n_rec = sum(v for k, v in count.items() if op_match(k, op))
    if not n_rec:
        return None                 # the workload's program never issues this op
    base = run() if base is None else base
    if delta is not None:
        new = run(op, 1.0, delta)
        return dict(model="S2 schedule, fixed cycles added to every record of the op", base_cycles=round(base, 1),
                    cycles=round(new, 1), added_cycles=round(new - base, 1), program_records=n_rec,
                    added_cycles_per_record=delta, e2e_loss_pct=round(loss_pct(base, new), 3))
    new = run(op, ratio)
    return dict(model="S2 schedule, op re-scheduled at its measured ratio", base_cycles=round(base, 1),
                cycles=round(new, 1), added_cycles=round(new - base, 1), program_records=n_rec,
                e2e_loss_pct=round(loss_pct(base, new), 3))


# ---------------------------------------------------------------------------------------------------------------
def compute(design, *, match=None, op=None, price=None, measured=None, ratio=None, scale=False,
            words_per_token=None, critical=True, workloads=None, node_delta=None, op_delta=None, op_fmt=None):
    """-> {workload: composition result} for one unit of one design"""
    spec = DESIGNS[design]
    out = {}
    for wl, name in spec["workloads"].items():
        if workloads and wl not in workloads:
            continue
        if spec["kind"] == "rom":
            doc = load_path(name)
            if words_per_token is not None:
                out[wl] = rate_loss(doc, words_per_token, price, measured, critical)
                continue
            try:
                out[wl] = rom_loss(doc, match, price, measured, scale=scale, node_delta=node_delta)
            except LedgerError:
                if len(spec["workloads"]) == 1 or workloads:
                    raise
        else:
            run, count = hbm_schedule(name, op_fmt)
            r = hbm_loss(run, count, op, ratio if ratio is not None else (measured / price if op_delta is None else None),
                         delta=op_delta)      # --op-delta: a fixed latency, --price may be 0 (unpriced transport)
            if r:
                out[wl] = r
    if not out:
        raise LedgerError(f"{design}: no workload runs this unit")
    return out


def unit_ratio(price, measured, rate=False):
    if not price:
        return None                 # an unpriced serial job: there is no price to hold a ratio against
    return round((price / measured) if rate else (measured / price), 4)


def make_row(design, unit, price, measured, per_workload, evidence, grade, note="", rate=False, date=None,
             unit_of_measure="cycles", group=None):
    """group: rows of one design that are alternative measurements of the SAME composition op share a group; the
    proposed total counts a group once, at its worst row (an accepted row always counts in full)."""
    if grade not in GRADES:
        raise LedgerError(f"grade must be one of {GRADES}")
    loss = max(v["e2e_loss_pct"] for v in per_workload.values())
    return dict(design=design, unit=unit, group=group or unit, measured=measured, price=price, unit_of_measure=unit_of_measure,
                unit_ratio=unit_ratio(price, measured, rate), e2e_loss_pct=loss,
                binding_workload=max(per_workload, key=lambda k: per_workload[k]["e2e_loss_pct"]),
                per_workload=per_workload, within_unit_limit=loss <= UNIT_LIMIT, evidence=evidence,
                evidence_grade=grade, date=date or datetime.date.today().isoformat(), status="proposed", note=note)


# ---------------------------------------------------------------------------------------------------------------
# the ledger
def empty_ledger():
    return dict(schema=SCHEMA,
                rule=("owner 2026-10-13 (HANDOFF 0e): a structurally safe unit over 1.10x may be accepted when its "
                      "measured end-to-end tok/s loss is <= 5 % and the design's accepted total is <= 15 %; never "
                      "re-priced; the clock stays 833 ps"),
                qualify_ratio=QUALIFY, unit_limit_pct=UNIT_LIMIT, design_limit_pct=DESIGN_LIMIT,
                loss_basis="composition model with the unit at its measured cycles (tools/throughput/accepted_cost.py)",
                rows=[], totals={})


def load_ledger(path=LEDGER):
    return json.loads(Path(path).read_text()) if Path(path).exists() else empty_ledger()


def totals(led):
    t = {}
    for d in DESIGNS:
        rows = [r for r in led["rows"] if r["design"] == d]
        acc = sum(r["e2e_loss_pct"] for r in rows if r["status"] == "accepted")
        grp = collections.defaultdict(float)
        for r in rows:
            if r["status"] == "proposed":
                grp[r.get("group", r["unit"])] = max(grp[r.get("group", r["unit"])], r["e2e_loss_pct"], 0.0)
        pro = sum(grp.values())
        t[d] = dict(accepted_pct=round(acc, 3), proposed_pct=round(pro, 3), accepted_plus_proposed_pct=round(acc + pro, 3),
                    limit_pct=DESIGN_LIMIT, accepted_rows=sum(r["status"] == "accepted" for r in rows),
                    proposed_rows=sum(r["status"] == "proposed" for r in rows),
                    headroom_pct=round(DESIGN_LIMIT - acc, 3),
                    owner_exception_rows=sum(bool(r.get("owner_exception")) for r in rows if r["status"] == "accepted"),
                    over_limit_by_owner_exception=acc > DESIGN_LIMIT,
                    superseded_rows=sum(r["status"] == "superseded" for r in rows),
                    superseded_pct_not_counted=round(sum(r["e2e_loss_pct"] for r in rows
                                                         if r["status"] == "superseded"), 3))
    return t


def save_ledger(led, path=LEDGER):
    led["rows"].sort(key=lambda r: (list(DESIGNS).index(r["design"]), r["unit"]))
    led["totals"] = totals(led)
    Path(path).write_text(json.dumps(led, indent=1) + "\n")


def find(led, design, unit):
    for r in led["rows"]:
        if r["design"] == design and r["unit"] == unit:
            return r
    return None


def propose(led, row, supersede_accepted=""):
    """supersede_accepted: the decision (owner, date) that replaces an accepted row with a new measurement."""
    old = find(led, row["design"], row["unit"])
    if old and old["status"] == "superseded":
        raise LedgerError(f"{row['design']} {row['unit']} is superseded ({old['superseded']['by']}); a unit of the "
                          f"current design needs its own row name")
    if old and old["status"] == "accepted" and supersede_accepted:
        row["supersedes"] = {k: old.get(k) for k in ("measured", "price", "unit_ratio", "e2e_loss_pct", "status",
                                                        "accepted_date", "acceptance_note")}
        row["supersedes"]["by"] = supersede_accepted
    elif old and old["status"] == "accepted":
        raise LedgerError(f"{row['design']} {row['unit']} is already accepted; a new measurement needs a new decision")
    if old:
        led["rows"].remove(old)
    led["rows"].append(row)
    return row


def refusal(led, row, root=ROOT, waive_limits=False):
    """Why this row may not be marked accepted (None = it may). waive_limits (an OWNER exception) skips only the
    5 %/unit and 15 %/design limits; the qualify and committed-bench rules still apply."""
    if row["unit_ratio"] is not None and row["unit_ratio"] <= QUALIFY:
        return f"unit ratio {row['unit_ratio']} is within {QUALIFY}: it qualifies, no acceptance is needed"
    if row["e2e_loss_pct"] > UNIT_LIMIT and not waive_limits:
        return f"end-to-end loss {row['e2e_loss_pct']} % is over the {UNIT_LIMIT} % unit limit"
    acc = sum(r["e2e_loss_pct"] for r in led["rows"]
              if r["design"] == row["design"] and r["status"] == "accepted" and r is not row)
    if acc + max(row["e2e_loss_pct"], 0.0) > DESIGN_LIMIT and not waive_limits:
        return (f"design total would be {acc + row['e2e_loss_pct']:.3f} %, over the {DESIGN_LIMIT} % limit "
                f"({acc:.3f} % already accepted)")
    if row.get("evidence_grade") != "committed_bench":
        return "the measurement is not a committed bench record (measure, never estimate)"
    ev = str(row.get("evidence") or "").split(" ")[0]
    if not ev or not (Path(root) / ev).exists():
        return f"evidence path {ev!r} is not in the repository"
    return None


def accept(led, design, unit, root=ROOT, note="", owner_exception=""):
    """Mark a row accepted (the refusal rules apply). `note` records the decision (who, when, on what basis); an
    already-accepted row only gets the note added, its accepted_date stays.
    owner_exception: an explicit OWNER decision that accepts the row above the 5 %/unit or 15 %/design limit. It
    waives only those two limits (a committed bench record is still required) and is written on the row; `check`
    then reports the over-limit total as an owner exception instead of a violation."""
    row = find(led, design, unit)
    if row is None:
        raise LedgerError(f"no row {design} {unit}")
    if row["status"] != "accepted" or owner_exception:
        why = refusal(led, row, root, waive_limits=bool(owner_exception))
        if why:
            raise LedgerError(f"REFUSED {design} {unit}: {why}")
        if row["status"] != "accepted":
            row["status"] = "accepted"
            row["accepted_date"] = datetime.date.today().isoformat()
    if owner_exception:
        row["owner_exception"] = owner_exception
    if note:
        row["acceptance_note"] = note
    return row


def supersede(led, design, pattern, by, reason, date=None):
    """Mark every proposed / accepted row of `design` whose group (or unit) matches regex `pattern` superseded: the
    unit belongs to a retired design revision.  `by` names the superseding die revision, `reason` the decision.
    Rows are never deleted; their numbers stay; they leave every total.  -> the rows marked."""
    if not by or not reason:
        raise LedgerError("supersede needs the superseding die revision (by) and a reason")
    rx = re.compile(pattern)
    hits = [r for r in led["rows"] if r["design"] == design and r["status"] in ("proposed", "accepted")
            and (rx.search(r.get("group") or r["unit"]) or rx.search(r["unit"]))]
    if not hits:
        raise LedgerError(f"no proposed / accepted {design} row matches {pattern!r}")
    for r in hits:
        r["superseded"] = dict(from_status=r["status"], by=by, reason=reason,
                               date=date or datetime.date.today().isoformat())
        r["status"] = "superseded"
    return hits


SHARE_BASES = ("measured", "modelled")


def annotate(led, design, unit, share_basis=None, append=""):
    """Qualify a row without touching its numbers or its status: who measured the token share, and a note."""
    row = find(led, design, unit)
    if row is None:
        hits = [r for r in led["rows"] if r["design"] == design and r.get("group") == unit]
        if len(hits) != 1:
            raise LedgerError(f"no row {design} {unit}")
        row = hits[0]
    if share_basis:
        if share_basis not in SHARE_BASES:
            raise LedgerError(f"share basis {share_basis!r} is not one of {SHARE_BASES}")
        row["share_basis"] = share_basis
    if append and append not in row.get("note", ""):
        row["note"] = (row.get("note", "").rstrip() + "  " + append).strip()
    return row


def check(led, root=ROOT):
    """Violations of a ledger as written (hand edits included)."""
    bad = []
    for d in DESIGNS:
        acc = [r for r in led["rows"] if r["design"] == d and r["status"] == "accepted"]
        tot = sum(r["e2e_loss_pct"] for r in acc)
        if tot > DESIGN_LIMIT and not any(r.get("owner_exception") for r in acc):
            bad.append(f"{d}: accepted total {tot:.3f} % over {DESIGN_LIMIT} %")
        for r in acc:
            if r["e2e_loss_pct"] > UNIT_LIMIT and not r.get("owner_exception"):
                bad.append(f"{d} {r['unit']}: accepted at {r['e2e_loss_pct']} % over {UNIT_LIMIT} %")
            if r.get("evidence_grade") != "committed_bench":
                bad.append(f"{d} {r['unit']}: accepted without a committed bench record")
    for r in led["rows"]:
        if r["design"] not in DESIGNS:
            bad.append(f"unknown design {r['design']}")
        if r.get("share_basis", "modelled") not in SHARE_BASES:   # absent = not stated yet
            bad.append(f"{r['design']} {r['unit']}: share basis {r.get('share_basis')!r}")
        if r["status"] not in STATUSES:
            bad.append(f"{r['design']} {r['unit']}: status {r['status']!r}")
        if r["status"] == "superseded" and not all((r.get("superseded") or {}).get(k) for k in ("by", "reason", "from_status")):
            bad.append(f"{r['design']} {r['unit']}: superseded without by / reason / from_status")
        if r.get("unit_ratio") is None and r.get("price"):
            bad.append(f"{r['design']} {r['unit']}: a priced row without a unit ratio")
        if abs(r["e2e_loss_pct"] - max(v["e2e_loss_pct"] for v in r["per_workload"].values())) > 1e-6:
            bad.append(f"{r['design']} {r['unit']}: e2e loss is not its worst workload")
    return bad


def table(led):
    out = ["| design | unit | measured | price | unit ratio | e2e loss % | binding workload | within 5 % | grade | token share | status |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in led["rows"]:
        if r["status"] == "superseded":          # retired design revision: kept in the JSON, not rendered or counted
            continue
        out.append(f"| {r['design']} | {r['unit']} | {r['measured']} | {r['price'] or 'unpriced'} | "
                   f"{r['unit_ratio'] if r['unit_ratio'] is not None else '-'} | "
                   f"{r['e2e_loss_pct']:.3f} | {r['binding_workload']} | {'yes' if r['within_unit_limit'] else 'NO'} | "
                   f"{r['evidence_grade']} | { {'modelled': 'MODELLED', 'measured': 'measured'}.get(r.get('share_basis'), '-') } | "
                   f"{r['status']}{' (owner exception)' if r.get('owner_exception') else ''} |")
    out.append("")
    out.append("token share MODELLED = the unit ratio is a measured run, the number of critical runs a token is the "
               "token-path model's: not a fully measured end-to-end loss until a per-layer die run shows the share; "
               "- = not stated by the row's owner")
    for d, t in totals(led).items():
        out.append(f"{d}: accepted {t['accepted_pct']} % + proposed {t['proposed_pct']} % = "
                   f"{t['accepted_plus_proposed_pct']} % of {DESIGN_LIMIT} %"
                   + (" -- OVER THE LIMIT BY OWNER EXCEPTION" if t.get("over_limit_by_owner_exception") else "")
                   + (f" ({t['superseded_rows']} superseded rows, {t['superseded_pct_not_counted']} %, not counted)"
                      if t.get("superseded_rows") else ""))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", default=str(LEDGER))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("compute", "propose"):
        p = sub.add_parser(name)
        p.add_argument("design", choices=DESIGNS)
        p.add_argument("--unit", required=True)
        p.add_argument("--match", help="ROM: regex on the token-path node id")
        p.add_argument("--op", help="HBM: UNIT.OP of the S2 schedule")
        p.add_argument("--price", type=float, required=True)
        p.add_argument("--measured", type=float, required=True)
        p.add_argument("--scale", action="store_true", help="ROM: scale every matched node by measured / price")
        p.add_argument("--node-delta", type=float, help="ROM: cycles added to every matched node")
        p.add_argument("--op-delta", type=float, help="HBM: cycles added to every record of --op (a fixed latency per "
                                                      "record; --price / --measured then describe the unit itself)")
        p.add_argument("--op-fmt", action="append", default=[], metavar="[OP:]OPERAND=FMT[/FMT]",
                       help="HBM: only records of --op whose operand descriptor has one of these formats (e.g. B=BF16; "
                            "SM.MATVEC:B=BF16/INT8 filters only the SM.MATVEC records of an 'SM.MATVEC|ATT.*' --op)")
        p.add_argument("--group", help="rows that measure the same composition op share a group")
        p.add_argument("--words-per-token", type=float, help="rate class: price / measured are words a cycle")
        p.add_argument("--off-critical", action="store_true")
        p.add_argument("--workload", action="append")
        p.add_argument("--evidence", default="")
        p.add_argument("--grade", choices=GRADES, default="committed_bench")
        p.add_argument("--note", default="")
    p = sub.add_parser("accept")
    p.add_argument("design", choices=DESIGNS)
    p.add_argument("unit")
    p.add_argument("--note", default="", help="the acceptance decision: who, when, basis")
    p.add_argument("--owner-exception", default="", help="OWNER decision accepting above the unit/design limit")
    p = sub.add_parser("annotate")
    p.add_argument("design", choices=DESIGNS)
    p.add_argument("unit", help="the row's unit string, or its group when one row holds it")
    p.add_argument("--share-basis", choices=SHARE_BASES)
    p.add_argument("--append", default="", help="text appended to the row note (once)")
    p = sub.add_parser("supersede", help="mark rows of a retired design revision superseded (never deleted)")
    p.add_argument("design", choices=DESIGNS)
    p.add_argument("pattern", help="regex on the row group (or unit)")
    p.add_argument("--by", required=True, help="the superseding die revision")
    p.add_argument("--reason", required=True)
    sub.add_parser("table")
    sub.add_parser("check")
    a = ap.parse_args(argv)
    try:
        led = load_ledger(a.ledger)
        if a.cmd in ("compute", "propose"):
            rate = a.words_per_token is not None
            per = compute(a.design, match=a.match, op=a.op, price=a.price, measured=a.measured, scale=a.scale,
                          words_per_token=a.words_per_token, critical=not a.off_critical, workloads=a.workload,
                          node_delta=a.node_delta, op_delta=a.op_delta,
                          op_fmt=parse_fmt(a.op_fmt))
            row = make_row(a.design, a.unit, a.price, a.measured, per, a.evidence, a.grade, a.note, rate,
                           unit_of_measure="words/cycle" if rate else "cycles", group=a.group)
            if a.cmd == "propose":
                propose(led, row)
                save_ledger(led, a.ledger)
            print(json.dumps(row, indent=1))
        elif a.cmd == "accept":
            accept(led, a.design, a.unit, note=a.note, owner_exception=a.owner_exception)
            save_ledger(led, a.ledger)
            print(f"ACCEPTED {a.design} {a.unit}")
        elif a.cmd == "annotate":
            row = annotate(led, a.design, a.unit, a.share_basis, a.append)
            save_ledger(led, a.ledger)
            print(f"ANNOTATED {row['design']} {row['unit']}: share basis {row.get('share_basis', 'not stated')}")
        elif a.cmd == "supersede":
            rows = supersede(led, a.design, a.pattern, a.by, a.reason)
            save_ledger(led, a.ledger)
            print("\n".join(f"SUPERSEDED {r['design']} {r.get('group') or r['unit']} (was {r['superseded']['from_status']})"
                            for r in rows))
        elif a.cmd == "table":
            print(table(led))
        else:
            bad = check(led)
            print("\n".join(bad) if bad else "ledger OK")
            return 1 if bad else 0
    except LedgerError as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
