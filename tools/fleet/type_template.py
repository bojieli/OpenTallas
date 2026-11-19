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
  rommap  PLAN --bind-rtl DIR --repo SRC [--rom-dir DIR] [--gds-dir DIR] [--all GLOB ...] --out JSON
                                                        die assembly map: per die position the layout it instantiates (the representative's, with the
                                                        position's origin / orient) and per ROM core the position's own image (INSTANCE string of its
                                                        bound RTL, via map file + sha) with the core rectangle in the die frame; checks that every
                                                        ROM core has the same module, LEF file sha, origin and orient as in the representative; exit 1
                                                        on any mismatch
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


def records(plan, bind_rtl, repo, rom_dir, rep, signoff, globs=(), lec_policy="advisory", via_policy="advisory", judge=CI.judge_signoff):
    """col_inherit records (dicts, nothing written) for every member of rep's template group.  The bound RTL text identity (rtl key)
    is the logic proof, so a record carries lec EQUIVALENT by construction with the rtl key."""
    g = next((x for x in groups(plan, bind_rtl, globs) if x["representative"] == rep), None)
    if g is None:
        raise KeyError("%s is not the representative of a template group" % rep)
    out = []
    for m in g["members"]:
        lec = dict(verdict="EQUIVALENT", method="bound RTL text identity outside the ROM image strings (type_template rtl key)",
                   rtl_key=g["rtl_key"], template_group=g["key"])
        rec = CI.build_record(plan, rep, m, signoff, repo, rom_dir, lec=lec, lec_policy=lec_policy, via_policy=via_policy, judge=judge,
                              group=dict(verdict="OK", reasons=[], layout_key="%s|tt%s" % (g["family"], g["key"])))
        rec["rom_images_checked"] = bool(rom_dir)
        if not rom_dir:
            # no image directory given: the via map files are a die assembly input (rommap checks them per position), not part of
            # the kit the sign-off covers, so their absence here is recorded and does not refuse the credit
            rec["credit_blockers"] = [b for b in rec["credit_blockers"] if not b.startswith("no viamap image for ")]
            rec["credit"] = not rec["credit_blockers"]
        out.append(rec)
    return out


def credit(plan, bind_rtl, repo, rom_dir, rep, signoff, out_dir, members_tsv=None, globs=(), lec_policy="advisory", via_policy="advisory",
           judge=CI.judge_signoff):
    """records() written as <out>/<member>/inherited.json (+ inherit_members.tsv rows for the credited ones).
    -> [(member, record path, credit)]"""
    res = []
    for rec in records(plan, bind_rtl, repo, rom_dir, rep, signoff, globs, lec_policy, via_policy, judge):
        m = rec["sibling"]
        path = CI.write_record(rec, out_dir)
        if members_tsv and rec["credit"]:
            with open(members_tsv, "a") as f:
                f.write(CI.members_row(rec, path) + "\n")
        res.append((m, path, rec["credit"]))
    return res


_HDR = re.compile(r"^\s*(\w+)\s*#\((.*?)\)\s*(\w+)\s*\(", re.M)
_IMGV = re.compile(r'\.INSTANCE\s*\(\s*"([^"]*)"\s*\)')
_FLIP = {"R0": (0, 0), "MX": (0, 1), "MY": (1, 0), "R180": (1, 1)}
_ORI = {v: k for k, v in _FLIP.items()}


def bound_images(text):
    """{bound instance name: (module, image INSTANCE string)} of a bound type RTL: every instance whose parameter list carries a
    non-empty .INSTANCE("...") (ROM macros and the element cores that hold ROMs; an empty string selects no image)"""
    out = {}
    for m in _HDR.finditer(_CMT.sub("", text)):
        v = _IMGV.search(m.group(2))
        if v and v.group(1):
            out[m.group(3)] = (m.group(1), v.group(1))
    return out


def die_rect(part_origin, part_orient, type_outline, origin, outline, orient="R0"):
    """a core rectangle of the type frame -> (lower-left xy in the die frame, orient in the die frame) for a position placed with
    R0 / MX / MY / R180 (the S81 col positions are MX and R180).  Any other orientation raises."""
    if part_orient not in _FLIP or orient not in _FLIP:
        raise ValueError("orientation %s / %s is not R0, MX, MY or R180" % (part_orient, orient))
    fx, fy = _FLIP[part_orient]
    x = type_outline[0] - origin[0] - outline[0] if fx else origin[0]
    y = type_outline[1] - origin[1] - outline[1] if fy else origin[1]
    cx, cy = _FLIP[orient]
    return [round(part_origin[0] + x, 4), round(part_origin[1] + y, 4)], _ORI[(fx ^ cx, fy ^ cy)]


def rommap(plan, bind_rtl, repo, rom_dir=None, globs=(), gds_dir=None):
    """the die assembly map of the template families.  -> dict(schema, positions=[...], errors=[...]).  A position row: part, type,
    layout (= representative: the one GDS / DEF the position instantiates), origin_um, orient, roms=[dict(inst, bound, module, image,
    viamap, viamap_sha256, lef_sha256, die_xy_um, die_orient)].  errors is empty only when, for every position, the ROM cores are the
    representative's (same bound instances and modules, same LEF file sha, origin and orient) and every image named has its via map
    (when rom_dir is given) and the representative's GDS exists (when gds_dir is given)."""
    pt = CI.plan_types(plan)
    rep_of = {}
    for g in groups(plan, bind_rtl, globs):
        for n in [g["representative"]] + g["members"]:
            rep_of[n] = g["representative"]
    lef_sha = {}

    def lsha(path):
        if path not in lef_sha:
            lef_sha[path] = CI.sha256_file(os.path.join(repo, path)) if path else None
        return lef_sha[path]

    def cores(n):
        """{bound instance name: plan hard core}: bind names 'u_r1.u_c5_0' u_u_c5_0 and (r0 frames) 'u_r0.u_c0_0' u_u_r0_u_c0_0"""
        out = {}
        for h in pt[n].get("hard_cores") or []:
            parts = str(h.get("inst")).split(".")
            for k in ("u_" + "_".join(parts), "u_" + "_".join(parts[1:])):
                out.setdefault(k, h)
        return out
    img_cache, core_cache = {}, {}
    names = sorted(os.listdir(rom_dir)) if rom_dir and os.path.isdir(rom_dir) else []
    rows, errors = [], []
    parts = plan.get("partitions") or []
    for p in parts if isinstance(parts, list) else parts.values():
        n = p.get("type")
        if n not in rep_of:
            continue
        r = rep_of[n]
        for x in (n, r):
            if x not in img_cache:
                img_cache[x] = bound_images(_rtl(bind_rtl, x) or "")
                core_cache[x] = cores(x)
        im, ir, cm, cr = img_cache[n], img_cache[r], core_cache[n], core_cache[r]
        if {k: v[0] for k, v in im.items()} != {k: v[0] for k, v in ir.items()}:
            errors.append("%s (%s): image instances / modules differ from the representative %s" % (p.get("name"), n, r))
        if gds_dir and not os.path.isfile(os.path.join(gds_dir, r + ".gds")):
            errors.append("%s: representative layout %s.gds is not in %s" % (p.get("name"), r, gds_dir))
        roms = []
        for b, (mod, image) in sorted(im.items()):
            h, hr = cm.get(b), cr.get(b)
            row = dict(bound=b, module=mod, image=image, inst=h and h.get("inst"))
            if h is None or hr is None:
                errors.append("%s (%s): image instance %s has no plan hard core" % (p.get("name"), n, b))
            else:
                a, c = lsha(h.get("lef")), lsha(hr.get("lef"))
                row["lef_sha256"] = a
                if not a or a != c or h.get("module") != hr.get("module") or h.get("module") != mod:
                    errors.append("%s (%s): %s LEF / module is not the representative's (%s)" % (p.get("name"), n, b, r))
                if h.get("origin_um") != hr.get("origin_um") or (h.get("orient") or "R0") != (hr.get("orient") or "R0") \
                        or h.get("outline_um") != hr.get("outline_um"):
                    errors.append("%s (%s): %s origin / orient / outline is not the representative's (%s)" % (p.get("name"), n, b, r))
                try:
                    row["die_xy_um"], row["die_orient"] = die_rect(p.get("origin_um") or [0, 0], p.get("orient") or "R0", pt[n]["outline_um"],
                                                                   h["origin_um"], h["outline_um"], h.get("orient") or "R0")
                except (ValueError, KeyError, TypeError) as e:
                    errors.append("%s (%s): %s has no die rectangle: %s" % (p.get("name"), n, b, e))
            if rom_dir:
                rx = re.compile(r"^%s%s\.viamap\.hex$" % (re.escape(image), CI.IMAGE_SUFFIX))
                files = [f for f in names if rx.match(f)]
                row["viamap"] = [dict(name=f, sha256=CI.sha256_file(os.path.join(rom_dir, f))) for f in files]
                if not files:
                    errors.append("%s (%s): no via map for image %s" % (p.get("name"), n, image))
            roms.append(row)
        rows.append(dict(part=p.get("name"), type=n, layout=r, origin_um=p.get("origin_um"), orient=p.get("orient") or "R0", roms=roms))
    return dict(schema="opentallas.type_template.rommap.v1", positions=rows, errors=errors,
                layouts=sorted(set(rep_of.values())), images=sum(len(x["roms"]) for x in rows))


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
    for name in ("groups", "check", "credit", "rommap"):
        s = sub.add_parser(name)
        s.add_argument("plan"); s.add_argument("--bind-rtl", required=True); s.add_argument("--all", nargs="*", default=[])
        if name != "groups":
            s.add_argument("--repo", required=True); s.add_argument("--rom-dir")
        if name == "check":
            s.add_argument("--out")
        if name == "rommap":
            s.add_argument("--out", required=True); s.add_argument("--gds-dir")
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
    if a.cmd == "rommap":
        r = rommap(plan, a.bind_rtl, a.repo, a.rom_dir, a.all, a.gds_dir)
        with open(a.out + ".tmp", "w") as fo:
            json.dump(r, fo, indent=1)
        os.replace(a.out + ".tmp", a.out)
        print("TYPE_TEMPLATE rommap: %d position(s), %d layout(s), %d ROM image(s), %d error(s)" % (
            len(r["positions"]), len(r["layouts"]), r["images"], len(r["errors"])))
        for e in r["errors"][:20]:
            print("  ERROR " + e)
        return 1 if r["errors"] else 0
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
