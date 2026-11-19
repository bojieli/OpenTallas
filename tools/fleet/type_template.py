#!/usr/bin/env python3
"""TYPE-TEMPLATE (OWNER 11-19, FABLE-TYPE-REDUCE-S81-COL): one kit per layout of a family, every other position counted by equivalence.

A die plan marks a partition type with `"type_template": true` (set per family by `flag`).  Marked types that are the SAME kit are one
template group: the wave builds the group's representative only, and a member counts when the representative is signed and the member's
equivalence record says credit (tools/fleet/col_inherit.py record, read by release_tree_plan.inherit_credit).

Two marked types are one group only when BOTH keys are equal (nothing is assumed):
  layout key  the plan type entry with names, notes, the cl/pv labels and the ROM image selectors (param_set P_*_INSTANCE) removed
              (col_typemerge layout hash; non-image parameters stay in the key);
  rtl key     the bound RTL of the type (bind out rtl/<type>.sv) with comments, its own module name and the ROM image strings
              (.INSTANCE("...") / .VIAMAP("...")) removed.  The reset tree, clock landings and every strap stay in the key: S81 D8e has 42
              col layout keys but 51 kits, because a position that exports a reset to its neighbour has another reset tree and pin.
A marked type with no bound RTL file is its own group (it builds on its own; never a member).

  groups  PLAN --bind-rtl DIR [--all GLOB ...]          template groups (representative, members); --all = treat the globbed types as marked
  check   PLAN --bind-rtl DIR --repo SRC [--all GLOB ...] [--rom-dir DIR] [--out JSON]
                                                        per position: layout key, rtl key, outline, hard-core LEF/lib sha (files of SRC), differing
                                                        parameters are image selectors only; exit 1 when any member fails
  flag    PLAN OUT GLOB [GLOB ...]                      set type_template true on the globbed types (the plan row of an event)
  credit  PLAN --bind-rtl DIR --repo SRC --rom-dir DIR --rep TYPE --signoff signoff.json --out DIR --members-tsv TSV [--lec-policy ...]
                                                        col_inherit records + inherit_members.tsv rows for every member of TYPE's group
  view    --rep TYPE --member TYPE --lef F --lib F --out DIR
                                                        the member's hard view = the representative's LEF / Liberty under the member's name
                                                        (die assembly places it with the position's orientation; the ROM via map is per instance)
"""
import argparse
import fnmatch
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import col_inherit as CI     # noqa: E402
import col_typemerge as TM   # noqa: E402

FLAG = "type_template"
SCHEMA = "opentallas.type_template.v1"
_CMT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_IMG = re.compile(r'\.(INSTANCE|VIAMAP)\s*\(\s*"[^"]*"\s*\)')


def family(name):
    return name.split("__", 1)[0]


def marked(pt, globs=()):
    """names of the types that carry the flag (or match one of globs)"""
    return sorted(n for n, t in pt.items() if isinstance(t, dict) and
                  (t.get(FLAG) is True or any(fnmatch.fnmatchcase(n, g) for g in globs)))


def layout_key(name, t):
    w = TM._norm({k: v for k, v in t.items() if k != FLAG}, name)
    fixed = {k: v for k, v in sorted(CI.param_set(t).items()) if not CI.IMAGE_PARAM_RE.match(k)}
    return CI.jsha([family(name), w, fixed])


def rtl_key(text, name):
    s = _CMT.sub("", text).replace(name, "@T")
    s = _IMG.sub(r".\1(@I)", s)
    return CI.sha256_bytes(re.sub(r"\s+", " ", s).strip().encode())


def _rtl(bind_rtl, name):
    try:
        with open(os.path.join(bind_rtl, name + ".sv"), errors="replace") as f:
            return f.read()
    except (OSError, TypeError):
        return None


def groups(plan, bind_rtl, globs=()):
    """-> [dict(family, key, layout_key, rtl_key, representative, members)] over the marked types, sorted; the representative is the
    first name of the group, so every host and every tick picks the same one."""
    pt = CI.plan_types(plan)
    by = {}
    for n in marked(pt, globs):
        text = _rtl(bind_rtl, n)
        lk = layout_key(n, pt[n])
        rk = rtl_key(text, n) if text is not None else "no-bound-rtl:" + n
        by.setdefault((family(n), lk, rk), []).append(n)
    out = []
    for (fam, lk, rk), names in sorted(by.items(), key=lambda kv: min(kv[1])):
        names = sorted(names)
        out.append(dict(family=fam, key=CI.jsha([lk, rk])[:16], layout_key=lk[:16], rtl_key=rk[:16] if not rk.startswith("no-") else rk,
                        representative=names[0], members=names[1:]))
    return out


