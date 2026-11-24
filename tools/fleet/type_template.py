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

STRICT CREDIT (S81-ROM-TEMPLATE 11-23; credit(..., rule="strict"), die option type_template_rule "strict"): a member is credited only
when ALL of these hold as well (each refusal is named in credit_blockers):
  logic    the ROM image strings are masked only on instances of the type's own plan hard cores (black boxes in synthesis and LEC); an
           image string on any other module stays in the rtl key, so equal keys mean the same netlist by construction
  images   every image instance of the member's BOUND RTL sits on the same bound instance / module as in the representative and names the
           same ROM path below the frame (no permutation), all in one frame, and no image is named by any other position of the die
  kit      the generated kit of the member equals the representative's (kit_files: every file, own name / image strings / part names /
           comments / provenance hashes normalised) - the automated geometry, constraint and hook equality check
  content  every image has its via map(s), listed with the same sha256 in a PASS weight record (rom_gen.py weights + verify-weights,
           schema opentallas.rom-weights-*), and the member's image set differs from the representative's and from every other member's

WINDOW CONTAINMENT (COORD 11-24 02:20 ruling; rule="contain", die option type_template_rule "contain"): the strict rule with the plan
clock.tap_window of the member allowed to differ from the representative's when the representative's signed window dominates it.
  windows  every kit clock port p: member D_p <= representative D_p (a port missing from a per_port_ps table takes the type's W_t; W_t
           itself too), and the two IO shifts of gen_phys (input max by the largest window, output min by the smallest) leave the
           representative's kit at least as tight: D_p - Wmax and D_p - Wmin of the member <= the representative's, for every port, with
           and without the unlisted-port W_t in the max / min.  A clock.tap_offset row on either type must be identical (offset form:
           no containment).  The window of the representative is its plan's, which is the signed one: the wave credits only a sign-off on
           the representative's current plan block, and the block identity holds the tap window (plan_block_identity).
  kit      the member's kit generated from the rep-window plan (winplan: every member's window rows set to its representative's)
           equals the representative's kit (kit_files), so the window rows are the only plan input in which the two kits differ.
The sign-off of the representative then covers the member: a cross-port pair is timed with the representative's wider window
(hold: launch early -D_i; setup: capture early -D_j), and every IO check of the member's kit is no tighter than the representative's.

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
  windows PLAN --bind-rtl DIR [--all GLOB ...] [--out JSON]
                                                        window containment of every member against its representative; exit 1 when any fails
  winplan PLAN OUT --bind-rtl DIR [--all GLOB ...]       the rep-window plan (each member's tap window rows = its representative's) to
                                                        generate the members' comparison kits from (never a plan of record)
  kitcmp  PLAN --rep TYPE --rep-kit DIR --member TYPE --member-kit DIR [--out JSON]
                                                        generated-kit equality of one pair (files that differ after normalisation); exit 1
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
_INST = re.compile(r"^(\s*)(\w+)(\s*#\s*\()(.*?)(\)\s*\w+\s*\()", re.M | re.S)


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


def hard_modules(t):
    """modules placed as hard cores of a plan type: black boxes of the kit, the only modules whose image string is not logic"""
    return frozenset(str(h.get("module")) for h in t.get("hard_cores") or [] if h.get("module") and h.get("lef") and h.get("lib"))


def rtl_key(text, name, hard=None):
    """hard = the modules whose INSTANCE / VIAMAP strings are masked (hard_modules); None = every module (the 11-19 key)"""
    s = _CMT.sub("", text).replace(name, "@T")
    if hard is None:
        s = _IMG.sub(r".\1(@I)", s)
    else:
        s = _INST.sub(lambda m: m.group(0) if m.group(2) not in hard else
                      m.group(1) + m.group(2) + m.group(3) + _IMG.sub(r".\1(@I)", m.group(4)) + m.group(5), s)
    return CI.sha256_bytes(re.sub(r"\s+", " ", s).strip().encode())


