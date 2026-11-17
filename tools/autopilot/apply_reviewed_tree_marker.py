#!/usr/bin/env python3
"""apply_reviewed_tree_marker: apply a concrete, already-authorized tree marker tuple under the coord lock.  No producer-state writes.
Moved into the repo (tools/autopilot) from tools-converge/apply_reviewed_tree_marker_1116.py (FLEET-OPS-R, COORD r397) and extended with
PILOT wave mode: the atomic apply switches die.src in kit_wave.json itself, so hold_records.apply_tree_switches never sees a switch;
this adds the pilot hold (all items held but one pilot, released by gen_pilot:<die>:<manifest sha12>) in the same locked write.
usage: apply_reviewed_tree_marker.py --candidate JSON --expect-source OLD_TREE --expect-event OLD_EVENT [--pilot-item ITEM | --no-pilot]
The pilot item is --pilot-item, else die.pilot_item, else the smallest item of the die's hold_event_items; none resolvable = refuse
(--no-pilot is the explicit opt-out; the output then says PILOT NONE)."""
import argparse, fcntl, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_records as HR  # noqa: E402


def atomic(path, data):
    tmp = path.with_name(path.name + ".tmp.atomic." + str(os.getpid()))
    tmp.write_text(json.dumps(data, indent=1) + "\n")
    os.replace(tmp, path)


def apply_marker(C, obj, expect_source, expect_event, pilot_item=None, no_pilot=False, TC=None, rt=None):
    C = Path(C)
    marker = dict(obj.get("marker", obj))
    die = marker["die"]
    tree = marker["tree"]
    want = marker.get("manifest_hash") or marker["src_manifest_sha"]
    mc = dict(marker.get("config") or {})
    hosts = list(mc.get("gen_hosts") or marker.get("hosts") or [])
    assert hosts and marker.get("smoke") == "PASS" and marker.get("plan") and marker.get("plan_sha256")
    if TC is None:
        import tree_check as TC
    rt = rt or HERE
    ident = TC.identity(die, tree, want, hosts, str(rt / "src_manifest.py"))
    guard = TC.read(C / "autopilot/tree_checks", ident)
    assert guard and guard.get("state") == "ok" and guard.get("full_ok") and not guard.get("running"), "exact current normal source guard is not ready"
    main = guard["main_sha"]
    assert len(main) == 40
    assert not any(k in mc for k in ["hold_records", "hold_items", "route_hold_items"]), "preserve inherited holds; add approved records explicitly"
    with (C / ".coord.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cfgpath = C / "autopilot/kit_wave.json"
        cfg = json.loads(cfgpath.read_text())
        d = cfg["dies"][die]
        assert d["src"] == expect_source and d["event"] == expect_event, "die changed since reviewed candidate"
        old = dict(src=d["src"], event=d["event"], plan=d.get("plan"), plan_sha256=d.get("plan_sha256"), kit_rtl=d.get("kit_rtl"))
        # decide the pilot BEFORE any write: a refusal leaves everything untouched
        pilot = ""
        if not no_pilot:
            pilot = pilot_item or HR.pilot_item_for(cfg, die, d)
            if not pilot:
                raise SystemExit("PILOT: no pilot item for die %s (--pilot-item ITEM, die.pilot_item, or --no-pilot); nothing applied" % die)
        HR._deep_set(d, mc)
        sup = d.setdefault("superseded_trees", [])
        if old["src"] and old["src"] != tree and old["src"] not in sup:
            sup.append(old["src"])
        d.update(src=tree, src_manifest=True, src_manifest_hash=want, plan=marker["plan"], plan_sha256=marker["plan_sha256"], gen_hosts=hosts,
                 gen_host=mc.get("gen_host") or hosts[0], cancel_superseded=False)
        d.setdefault("src_sha", main)
        d.setdefault("queue_src", "main@" + main)
        if "src_sha" not in mc:
            d["src_sha"] = main
        if "queue_src" not in mc:
            d["queue_src"] = "main@" + main
        HR._deep_set(d.setdefault("die_gen_env", {}), marker.get("die_gen_env") or {})
        if marker.get("asbuilt") and marker.get("bind_out"):
            HR._deep_set(d.setdefault("kit_rtl", {}), dict(mode="bind", asbuilt=marker["asbuilt"], bind_out=marker["bind_out"]))
        additions = list(obj.get("hold_records_add") or [])
        if obj.get("hold_record"):
            additions.append(obj["hold_record"])
        for rec in additions:
            assert not any(r.get("id") == rec["id"] for r in d.get("hold_records") or []), "duplicate approved hold id"
            HR.add_record(cfg, die, rec)
        for rec in d.get("hold_records") or []:
            rec["release"] = [("tree_ready:" + die + ":" + tree) if x == "tree_ready:" + die + ":" + expect_source else x for x in rec.get("release") or []]
        pilot_added = False
        if pilot:
            d["pilot_item"] = pilot
            pilot_added = HR.add_pilot_hold(cfg, die, d, dict(marker, manifest_hash=want))
        marker.update(manifest_hash=want, src_manifest_sha=want, status="ADOPTED reviewed tuple", written_by="root-authorized lane atomic apply")
        receipt = C / ("lanes/handoff/" + die + "_atomic_apply_" + str(time.time_ns()) + ".json")
        atomic(receipt, dict(die=die, prior=old, marker=marker, pilot=dict(item=pilot, hold_added=pilot_added, release="gen_pilot:%s:%s" % (die, want[:12])) if pilot else "NONE",
                             guard=str(TC.location(C / "autopilot/tree_checks", ident) / "result.json"), candidate=str(obj.get("_path", ""))))
        atomic(C / HR.tree_marker_rel(die), marker)
        atomic(cfgpath, cfg)
        return dict(applied=die, event=d.get("event"), source=tree, receipt=str(receipt), holds_preserved=True,
                    pilot=(dict(item=pilot, release="gen_pilot:%s:%s" % (die, want[:12]), hold_added=pilot_added) if pilot else "NONE"))


def main(argv=None):
    P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    P.add_argument("--candidate", required=True, help="JSON marker or {marker: marker, hold_record: optional_record}")
    P.add_argument("--expect-source", required=True)
    P.add_argument("--expect-event", required=True)
    P.add_argument("--pilot-item")
    P.add_argument("--no-pilot", action="store_true")
    P.add_argument("--coord", default="/home/ubuntu/coord")
    a = P.parse_args(argv)
    obj = json.loads(Path(a.candidate).read_text())
    obj["_path"] = a.candidate
    print(json.dumps(apply_marker(a.coord, obj, a.expect_source, a.expect_event, a.pilot_item, a.no_pilot)))


if __name__ == "__main__":
    main()
