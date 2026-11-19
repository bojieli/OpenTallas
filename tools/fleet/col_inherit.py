#!/usr/bin/env python3
"""S81-COL-INHERIT (OWNER via COORD 2026-11-14): sibling pv identities of an S81 col frame inherit the sign-off of ONE built
representative per (family, clock class) layout.

Why it is sound: the pv identities of one (family, clock class) differ only in P_*_INSTANCE strings, i.e. which per-instance
via map (<INSTANCE>.viamap.hex, tools/mem_compiler/rom_gen.py personalise) a generated ot_rom_4096x72_m8 / elem ROM hard core
carries.  The ROM macro's LEF and Liberty are content-independent (rom_gen: "characterised with every via present"), and no
standard cell logic derives from INSTANCE.  The tool proves each premise per sibling instead of assuming it:

  groups  PLAN                        -> JSON: layouts, representatives candidates, siblings, singletons (groups that fail
                                         the layout checks are excluded, with the reason)
  record  --plan P --rep R --sibling S --signoff signoff.json --repo SRC --rom-dir DIR --out DIR [--netlist N --sibling-rtl F...]
                                      -> <out>/<sibling>/inherited.json (schema opentallas.col_inherit.v1)
  archive --records DIR... --rtx-root R --agi-root A [--agi-ssh "ssh -i ..."] [--dry-run]
                                      -> a new dir per record on rtx-pro and AGIdock, append-only INDEX.tsv row

A record credits the sibling (credit true) only when ALL hold: the representative's signoff.json passes the R-MINIMAL gates
(DRC 0, TT setup >= -42 ps, internal FF hold >= 0; tools/die_plan/signoff_profile.judge); one hard-core signature and one
geometry/clock key across the layout; every differing parameter is a *_INSTANCE image selector; every ROM image of the sibling
(including the elem cores' inner ROMs) exists with a sha; each hard-core macro's LEF and Liberty sha equal the representative's;
via-mask DRC on the swapped image is not FAIL; the LEC of the sibling RTL against the representative's netlist (ROM instances
re-parameterised to the sibling's images) is EQUIVALENT.  `--lec-policy advisory` / `--via-policy advisory` accept NOT_RUN or
UNPROVEN (never NOT_EQUIVALENT / FAIL).  The counter (tools/fleet/release_tree_plan.py inherit_credit) reads these records.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

SCHEMA = "opentallas.col_inherit.v1"
IDENT_RE = re.compile(r"^(col_h(?:9|10)_r[012](?:_p\d+)?)__t1(?:__(cl[0-9a-f]+))?(?:__pv([0-9a-f]+))?$")   # r0 frames carry _p<n> and may have no clock-class label
IMAGE_PARAM_RE = re.compile(r"^P_.*_INSTANCE$")
PV_LABEL_RE = re.compile(r"[A-Za-z0-9_.]*__pv[0-9a-f]{6,}[A-Za-z0-9_.]*")
CL_LABEL_RE = re.compile(r"__cl[0-9a-f]{6,}")   # clock-class label (S81-TYPEMERGE R1: the layout hash ignores it)
# viamap names of one INSTANCE (rom_gen personalise; elem cores take <I>_0/_1, the second bank <I>b..., head bundles <I>a<n>)
IMAGE_SUFFIX = r"(?:b|a\d+)?(?:_[01])?"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(p):
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        return h.hexdigest()
    except OSError:
        return None


def jsha(o):
    return sha256_bytes(json.dumps(o, sort_keys=True, separators=(",", ":")).encode())


def unquote(v):
    v = str(v).strip()
    return v[1:-1] if len(v) >= 2 and v[0] == v[-1] == '"' else v


# ---------------------------------------------------------------- plan side
def plan_types(plan):
    return plan["partition_types"] if "partition_types" in plan else plan


def hard_core_signature(t, repo=None):
    """sorted (inst, module, lef, lib, origin, orient[, lef sha, lib sha]) of a type's hard cores"""
    out = []
    for h in t.get("hard_cores") or []:
        row = [h.get("inst"), h.get("module"), h.get("lef"), h.get("lib"), list(h.get("origin_um") or []), h.get("orient")]
        if repo is not None:
            row += [sha256_file(os.path.join(repo, h["lef"])) if h.get("lef") else None,
                    sha256_file(os.path.join(repo, h["lib"])) if h.get("lib") else None]
        out.append(row)
    return sorted(out, key=lambda r: (str(r[0]), str(r[1])))


