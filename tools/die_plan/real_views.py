#!/usr/bin/env python3
"""REAL-VIEWS-1119 (DIE-LEVEL-CHECK-1119, COORD 11-19): die_sta_related real-view arguments for one die plan.

    real_views.py PLAN --out DIR [--view-root DIR ...] [--records JSON] [--fetch] [--digest JSON ...]
    real_views.py digest EXPORT --die DIE --out JSON [--names FILE]     (on the host holding the signed export)
    real_views.py report STA_DIR [--views real_views.json]              (measured vs contract hold per class)

Writes DIR/args.txt (one die_sta_related argument per line: --core-view MODULE=VIEWDIR / --kit TYPE=KIT.json) and
DIR/real_views.json (status per core module and per type).  Every view it passes is SIGNED and pin-matched to PLAN;
everything else stays on the plan contract (declared insertion / kit-contract window) and is listed with its reason.

Cores (plan hard_cores[].module): candidate view dirs = the plan's own lib dir, then every <MODULE>_tt.lib dir under
each --view-root (another plan's view of the same module counts when its pins match this plan).  A candidate needs
<MODULE>_tt.lib + <MODULE>_ff.lib and a SIGNED verdict (signoff.json beside the libs, or provenance.json verdict).
Pin identity: provenance.json kit.pins_sha256 (die_sta_related reads it as is), else the dir's own pins.json (a shadow
view dir DIR/core_views/<MODULE>/ links the libs and carries a provenance.json naming that pins.json).  The match is
die_sta_related.pins_relation (content, canonical or exact mirror) against every plan instance's pins_file; a module
passes when at least one instance matches (die_sta_related re-checks per instance and keeps the rest on contract).

Types: --records = {"signed_types": {TYPE: ["host:/path/signoff.json ...", ...]}} (release_tree_plan cache form, one
die).  A record counts when its signoff.json verdict is SIGNED, it has corners.{tt,ff}.insertion_pinflops, and its pins
(the record's face_guard.pins / inputs.pins, else <record>/../pins.json) cover every gen_phys.type_pins pin of the type in
PLAN with the same layer and position (1 nm).  Remote records are read with --fetch (ssh, 20 s timeout) into DIR/fetch/.
Kit JSON: lat_min/lat_max = insertion_pinflops min/max per corner (measured pin-register clock arrival); clkq/setup/hold
are left to die_sta_related's characterised pin register (kit_model fills absent arcs).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

NM = 1e-3
TANG_NM = 2.0       # along the face: same track (1 nm grid, rounding both sides)
FACE_NM = 1000.0    # across the face: DEF pin point sits <= ~0.5 um inside the edge
CORNERS = (("tt", "TT"), ("ff", "FF"))


def _json(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def signed_verdict(d):
    """SIGNED verdict of a view dir: signoff.json verdict, else provenance.json verdict."""
    for f in ("signoff.json", "provenance.json"):
        j = _json(Path(d) / f)
        if isinstance(j, dict) and j.get("verdict"):
            v = str(j["verdict"])
            # provenance form: "SIGNED (signoff.py verdict SIGNED; routed LEC ...)" -- the signoff.py verdict decides
            return signed_verdict_str(v)
    return None


def signed_verdict_str(v):
    v = str(v) if v is not None else None
    if v and v.startswith("SIGNED (signoff.py verdict "):    # provenance form: the signoff.py verdict decides
        v = v[len("SIGNED (signoff.py verdict "):].split(";")[0].split(")")[0].strip()
    return v


# signed for view purposes = what the release counter credits: SIGNED, and LOCAL_PASS_NEEDS_PARENT (a block signed
# off locally whose remaining check is the die parent, i.e. this very die STA)
SIGNED_OK = ("SIGNED", "LOCAL_PASS_NEEDS_PARENT")


def view_meta(d):
    """the provenance meta die_sta_related.core_view_model builds (pins identity), or None."""
    p = _json(Path(d) / "provenance.json")
    if not isinstance(p, dict):
        return None
    k = p.get("kit") if isinstance(p.get("kit"), dict) else {}
    if not (k.get("pins_sha256") or k.get("pins_canon_sha256")):
        return None
    return dict(verdict=p.get("verdict"), pins_sha256=k.get("pins_sha256"), pins_file=k.get("pins_file"),
                pins_canon_sha256=k.get("pins_canon_sha256"), outline_um=k.get("outline_um"))


def shadow_view(module, src, pins, out):
    """DIR/core_views/<module>/: links to the signed libs (+ core.json) and a provenance.json naming the view's pins.json."""
    d = Path(out) / "core_views" / f"{module}__{hashlib.sha256(str(Path(src).resolve()).encode()).hexdigest()[:10]}"
    d.mkdir(parents=True, exist_ok=True)
    for f in (f"{module}_tt.lib", f"{module}_ff.lib", f"{module}.core.json"):
        s, t = Path(src) / f, d / f
        if s.exists() and not t.exists():
            t.symlink_to(s.resolve())
    prov = dict(verdict="SIGNED", source=str(Path(src).resolve()), note="REAL-VIEWS-1119 shadow: pins identity = the "
                "signed view dir's own pins.json", kit=dict(pins_sha256=_sha(pins), pins_file=str(Path(pins).resolve())))
    (d / "provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    return d


def core_candidates(module, plan_lib_dir, roots):
    seen, out = set(), []
    for d in [plan_lib_dir] + [p.parent for r in roots for p in sorted(Path(r).rglob(f"{module}_tt.lib"))]:
        if d is None:
            continue
        k = str(Path(d).resolve())
        if k not in seen:
            seen.add(k)
            out.append(Path(d))
    return out


def record_pins(d, spec_lines, out, fetch):
    """pins.json of a signed view dir whose signoff.json is byte-equal to one of the counter's signed_cores records
    (host:path): that record's inputs.pins / face_guard.pins, else <record>/../pins.json, read from the same host."""
    so = Path(d) / "signoff.json"
    if not so.exists():
        return None
    want = _sha(so)
    rec = _json(so) or {}
    for line in spec_lines or []:
        spec = line.split()[0]
        f = _fetch(spec, out, fetch)
        if f is None or _sha(f) != want:
            continue
        host = spec.split(":", 1)[0] if ":" in spec else ""
        fg = rec.get("face_guard") if isinstance(rec.get("face_guard"), dict) else {}
        inp = rec.get("inputs") if isinstance(rec.get("inputs"), dict) else {}
        for ps in [x for x in (fg.get("pins"), inp.get("pins")) if x] + [str(Path(spec.split(":", 1)[-1]).parent.parent / "pins.json")]:
            pf = _fetch(f"{host}:{ps}" if host else ps, out, fetch)
            if pf and _json(pf):
                return pf
    return None


def etm_problem(module, d):
    """None when die_sta_related can model both corner ETMs of the view (boundary out/setup/hold arcs), else the reason;
    one unusable signed view must leave that core on contract, not stop the die STA (S81 dsdv_bksel_c: no out arcs)."""
    import die_sta_related as R
    for c in ("tt", "ff"):
        try:
            R.parse_etm(Path(d) / f"{module}_{c}.lib", 1.0)
        except SystemExit as e:
            return f"{c}: {str(e).split(': ', 1)[-1][:120]}"
        except Exception as e:                         # unreadable / unparsable liberty
            return f"{c}: {type(e).__name__} {str(e)[:100]}"
    return None


def resolve_cores(plan, plan_path, roots, out, records=None, fetch=False):
    import schema as S
    import die_sta_related as R
    P = S.Plan(plan)
    plan_dir = Path(plan_path).parent
    inst = {}
    for n, p in P.parts.items():
        for h in P.types[p["type"]].get("hard_cores", []) or []:
            inst.setdefault(h["module"], []).append(h)
    args, status = [], {}
    for mod, hs in sorted(inst.items()):
        lib = hs[0].get("lib")
        own = None
        for base in (plan_dir, *plan_dir.parents):
            if lib and (base / lib).exists():
                own = (base / lib).parent
                break
        why = []
        chosen = None
        for d in core_candidates(mod, own, roots):
            if not ((d / f"{mod}_tt.lib").exists() and (d / f"{mod}_ff.lib").exists()):
                why.append(f"{d}: no tt+ff lib")
                continue
            v = signed_verdict(d)
            if v not in SIGNED_OK:
                why.append(f"{d}: verdict {v}")
                continue
            meta, vdir = view_meta(d), d
            if meta is None and (d / "pins.json").exists():
                vdir = shadow_view(mod, d, d / "pins.json", out)
                meta = view_meta(vdir)
            if meta is None:
                rp = record_pins(d, ((records or {}).get("signed_cores") or {}).get(mod), out, fetch)
                if rp is not None:
                    vdir = shadow_view(mod, d, rp, out)
                    meta = view_meta(vdir)
            if meta is None:
                why.append(f"{d}: signed, no pins identity (no provenance pins sha, no pins.json)")
                continue
            bad = etm_problem(mod, d)
            if bad:
                why.append(f"{d}: ETM unusable ({bad})")
                continue
            hit = [h for h in hs if R.pins_match(meta, h.get("pins_file"), plan_dir, h.get("outline_um")) is None]
            if not hit:
                r = R.pins_match(meta, hs[0].get("pins_file"), plan_dir, hs[0].get("outline_um"))
                why.append(f"{d}: pins mismatch ({r})")
                continue
            chosen = (vdir, d, len(hit))
            break
        if chosen:
            args.append(f"--core-view={mod}={chosen[0]}")
            status[mod] = dict(status="REAL", verdict=signed_verdict(chosen[1]), view=str(chosen[1]), via=str(chosen[0]), instances=len(hs),
                               instances_pin_match=chosen[2])
        else:
            status[mod] = dict(status="CONTRACT", instances=len(hs), reasons=why or ["no view dir found"])
    return args, status


def _canon_rows(doc):
    rows = doc if isinstance(doc, list) else (doc.get("pins", []) if isinstance(doc, dict) else [])
    out = {}
    for p in rows:
        name = p.get("name") or (f"{p['bus']}[{p['bit']}]" if p.get("bit") is not None else p.get("bus"))
        if name is None or "x" not in p or "y" not in p:
            continue
        out[str(name)] = (p.get("layer"), round(float(p["x"]) / NM), round(float(p["y"]) / NM))
    return out


def type_pins_match(P, tn, pins_doc):
    """None when every gen_phys.type_pins pin of tn is in pins_doc with the same layer and position, else the reason.
    pins_doc: a pins.json form, or {name: [layer, x_um, y_um]} from a routed DEF (def_pins).  Position: the coordinate
    along the face within TANG_NM, the coordinate across it within FACE_NM (a DEF pin point sits inside the edge)."""
    import gen_phys as G
    if isinstance(pins_doc, dict) and pins_doc and all(isinstance(v, list) and len(v) == 3 for v in pins_doc.values()):
        w, h = P.types[tn]["outline_um"]
        miss = bad = 0
        for bus, bit, layer, x, y, face in G.type_pins(P, tn):
            r = pins_doc.get(f"{bus}[{bit}]") or (pins_doc.get(bus) if bit in (0, None) else None)
            if r is None:
                miss += 1
                continue
            ta, tb = (r[2], y) if face in "EW" else (r[1], x)
            na, nb = (r[1], x) if face in "EW" else (r[2], y)
            if r[0] != layer or abs(ta - tb) * 1e3 > TANG_NM or abs(na - nb) * 1e3 > FACE_NM:
                bad += 1
        return None if not (miss or bad) else f"plan pins missing {miss}, moved {bad} (signed DEF)"
    have = _canon_rows(pins_doc)
    if not have:
        return "record pins empty/unreadable"
    miss = bad = 0
    for bus, bit, layer, x, y, _face in G.type_pins(P, tn):
        r = have.get(f"{bus}[{bit}]") or (have.get(bus) if bit in (0, None) else None)
        if r is None:
            miss += 1
        elif r[0] != layer or abs(r[1] - round(x / NM)) > 1 or abs(r[2] - round(y / NM)) > 1:
            bad += 1
    return None if not (miss or bad) else f"plan pins missing {miss}, moved {bad}"


def _fetch(spec, out, fetch):
    """'host:/path' -> local Path (read in place when local, copied with --fetch), or None."""
    host, _, path = spec.partition(":")
    if not path:
        host, path = "", spec
    lp = Path(path)
    if lp.exists():
        return lp
    if not fetch or not host:
        return None
    dst = Path(out) / "fetch" / host / path.lstrip("/")
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(["timeout", "20", "ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", host,
                            f"cat {path}"], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or not r.stdout:
        return None
    dst.write_bytes(r.stdout)
    return dst


def def_pins(path):
    """{name: (layer, x_um, y_um)} signal pins of a DEF, streamed up to END PINS (the routed DEF is ~1 GB; PINS is near
    the top).  Point = FIXED/PLACED origin + first LAYER rect centre, rotated by the pin orientation."""
    u, out, cur = 1000.0, {}, None
    rot = {"N": lambda x, y: (x, y), "S": lambda x, y: (-x, -y), "E": lambda x, y: (y, -x), "W": lambda x, y: (-y, x),
           "FN": lambda x, y: (-x, y), "FS": lambda x, y: (x, -y), "FE": lambda x, y: (y, x), "FW": lambda x, y: (-y, -x)}
    with open(path, "rb") as fh:                       # PINS follows COMPONENTS: find it by byte search, parse it only
        head = fh.read(1 << 20)
        m = re.search(rb"\nUNITS DISTANCE MICRONS (\d+)", head)
        u = float(m.group(1)) if m else u
        fh.seek(0)
        off, tail, at = 0, b"", -1
        while True:
            blk = fh.read(1 << 26)
            if not blk:
                break
            buf = tail + blk
            i = buf.find(b"\nPINS ")
            if i >= 0:
                at = off - len(tail) + i + 1
                break
            tail, off = buf[-16:], off + len(blk)
        if at < 0:
            return out
        fh.seek(at)
        lines = []
        for ln in fh:
            if ln.startswith(b"END PINS"):
                break
            lines.append(ln.decode(errors="replace"))
    for ln in lines:
            t = ln.split()
            if not t:
                continue
            if t[0] == "-":
                cur = dict(name=t[1], skip=("POWER" in t or "GROUND" in t or "SPECIAL" in t))
            elif cur is not None and not cur["skip"]:
                if "LAYER" in t and "rect" not in cur:
                    i = t.index("LAYER")
                    cur["layer"] = t[i + 1]
                    n = [int(v) for v in t[i + 2:] if v.lstrip("-").isdigit()]
                    if len(n) >= 4:
                        cur["rect"] = ((n[0] + n[2]) / 2.0, (n[1] + n[3]) / 2.0)
                if ("FIXED" in t or "PLACED" in t) and "rect" in cur:
                    i = t.index("FIXED") if "FIXED" in t else t.index("PLACED")
                    x, y, o = int(t[i + 2]), int(t[i + 3]), t[i + 5]
                    dx, dy = rot.get(o, rot["N"])(*cur["rect"])
                    out[cur["name"]] = (cur["layer"], (x + dx) / u, (y + dy) / u)
                    cur["skip"] = True
    return out


def digest(export, die, out, names=None):
    """small per-element digest of a signed export (<export>/<die>/<element>/{signoff.json,6_final.def}).  DEF pins are
    read only for SIGNED records with insertion data whose name (re-sign suffix stripped) is in names (when given)."""
    res = {}
    for d in sorted((Path(export) / die).iterdir()):
        so = d / "signoff.json"
        rec = _json(so) if so.exists() else None
        if not isinstance(rec, dict):
            continue
        sc = _json(d / "signoff_ports.json") if (d / "signoff_ports.json").exists() else None
        if isinstance(sc, dict) and sc.get("record_sha256") not in (None, _sha(so)):
            sc = None                                   # a sidecar of another record: ignore
        kit = kit_from_record(rec, sc)
        df = d / "6_final.def"
        want = kit and signed_verdict_str(rec.get("verdict")) in SIGNED_OK and (names is None or VARIANT.sub("", d.name) in names)
        res[d.name] = dict(verdict=rec.get("verdict"), name=rec.get("name"), signoff_sha256=_sha(so), kit=kit,
                           record=f"{os.uname().nodename}:{so}",
                           pins=({k: list(v) for k, v in def_pins(df).items()} if want and df.exists() else None))
    Path(out).write_text(json.dumps(dict(schema="real_views.digest.v1", export=str(export), die=die, elements=res)) + "\n")
    print(f"DIGEST {die}: {len(res)} records, {sum(1 for v in res.values() if v['pins'])} with DEF pins -> {out}")


def ports_from(rec, sidecar=None):
    """{clock port: {TT|FF: {lat_min_ps, lat_max_ps, n}}} from the record's own corners.<c>.port_pinflops (sign-offs
    after REAL-VIEWS-PORTS) or a MATCH signoff_ports.json sidecar of that record (existing sign-offs, signoff_ports.py).
    Port '-' (pin flops not traced to a clock port) is left out."""
    src = {}
    for c, C in CORNERS:
        pp = ((rec.get("corners") or {}).get(c) or {}).get("port_pinflops")
        if pp:
            src[C] = pp
    if not src and isinstance(sidecar, dict) and sidecar.get("verdict") == "MATCH":
        src = {C: v for C, v in (sidecar.get("corners") or {}).items() if v}
    out = {}
    for C, pp in src.items():
        for port, v in pp.items():
            if port == "-" or not v or v.get("min") is None:
                continue
            out.setdefault(port, {})[C] = dict(lat_min_ps=float(v["min"]), lat_max_ps=float(v["max"]), n=v.get("n"))
    return {p: v for p, v in out.items() if all(C in v for _, C in CORNERS)} or None


def kit_from_record(rec, sidecar=None):
    corners = {}
    for c, C in CORNERS:
        ip = ((rec.get("corners") or {}).get(c) or {}).get("insertion_pinflops") or {}
        if ip.get("min") is None or ip.get("max") is None:
            return None
        corners[C] = dict(lat_min_ps=float(ip["min"]), lat_max_ps=float(ip["max"]), n=ip.get("n"))
    k = dict(schema="real_views.kit.v1", corners=corners)
    pts = ports_from(rec, sidecar)
    if pts:
        k["ports"] = pts
    return k


VARIANT = re.compile(r"__(a\d+_\d{4}|legalrows_\d+)$")   # count_hourly: re-sign suffixes of the same type


def resolve_types(plan, records, out, fetch, digests=()):
    import schema as S
    P = S.Plan(plan)
    used = sorted({p["type"] for p in P.parts.values()})
    signed = (records or {}).get("signed_types") or {}
    args, status = [], {}
    (Path(out) / "kits").mkdir(parents=True, exist_ok=True)
    byname = {}
    for dg in digests:
        for el, v in (dg.get("elements") or {}).items():
            byname.setdefault(VARIANT.sub("", el), []).append((el, v))
    for t in used:
        recs = signed.get(t) or []
        why, done = [], False
        for el, v in byname.get(t, []):
            if signed_verdict_str(v.get("verdict")) not in SIGNED_OK:
                why.append(f"export {el}: verdict {v.get('verdict')}")
                continue
            if not v.get("kit"):
                why.append(f"export {el}: no insertion_pinflops")
                continue
            if not v.get("pins"):
                why.append(f"export {el}: no DEF pins")
                continue
            r = type_pins_match(P, t, v["pins"])
            if r:
                why.append(f"export {el}: {r}")
                continue
            kit = dict(v["kit"], source=v.get("record"), signoff_sha256=v.get("signoff_sha256"))
            kf = Path(out) / "kits" / f"{t}.json"
            kf.write_text(json.dumps(kit, indent=1) + "\n")
            args.append(f"--kit={t}={kf}")
            status[t] = dict(status="REAL", record=v.get("record"), verdict=signed_verdict_str(v.get("verdict")),
                             via="export DEF pins", lat=kit["corners"], per_port=len(kit.get("ports") or {}))
            done = True
            break
        if done:
            continue
        for line in recs:
            spec = line.split()[0]
            f = _fetch(spec, out, fetch)
            if f is None:
                why.append(f"{spec}: unreadable")
                continue
            rec = _json(f)
            if not isinstance(rec, dict) or signed_verdict_str(rec.get("verdict")) not in SIGNED_OK:
                why.append(f"{spec}: verdict {rec.get('verdict') if isinstance(rec, dict) else None}")
                continue
            scf = _fetch(str(Path(spec).with_name("signoff_ports.json")), out, fetch)
            sc = _json(scf) if scf else None
            if isinstance(sc, dict) and sc.get("record_sha256") not in (None, _sha(f)):
                sc = None
            kit = kit_from_record(rec, sc)
            if kit is None:
                why.append(f"{spec}: no insertion_pinflops")
                continue
            host = spec.split(":", 1)[0] if ":" in spec else ""
            fg = rec.get("face_guard") if isinstance(rec.get("face_guard"), dict) else {}
            inp = rec.get("inputs") if isinstance(rec.get("inputs"), dict) else {}
            pspecs = [x for x in (fg.get("pins"), inp.get("pins")) if x] + [str(Path(spec.split(":", 1)[-1]).parent.parent / "pins.json")]
            pdoc = None
            for ps in pspecs:
                pf = _fetch(f"{host}:{ps}" if host else ps, out, fetch)
                pdoc = _json(pf) if pf else None
                if pdoc:
                    break
            if pdoc is None:
                why.append(f"{spec}: pins unreadable")
                continue
            r = type_pins_match(P, t, pdoc)
            if r:
                why.append(f"{spec}: {r}")
                continue
            kit["source"] = spec
            kf = Path(out) / "kits" / f"{t}.json"
            kf.write_text(json.dumps(kit, indent=1) + "\n")
            args.append(f"--kit={t}={kf}")
            status[t] = dict(status="REAL", record=spec, lat=kit["corners"], per_port=len(kit.get("ports") or {}))
            done = True
            break
        if not done:
            status[t] = dict(status="CONTRACT", reasons=why or ["no signed record for this type"])
    return args, status


def report(sta_dir, views=None):
    """measured vs contract hold per pair class of a die_sta_related run (FF corner holds, TT setup)."""
    r = _json(Path(sta_dir) / "die_sta_related.json")
    if not isinstance(r, dict):
        print(f"HOLD-REPORT {sta_dir}: no die_sta_related.json")
        return 1
    rv = _json(views) if views else None
    if isinstance(rv, dict):
        s = rv.get("summary", {})
        print(f"HOLD-REPORT views: cores {s.get('cores_real')}/{s.get('cores')} types {s.get('types_real')}/{s.get('types')} real")
    rows = []
    for c, cr in (r.get("corners") or {}).items():
        for k, v in (cr.get("classes") or {}).items():
            if not v.get("pairs") or c != "FF":
                continue
            hm = v.get("hold_measured") or {}
            kc = v.get("kit_contract_hold") or {}
            rows.append(dict(cls=k, pairs=v["pairs"], contract_hold_ps=v.get("worst_hold_slack_ps"),
                             kit_contract_hold_ps=kc.get("worst_hold_bound_ps"),
                             measured_hold_ps=hm.get("hold_margin_ps"), measured_pairs=hm.get("pairs_measured"),
                             unmeasured_pairs=hm.get("pairs_unmeasured"), measured_neg=hm.get("neg_pairs"),
                             status=hm.get("status")))
            print(f"HOLD-REPORT FF {k:14s} pairs {v['pairs']:8d} | CONTRACT all-pair {v.get('worst_hold_slack_ps')} "
                  f"kit-contract {kc.get('worst_hold_bound_ps')} | MEASURED {hm.get('hold_margin_ps')} "
                  f"({hm.get('pairs_measured')} measured, {hm.get('pairs_unmeasured')} unmeasured, neg {hm.get('neg_pairs')}) "
                  f"{hm.get('status')}")
    Path(sta_dir, "hold_report.json").write_text(json.dumps(rows, indent=1) + "\n")
    return 0


def plan_die(path, plan):
    """die name: plan 'die' key, else the physical/die_plan/<die>/ path component."""
    if isinstance(plan.get("die"), str):
        return plan["die"]
    parts = Path(path).resolve().parts
    return parts[parts.index("die_plan") + 1] if "die_plan" in parts[:-1] else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--view-root", action="append", default=[])
    ap.add_argument("--records", help="release_tree_plan cache entry for this die (signed_types)")
    ap.add_argument("--fetch", action="store_true", help="read remote records over ssh")
    ap.add_argument("--digest", action="append", default=[], help="signed-export digest JSON (real_views.py digest)")
    ap.add_argument("--store", help="dir with rec_<die>.json (counter signed_types/signed_cores) and digest_<die>.json")
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "report":
        rp = argparse.ArgumentParser(prog="real_views.py report")
        rp.add_argument("sta_dir"), rp.add_argument("--views")
        b = rp.parse_args(argv[1:])
        return report(b.sta_dir, b.views)
    if argv and argv[0] == "digest":
        dp = argparse.ArgumentParser(prog="real_views.py digest")
        dp.add_argument("export"), dp.add_argument("--die", required=True), dp.add_argument("--out", required=True)
        dp.add_argument("--names", help="file of type names (one per line): read DEF pins only for these")
        b = dp.parse_args(argv[1:])
        digest(b.export, b.die, b.out, set(Path(b.names).read_text().split()) if b.names else None)
        return 0
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(Path(a.plan).read_text())
    die = plan_die(a.plan, plan)
    if not a.view_root:
        a.view_root = [str(p) for p in Path(a.plan).resolve().parents if p.parent.name == "die_plan"][:1]
    if a.store and die:
        st = Path(a.store)
        if not a.records and (st / f"rec_{die}.json").exists():
            a.records = str(st / f"rec_{die}.json")
        if (st / f"digest_{die}.json").exists():
            a.digest.append(str(st / f"digest_{die}.json"))
    recs = _json(a.records) if a.records else None
    cargs, cst = resolve_cores(plan, a.plan, a.view_root, out, recs, a.fetch)
    targs, tst = resolve_types(plan, recs, out, a.fetch,
                               [d for d in (_json(x) for x in a.digest) if d])
    (out / "args.txt").write_text("".join(x + "\n" for x in cargs + targs))
    rep = dict(plan=str(a.plan), plan_sha256=_sha(a.plan), die=die, view_roots=a.view_root, records=a.records,
               digests=a.digest, cores=cst, types=tst,
               summary=dict(cores_real=sum(v["status"] == "REAL" for v in cst.values()), cores=len(cst),
                            types_real=sum(v["status"] == "REAL" for v in tst.values()), types=len(tst)))
    (out / "real_views.json").write_text(json.dumps(rep, indent=1) + "\n")
    rep["summary"]["types_per_port"] = sum(1 for v in tst.values() if v.get("per_port"))
    s = rep["summary"]
    print(f"REAL_VIEWS cores {s['cores_real']}/{s['cores']} types {s['types_real']}/{s['types']} "
          f"(per-port {s['types_per_port']}; type views without per-port arrivals are an in-type range BOUND) "
          f"(rest on contract; reasons in {out / 'real_views.json'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
