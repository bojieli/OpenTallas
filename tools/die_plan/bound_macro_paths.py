"""Physical instance paths of a bound kit's placed macros (KW-FIX-1/S81PF 11-02, default on).

bind.py flattens each plan content into the bound partition module: the as-built leaf `<root>.u_r0.u_bn0` becomes the
bound instance `u_u_r0_u_bn0` (comment `// as-built <path>` above it), and the kit wrapper instantiates the bound module
as `u_bound`.  A plan hard core / macro content still names its plan path (`u_r0.u_bn0`, `u_lf.u_ve.u_m`), so the kit
placed macros by names that do not exist in the kit RTL (KIT_PREFLIGHT macro_instances, 42 S81 kit-wave items).

This module derives the bound path of each such macro from the kit's own bound RTL and declares it as the existing
kit-only physical identity (physical_inst / physical_master, gen_phys.content_physical_identity) in a projected copy
of the plan.  The plan of record, logical identities, geometry, pins, clocks and cycles are unchanged.  A macro that
does not map exactly (no unique content root, or a different module at the full path) keeps its plan name, so the
preflight still reports it.
"""
import copy
import json
import re
from pathlib import Path

SCHEMA = "opentallas.die_plan.bound_macro_paths.v1"
RECEIPT = "bound_macro_paths.json"
_ASBUILT = re.compile(r"(?m)^[ \t]*// as-built ([^\s]+)[ \t]*\n[ \t]*(\w+)(?:[ \t]*#\(.*?\))?[ \t]+(\w+)[ \t]*\(", re.S)


def asbuilt_map(bound_text):
    """{as-built hierarchical path: (bound instance name, module)} from the bind's `// as-built` comments."""
    out = {}
    for m in _ASBUILT.finditer(bound_text):
        out.setdefault(m.group(1), (m.group(3), m.group(2)))
    return out


def _macro_entries(t):
    """plan entries the kit places by instance name: hard_cores[] with a lef, contents[] with a lef (not a core)."""
    cores = [c for c in t.get("hard_cores", []) or [] if c.get("lef")]
    names = {c["inst"] for c in t.get("hard_cores", []) or []}
    return cores + [c for c in t.get("contents", []) or [] if c.get("lef") and c["inst"] not in names]


def resolve(t, bound_text):
    """[{inst, physical_inst, physical_master, asbuilt}] for the plan type t's placed macros that carry no physical
    identity and whose plan path maps to the bound netlist.  A content root (plan content inst -> as-built prefix) is
    accepted only when every mapped macro under it agrees on one prefix."""
    rows = _resolve_flat(t, bound_text)
    ab = asbuilt_map(bound_text)
    if not ab:
        return rows
    todo = [c for c in _macro_entries(t)
            if "physical_inst" not in c and "physical_master" not in c and not c["inst"].startswith("u_bound.")
            and "." in c["inst"]]
    groups = {}
    for c in todo:
        head, rest = c["inst"].split(".", 1)
        groups.setdefault(head, []).append((c, rest.split(".")))
    for head, members in sorted(groups.items()):
        # prefix candidates per macro: an as-built path ending in a leading run of its plan components below the root
        common = None
        for c, rest in members:
            cand = set()
            for j in range(len(rest), 0, -1):
                tail = "." + ".".join(rest[:j])
                cand |= {a[:-len(tail)] for a in ab if a.endswith(tail) and len(a) > len(tail)}
            if cand:                               # a macro with no as-built match stays unmapped, never vetoes
                common = cand if common is None else common & cand
        if common is None:
            # S81 bk_sel__t2: the content is bound whole (as-built u_bk_sel = bound u_core), so nothing below it is
            # in the as-built map and the macros sit under that one instance.  Same module as the plan content only.
            whole = ab.get(head)
            module = next((x.get("module") for x in t.get("contents", []) or [] if x.get("inst") == head), None)
            if whole and whole[1] == module:
                rows.extend(dict(inst=c["inst"], physical_inst="u_bound." + whole[0] + "." + ".".join(rest),
                                 physical_master=c["module"], asbuilt=head) for c, rest in members)
                continue
            # KW-FIX-17 11-05 (S81 serdes, I138 u_phy -> u_core): the plan path already names the BOUND instance
            # (u_core.u_dec.u_chn, bound u_core = as-built u_lk_ES1 bound whole), only the kit wrapper's u_bound is
            # missing.  Exactly one bound leaf of that name and no as-built path of that name; preflight still checks
            # the full path and the leaf module.
            named = [a for a, v in ab.items() if v[0] == head]
            if whole is None and len(named) == 1:
                rows.extend(dict(inst=c["inst"], physical_inst="u_bound." + c["inst"], physical_master=c["module"],
                                 asbuilt=named[0]) for c, rest in members)
            continue
        if len(common) != 1:
            rows.extend(_resolve_scoped(members, ab))
            continue
        root = next(iter(common))
        for c, rest in members:
            for j in range(len(rest), 0, -1):
                hit = ab.get(root + "." + ".".join(rest[:j]))
                if hit is None:
                    continue
                inst, mod = hit
                if j == len(rest) and mod != c.get("module"):
                    hit = None                     # same path, different module: not this macro
                break
            if hit is None:
                continue
            phys = "u_bound." + inst + ("." + ".".join(rest[j:]) if j < len(rest) else "")
            rows.append(dict(inst=c["inst"], physical_inst=phys, physical_master=c["module"],
                             asbuilt=root + "." + ".".join(rest[:j])))
    return rows