def _rtl(bind_rtl, name):
    try:
        with open(os.path.join(bind_rtl, name + ".sv"), errors="replace") as f:
            return f.read()
    except (OSError, TypeError):
        return None


def groups(plan, bind_rtl, globs=(), strict=False):
    """-> [dict(family, key, layout_key, rtl_key, representative, members)] over the marked types, sorted; the representative is the
    first name of the group, so every host and every tick picks the same one."""
    pt = CI.plan_types(plan)
    by = {}
    for n in marked(pt, globs):
        text = _rtl(bind_rtl, n)
        lk = layout_key(n, pt[n])
        rk = rtl_key(text, n, hard_modules(pt[n]) if strict else None) if text is not None else "no-bound-rtl:" + n
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


# ---------------------------------------------------------------- strict rule: images, kit equality, ROM content
def image_owners(plan, bind_rtl):
    """{image string: [type]} over every type of the plan that has a bound RTL file (a die-wide census: an image named twice is refused)"""
    out = {}
    for n in CI.plan_types(plan):
        text = _rtl(bind_rtl, n)
        for _m, image in (bound_images(text) if text else {}).values():
            out.setdefault(image, []).append(n)
    return out


def image_blockers(plan, bind_rtl, rep, member, owners):
    """why the member's ROM images are not the representative's with another frame: instance / module set, permutation, frame, sharing.
    The bound RTL is the source (a type without param_set takes its images from parameter defaults: param_set alone is blind there)."""
    pt = CI.plan_types(plan)
    a, b = bound_images(_rtl(bind_rtl, member) or ""), bound_images(_rtl(bind_rtl, rep) or "")
    why = []
    if not a:
        why.append("no ROM image instance in the bound RTL")
    if {k: v[0] for k, v in a.items()} != {k: v[0] for k, v in b.items()}:
        why.append("image instances / modules differ from the representative")
    hard = hard_modules(pt[member])
    soft = sorted({v[0] for v in a.values() if v[0] not in hard})
    if soft:
        why.append("image string on module(s) that are not plan hard cores: " + ",".join(soft[:3]))
    tail = lambda x: x.split(".", 1)[1] if "." in x else x
    perm = sorted(k for k in set(a) & set(b) if tail(a[k][1]) != tail(b[k][1]))
    if perm:
        why.append("image permuted at %d instance(s), e.g. %s = %s" % (len(perm), perm[0], a[perm[0]][1]))
    if len({v[1].split(".", 1)[0] for v in a.values()}) > 1:
        why.append("images of more than one frame")
    if len({v[1] for v in a.values()}) != len(a):
        why.append("one image on two instances")
    shared = sorted(v[1] for v in a.values() if [t for t in owners.get(v[1], []) if t != member])
    if shared:
        why.append("image also named by another position: %s (%s)" % (shared[0], owners[shared[0]][0]))
    return why


def load_weights(paths):
    """PASS weight records -> ({viamap file name: sha256}, [errors]).  A record = <dir>/weights.manifest.json (rom_gen weights)
    with a verify-weights result next to it (weights.verify.json, verdict PASS, same manifest sha)."""
    out, err = {}, []
    for p in paths or []:
        raw = open(p, "rb").read()
        man = json.loads(raw)
        vp = os.path.join(os.path.dirname(p), "weights.verify.json")
        try:
            v = json.load(open(vp))
        except (OSError, ValueError):
            err.append("%s: no weights.verify.json" % p)
            continue
        if v.get("verdict") != "PASS" or v.get("manifest_sha256") != CI.sha256_bytes(raw):
            err.append("%s: verify-weights is not PASS on this manifest" % p)
            continue
        if not (man.get("checkpoint") or {}).get("index_sha256_seen"):
            err.append("%s: the images name no checkpoint" % p)
            continue
        for r in man.get("instances") or []:
            out[os.path.basename(str(r.get("viamap")))] = r.get("viamap_sha256")
    return out, err


