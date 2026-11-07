#!/usr/bin/env python3
"""HEAD plan event l48uo (DH81-EVENT, COORD 11-07 10:35), on l48un. No K, strap, pin, station or outline moves.

 1. sink_bins_file -> plan_of_record/l48uo/assets/sink_bins_N.json, stored PLAIN.  l48un named .json but main holds .json.gz,
    so taps + reset_tree failed on a clean checkout and only the counter's overlay gunzip hid it.  core_pins/ and
    native_domains/ (plan-relative, same fault, read by reset_tree and hd_serdes taps) are stored plain beside it, same bytes.
 2. clock.landing_network.count_aligned_cycles[port] = sidecar count_aligned.ports[port].sched_lat, the value the RTL and
    bind already use (clock_landings.py row added_cycles; bind.py LANE_LANDING_LATENCY).  latency.lanes is then regenerated
    with gen.latency_table, so gen.py latency and reform_rebaseline see the same cycles as the hardware.
    The sidecar stays byte-same: its stale ports[].added_cycles rows are not read for count-aligned crossings.
 3. the hd_serdes warm-reset sequencer: head_serdes_locksafe_event (hd_serdes block, wrapper, 12 die ports) with no change.

usage: head_l48uo_event.py L48UI_DIR OUT_DIR --tools-root ROOT   (L48UI_DIR = the tracked dir with .gz files; OUT_DIR below ROOT)
"""
import argparse
import gzip
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

EVENT = "l48uo"
BASE_PLAN = "source_plan_l48un.json"
SEQ_EVENT = "l48uo_seq"
PLAIN_DIRS = ("assets/", "core_pins/", "native_domains/")   # plan-relative tables tools read by their plain name


def sha(b):
    return hashlib.sha256(b).hexdigest()


def repoint_sink_bins(plan, rel_dir):
    """every clock.sink_bins_file -> rel_dir/assets/<same name>; -> {type: new path}"""
    out = {}
    for tn, t in plan["partition_types"].items():
        f = t.get("clock", {}).get("sink_bins_file")
        if f:
            t["clock"]["sink_bins_file"] = out[tn] = f"{rel_dir}/assets/{Path(f).name}"
    return out


def carry_sched_lat(plan, sidecar):
    """plan count_aligned_cycles <- sidecar sched_lat; only rises are accepted; -> [dict(port, lane, old, new)]"""
    cac = plan["clock"]["landing_network"]["count_aligned_cycles"]
    ports = sidecar["count_aligned"]["ports"]
    if set(cac) != set(ports):
        raise ValueError("plan count_aligned_cycles and sidecar count_aligned.ports name different crossings")
    lane = {p: ln["id"] for ln in plan["lanes"] for p in ln["ports"]}
    rows = []
    for p in sorted(cac):
        old, new = int(cac[p]), int(ports[p]["sched_lat"])
        if new < old:
            raise ValueError(f"{p}: sidecar sched_lat {new} below plan {old}")
        if new != old:
            cac[p] = new
            rows.append(dict(port=p, lane=lane[p], old=old, new=new))
    return rows


def refresh_latency(plan, gen, schema):
    """same table as gen.py latency --inplace; -> {lane: (old cycles, new cycles)} for lanes that moved"""
    old = {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()}
    tab = json.loads(json.dumps(gen.latency_table(schema.Plan(json.loads(json.dumps(plan))))))
    for row in tab.values():
        row.pop("param", None)      # this plan's stored table has no SV parameter names; no other key moves
    plan["latency"] = {"lanes": tab}
    return {k: (old.get(k), v["cycles"]) for k, v in sorted(tab.items()) if old.get(k) != v["cycles"]}