def geometry_key(t):
    """layout identity: outline, buses, ft slots, internal stations, reset, contents (inst, module), sources, hard flag"""
    return jsha(dict(o=t.get("outline_um"), b=t.get("buses"), f=t.get("ft_slots"), s=t.get("internal_stations"),
                     r=t.get("reset"), c=[(c.get("inst"), c.get("module")) for c in t.get("contents") or []],
                     src=t.get("sources"), hard=t.get("hard")))


def clock_key(t, merge_classes=False):
    """clock identity with the per-type __pv<hash> labels removed (collector_tree.type carries the identity name);
    merge_classes also removes the __cl<hash> label, so classes with the same layout share one key"""
    s = PV_LABEL_RE.sub("<PV>", json.dumps(t.get("clock"), sort_keys=True))
    if merge_classes:
        s = CL_LABEL_RE.sub("", s)
    return sha256_bytes(s.encode())


def param_set(t):
    return dict(t.get("param_set") or {})


def param_set_sha(t):
    return jsha(param_set(t))


def parse_identity(name):
    m = IDENT_RE.match(name)
    return None if not m else dict(family=m.group(1), clock_class=m.group(2), pv=m.group(3))


def groups(plan, repo=None, merge_classes=False):
    """{(family, cl): dict(members=[names with ROM params], singletons=[names without], verdict=..., reasons=[...], keys...)}.
    A (family, clock class) whose pv identities carry different clock / reset-collector contracts (clock key with the __pv labels
    stripped) is split into one sub-layout per clock key, keyed (family, '<cl>/ck<8 hex>'): inheritance never crosses a clock key.
    merge_classes=True (S81-TYPEMERGE R1, sign-off key = layout hash): the clock class label is not part of the key; one group per
    (family, clock key), keyed (family, 'ck<8 hex>'); the geometry / hard-core checks below still run over the whole group."""
    pt = plan_types(plan)
    raw = {}
    for n, t in pt.items():
        p = parse_identity(n)
        if p:
            raw.setdefault((p["family"], "" if merge_classes else (p["clock_class"] or "")), []).append(n)
    out = {}
    for k0, allnames in sorted(raw.items()):
        byclk = {}
        for n in allnames:
            byclk.setdefault(clock_key(pt[n], merge_classes), []).append(n)
        for ck, names in sorted(byclk.items(), key=lambda kv: min(kv[1])):
            k = k0 if len(byclk) == 1 and not merge_classes else (k0[0], ("%s/ck%s" % (k0[1], ck[:8])).lstrip("/"))
            members = [n for n in names if param_set(pt[n])]
            singles = [n for n in names if not param_set(pt[n])]
            g = dict(family=k[0], clock_class=k[1], members=sorted(members), singletons=sorted(singles), reasons=[],
                     clock_split=len(byclk) > 1)
            sig = {jsha(hard_core_signature(pt[n])) for n in names}
            geo = {geometry_key(pt[n]) for n in names}
            if len(sig) != 1:
                g["reasons"].append("hard-core signature differs across the layout (%d)" % len(sig))
            if len(geo) != 1:
                g["reasons"].append("geometry key differs across the layout (%d)" % len(geo))
            if members:
                names_p = [set(param_set(pt[n])) for n in members]
                if any(s != names_p[0] for s in names_p):
                    g["reasons"].append("param key sets differ")
                bad = sorted(x for x in names_p[0] if not IMAGE_PARAM_RE.match(x))
                if bad:
                    g["reasons"].append("non-image parameters %s" % ",".join(bad[:5]))
                for n in members:
                    for pk, pv in param_set(pt[n]).items():
                        if IMAGE_PARAM_RE.match(pk) and not str(pv).strip().startswith('"'):
                            g["reasons"].append("%s %s is not a string image selector" % (n, pk)); break
                if len({param_set_sha(pt[n]) for n in members}) != len(members):
                    g["reasons"].append("two members carry the same parameter set (one identity?)")
            g["layout_key"] = "%s|%s|%s|%s" % (k[0], k[1], next(iter(geo))[:12], ck[:12])
            g["verdict"] = "OK" if not g["reasons"] else "EXCLUDED"
            out[k] = g
    return out


