#!/usr/bin/env python3
"""apply_reviewed_tree_marker: apply a concrete, already-authorized tree marker tuple under the coord lock.  No producer-state writes.
Moved into the repo (tools/autopilot) from tools-converge/apply_reviewed_tree_marker_1116.py (FLEET-OPS-R, COORD r397) and extended with
PILOT wave mode: the atomic apply switches die.src in kit_wave.json itself, so hold_records.apply_tree_switches never sees a switch;
this adds the pilot hold (all items held but one pilot, released by gen_pilot:<die>:<manifest sha12>) in the same locked write.
PUBLISH-GATE-1116: refuses without a PASS record of tools/autopilot/publish_gate.py (run it first; no opt-out flag).
usage: apply_reviewed_tree_marker.py --candidate JSON --expect-source OLD_TREE --expect-event OLD_EVENT [--pilot-item ITEM | --no-pilot]
       [--keep-gen-hosts]
--keep-gen-hosts (or candidate key keep_gen_hosts: true; HEAD-DIE-R, COORD r400/r401): keep the die's CURRENT gen_hosts (e.g. a
replica FLEET-OPS added after the candidate was written) instead of the candidate list.  The normal source guard must be full_ok on
exactly those hosts, and the apply refuses when gen_hosts changed between that guard read and the locked write.
The pilot item is --pilot-item, else die.pilot_item, else the smallest item of the die's hold_event_items; none resolvable = refuse
(--no-pilot is the explicit opt-out; the output then says PILOT NONE)."""
import os
import argparse, fcntl, json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_records as HR  # noqa: E402


def atomic(path, data):
    tmp = path.with_name(path.name + ".tmp.atomic." + str(os.getpid()))
    tmp.write_text(json.dumps(data, indent=1) + "\n")
    os.replace(tmp, path)


def ensure_tree_on_hosts(tree, want, current_hosts, hosts, rt, run=None, link_from=""):
    """WAVE-FLOW-R2 11-17 (FABLE-FLOW-1700 item 3): the apply must not narrow the die to the hosts the candidate happens to list.  Every host that serves the die today
    (current_hosts) and is not in the candidate list gets the tree replicated (src_manifest replicate --link-from) and verified (hosts --expect); any failure refuses with
    the host list.  -> (hosts the die will have = candidate + verified extras, [detail lines])"""
    extra = [h for h in current_hosts if h not in hosts]
    if not extra:
        return list(hosts), []
    import shlex
    import subprocess
    sm = str(Path(rt) / "src_manifest.py")

    def sh(cmd):
        if run:
            return run(cmd)
        r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=14400)   # 11-18: a 58 GB tree copy + verify ran past the old 3600 s and was killed (epyc7, epyc10 DROPPED at QC N4.1q)
        return r.returncode, (r.stdout + r.stderr).strip()
    # LATENCY-R 11-18 (QC N3 sat ready ~1 h+ because intel1 scratch2 was full): one extra host that cannot take the tree (disk floor, down) no longer refuses the
    # whole apply.  Each extra host is replicated + verified on its own; a host that fails is DROPPED from the die's gen_hosts for this tree (named in the detail
    # lines; derive_gen_hosts adds it back hourly once it holds the tree).  The candidate's own hosts are kept: their guard already covered them.
    kept, notes = [], []
    # FABLE-FLOW-1400 (2): the apply runs on the hub, which holds no tree ("not a manifest tree" dropped epyc10 at QC N4 s1).  The copy is made FROM
    # the first candidate host that holds the tree and verifies it against the manifest hash, over ssh on that host; no verified source = every
    # extra host is DROPPED (named), never a copy of an unverified tree.
    src = ""
    for s in hosts:
        rc, out = sh(f"python3 -I {shlex.quote(sm)} hosts {shlex.quote(tree)} --hosts {shlex.quote(s)} --expect {shlex.quote(want)}")
        if not rc:
            src = s
            break
        notes.append(f"source {s} not verified: {out[-160:]}")
    if not src:
        return list(hosts), [f"DROPPED {h}: no candidate host holds a verified copy of {tree} to replicate from" for h in extra] + notes
    ssh = "ssh -n -o BatchMode=yes -o ControlPath=none -o ConnectTimeout=15 "
    for h in extra:
        # 11-19 (QC N4.2, epyc10 dropped 3 times with 'target exists or not writable'): an earlier apply's copy had already finished there, so replicate refused the existing tree.
        # A target that already holds the tree is VERIFIED first; a verified copy is kept without a new replicate (an unverified existing one still goes to replicate / the DROPPED note).
        rc0, _out0 = sh(f"python3 -I {shlex.quote(sm)} hosts {shlex.quote(tree)} --hosts {shlex.quote(h)} --expect {shlex.quote(want)}")
        if not rc0:
            kept.append(h)
            notes.append(f"{h}: already holds a verified copy")
            continue
        rep = f"python3 -I {shlex.quote(sm)} replicate {shlex.quote(tree)} --hosts {shlex.quote(h)}" + (f" --link-from {shlex.quote(link_from)}" if link_from else "")
        rc, out = sh(ssh + shlex.quote(src) + " " + shlex.quote(rep))
        if not rc:
            rc, out = sh(f"python3 -I {shlex.quote(sm)} hosts {shlex.quote(tree)} --hosts {shlex.quote(h)} --expect {shlex.quote(want)}")
        if rc:
            notes.append(f"DROPPED {h}: replicate/verify rc {rc}: {out[-200:]}")
        else:
            kept.append(h)
    notes = [n for n in notes if not n.startswith("source ")] + [n for n in notes if n.startswith("source ")]
    if kept:
        notes.insert(0, f"replicated from {src} and verified on {','.join(kept)}")
    return list(hosts) + kept, notes