def member_images(bind_rtl, name, rom_dir):
    """[(image string, [(file, sha256)])] of every image of the bound RTL"""
    names = sorted(os.listdir(rom_dir)) if rom_dir and os.path.isdir(rom_dir) else []
    out = []
    for image in sorted({v[1] for v in bound_images(_rtl(bind_rtl, name) or "").values()}):
        rx = re.compile(r"^%s%s\.viamap\.hex$" % (re.escape(image), CI.IMAGE_SUFFIX))
        out.append((image, [(f, CI.sha256_file(os.path.join(rom_dir, f))) for f in names if rx.match(f)]))
    return out


def content_blockers(images, weights, other_sets):
    """images = member_images; weights = load_weights map; other_sets = content sets (frozenset of sha) of the representative and of the
    members already checked.  A content equal to another position's is refused: the variant would not be a different ROM."""
    why = []
    miss = [i for i, f in images if not f]
    if not images or miss:
        why.append("no via map for %s" % (miss[0] if miss else "any image"))
    bad = [f for _i, files in images for f, sha in files if sha is None or weights.get(f) != sha]
    if bad:
        why.append("%d via map(s) not in a PASS weight record, e.g. %s" % (len(bad), bad[0]))
    cs = frozenset(s for _i, files in images for _f, s in files)
    if cs and cs in other_sets:
        why.append("ROM contents equal another position's (not a different image)")
    return why, cs


def part_names(plan, name):
    parts = plan.get("partitions") or []
    return sorted((str(p.get("name")) for p in (parts if isinstance(parts, list) else parts.values()) if isinstance(p, dict) and p.get("type") == name),
                  key=lambda x: -len(x))


KIT_SKIP_DIRS = {"__pycache__", "run", "bind_sidecars", "geom", "logs", "future_lec"}
# records of WHAT the kit was made from (name / sha / path of other files); the files themselves are compared
KIT_PROV_KEYS = re.compile(r'"(?:[A-Za-z_0-9]*sha256|[A-Za-z_0-9]*_sha|created|generated|mtime|contract|source|src|path|seal|digest)"\s*:\s*"[^"]*"')


def kit_norm(text, name, parts, images, code):
    """a kit file's text with what may differ between two ROM variants removed: RTL comments (code files), own name, the parts placed as
    this type, the type's own image strings, scratch paths, provenance hashes.  Nothing numeric is touched."""
    if code:
        text = _CMT.sub("", text)
    for i in sorted(images, key=lambda x: -len(x)):         # any quoting (".." in RTL, \".\" in a JSON copy of the plan, bare in notes)
        text = re.sub(r"(?<![A-Za-z0-9_.])%s(?![A-Za-z0-9_])" % re.escape(i), "@I", text)
    text = re.sub(r'"note"\s*:\s*"(?:[^"\\]|\\.)*"', '"note": "@N"', text)
    text = text.replace(name, "@T")
    for p in parts:
        text = re.sub(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(p), "@P", text)
    text = KIT_PROV_KEYS.sub(lambda m: m.group(0).split(":", 1)[0] + ': "@H"', text)
    return re.sub(r"/(?:srv|tmp|home)/[^\s\"':,;)\]}]*", "@D", text)


def kit_files(kit, plan, name, images=None):
    """{relative file: sha256 of the normalised bytes} of a generated (not built) kit directory"""
    if images is None:
        images = {CI.unquote(v) for k, v in CI.param_set(CI.plan_types(plan)[name]).items() if CI.IMAGE_PARAM_RE.match(k)}
    parts, out = part_names(plan, name), {}
    for root, ds, fs in os.walk(kit, followlinks=True):
        ds[:] = sorted(x for x in ds if x not in KIT_SKIP_DIRS)
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, kit).replace(name, "@T")
            raw = open(p, "rb").read()
            try:
                raw = kit_norm(raw.decode(), name, parts, images, f.endswith((".sv", ".v", ".svh", ".vh"))).encode()
            except UnicodeDecodeError:
                pass
            out[rel] = CI.sha256_bytes(raw)
    return out