def resolve_sub_cores(t, bound_text, sub_core_leaf, variants=None):
    """Root explicit split-core paths through the producer's exact parent-to-leaf table.

    The remaining subpath and master are preserved for kit_preflight to validate;
    a table entry never makes a missing split implementation a legal macro.
    """
    ab = asbuilt_map(bound_text)
    rows = []
    for c in _macro_entries(t):
        path = c.get("physical_inst") or ""
        if ".u_fcore." not in path or path.startswith("u_bound."):
            continue
        parent, tail = path.split(".u_fcore.", 1)
        leaf = sub_core_leaf.get(parent)
        # DIE-HBM-92-PHY 11-08: a physical variant type binds the same plan content from another as-built leaf
        # (HBM NE_spb0 = q_spb0__physical_v1: plan u_lk_S0 is as-built lk_S3).  The producer declares those
        # alternates in asbuilt.sub_core_leaf_variants; exactly one declared leaf must be in this bound file.
        found = [x for x in ([leaf] + list((variants or {}).get(parent, []))) if x and x in ab] if leaf else []
        if len(found) != 1:
            continue
        leaf = found[0]
        hit = ab[leaf]
        rows.append(dict(inst=c["inst"], physical_inst="u_bound." + hit[0] + ".u_fcore." + tail,
                         physical_master=c["physical_master"], asbuilt=leaf, source_physical_inst=path,
                         source_parent=c.get("sub_core_parent", parent)))
    return rows


def resolve_hard_core_leaf(t, bound_text, table):
    """DIE-HBM-92-SU 11-08: a plan hard core without a physical path that the bind regroups inside one composed cut
    (asbuilt.compose_split, e.g. HBM u_su_Q2_pretree = ot_hbm_su_static_pgslice_lg__pretree inside as-built
    su_NE2.__cut_pretree).  Exact producer table {plan inst: {"leaves": [as-built cut, ...], "inner": instance in the
    cut}}; exactly one listed leaf must be in this bound file.  kit_preflight still checks the path and the master."""
    ab = asbuilt_map(bound_text)
    rows = []
    for c in _macro_entries(t):
        e = (table or {}).get(c["inst"])
        if not e or c.get("physical_inst"):
            continue
        found = [x for x in e.get("leaves", []) if x in ab]
        if len(found) != 1:
            continue
        rows.append(dict(inst=c["inst"], physical_inst="u_bound." + ab[found[0]][0] + "." + e["inner"],
                         physical_master=c["module"], asbuilt=found[0]))
    return rows


def _strip_scope(prefix):
    """as-built prefix without its trailing generate blocks: u_s_3S.u_sl.g_c3 -> u_s_3S.u_sl."""
    parts = prefix.split(".")
    while parts and re.fullmatch(r"g_\w+", parts[-1]):
        parts.pop()
    return ".".join(parts)