def member_map(plan, bind_rtl, globs=()):
    """{member: representative} (representatives and unmarked types are absent)"""
    return {m: g["representative"] for g in groups(plan, bind_rtl, globs) for m in g["members"]}


def orients(plan):
    out = {}
    parts = plan.get("partitions") or []
    for p in parts if isinstance(parts, list) else parts.values():
        if isinstance(p, dict):
            out.setdefault(p.get("type"), []).append(p.get("orient") or "R0")
    return out


def check(plan, bind_rtl, repo, globs=(), rom_dir=None):
    """the per-position equivalence proof.  -> dict(schema, groups, positions=[...], failed=[names])"""
    pt = CI.plan_types(plan)
    ori = orients(plan)
    gs = groups(plan, bind_rtl, globs)
    rows, failed = [], []
    sig_cache = {}

    def sig(n):
        if n not in sig_cache:
            sig_cache[n] = CI.hard_core_signature(pt[n], repo)
        return sig_cache[n]
    for g in gs:
        rep = g["representative"]
        tr = pt[rep]
        for n in [rep] + g["members"]:
            t = pt[n]
            why = []
            if n != rep:
                if layout_key(n, t) != layout_key(rep, tr):
                    why.append("layout key differs")
                a, b = _rtl(bind_rtl, n), _rtl(bind_rtl, rep)
                if a is None or b is None or rtl_key(a, n) != rtl_key(b, rep):
                    why.append("bound RTL differs outside the ROM image strings")
                if t.get("outline_um") != tr.get("outline_um"):
                    why.append("outline differs")
                if sig(n) != sig(rep):
                    why.append("hard-core signature (module, LEF, lib, origin, orient, file sha) differs")
                pa, pb = CI.param_set(t), CI.param_set(tr)
                diff = sorted(k for k in set(pa) | set(pb) if pa.get(k) != pb.get(k))
                bad = [k for k in diff if not CI.IMAGE_PARAM_RE.match(k)]
                if bad:
                    why.append("differing non-image parameters " + ",".join(bad[:5]))
            if any(r[6] is None or r[7] is None for r in sig(n) if r[2] or r[3]):
                why.append("a hard-core LEF or lib file is missing in the tree")
            imgs = None
            if rom_dir:
                im = CI.rom_images(t, rom_dir)
                imgs = sum(len(i["files"]) for i in im)
                miss = [i["instance"] for i in im if not i["files"]]
                if miss:
                    why.append("no via map image for %d instance(s), e.g. %s" % (len(miss), miss[0]))
            rows.append(dict(type=n, group=g["key"], representative=rep, role="representative" if n == rep else "member",
                             orient=sorted(set(ori.get(n) or [])), hard_cores=len(t.get("hard_cores") or []),
                             image_params=sum(1 for k in CI.param_set(t) if CI.IMAGE_PARAM_RE.match(k)), rom_images=imgs,
                             equivalent=not why, reasons=why))
            if why:
                failed.append(n)
    return dict(schema=SCHEMA, groups=gs, positions=rows, failed=failed)


def flag(plan, globs):
    """set the flag on the globbed types (in place).  -> names newly marked"""
    pt = CI.plan_types(plan)
    done = []
    for n, t in pt.items():
        if isinstance(t, dict) and t.get(FLAG) is not True and any(fnmatch.fnmatchcase(n, g) for g in globs):
            t[FLAG] = True
            done.append(n)
    return sorted(done)


def credit(plan, bind_rtl, repo, rom_dir, rep, signoff, out_dir, members_tsv=None, globs=(), lec_policy="advisory", via_policy="advisory",
           judge=CI.judge_signoff):
    """col_inherit records for every member of rep's template group.  The bound RTL text identity (rtl key) is the logic proof, so the
    record carries lec EQUIVALENT by construction with the two rtl keys.  -> [(member, record path, credit)]"""
    g = next((x for x in groups(plan, bind_rtl, globs) if x["representative"] == rep), None)
    if g is None:
        raise KeyError("%s is not the representative of a template group" % rep)
    res = []
    for m in g["members"]:
        lec = dict(verdict="EQUIVALENT", method="bound RTL text identity outside the ROM image strings (type_template rtl key)",
                   rtl_key=g["rtl_key"], template_group=g["key"])
        rec = CI.build_record(plan, rep, m, signoff, repo, rom_dir, lec=lec, lec_policy=lec_policy, via_policy=via_policy, judge=judge,
                              group=dict(verdict="OK", reasons=[], layout_key="%s|tt%s" % (g["family"], g["key"])))
        path = CI.write_record(rec, out_dir)
        if members_tsv and rec["credit"]:
            with open(members_tsv, "a") as f:
                f.write(CI.members_row(rec, path) + "\n")
        res.append((m, path, rec["credit"]))
    return res