def kit_blockers(kit_rep, kit_mem, plan, rep, member, bind_rtl=None):
    """-> (blockers, kit key, files compared)"""
    for d in (kit_rep, kit_mem):
        if not d or not os.path.isdir(d):
            return ["no generated kit to compare (%s)" % d], None, 0
    im = lambda n: {v[1] for v in bound_images(_rtl(bind_rtl, n) or "").values()} or None
    a, b = kit_files(kit_rep, plan, rep, im(rep)), kit_files(kit_mem, plan, member, im(member))
    if not a or "config.mk" not in b:
        return ["kit directory holds no generated kit (config.mk)"], None, len(b)
    diff = sorted(f for f in set(a) | set(b) if a.get(f) != b.get(f))
    why = ["%d generated kit file(s) differ: %s" % (len(diff), ",".join(diff[:6]))] if diff else []
    return why, CI.jsha(sorted(b.items()))[:16], len(b)


WINDOW_RULES = ("contain",)


def type_windows(plan, name):
    """(W_t, {port: D_p}, tap_offset row) of a type: plan clock.tap_window window_ps / per_type_ps / per_port_ps and clock.tap_offset
    (as gen_phys.tap_window_ps / tap_window_port_table / tap_offset_table read them)"""
    ck = plan.get("clock") or {}
    tw = ck.get("tap_window") or {}
    w = float((tw.get("per_type_ps") or {}).get(name, tw.get("window_ps", 0.0))) if tw else 0.0
    tab = {str(k): float(v) for k, v in (((tw.get("per_port_ps") or {}).get(name) or {}) if tw else {}).items()}
    return w, tab, ((ck.get("tap_offset") or {}).get("per_port_ps") or {}).get(name) or {}


def window_blockers(plan, rep, member):
    """-> (blockers, summary) of the window containment of member in rep (module docstring)"""
    wr, tr, orr = type_windows(plan, rep)
    wm, tm, om = type_windows(plan, member)
    why = []
    if (orr or om) and orr != om:
        why.append("clock.tap_offset rows differ (offset form has no containment rule)")
    ports = sorted(set(tr) | set(tm))
    d = lambda tab, w, p: w if p == "*" else tab.get(p, w)
    over = [p for p in ports + ["*"] if d(tm, wm, p) > d(tr, wr, p)]
    if over:
        why.append("%d window port(s) wider than the representative's: %s" % (len(over), ",".join(
            "%s %g>%g" % ("W_t" if p == "*" else p, d(tm, wm, p), d(tr, wr, p)) for p in over[:6])))
    io = []
    for ps in ([ports, ports + ["*"]] if ports else [["*"]]):
        mx = lambda tab, w: max(d(tab, w, p) for p in ps)
        mn = lambda tab, w: min(d(tab, w, p) for p in ps)
        for p in ps:
            for what, fm, fr in (("input max shift", mx(tm, wm), mx(tr, wr)), ("output min shift", mn(tm, wm), mn(tr, wr))):
                if d(tm, wm, p) - fm > d(tr, wr, p) - fr + 1e-9 and (what, p) not in [x[:2] for x in io]:
                    io.append((what, p, round(d(tm, wm, p) - fm, 3), round(d(tr, wr, p) - fr, 3)))
    if io:
        why.append("%d IO check(s) tighter in the member's kit: %s" % (len(io), ",".join("%s@%s %g>%g" % x for x in io[:4])))
    return why, dict(ports=len(ports), over=len(over), max_excess_ps=max([d(tm, wm, p) - d(tr, wr, p) for p in ports + ["*"]]),
                     io_tighter=len(io))