def group_of(plan, *names):
    """the layout group that holds every given identity, else None"""
    for g in groups(plan).values():
        allm = set(g["members"]) | set(g["singletons"])
        if all(n in allm for n in names):
            return g
    return None


def macro_views(t, repo):
    """per hard-core module: lef/lib path + sha (one module = one view set; instances listed)"""
    out = {}
    for h in t.get("hard_cores") or []:
        m = out.setdefault(h["module"], dict(module=h["module"], lef=h.get("lef"), lib=h.get("lib"), instances=[],
                                             lef_sha=sha256_file(os.path.join(repo, h["lef"])) if h.get("lef") else None,
                                             lib_sha=sha256_file(os.path.join(repo, h["lib"])) if h.get("lib") else None))
        m["instances"].append(h.get("inst"))
    return out


def rom_images(t, rom_dir):
    """ROM image list: for each *_INSTANCE param the viamap files of that INSTANCE (plain, _0/_1 inner ROMs of elem cores,
    second bank 'b', head-bundle 'a<n>') with a sha each.  -> [dict(param, instance, files=[dict(name, sha256)] )]"""
    names = sorted(os.listdir(rom_dir)) if rom_dir and os.path.isdir(rom_dir) else []
    out = []
    for pk, pv in sorted(param_set(t).items()):
        if not IMAGE_PARAM_RE.match(pk):
            continue
        inst = unquote(pv)
        rx = re.compile(r"^%s%s\.viamap\.hex$" % (re.escape(inst), IMAGE_SUFFIX))
        files = [dict(name=n, sha256=sha256_file(os.path.join(rom_dir, n))) for n in names if rx.match(n)]
        out.append(dict(param=pk, instance=inst, files=files))
    return out


# ------------------------------------------------------------------- LEC
def rewrite_instances(text, rep_params, sib_params):
    """swap every representative INSTANCE string in a netlist / RTL text for the sibling's (quoted string occurrences only)"""
    n = 0
    for pk, rv in rep_params.items():
        if not IMAGE_PARAM_RE.match(pk) or pk not in sib_params:
            continue
        a, b = unquote(rv), unquote(sib_params[pk])
        if a != b:
            n += text.count('"%s"' % a)
            text = text.replace('"%s"' % a, '"%s"' % b)
    return text, n


BB_MOD_RE = re.compile(r"module\s+(\w+)\s*(?:#\s*\((?P<par>.*?)\))?\s*\((?P<ports>.*?)\)\s*;", re.S)
BB_PORT_RE = re.compile(r"(input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?(\w+)")