def _resolve_scoped(members, ab):
    """DIE-S81-56/IQKV 11-04: siblings of one content root where some sit under a generate block of that root (slice_w3:
    u_sl.u_cap, u_sl.g_c3.u_xr), so no single prefix fits.  Exact-module full-path hits must all reduce to one root; a macro
    without exactly one such hit gets no row, and preflight reports it."""
    cands = []
    for c, rest in members:
        tail = "." + ".".join(rest)
        cands.append([a for a in ab if a.endswith(tail) and len(a) > len(tail) and ab[a][1] == c.get("module")])
    roots = {_strip_scope(a[:-len("." + ".".join(rest))]) for (c, rest), hits in zip(members, cands) for a in hits}
    if len(roots) != 1:
        return []
    rows = []
    for (c, rest), hits in zip(members, cands):
        if len(hits) == 1:
            rows.append(dict(inst=c["inst"], physical_inst="u_bound." + ab[hits[0]][0], physical_master=c["module"],
                             asbuilt=hits[0]))
    return rows


def _sv_id(s):
    """bind.sv_id: the bound netlist identifier of a plan name."""
    s = re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", s)).strip("_")
    return s if s and not s[0].isdigit() else "n" + s


def _resolve_flat(t, bound_text):
    """DIE-QC-68/TYPES 11-04: a flat plan core name (QC u_lane0, u_t22, u_suvm_u_vm8q_u_bt) is one bound leaf `<inst>` or
    `u_<inst>` of that exact module, inside the kit wrapper's u_bound.  No exact unique leaf: no row (preflight reports)."""
    rows = []
    for c in _macro_entries(t):
        inst = c["inst"]
        if "physical_inst" in c or "physical_master" in c or "." in inst:
            continue
        # DIE-HBM-92-SU-IDX 11-08: the bind names a leaf u_<sv_id(inst)> (runs of _ folded: HBM u_hb_idx__s_Q2_r0c0_k0h1
        # -> u_u_hb_idx_s_Q2_r0c0_k0h1)
        hits = [name for name in dict.fromkeys((inst, "u_" + inst, "u_" + _sv_id(inst)))
                if re.search(r"(?m)^[ \t]+" + re.escape(c.get("module", inst)) + r"(?:[ \t]+#\(.*?\))?[ \t]+"
                             + re.escape(name) + r"[ \t]*\(", bound_text)]
        if len(hits) == 1:
            rows.append(dict(inst=inst, physical_inst="u_bound." + hits[0], physical_master=c.get("module", inst),
                             asbuilt=None))
    return rows


def _bound_file(filelist):
    kj = Path(filelist).with_name("kit_rtl.json")
    if not kj.is_file():
        return None
    bmod = json.loads(kj.read_text()).get("bound_module")
    if not bmod:
        return None
    files = [Path(x) for x in Path(filelist).read_text().split() if x and not x.startswith(("+", "-"))]
    return next((f for f in files if f.name == f"{bmod}.sv" and f.is_file()), None)


def project(raw, kit_rtl):
    """(plan copy with the derived physical identities, {type: rows}); raw itself when nothing maps."""
    result, receipts = raw, {}
    for tn, fl in sorted((kit_rtl or {}).items()):
        t = raw["partition_types"].get(tn)
        bf = _bound_file(fl) if t else None
        if bf is None:
            continue
        bound_text = bf.read_text(errors="replace")
        rows = resolve(t, bound_text)
        kr = json.loads(Path(fl).with_name("kit_rtl.json").read_text())
        manifest = kr.get("asbuilt_manifest")
        man = (json.loads(Path(manifest).read_text())
               if manifest and Path(manifest).is_file() and any(
                   ".u_fcore." in (c.get("physical_inst") or "") or not c.get("physical_inst")
                   for c in _macro_entries(t)) else {})
        rows += resolve_sub_cores(t, bound_text, man.get("sub_core_leaf", {}), man.get("sub_core_leaf_variants", {}))
        rows += resolve_hard_core_leaf(t, bound_text, man.get("hard_core_leaf", {}))
        if not rows:
            continue
        if result is raw:
            result = copy.deepcopy(raw)
        by = {r["inst"]: r for r in rows}
        nt = result["partition_types"][tn]
        for c in nt.get("hard_cores", []) + nt.get("contents", []):
            r = by.get(c["inst"])
            if r and c.get("lef") and ("physical_inst" not in c or
                    r.get("source_physical_inst") == c.get("physical_inst")):
                c["physical_inst"], c["physical_master"] = r["physical_inst"], r["physical_master"]
                if r.get("source_parent"):
                    c.setdefault("sub_core_parent", r["source_parent"])
        receipts[tn] = dict(schema=SCHEMA, type=tn, bound_rtl=str(bf), rows=rows,
                            rule="plan macro path -> bound netlist path from the bind's as-built comments; "
                                 "logical identity, geometry, pins and clocks unchanged")
    return result, receipts