def rep_window_plan(plan, bind_rtl, globs=()):
    """-> (plan copy whose members carry their representative's window rows, members changed).  Only for generating comparison kits."""
    out = json.loads(json.dumps(plan))
    ck = out.setdefault("clock", {})
    n = 0
    for g in groups(plan, bind_rtl, globs, strict=True):
        for m in g["members"]:
            before = type_windows(out, m)
            for sec, key in (("tap_window", "per_port_ps"), ("tap_window", "per_type_ps"), ("tap_offset", "per_port_ps")):
                tab = (ck.get(sec) or {}).get(key)
                if tab is None:
                    continue
                if g["representative"] in tab:
                    tab[m] = json.loads(json.dumps(tab[g["representative"]]))
                else:
                    tab.pop(m, None)
            n += type_windows(out, m) != before
    return out, n


def window_report(plan, bind_rtl, globs=()):
    rows = []
    for g in groups(plan, bind_rtl, globs, strict=True):
        for m in g["members"]:
            why, sm = window_blockers(plan, g["representative"], m)
            rows.append(dict(member=m, representative=g["representative"], contained=not why, reasons=why, **sm))
    return dict(schema=SCHEMA, rule="contain", members=len(rows), contained=sum(r["contained"] for r in rows), rows=rows)


def records(plan, bind_rtl, repo, rom_dir, rep, signoff, globs=(), lec_policy="advisory", via_policy="advisory", judge=CI.judge_signoff,
            rule="", kits=None, weights=None):
    """col_inherit records (dicts, nothing written) for every member of rep's template group.  The bound RTL text identity (rtl key)
    is the logic proof, so a record carries lec EQUIVALENT by construction with the rtl key.
    rule "strict" (module docstring): kits = {type: generated kit dir}, weights = paths of weights.manifest.json."""
    if rule not in ("", "strict") + WINDOW_RULES:
        raise ValueError("type_template rule %r" % rule)
    strict = rule in ("strict",) + WINDOW_RULES
    g = next((x for x in groups(plan, bind_rtl, globs, strict=strict) if x["representative"] == rep), None)
    if g is None:
        raise KeyError("%s is not the representative of a template group" % rep)
    out = []
    if strict:
        owners, (wmap, werr) = image_owners(plan, bind_rtl), load_weights(weights)
        sets = {frozenset(s for _i, f in member_images(bind_rtl, rep, rom_dir) for _n, s in f)} - {frozenset()}
        own_rep = image_blockers(plan, bind_rtl, rep, rep, owners)
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
        if strict:
            why = ["representative: " + w for w in own_rep] + image_blockers(plan, bind_rtl, rep, m, owners)
            kw, key, nf = kit_blockers((kits or {}).get(rep), (kits or {}).get(m), plan, rep, m, bind_rtl)
            ww, wsum = (window_blockers(plan, rep, m) if rule in WINDOW_RULES else ([], None))
            kr, km = (kits or {}).get(rep), (kits or {}).get(m)
            if rule in WINDOW_RULES and kr and km and os.path.realpath(kr) == os.path.realpath(km):
                ww = ww + ["member kit is the representative's kit directory"]
            kw = kw + ww
            cw, cs = content_blockers(member_images(bind_rtl, m, rom_dir), wmap, sets)
            sets.add(cs)
            rec["credit_blockers"] = rec["credit_blockers"] + why + kw + werr + cw
            rec["credit"] = not rec["credit_blockers"]
            if wsum is not None:
                rec.update(window_check=not ww, windows=wsum)
            rec.update(rule=rule, kit_key=key, kit_files_compared=nf, image_check=not why, content_check=not (werr + cw),
                       images=len(bound_images(_rtl(bind_rtl, m) or "")), plan_sha256=CI.jsha(plan))
        out.append(rec)
    return out