def standin_verilog(bb_text):
    """uninterpreted stand-in for each ANSI-style black-box module: every output is a fixed mixing function of all inputs, so a
    hard core is the SAME logic in gold and gate and the proof covers everything around it (ROM content is not logic here)."""
    out = []
    for m in BB_MOD_RE.finditer(bb_text):
        ins, outs = [], []
        for d, hi, lo, n in BB_PORT_RE.findall(m.group("ports")):
            w = abs(int(hi) - int(lo)) + 1 if hi != "" else 1
            (outs if d == "output" else ins).append((n, w))
        if not outs:
            continue
        ports = ", ".join("%s %s%s" % (d, "[%d:0] " % (w - 1) if w > 1 else "", n) for d, lst in (("input", ins), ("output", outs)) for n, w in lst)
        par = ("#(%s) " % m.group("par").strip()) if m.group("par") else ""
        allv = "{%s}" % ", ".join(n for n, _ in ins) if ins else "1'b0"
        body = ["module %s %s(%s);" % (m.group(1), par, ports), "  localparam IW = %d;" % max(1, sum(w for _, w in ins)),
                "  wire [IW-1:0] x = %s;" % allv]
        for i, (n, w) in enumerate(outs):
            body.append("  wire [%d:0] pad%d = {{%d{1'b0}}, x};" % (w + sum(w2 for _, w2 in ins) - 1, i, w))
            body.append("  assign %s = {%d{^x}} ^ pad%d[%d:0] ^ %d'd%d;" % (n, w, i, w - 1, w, i))
        body.append("endmodule")
        out.append("\n".join(body))
    return "\n".join(out) + "\n"


def lec_script(gold_files, gate_netlist, top_gold, top_gate, standins, sib_params):
    """yosys script: gold = sibling RTL (parameters chparam'd to the sibling's images), gate = representative netlist with its ROM
    instances re-parameterised to the sibling's images; hard cores are the uninterpreted stand-ins (standin_verilog files);
    sequential equivalence by induction (equiv_make matches wires by name, so register names must agree: lec.py rule)."""
    q = shlex.quote
    bb = ["read_verilog -sv -defer " + q(f) for f in standins]
    prep = "proc; flatten; opt_clean; async2sync"
    s = bb + ["read_verilog -sv -defer " + q(f) for f in gold_files]
    s += ["chparam -set %s %s %s" % (k, v if v.startswith('"') else '"%s"' % v, top_gold) for k, v in sorted(sib_params.items())]   # before hierarchy: yosys derives the instances from the new value; "text" is unquoted by the shell
    s += ["hierarchy -top " + top_gold, prep, "design -stash gold", "design -reset"]
    s += bb + ["read_verilog -sv -defer " + q(gate_netlist), "hierarchy -top " + top_gate, prep, "design -stash gate", "design -reset",
               "design -copy-from gold -as gold " + top_gold, "design -copy-from gate -as gate " + top_gate,
               "equiv_make gold gate equiv", "hierarchy -top equiv", "equiv_simple -seq 5", "equiv_induct -seq 5", "equiv_status -assert"]
    return "\n".join(s) + "\n"