def placed_paths(t):
    """[(placed instance path, master)] the kit's macro_place.tcl names for plan type t (gen_phys.type_macros order and
    identity rules, no view resolution): hard_cores with a lef, contents physical_parts, contents with a lef."""
    out, cores = [], {c["inst"] for c in t.get("hard_cores", []) or []}
    for c in t.get("hard_cores", []) or []:
        if c.get("lef"):
            out.append((c.get("physical_inst", c["inst"]), c.get("physical_master", c.get("module", c["inst"]))))
    for c in t.get("contents", []) or []:
        for q in c.get("physical_parts", []) or []:
            out.append((q["physical_inst"], q["physical_master"]))
        if c.get("lef") and c["inst"] not in cores:
            out.append((c.get("physical_inst", c["inst"]), c.get("physical_master", c.get("module"))))
    return out


def _words(text):
    """identifier tokens of Verilog text outside comments (escaped names split at their . and [ ])."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", " ", text, flags=re.S)
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_$]*", text))


def unplaceable(tn, t, top_text, bound_text=None, source="kit source"):
    """T51-INST 11-10 (DIE-S81-85 sub-lane, class: plan hard core inst names a module the kit source never instantiates;
    S81 slice_station__t51 native_w/_e placed by module name over the unsplit bound station, KIT_PREFLIGHT
    macro_instances FAIL at 19:07 after a full kit-gen).  Gen-time refusal for the CERTAIN cases only: the first path
    component is no identifier of the kit top text at all, or the component below u_bound is no identifier of the
    bound module.  Anything that might resolve (generate blocks, escaped flat names, deeper levels) is left to
    kit_contract.macro_instances, which stays the full check.  -> [error]"""
    top_w = _words(top_text)
    bound_w = _words(bound_text) if bound_text is not None else None
    err = []
    for path, master in placed_paths(t):
        parts = path.split(".")
        head = re.sub(r"(\[[^\]]*\])+$", "", parts[0]).lstrip("\\")
        bad = None
        if head not in top_w:
            bad = head
        elif head == "u_bound" and len(parts) > 1 and bound_w is not None:
            sub = re.sub(r"(\[[^\]]*\])+$", "", parts[1]).lstrip("\\")
            if sub not in bound_w:
                bad = "u_bound." + sub
        if bad is None:
            continue
        hint = (" (the plan inst is the module name: the kit source has no instance of that module, e.g. a split"
                " that exists only as a side netlist; bind the split or give the type a kit netlist source)"
                if path.split(".")[-1] == master else "")
        err.append(f"type {tn}: placed macro {path} ({master}): {bad!r} is not an instance in the {source}; a plan "
                   f"hard_cores/contents inst must be the kit netlist path (u_bound.<bound leaf>){hint}")
    return err


def overlay(kd, entries):
    """kit_contract._plan_contents helper: add {physical_inst: entry} for the kit's receipt rows (no-op without one)."""
    p = Path(kd) / RECEIPT
    if not p.is_file():
        return entries
    for r in json.loads(p.read_text()).get("rows", []):
        e = entries.get(r["inst"]) or entries.get(r.get("source_physical_inst"))
        if e is not None and r["physical_inst"] not in entries:
            entries[r["physical_inst"]] = dict(e, inst=r["physical_inst"], module=r["physical_master"])
    return entries