def credit(plan, bind_rtl, repo, rom_dir, rep, signoff, out_dir, members_tsv=None, globs=(), lec_policy="advisory", via_policy="advisory",
           judge=CI.judge_signoff, rule="", kits=None, weights=None):
    """records() written as <out>/<member>/inherited.json (+ inherit_members.tsv rows for the credited ones).
    -> [(member, record path, credit)]"""
    res = []
    for rec in records(plan, bind_rtl, repo, rom_dir, rep, signoff, globs, lec_policy, via_policy, judge, rule, kits, weights):
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
            s.add_argument("--rule", default="", choices=("", "strict") + WINDOW_RULES); s.add_argument("--kits", help="JSON {type: generated kit dir}")
            s.add_argument("--weights", nargs="*", default=[])
    k = sub.add_parser("kitcmp"); k.add_argument("plan"); k.add_argument("--bind-rtl"); k.add_argument("--out")
    for x in ("rep", "rep-kit", "member", "member-kit"):
        k.add_argument("--" + x, required=True)
    w = sub.add_parser("windows"); w.add_argument("plan"); w.add_argument("--bind-rtl", required=True); w.add_argument("--all", nargs="*", default=[])
    w.add_argument("--out")
    w = sub.add_parser("winplan"); w.add_argument("plan"); w.add_argument("out"); w.add_argument("--bind-rtl", required=True)
    w.add_argument("--all", nargs="*", default=[])
    f = sub.add_parser("flag"); f.add_argument("plan"); f.add_argument("out"); f.add_argument("globs", nargs="+")
    v = sub.add_parser("view")
    for k in ("rep", "member", "lef", "lib", "out"):
        v.add_argument("--" + k, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "view":
        print("\n".join(clone_view(a.rep, a.member, a.lef, a.lib, a.out)))
        return 0
    plan = json.load(open(a.plan))
    if a.cmd == "kitcmp":
        why, key, nf = kit_blockers(a.rep_kit, a.member_kit, plan, a.rep, a.member, a.bind_rtl)
        print("TYPE_TEMPLATE kitcmp %s vs %s: %d file(s), %s" % (a.member, a.rep, nf, "; ".join(why) or "EQUAL key %s" % key))
        if a.out:
            with open(a.out, "w") as fo:
                json.dump(dict(rep=a.rep, member=a.member, equal=not why, reasons=why, kit_key=key, files=nf), fo, indent=1)
        return 1 if why else 0
    if a.cmd == "windows":
        r = window_report(plan, a.bind_rtl, a.all)
        if a.out:
            with open(a.out, "w") as fo:
                json.dump(r, fo, indent=1)
        print("TYPE_TEMPLATE windows: %d member(s), %d contained" % (r["members"], r["contained"]))
        for row in r["rows"][:20]:
            if not row["contained"]:
                print("  NOT-CONTAINED %s in %s: %s" % (row["member"], row["representative"], "; ".join(row["reasons"])))
        return 0 if r["contained"] == r["members"] else 1
    if a.cmd == "winplan":
        out, n = rep_window_plan(plan, a.bind_rtl, a.all)
        with open(a.out + ".tmp", "w") as fo:
            json.dump(out, fo, indent=1)
            fo.write("\n")
        os.replace(a.out + ".tmp", a.out)
        print("TYPE_TEMPLATE winplan: %d member(s) given their representative's window rows" % n)
        return 0
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
    res = credit(plan, a.bind_rtl, a.repo, a.rom_dir, a.rep, a.signoff, a.out, a.members_tsv, a.all, a.lec_policy, a.via_policy,
                 rule=a.rule, kits=json.load(open(a.kits)) if a.kits else None, weights=a.weights)
    for m, p, c in res:
        print("%s\t%s\t%s" % ("CREDIT" if c else "NO-CREDIT", m, p))
    return 0 if all(c for _m, _p, c in res) else 1


if __name__ == "__main__":
    sys.exit(main())
