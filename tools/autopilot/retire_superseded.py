#!/usr/bin/env python3
"""retire_superseded: FLEET-OPS-R.  apply_tree_switches (hold_records.py) records the tree a die just left in dies.<die>.superseded_trees.
This tool retires those trees WHOLE through ot_delete_guard, per host, with a per-tree JSONL log; it never edits kit_wave.json except to
drop a tree that is gone or now named again.  A tree is skipped (kept in the list) when any die's src / item_inputs src names it, the guard
refuses it (protected root, live process, symlink, partial path), or the host is unreachable.  Dry unless --apply.
usage: retire_superseded.py --kit-wave kit_wave.json --guard-module ot_delete_guard.py --list protected.txt --log LOG.jsonl [--apply]
(run on each host that holds trees; it only touches trees that exist locally)"""
import argparse, importlib.util, json, os, shutil, socket, sys, time


def named(cfg):
    s = set()
    for d in (cfg.get("dies") or {}).values():
        for it in [d] + [i for i in (d.get("item_inputs") or {}).values() if isinstance(i, dict)]:
            if it.get("src"):
                s.add(os.path.realpath(it["src"]))
    return s


def run(cfg, refuse, delete, log, apply=False, now=None):
    """-> list of records; delete(tree) is only called for an allowed tree when apply"""
    keep = named(cfg); out = []
    for die, d in (cfg.get("dies") or {}).items():
        for t in list(d.get("superseded_trees") or []):
            rec = dict(die=die, tree=t, t=time.strftime("%F %T", time.localtime(now)), host=socket.gethostname())
            if not os.path.lexists(t):
                rec["result"] = "absent"
            elif os.path.realpath(t) in keep:
                rec["result"] = "KEEP named again by a die"
            else:
                r = refuse(t)
                if r:
                    rec["result"] = "KEEP guard: " + str(r)[:120]
                elif not apply:
                    rec["result"] = "WOULD-DELETE"
                else:
                    delete(t); rec["result"] = "DELETED" if not os.path.lexists(t) else "FAILED"
            out.append(rec); log(rec)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kit-wave", required=True); ap.add_argument("--guard-module", required=True); ap.add_argument("--list", required=True)
    ap.add_argument("--log", required=True); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    sp = importlib.util.spec_from_file_location("g", a.guard_module); g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
    prot, err = g.load_list(a.list)
    if prot is None:
        print("protected list unusable (fail closed): " + str(err)); return 3
    cfg = json.load(open(a.kit_wave))

    def delete(t):
        os.system("find " + __import__("shlex").quote(t) + " -type d -exec chmod u+w {} +"); shutil.rmtree(t, ignore_errors=True)
    with open(a.log, "a") as lf:
        recs = run(cfg, lambda t: g.refuse(t, prot), delete, lambda r: lf.write(json.dumps(r) + "\n"), a.apply)
    for r in recs:
        print(r["result"], r["die"], r["tree"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
