#!/usr/bin/env python3
"""Compose a new HEAD plan receipt for an unchanged, qualified native reset contract."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys


def json_load(path):
    return json.loads(path.read_text())


def hexdigest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def serdes_parts(plan):
    return {part["name"]: part for part in plan["partitions"] if part["type"] == "hd_serdes"}


# P-RESET-RECEIPT guard change (HEAD-PROBE-R3 11-27, review-hardened): a CHANGED hd_serdes partition (reset_entry_phase, id_straps, ...) used to be
# refused outright.  It is accepted only with --new-receipt: a receipt produced on the NEW plan digest whose proof.entry_phase_evidence names an evidence file
# (inside receipt files, hash-verified) that (1) is for the new digest and the shipped ot_dp_rrelay_ph cell hash, (2) carries verdict PASS with the pass marker
# present in the hash-verified bench log, and (3) lists a (partition, field, old, new) row for EVERY leaf that differs between the two plans: coverage compares
# VALUES, not key names.  Anything else, and any malformed receipt, is a ValueError (fail closed).
def _flat(prefix, v, out):
    if isinstance(v, dict) and v:
        for k in sorted(v, key=str):
            _flat(prefix + "\x1f" + str(k) if prefix else str(k), v[k], out)
    else:
        out[prefix] = json.dumps(v, sort_keys=True)


def part_leaves(old_parts, new_parts):
    """[(partition, key path 'a.b', old json or None, new json or None)] for every differing leaf (added, removed, changed; {} is a leaf)"""
    out = []
    for name in sorted(set(old_parts) | set(new_parts)):
        a, b = {}, {}
        if name in old_parts:
            _flat("", old_parts[name], a)
        if name in new_parts:
            _flat("", new_parts[name], b)
        for k in sorted(set(a) | set(b)):
            if a.get(k) != b.get(k):
                out.append((name, k.replace("\x1f", "."), a.get(k), b.get(k)))
    return out


def part_diff(old_parts, new_parts):
    return ["partitions[%s].%s" % (n, k) for n, k, _a, _b in part_leaves(old_parts, new_parts)]


def _sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_changed_binding(old_parts, new_parts, new_receipt, new_digest, receipt_dir=None, cell_sha=None):
    """-> sorted diff paths when the receipt's hash-verified entry-phase evidence covers every differing leaf by value; ValueError otherwise"""
    if new_receipt is None:
        if part_leaves(old_parts, new_parts):
            raise ValueError("HEAD native reset instance bindings changed")
        return []
    if not isinstance(new_receipt, dict) or not isinstance(new_receipt.get("proof"), dict) or not isinstance(new_receipt.get("files"), dict):
        raise ValueError("HEAD native reset instance bindings changed: receipt is malformed")
    leaves = part_leaves(old_parts, new_parts)
    if not leaves:
        return []
    if new_receipt.get("plan_sha256") != new_digest:
        raise ValueError("HEAD native reset instance bindings changed: receipt is not for the new plan digest")
    name = new_receipt["proof"].get("entry_phase_evidence")
    if not isinstance(name, str) or not name or name not in new_receipt["files"]:
        raise ValueError("HEAD native reset instance bindings changed: receipt names no entry-phase evidence file in files")
    if receipt_dir is None or cell_sha is None:
        raise ValueError("HEAD native reset instance bindings changed: evidence cannot be verified (no receipt dir / cell hash)")
    root = Path(receipt_dir)
    ev_path = root / name
    if not ev_path.is_file() or _sha_file(ev_path) != new_receipt["files"][name]:
        raise ValueError("HEAD native reset instance bindings changed: evidence file missing or hash differs")
    try:
        ev = json.loads(ev_path.read_text())
    except ValueError as e:
        raise ValueError("HEAD native reset instance bindings changed: evidence is not JSON") from e
    if not isinstance(ev, dict) or ev.get("schema") != "opentallas.entry_phase_evidence.v1":
        raise ValueError("HEAD native reset instance bindings changed: evidence schema")
    if ev.get("plan_digest") != new_digest or ev.get("cell_sha256") != cell_sha:
        raise ValueError("HEAD native reset instance bindings changed: evidence is for another plan or another cell")
    if ev.get("verdict") != "PASS" or not isinstance(ev.get("artifacts"), dict) or not isinstance(ev.get("log"), str):
        raise ValueError("HEAD native reset instance bindings changed: evidence verdict is not PASS")
    for fn, h in ev["artifacts"].items():
        f = root / fn
        if fn not in new_receipt["files"] or new_receipt["files"][fn] != h or not f.is_file() or _sha_file(f) != h:
            raise ValueError("HEAD native reset instance bindings changed: evidence artifact %s missing or hash differs" % fn)
    log = root / ev["log"]
    marker = ev.get("pass_marker")
    if ev["log"] not in ev["artifacts"] or not isinstance(marker, str) or not marker or marker not in log.read_text(errors="replace"):
        raise ValueError("HEAD native reset instance bindings changed: bench log lacks the pass marker")
    rows = ev.get("rows")
    if not isinstance(rows, list):
        raise ValueError("HEAD native reset instance bindings changed: evidence rows")
    have = {(r.get("partition"), r.get("field"), json.dumps(r.get("old"), sort_keys=True), json.dumps(r.get("new"), sort_keys=True))
            for r in rows if isinstance(r, dict)}
    missing = []
    for n, k, a, b in leaves:
        # the plan value of a leaf is json text; the row stores the plain value, so compare after normalising both through json
        ra = json.dumps(json.loads(a), sort_keys=True) if a is not None else json.dumps(None)
        rb = json.dumps(json.loads(b), sort_keys=True) if b is not None else json.dumps(None)
        if (n, k, ra, rb) not in have:
            missing.append("partitions[%s].%s %s->%s" % (n, k, ra, rb))
    if missing:
        raise ValueError("HEAD native reset instance bindings changed: evidence does not cover " + ", ".join(missing[:6]))
    return ["partitions[%s].%s" % (n, k) for n, k, _a, _b in leaves]