def repoint_gen_env(d, old_tree, new_tree, exists=os.path.exists):
    """11-18 (third time tonight: OT_SIGNED_VIEW_SHA left outside the new tree, every launch refused): every die_gen_env / item_env string naming a path inside the OLD tree is rewritten to the
    same relative path in the NEW tree; a repointed file missing there fails the apply (SystemExit, nothing written)."""
    if not old_tree or not new_tree or old_tree == new_tree:
        return []
    old, new, missing, done = old_tree.rstrip("/"), new_tree.rstrip("/"), [], []

    def fix(env, where):
        for k, v in list((env or {}).items()):
            if isinstance(v, str) and old + "/" in v + "/" and v.startswith(old):
                nv = new + v[len(old):]
                env[k] = nv
                done.append(f"{where}{k}")
                if not exists(nv):
                    missing.append(f"{where}{k} -> {nv}")
    fix(d.get("die_gen_env"), "die_gen_env.")
    for it, env in (d.get("item_env") or {}).items():
        fix(env, f"item_env.{it}.")
    if missing:
        raise SystemExit("APPLY REFUSED: gen env file missing in the new tree: " + "; ".join(missing[:6]) + " (add it to the tree manifest); nothing applied")
    return done


def marker_event_of(mc, d):
    return mc.get("event") or d.get("event")