def run_lec(script, work, yosys="yosys", timeout=3600):
    pathlib.Path(work).mkdir(parents=True, exist_ok=True)
    ys = pathlib.Path(work) / "lec.ys"
    ys.write_text(script)
    try:
        p = subprocess.run([yosys, "-q", "-l", str(pathlib.Path(work) / "lec.log"), str(ys)], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return dict(verdict="NOT_RUN", reason="yosys not found")
    except subprocess.TimeoutExpired:
        return dict(verdict="UNPROVEN", reason="timeout %ss" % timeout)
    log = (pathlib.Path(work) / "lec.log").read_text() if (pathlib.Path(work) / "lec.log").exists() else p.stdout
    if p.returncode == 0:
        return dict(verdict="EQUIVALENT", log_sha256=sha256_bytes(log.encode()))
    if re.search(r"Found \d+ unproven|unproven", log) and "failed" not in log.lower().split("equiv_status")[-1]:
        return dict(verdict="UNPROVEN", reason=log[-300:], log_sha256=sha256_bytes(log.encode()))
    if "ERROR" in log and "equiv" not in log.split("ERROR")[0][-200:]:
        return dict(verdict="ERROR", reason=log[-300:])
    return dict(verdict="NOT_EQUIVALENT", reason=log[-300:], log_sha256=sha256_bytes(log.encode()))


def via_mask_drc(images, gds=None, cmd=None):
    """via-mask DRC of the swapped image on the ROM macro GDS.  The repo carries LEF/Liberty abstracts only (rom_gen writes no GDS),
    so without --rom-gds and --via-drc-cmd the result is NOT_RUN with that reason.  cmd gets env OT_ROM_GDS, OT_VIAMAP_HEX."""
    if not gds or not cmd:
        return dict(verdict="NOT_RUN", reason="no ROM macro GDS / via-mask DRC command supplied (repo has abstracts only)")
    res = []
    for im in images:
        for f in im["files"]:
            env = dict(os.environ, OT_ROM_GDS=gds, OT_VIAMAP_HEX=f["name"])
            p = subprocess.run(shlex.split(cmd), env=env, capture_output=True, text=True)
            res.append(dict(file=f["name"], rc=p.returncode, tail=(p.stdout + p.stderr)[-160:]))
    return dict(verdict="PASS" if all(r["rc"] == 0 for r in res) else "FAIL", checked=len(res), results=res[:50])


# ---------------------------------------------------------------- record
def judge_signoff(signoff_path, repo=None):
    sys.path.insert(0, os.path.join(repo or pathlib.Path(__file__).resolve().parents[2], "tools", "die_plan"))
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "die_plan"))
    import signoff_profile as SP
    raw = pathlib.Path(signoff_path).read_bytes()
    rec = json.loads(raw)
    j = SP.judge(rec, die="s81")
    return dict(path=str(signoff_path), sha256=sha256_bytes(raw), verdict=j["verdict"], gates=j["gates"], reasons=j["reasons"],
                drc=j["drc"], tt_wns_ps=j["tt_wns_ps"], ff_hold_wns_ps=j["ff_hold_wns_ps"])


def build_record(plan, rep, sib, signoff_path, repo, rom_dir, lec=None, via=None, lec_policy="require", via_policy="advisory",
                 judge=judge_signoff, group=None):
    """group: a layout group the caller already proved for (rep, sib) (tools/fleet/type_template.py: layout key + bound RTL key);
    default = the (family, clock class, clock key) group of this plan."""
    pt = plan_types(plan)
    blockers = []
    pr, ps = parse_identity(rep), parse_identity(sib)
    if rep not in pt or sib not in pt:
        raise KeyError("identity not in plan")
    g = group if group is not None else group_of(plan, rep, sib)
    if not pr or not ps or g is None:
        blockers.append("sibling and representative are not in the same layout (family, clock class, clock key)")
    elif g["verdict"] != "OK":
        blockers.append("layout group excluded: %s" % "; ".join(g["reasons"]))
    tr, ts = pt[rep], pt[sib]
    sg = judge(signoff_path, repo)
    if sg["verdict"] != "SIGNED":
        blockers.append("representative signoff.json does not pass the gates: %s" % "; ".join(sg["reasons"]))
    mr, ms = macro_views(tr, repo), macro_views(ts, repo)
    views = []
    for mod in sorted(set(mr) | set(ms)):
        a, b = mr.get(mod), ms.get(mod)
        eq_lef = bool(a and b and a["lef_sha"] and a["lef_sha"] == b["lef_sha"])
        eq_lib = bool(a and b and a["lib_sha"] and a["lib_sha"] == b["lib_sha"])
        views.append(dict(module=mod, instances=len((b or a)["instances"]), lef_sha_rep=a and a["lef_sha"], lef_sha_sibling=b and b["lef_sha"],
                          lib_sha_rep=a and a["lib_sha"], lib_sha_sibling=b and b["lib_sha"], lef_equal=eq_lef, lib_equal=eq_lib))
        if not (eq_lef and eq_lib):
            blockers.append("macro %s LEF/lib sha not equal or missing" % mod)
    imgs, rimgs = rom_images(ts, rom_dir), rom_images(tr, rom_dir)
    for im in imgs:
        if not im["files"] or any(not f["sha256"] for f in im["files"]):
            blockers.append("no viamap image for %s=%s" % (im["param"], im["instance"]))
    differing = sorted(k for k in set(param_set(tr)) | set(param_set(ts)) if param_set(tr).get(k) != param_set(ts).get(k))
    if any(not IMAGE_PARAM_RE.match(k) for k in differing):
        blockers.append("differing non-image parameters: %s" % ",".join(k for k in differing if not IMAGE_PARAM_RE.match(k))[:200])
    lec = lec or dict(verdict="NOT_RUN", reason="not requested")
    via = via or dict(verdict="NOT_RUN", reason="not requested")
    ok_l = ("EQUIVALENT",) if lec_policy == "require" else ("EQUIVALENT", "NOT_RUN", "UNPROVEN")
    ok_v = ("PASS",) if via_policy == "require" else ("PASS", "NOT_RUN")
    if lec["verdict"] not in ok_l:
        blockers.append("LEC %s (policy %s)" % (lec["verdict"], lec_policy))
    if via["verdict"] not in ok_v:
        blockers.append("via-mask DRC %s (policy %s)" % (via["verdict"], via_policy))
    return dict(schema=SCHEMA, created=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                die="s81", sibling=sib, representative=rep,
                layout_key=g and g.get("layout_key"), clock_class=ps and ps["clock_class"], family=ps and ps["family"],
                param_set_sha=param_set_sha(ts), representative_param_set_sha=param_set_sha(tr),
                differing_params=differing, representative_signoff=sg, rom_images=imgs, representative_rom_images=rimgs,
                macro_views=views, via_mask_drc=via, lec=lec, lec_policy=lec_policy, via_policy=via_policy,
                credit=not blockers, credit_blockers=blockers)