def clone_view(rep, member, lef, lib, out_dir):
    """the member's LEF / Liberty = the representative's with the macro / cell name replaced.  Refuses when the name does not occur as
    the MACRO / cell name exactly once per file.  -> (lef path, lib path)"""
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for src, pat, ext in ((lef, r"^(\s*MACRO\s+)%s\s*$", ".lef"), (lib, r"^(\s*cell\s*\(\s*\"?)%s(\"?\s*\))", "_tt.lib")):
        text = open(src, errors="replace").read()
        if len(re.findall(pat % re.escape(rep), text, re.M)) != 1:
            raise ValueError("%s: %s is not the single macro / cell name" % (src, rep))
        text = re.sub(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(rep), member, text)
        p = os.path.join(out_dir, member + ext)
        with open(p + ".tmp", "w") as f:
            f.write(text)
        os.replace(p + ".tmp", p)
        out.append(p)
    return tuple(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("groups", "check", "credit"):
        s = sub.add_parser(name)
        s.add_argument("plan"); s.add_argument("--bind-rtl", required=True); s.add_argument("--all", nargs="*", default=[])
        if name != "groups":
            s.add_argument("--repo", required=True); s.add_argument("--rom-dir")
        if name == "check":
            s.add_argument("--out")
        if name == "credit":
            s.add_argument("--rep", required=True); s.add_argument("--signoff", required=True); s.add_argument("--out", required=True)
            s.add_argument("--members-tsv"); s.add_argument("--lec-policy", default="advisory", choices=("require", "advisory"))
            s.add_argument("--via-policy", default="advisory", choices=("require", "advisory"))
    f = sub.add_parser("flag"); f.add_argument("plan"); f.add_argument("out"); f.add_argument("globs", nargs="+")
    v = sub.add_parser("view")
    for k in ("rep", "member", "lef", "lib", "out"):
        v.add_argument("--" + k, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "view":
        print("\n".join(clone_view(a.rep, a.member, a.lef, a.lib, a.out)))
        return 0
    plan = json.load(open(a.plan))
    if a.cmd == "flag":
        done = flag(plan, a.globs)
        with open(a.out + ".tmp", "w") as fo:
            json.dump(plan, fo, indent=1)
            fo.write("\n")
        os.replace(a.out + ".tmp", a.out)
        print("TYPE_TEMPLATE flag: %d type(s) marked" % len(done))
        return 0
    if a.cmd == "groups":
        gs = groups(plan, a.bind_rtl, a.all)
        fam = {}
        for g in gs:
            fam.setdefault(g["family"], []).append(1 + len(g["members"]))
        for k, v in sorted(fam.items()):
            print("%-18s types %3d templates %2d  sizes %s" % (k, sum(v), len(v), sorted(v, reverse=True)))
        print("TOTAL types %d templates %d" % (sum(map(sum, fam.values())), len(gs)))
        print(json.dumps(gs, indent=1))
        return 0
    if a.cmd == "check":
        r = check(plan, a.bind_rtl, a.repo, a.all, a.rom_dir)
        if a.out:
            with open(a.out, "w") as fo:
                json.dump(r, fo, indent=1)
        n = len(r["positions"])
        print("TYPE_TEMPLATE check: %d position(s), %d group(s), %d equivalent, %d FAILED" % (n, len(r["groups"]), n - len(r["failed"]), len(r["failed"])))
        for row in r["positions"]:
            if not row["equivalent"]:
                print("  FAIL %s vs %s: %s" % (row["type"], row["representative"], "; ".join(row["reasons"])))
        return 1 if r["failed"] else 0
    res = credit(plan, a.bind_rtl, a.repo, a.rom_dir, a.rep, a.signoff, a.out, a.members_tsv, a.all, a.lec_policy, a.via_policy)
    for m, p, c in res:
        print("%s\t%s\t%s" % ("CREDIT" if c else "NO-CREDIT", m, p))
    return 0 if all(c for _m, _p, c in res) else 1


if __name__ == "__main__":
    sys.exit(main())