def apply_marker(C, obj, expect_source, expect_event, pilot_item=None, no_pilot=False, TC=None, rt=None, keep_gen_hosts=False, PG=None, optimistic=None):
    """optimistic (COORD 11-18, OWNER "build all types directly from the latest plan"; candidate key optimistic: true or --optimistic): the publish gate record,
    the normal source guard and the smoke flag are ADVISORY (logged in the receipt as warnings, never a refusal) and no pilot hold is added (every type of the
    plan launches at once) unless --pilot-item names one.  Strict bind + LATCHECK, run in parallel by the lane, are the only blocking plan checks: a failure
    holds just the types it names (publish_apply.py bind-fail)."""
    C = Path(C)
    optimistic = bool(obj.get("optimistic")) if optimistic is None else bool(optimistic)
    warnings = []
    marker = dict(obj.get("marker", obj))
    die = marker["die"]
    tree = marker["tree"]
    want = marker.get("manifest_hash") or marker["src_manifest_sha"]
    mc = dict(marker.get("config") or {})
    hosts = list(mc.get("gen_hosts") or marker.get("hosts") or [])
    keep = bool(keep_gen_hosts or obj.get("keep_gen_hosts"))
    if keep:
        cur = json.loads((C / "autopilot/kit_wave.json").read_text())["dies"][die]
        hosts = list(cur.get("gen_hosts") or [])
        assert hosts, "keep_gen_hosts: the die has no current gen_hosts"
        mc.pop("gen_hosts", None)
        mc.pop("gen_host", None)
    assert hosts and marker.get("plan") and marker.get("plan_sha256")
    if marker.get("smoke") != "PASS":
        assert optimistic, "candidate smoke is not PASS"
        warnings.append(f"ADVISORY smoke={marker.get('smoke')!r}")
    if optimistic and not pilot_item:
        no_pilot = True
    replicated = []
    if not keep:
        _cfg0 = json.loads((C / "autopilot/kit_wave.json").read_text())
        _cur = [h for h in (_cfg0["dies"][die].get("gen_hosts") or []) if h not in (_cfg0.get("retired_hosts") or [])]
        hosts, replicated = ensure_tree_on_hosts(tree, want, _cur, hosts, rt or HERE, link_from=os.path.basename(str(_cfg0["dies"][die].get("src") or "")))
        mc.pop("gen_hosts", None) if replicated else None
        warnings += [x for x in replicated if x.startswith("DROPPED")]
    # PUBLISH-GATE-1116: no switch without a PASS record of the pre-apply gate (schema, PRE/G0, provenance hashes, dry gen) keyed to
    # this tree manifest sha.  PG=False is only publish_gate.project_cfg() projecting the apply on a scratch copy.
    if PG is not False:
        if PG is None:
            import publish_gate as PG
        why = PG.require_pass(C, die, tree, want, marker["plan_sha256"])
        if why and optimistic:
            warnings.append("ADVISORY publish_gate: " + str(why)[:300])
        else:
            assert not why, why
    if TC is None:
        import tree_check as TC
    rt = rt or HERE
    ident = TC.identity(die, tree, want, hosts, str(rt / "src_manifest.py"))
    guard = TC.read(C / "autopilot/tree_checks", ident)
    if optimistic and not (guard and guard.get("state") == "ok" and guard.get("full_ok") and not guard.get("running")):
        warnings.append("ADVISORY source guard not ready: " + str({k: (guard or {}).get(k) for k in ("state", "full_ok", "running")}))
        main = str((guard or {}).get("main_sha") or marker.get("main_sha") or "")
    else:
        assert guard and guard.get("state") == "ok" and guard.get("full_ok") and not guard.get("running"), "exact current normal source guard is not ready"
        main = guard["main_sha"]
        assert len(main) == 40
    assert not any(k in mc for k in ["hold_records", "hold_items", "route_hold_items"]), "preserve inherited holds; add approved records explicitly"
    with (C / ".coord.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        cfgpath = C / "autopilot/kit_wave.json"
        _cfg_base_text = cfgpath.read_text()
        cfg = json.loads(_cfg_base_text)
        d = cfg["dies"][die]
        assert d["src"] == expect_source and d["event"] == expect_event, "die changed since reviewed candidate"
        if keep:
            assert sorted(d.get("gen_hosts") or []) == sorted(hosts), "keep_gen_hosts: gen_hosts changed since the guard read; nothing applied"
        old = dict(src=d["src"], event=d["event"], plan=d.get("plan"), plan_sha256=d.get("plan_sha256"), kit_rtl=d.get("kit_rtl"))
        # decide the pilot BEFORE any write: a refusal leaves everything untouched
        pilot = ""
        if not no_pilot:
            pilot = pilot_item or HR.pilot_item_for(cfg, die, d)
            if not pilot:
                raise SystemExit("PILOT: no pilot item for die %s (--pilot-item ITEM, die.pilot_item, or --no-pilot); nothing applied" % die)
        HR._deep_set(d, mc)
        # FABLE-FLOW-2200: keep the CURRENT tree and ONE rollback (the tree just replaced); the rollback of the previous switch is now two versions back
        # and becomes superseded (retired whole through the guard by retire_superseded.py)
        sup = d.setdefault("superseded_trees", [])
        rb = d.get("rollback_tree")
        if rb and rb != tree and rb != old["src"] and rb not in sup:
            sup.append(rb)
        if old["src"] and old["src"] != tree:
            d["rollback_tree"] = old["src"]
        # WAVE-FLOW-R2 11-17 (COORD r631): the event this apply replaces joins the die's recorded lineage (event_adopt terms of any ancestor stay met)
        if old["event"] and old["event"] != d.get("event") and old["event"] != marker_event_of(mc, d):
            lin = list(d.get("event_lineage") or [])
            if old["event"] not in lin:
                lin.append(old["event"])
            d["event_lineage"] = lin
        d.update(src=tree, src_manifest=True, src_manifest_hash=want, plan=marker["plan"], plan_sha256=marker["plan_sha256"], gen_hosts=hosts,
                 gen_host=mc.get("gen_host") or (d.get("gen_host") if keep and d.get("gen_host") in hosts else hosts[0]),
                 cancel_superseded=False)
        # WAVE-FLOW-R2 11-17 (COORD): an applied event is a plan of record by definition; the wave gate() rejects an event outside GATE_EVENTS / gate_events_extra and the
        # die went OFF silently after NF15d2r1 (08:13) and NF15f (17:24, no HEAD item launched for 3 h).  The apply adds the label in the same atomic write.
        if d.get("event"):
            ge = list(d.get("gate_events_extra") or [])
            if d["event"] not in ge:
                d["gate_events_extra"] = ge + [d["event"]]
        if main:
            d.setdefault("src_sha", main)
            d.setdefault("queue_src", "main@" + main)
            if "src_sha" not in mc:
                d["src_sha"] = main
            if "queue_src" not in mc:
                d["queue_src"] = "main@" + main
        HR._deep_set(d.setdefault("die_gen_env", {}), marker.get("die_gen_env") or {})
        repoint_gen_env(d, old["src"], tree)
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
        prior_pilots = [r for r in d.get("hold_records") or [] if r.get("auto_pilot")]
        if pilot:
            d["pilot_item"] = pilot
            pilot_added = HR.add_pilot_hold(cfg, die, d, dict(marker, manifest_hash=want))
        current_ids = {r.get("id") for r in d.get("hold_records") or []}
        retired_pilots = [r for r in prior_pilots if r.get("id") not in current_ids]
        published_gen_import = {"status": "NORMAL-GEN"}
        if pilot and PG is not False:
            try:
                import published_gen_origin as PGO
                import kit_wave as KW
                ref, why = PGO.reference_for_apply(C, cfg, die, pilot, KW, recipe_archive=obj.get("published_gen_recipe_archive"))
                pilot_record = next((r for r in d.get("hold_records") or []
                                     if r.get("id") == "pilot-%s-%s" % (die, want[:12]) and r.get("auto_pilot")), None)
                if ref and pilot_record is not None:
                    pilot_record["published_gen_proof"] = ref
                    published_gen_import = {"status": "IMPORTED", "proof": ref}
                else:
                    published_gen_import["why"] = why or "no automatic pilot hold"
            except (ImportError, AssertionError, OSError, ValueError, TypeError, KeyError, AttributeError) as e:
                published_gen_import["why"] = str(e)
        marker.update(manifest_hash=want, src_manifest_sha=want, status="ADOPTED reviewed tuple", written_by="root-authorized lane atomic apply")
        receipt = C / ("lanes/handoff/" + die + "_atomic_apply_" + str(time.time_ns()) + ".json")
        atomic(receipt, dict(die=die, prior=old, marker=marker, published_gen_import=published_gen_import, pilot=dict(item=pilot, hold_added=pilot_added, retired=retired_pilots, release="gen_pilot:%s:%s" % (die, want[:12])) if pilot else "NONE",
                             guard=str(TC.location(C / "autopilot/tree_checks", ident) / "result.json"), candidate=str(obj.get("_path", "")),
                             optimistic=optimistic, warnings=warnings))
        atomic(C / HR.tree_marker_rel(die), marker)
        try:
            import kit_wave_edit as _KWE
            _KWE.cas_write(C, cfg, _cfg_base_text)          # lock + compare-and-swap: a config that moved during the apply is never overwritten with this stale copy
        except ImportError:
            atomic(cfgpath, cfg)
        return dict(applied=die, event=d.get("event"), source=tree, receipt=str(receipt), holds_preserved=True, optimistic=optimistic, warnings=warnings, gen_hosts=hosts,
                    pilot=(dict(item=pilot, release="gen_pilot:%s:%s" % (die, want[:12]), hold_added=pilot_added) if pilot else "NONE"))


def commit_apply(coord, res):
    """FABLE-FLOW-1100 (6): the apply wrote kit_wave.json, the die's tree_switch marker and a receipt but committed nothing; the hub git sync then reported HUB-SYNC-FAILED
    (22 times, 28+ min each) until some other lane's commit swept the files in.  The writer commits its own files through bin/coord-commit.sh.  -> 'ok' | 'FAILED rc' | 'skipped'"""
    import subprocess
    C = Path(coord); script = C / "bin/coord-commit.sh"
    if not script.is_file():
        return "skipped: no coord-commit.sh"
    rel = ["autopilot/kit_wave.json", "lanes/handoff/" + HR.tree_marker_rel(res["applied"]).split("lanes/handoff/")[-1] if "lanes/handoff/" in str(HR.tree_marker_rel(res["applied"])) else str(HR.tree_marker_rel(res["applied"]))]
    try:
        rel.append(str(Path(res["receipt"]).relative_to(C)))
    except (KeyError, ValueError):
        pass
    r = subprocess.run(["bash", str(script), "atomic apply %s %s (written by apply_reviewed_tree_marker)" % (res.get("applied"), str(res.get("event"))[:60]), *rel],
                       cwd=str(C), capture_output=True, text=True, timeout=600)
    return "ok" if r.returncode == 0 else "FAILED rc %d: %s" % (r.returncode, (r.stderr or r.stdout)[-160:])


def main(argv=None):
    P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    P.add_argument("--candidate", required=True, help="JSON marker or {marker: marker, hold_record: optional_record}")
    P.add_argument("--expect-source", required=True)
    P.add_argument("--expect-event", required=True)
    P.add_argument("--pilot-item")
    P.add_argument("--no-pilot", action="store_true")
    P.add_argument("--keep-gen-hosts", action="store_true", help="keep the die's current gen_hosts (guard must cover exactly them)")
    P.add_argument("--coord", default="/home/ubuntu/coord")
    P.add_argument("--no-commit", action="store_true", help="leave the written files uncommitted (the caller commits)")
    P.add_argument("--optimistic", action="store_true", help="COORD 11-18: gate record, source guard and smoke are advisory; no pilot hold unless --pilot-item")
    a = P.parse_args(argv)
    obj = json.loads(Path(a.candidate).read_text())
    obj["_path"] = a.candidate
    res = apply_marker(a.coord, obj, a.expect_source, a.expect_event, a.pilot_item, a.no_pilot, keep_gen_hosts=a.keep_gen_hosts, optimistic=True if a.optimistic else None)
    if not a.no_commit:
        res["commit"] = commit_apply(a.coord, res)
    print(json.dumps(res))


if __name__ == "__main__":
    main()