def rerun_bench_evidence(old_plan, new_plan, tools):
    """re-run entry_phase_bench from the two plans (iverilog + the real ot_dp_rrelay_ph) into a scratch dir -> the evidence dict it produces.
    The receipt's own evidence is never trusted on its own: its rows / cases / verdict must equal this re-run."""
    import importlib.util
    import tempfile
    spec = importlib.util.spec_from_file_location("entry_phase_bench", Path(__file__).resolve().parent / "entry_phase_bench.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory() as d:
        rc = mod.main(old_plan, new_plan, d, tools)
        ev = json.loads((Path(d) / "entry_phase_evidence.json").read_text())
    if rc != 0 or ev.get("verdict") != "PASS":
        raise ValueError("HEAD native reset instance bindings changed: the re-run entry-phase bench does not pass")
    return ev


def check_rerun(receipt_ev, rerun_ev):
    """the receipt evidence must equal the guard's own bench re-run on rows, simulated cases and cell hash (log text and paths are not compared)"""
    def case_key(c):
        return (c.get("partition"), c.get("version"), c.get("h"), c.get("strap"), c.get("release_delta"), c.get("expect_cycles"), c.get("sim_cycles"))
    same = (receipt_ev.get("rows") == rerun_ev.get("rows")
            and sorted(map(case_key, receipt_ev.get("cases") or [])) == sorted(map(case_key, rerun_ev.get("cases") or []))
            and receipt_ev.get("cell_sha256") == rerun_ev.get("cell_sha256") and receipt_ev.get("plan_digest") == rerun_ev.get("plan_digest"))
    if not same or not rerun_ev.get("cases"):
        raise ValueError("HEAD native reset instance bindings changed: receipt evidence differs from the guard's own bench re-run")


def check_release_consistency(old_wf, new_wf, old_parts, new_parts, release_delta):
    """CONSUMER CHECK (reset_tree.wf_plan): for every hd_serdes partition whose reset_entry_phase changed, the published wavefront release must move by exactly
    release_delta(new h) - release_delta(old h); every other partition's release and entry_stages must be unchanged.  -> {partition: [old, new]} of the moved
    releases; ValueError otherwise.  (HEAD-PROBE-R3 11-27: lk_WN1 76 -> 77; the lane table and LATCHECK do not observe reset release, wf_plan does.)"""
    op, np_ = old_wf.get("parts") or {}, new_wf.get("parts") or {}
    if not op or not np_:
        raise ValueError("release consistency: wf_plan has no parts")
    for name in set(old_parts) | set(new_parts):
        if name not in op or name not in np_:
            raise ValueError("release consistency: hd_serdes partition %s is not in wf_plan parts" % name)
    moved = {}
    for name in sorted(set(op) | set(np_)):
        a, b = op.get(name), np_.get(name)
        if a is None or b is None:
            raise ValueError("release consistency: partition %s missing on one side" % name)
        want = 0
        if name in old_parts and name in new_parts:
            want = release_delta(int(new_parts[name].get("reset_entry_phase", 0))) - release_delta(int(old_parts[name].get("reset_entry_phase", 0)))
        if b["release"] - a["release"] != want:
            raise ValueError("release consistency: %s release moved %+d, release_delta says %+d" % (name, b["release"] - a["release"], want))
        if want:
            moved[name] = [a["release"], b["release"]]
        elif a.get("entry_stages") != b.get("entry_stages"):
            raise ValueError("release consistency: %s entry_stages changed without a release change" % name)
    return moved


def fwd_only_delta(a, b):
    """FWDTAP-1 serdes requal: the hd_serdes type may differ ONLY by the reach_rules fix_fwd form on forwarded clock
    exports (pins[i].source_clock_port of an out clock pin fclk_out_*, and landing_contract.forwarded_clock_only_inputs
    -> true).  u_phy content, hard cores and every other key must be identical; qualify() then re-checks the receipt."""
    import copy
    a, b = copy.deepcopy(a), copy.deepcopy(b)
    # HEAD-WEST w5 (COORD 05:15): realize_internal_stations only adds the planned FIRM u_ist_ stations to the gen wrapper;
    # u_phy content, hard cores and the native reset production sources are untouched (qualify() re-checks them below).
    for k in ("realize_internal_stations", "note"):
        if a.get(k) != b.get(k):
            print("REALIZE_DELTA", k)
        a.pop(k, None); b.pop(k, None)
    la, lb = a.get("clock", {}).get("landing_contract", {}), b.get("clock", {}).get("landing_contract", {})
    if lb.get("forwarded_clock_only_inputs") not in (None, True) or la.get("forwarded_clock_only_inputs") not in (None, True):
        raise ValueError("HEAD native reset type changed: forwarded_clock_only_inputs")
    la.pop("forwarded_clock_only_inputs", None); lb.pop("forwarded_clock_only_inputs", None)
    pa, pb = la.get("pins", []), lb.get("pins", [])
    if len(pa) != len(pb):
        raise ValueError("HEAD native reset type changed: pin count")
    moved = []
    for x, y in zip(pa, pb):
        if x.get("source_clock_port") != y.get("source_clock_port"):
            if not (x.get("name") == y.get("name") and str(x.get("name", "")).startswith("fclk_out_")
                    and x.get("dir") == "out" and x.get("kind") == "clock"):
                raise ValueError("HEAD native reset type changed: source port of " + str(x.get("name")))
            moved.append((x["name"], x.get("source_clock_port"), y.get("source_clock_port")))
            x.pop("source_clock_port", None); y.pop("source_clock_port", None)
    # HEAD-SERDES-REFLOOR: physical-only keys (pad M7 sites, die-clock reserved sites) are not part of the native reset contract
    for x in (a, b):
        for pd in x.get("pads", []):
            pd.pop("sites_um", None); pd.pop("layer", None)
        x.get("clock", {}).pop("reserved_sites_um", None)
        x.pop("place_regions", None)
        for hc in x.get("hard_cores", []): hc.pop("origin_um", None)
    if a != b:
        raise ValueError("HEAD native reset type changed")
    print("FWD_ONLY_DELTA", moved)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old_plan", "new_plan", "old_receipt", "out", "tools"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--new-receipt", type=Path, default=None,
                        help="receipt produced on the NEW plan digest whose proof.exercised_plan_fields cover every changed hd_serdes partition key")
    args = parser.parse_args()
    sys.path.insert(0, str(args.tools))
    import cores
    import head_native_release
    import reset_tree
    import schema

    old, new = json_load(args.old_plan), json_load(args.new_plan)
    receipt = json_load(args.old_receipt)
    fwd_only_delta(old["partition_types"]["hd_serdes"], new["partition_types"]["hd_serdes"])
    if serdes_parts(old) != serdes_parts(new):
        import pin_entry_phase
        nr = json_load(args.new_receipt) if args.new_receipt else None
        cell_sha = hashlib.sha256(pin_entry_phase.CELL_RTL.encode()).hexdigest()
        diff = check_changed_binding(serdes_parts(old), serdes_parts(new), nr, head_native_release.digest(new),
                                     args.new_receipt.parent if args.new_receipt else None, cell_sha)
        check_rerun(json.loads((args.new_receipt.parent / nr["proof"]["entry_phase_evidence"]).read_text()), rerun_bench_evidence(args.old_plan, args.new_plan, args.tools))
        old_plan = schema.Plan(old, args.old_plan)
        head_native_release.qualify(old_plan, reset_tree.wf_plan(old_plan), args.old_receipt)     # anchor the old side as the old path does
        new_plan0 = schema.Plan(new, args.new_plan)
        moved = check_release_consistency(reset_tree.wf_plan(old_plan), reset_tree.wf_plan(new_plan0), serdes_parts(old), serdes_parts(new), pin_entry_phase.release_delta)
        args.out.mkdir(parents=True, exist_ok=False)
        root = args.new_receipt.parent.resolve()
        files = {}
        for fname, fsha in nr["files"].items():
            src = (root / fname).resolve()
            if src.is_relative_to(root):
                dst = args.out / fname
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                files[fname] = fsha
            else:
                files[os.path.relpath(src, args.out.resolve())] = fsha
        nr["files"] = files
        nr["limits"] = list(nr.get("limits") or []) + ["entry-phase seam timing, whole-cycle label, START entry and strap tie: PENDING die STA on this plan digest"]
        candidate = args.out / "candidate_receipt.json"
        candidate.write_text(json.dumps(nr, indent=1) + "\n")
        accepted = args.out / "native_release_receipt.json"
        new_plan = schema.Plan(new, args.new_plan)
        result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), candidate)      # re-qualify the artifact actually written, then publish it
        candidate.replace(accepted)
        cover = dict(old_plan_sha256=hexdigest(args.old_plan), new_plan_sha256=hexdigest(args.new_plan), old_receipt_sha256=hexdigest(args.old_receipt),
                     new_receipt_sha256=hexdigest(args.new_receipt), covered=diff, wf_plan_release_moved=moved,
                     pending="PENDING die STA on the new plan digest: seam setup/hold at the new capture edge, whole-cycle label, START entry, strap tie in the generated top")
        (args.out / "changed_binding_cover.json").write_text(json.dumps(cover, indent=1) + "\n")
        print("CHANGED_BINDING_COVERED", len(diff), "paths", diff[:8])
        print("WF_PLAN_RELEASE_MOVED", moved)
        print("PENDING_DIE_STA entry-phase seam timing and whole-cycle label are not proven by this receipt")
        print("NATIVE_RELEASE", result["release_qualification"]["verdict"], len(result["release_qualification"]["native_targets"]), "targets", accepted)
        print("ORIGINAL_PROOF", args.old_receipt, hexdigest(args.old_receipt))
        print("PLAN", args.new_plan, hexdigest(args.new_plan))
        return
    old_plan = schema.Plan(old, args.old_plan)
    head_native_release.qualify(old_plan, reset_tree.wf_plan(old_plan), args.old_receipt)
    args.out.mkdir(parents=True, exist_ok=False)
    old_root = args.old_receipt.parent.resolve()
    files = {}
    for name, sha in receipt["files"].items():
        old_file = (old_root / name).resolve()
        if old_file.is_relative_to(old_root):
            copied = args.out / name
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(old_file, copied)
            files[name] = sha
        else:
            files[os.path.relpath(old_file, args.out)] = sha
    sources = receipt["proof"]["production_sources"]
    if any(hexdigest(cores.resolve(name)) != sha for name, sha in sources.items()):
        raise ValueError("HEAD native reset production source differs from measured proof")
    receipt["files"] = files
    receipt["plan_sha256"] = head_native_release.digest(new)
    destination = args.out / "candidate_receipt.json"
    destination.write_text(json.dumps(receipt, indent=1) + "\n")
    new_plan = schema.Plan(new, args.new_plan)
    result = head_native_release.qualify(new_plan, reset_tree.wf_plan(new_plan), destination)
    accepted = args.out / "native_release_receipt.json"
    destination.replace(accepted)
    qualified = result["release_qualification"]
    print("NATIVE_RELEASE", qualified["verdict"], len(qualified["native_targets"]), "targets", accepted)
    print("ORIGINAL_PROOF", args.old_receipt, hexdigest(args.old_receipt))
    print("PLAN", args.new_plan, hexdigest(args.new_plan))


if __name__ == "__main__":
    main()