def write_record(rec, out_dir):
    d = pathlib.Path(out_dir) / rec["sibling"]
    d.mkdir(parents=True, exist_ok=True)
    f = d / "inherited.json"
    if f.exists():
        raise FileExistsError("append-only: %s exists" % f)
    f.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return f


def index_row(rec_path, rec, db, rtx_db):
    raw = pathlib.Path(rec_path).read_bytes()
    st = "ARCHIVED-BOTH"
    cols = [rec["die"], rec["sibling"], "t", "", db, rtx_db, str(len(raw)), sha256_bytes(raw), "", db, st,
            "INHERITED from %s (S81-COL-INHERIT; credit %s)" % (rec["representative"], str(rec["credit"]).lower())]
    return "\t".join(cols)


def members_row(rec, rec_path):
    return "\t".join([rec["die"], rec["sibling"], rec["representative"], str(rec_path), sha256_file(rec_path) or ""])


def archive(records, rtx_root, agi_root, agi_ssh=None, dry=False):
    """a new dir per record under rtx_root/s81/<sibling>/ and agi_root/s81/<sibling>/ (never overwritten), one INDEX.tsv row each,
    append-only.  AGIdock: ONE ssh session for the whole batch (tar stream + remote append)."""
    rows, rtx_rows, items = [], [], []
    for rp in records:
        rp = pathlib.Path(rp)
        rec = json.loads(rp.read_text())
        rel = "s81/%s/inherited.json" % rec["sibling"]
        db, rdb = "%s/%s" % (agi_root, rel), "%s/%s" % (rtx_root, rel)
        row = index_row(rp, rec, db, rdb)
        items.append((rp, rel, row))
    if dry:
        return [r for _, _, r in items]
    for rp, rel, row in items:
        dst = pathlib.Path(rtx_root) / rel
        if dst.exists():
            raise FileExistsError(str(dst))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(rp.read_bytes())
        with open(pathlib.Path(rtx_root) / "INDEX.tsv", "a") as f:
            f.write(row + "\n")
    if agi_ssh:
        with tempfile.TemporaryDirectory() as td:
            for rp, rel, row in items:
                p = pathlib.Path(td) / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(rp.read_bytes())
            (pathlib.Path(td) / "INDEX.rows").write_text("".join(r + "\n" for _, _, r in items))
            # one session: stream, extract without overwriting (-k), append the rows
            remote = "set -e; cd %s; cat > /tmp/colinh_in.tar; tar -xkf /tmp/colinh_in.tar --exclude=INDEX.rows; tar -xOf /tmp/colinh_in.tar ./INDEX.rows >> INDEX.tsv; rm -f /tmp/colinh_in.tar" % shlex.quote(agi_root)
            subprocess.run("tar -C %s -cf - . | %s %s" % (shlex.quote(td), agi_ssh, shlex.quote(remote)), shell=True, check=True)
    return [r for _, _, r in items]