def plain_tree(src, dst):
    """tracked plan dir -> plain files, *.gz gunzipped"""
    for f in sorted(src.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(src).as_posix()
        data = f.read_bytes()
        if rel.endswith(".gz"):
            rel, data = rel[:-3], gzip.decompress(data)
        t = dst / rel
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(data)


def pack(src, out):
    """out plain -> stored form: PLAIN_DIRS plain; a file stored plain in src stays plain; a file unchanged from src keeps
    its exact .gz bytes (same git blob); anything else gzip -n."""
    n = dict(reused=0, new_gz=[], plain=[])
    for f in sorted(out.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(out).as_posix()
        if rel.startswith(PLAIN_DIRS) or not ((src / (rel + ".gz")).is_file() or rel == "source_plan.json"):
            n["plain"].append(rel)
            continue
        data, old = f.read_bytes(), src / (rel + ".gz")
        if old.is_file() and gzip.decompress(old.read_bytes()) == data:
            shutil.copyfile(old, f.with_name(f.name + ".gz"))
            n["reused"] += 1
        else:
            f.with_name(f.name + ".gz").write_bytes(gzip.compress(data, 9, mtime=0))
            n["new_gz"].append(rel)
        f.unlink()
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--tools-root", type=Path, required=True)
    a = ap.parse_args(argv)
    root, src, out = a.tools_root.resolve(), a.src.resolve(), a.out.resolve()
    sys.path[:0] = [str(root / "tools/die_plan"), str(root / "tools/s81_head")]
    import gen
    import schema
    import head_serdes_locksafe_event as E
    if out.exists():
        raise SystemExit(f"{out} exists: an event never overwrites")
    rel_dir = out.relative_to(root).as_posix()
    with tempfile.TemporaryDirectory(dir=out.parent) as td:
        pre = Path(td) / "pre"
        plain_tree(src, pre)
        base_bytes = (pre / BASE_PLAN).read_bytes()
        plan = json.loads(base_bytes)
        side_bytes = (pre / "source_sidecar.json").read_bytes()
        side = json.loads(side_bytes)
        (pre / BASE_PLAN).unlink()
        bins = repoint_sink_bins(plan, rel_dir)
        rows = carry_sched_lat(plan, side)
        moved = refresh_latency(plan, gen, schema)
        plan["note"] = plan.get("note", "") + (" | l48uo (DH81-EVENT 11-07): plain sink_bins assets; count_aligned_cycles = sidecar "
                                               "sched_lat (15 crossings, 13 lanes); hd_serdes warm-reset sequencer")
        (pre / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
        rec = json.loads((pre / "wave_prepare.json").read_text())
        rec["prepared_plan_sha256"] = sha((pre / "source_plan.json").read_bytes())
        (pre / "wave_prepare.json").write_text(json.dumps(rec, indent=1) + "\n")
        E.main([str(pre), str(out), "--republish", str(root), "--event", SEQ_EVENT])
    final = json.loads((out / "source_plan.json").read_text())
    if {k: v["cycles"] for k, v in final["latency"]["lanes"].items()} != {k: v["cycles"] for k, v in plan["latency"]["lanes"].items()}:
        raise SystemExit("the sequencer delta moved a lane")
    for f in out.glob("republish_*.log"):
        f.unlink()
    plan_sha = sha((out / "source_plan.json").read_bytes())
    record = dict(event=EVENT, tool="tools/s81_head/head_l48uo_event.py", base_plan=BASE_PLAN, base_plan_sha256=sha(base_bytes),
                  plan_sha256=plan_sha, sidecar_sha256=sha(side_bytes), sidecar_changed=False,
                  sink_bins_file=bins, ports_sched_lat=rows, lanes_moved={k: list(v) for k, v in moved.items()},
                  lane_cycles_added=sum(r["new"] - r["old"] for r in rows), sequencer=SEQ_EVENT, k_changed=False)
    w = json.loads((out / "wave_prepare.json").read_text())
    w[EVENT] = record
    (out / "wave_prepare.json").write_text(json.dumps(w, indent=1) + "\n")
    (out / "l48uo_event.json").write_text(json.dumps(record, indent=1) + "\n")
    sums = out / "SHA256SUMS"
    sums.write_text("".join(f"{sha((out / n).read_bytes())}  {n}\n" for n in
                            (ln.partition("  ")[2] for ln in sums.read_text().splitlines()) if (out / n).is_file()))
    print(json.dumps(dict(plan_sha256=plan_sha, ports=len(rows), lanes=len(moved), pack=pack(src, out)), indent=1))


if __name__ == "__main__":
    main()