# --------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("groups"); g.add_argument("plan"); g.add_argument("--repo"); g.add_argument("--merge-classes", action="store_true")
    r = sub.add_parser("record")
    r.add_argument("--plan", required=True); r.add_argument("--rep", required=True); r.add_argument("--sibling", action="append", required=True)
    r.add_argument("--signoff", required=True); r.add_argument("--repo", required=True); r.add_argument("--rom-dir", required=True)
    r.add_argument("--out", required=True); r.add_argument("--netlist"); r.add_argument("--rep-top")
    r.add_argument("--sibling-rtl", nargs="*", default=[]); r.add_argument("--blackbox", nargs="*", default=[])
    r.add_argument("--lec-policy", default="require", choices=("require", "advisory"))
    r.add_argument("--via-policy", default="advisory", choices=("require", "advisory"))
    r.add_argument("--rom-gds"); r.add_argument("--via-drc-cmd"); r.add_argument("--members-tsv")
    a = sub.add_parser("archive")
    a.add_argument("--records", nargs="+", required=True); a.add_argument("--rtx-root", required=True); a.add_argument("--agi-root", required=True)
    a.add_argument("--agi-ssh"); a.add_argument("--dry-run", action="store_true")
    ns = ap.parse_args(argv)
    if ns.cmd == "groups":
        plan = json.load(open(ns.plan))
        res = {"%s|%s" % k: v for k, v in groups(plan, ns.repo, merge_classes=ns.merge_classes).items()}
        print(json.dumps(res, indent=1)); return 0
    if ns.cmd == "record":
        plan = json.load(open(ns.plan)); pt = plan_types(plan)
        rc = 0
        for sib in ns.sibling:
            lec = None
            if ns.netlist and ns.sibling_rtl:
                work = pathlib.Path(ns.out) / sib / "lec"
                rep_net = pathlib.Path(ns.netlist).read_text()
                new, n = rewrite_instances(rep_net, param_set(pt[ns.rep]), param_set(pt[sib]))
                work.mkdir(parents=True, exist_ok=True)
                (work / "gate.v").write_text(new)
                standin = work / "standin.v"
                standin.write_text("".join(standin_verilog(pathlib.Path(b).read_text()) for b in ns.blackbox))
                lec = run_lec(lec_script(ns.sibling_rtl, str(work / "gate.v"), sib, ns.rep_top or ns.rep, [str(standin)], param_set(pt[sib])), str(work))
                lec["rewritten_instances"] = n
            imgs = rom_images(pt[sib], ns.rom_dir)
            via = via_mask_drc(imgs, ns.rom_gds, ns.via_drc_cmd)
            rec = build_record(plan, ns.rep, sib, ns.signoff, ns.repo, ns.rom_dir, lec, via, ns.lec_policy, ns.via_policy)
            f = write_record(rec, ns.out)
            if ns.members_tsv:
                with open(ns.members_tsv, "a") as m:
                    if rec["credit"]:
                        m.write(members_row(rec, f) + "\n")
            print("%s credit=%s %s" % (sib, rec["credit"], "; ".join(rec["credit_blockers"])[:200])); rc |= 0 if rec["credit"] else 1
        return rc
    rows = archive(ns.records, ns.rtx_root, ns.agi_root, ns.agi_ssh, ns.dry_run)
    print("\n".join(rows)); return 0


if __name__ == "__main__":
    sys.exit(main())
