#!/usr/bin/env python3
"""Macro view export at SS / FF / TT (OWNER OPTION B 2026-10-07: setup signs off at TT, hold at FF, SS = sensitivity).

write_timing_model from the routed 6_final odb + spef (write_abstract_lef in the SS pass), at SS, FF and TT (ASAP7 NLDM
libraries and each sub-macro's <name>_<corner>.lib).  Self-contained (no repo imports) so it can be copied to any host
and run next to the route:

    python3 view_export.py --orfs-dir W/work/orfs --name NAME --out DIR [--interface-sdc F] [--macro-view D ...]
                           [--corners ss,ff,tt] [--image openroad/orfs:latest] [--tmp-dir T]
                           [--verdict-json F | --no-verdict] [--sdc-name N] [--post-sdc F ...] [--verdict-tol PS]

CONSTRAINT SEQUENCE (export-sdc 2026-10-13).  A view must carry the timing its route was SIGNED OFF with, so the
constraints are read in the verdict's own order, never a substitute:
  1. VERDICT REPLAY (default whenever the route sits in a closure-loop run: <RUN>/routes/<L>/work/orfs with
     <RUN>/cl/routed_ioref.a<N>*.json, or --verdict-json F): the constraint section of the verdict's own STA Tcl
     (<json stem>_meas/meas_{ss,ff}.tcl, from read_db up to the reports: routed 6_final.sdc, SPEF, propagated clocks,
     every post-SDC, io_ref_routed.sdc last) is replayed VERBATIM with the verdict's mounts (/work = the verdict's ORFS
     dir, /src = <RUN>/src, /meas).  SS and TT replay the setup Tcl, FF the hold Tcl.  The session slack is then checked
     against the verdict (TT setup, FF hold; --verdict-tol, default 0.05 ps): a mismatch FAILS the export.  A verdict
     timed on another ODB / SPEF than the one being exported is refused (stale verdict), not skipped.
  2. CORNER_STA REPLAY (a loop run without a routed_ioref verdict): the constraint section of the route's own
     corner_sta Tcl (<orfs>/w18_sta_{ss,ff}.tcl), verbatim; recorded as unchecked.
  3. --post-sdc F ... (no verdict to replay): routed <--sdc-name>, SPEF, set_propagated_clock, then each F in order
     (tools/w18/corner_sta.py's order).
  4. legacy (none of these): the routed 6_final.sdc, or --interface-sdc read INSTEAD of it.  This is an interface extraction
     for hand flows; it is NOT the sign-off sequence (s81su SMT: FF -19.69 exported vs +3.66 verdict).
With a verdict replay --interface-sdc is recorded but does not change the sequence.

--corners tt alone adds <name>_tt.lib to a view whose LEF / SS / FF were already written from the SAME route by
hbm_fmax_attn_abstract.py (pass the same --interface-sdc / --macro-view it used).  Exit 0 iff every corner finished.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
CELLS = ["asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz",
         "asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib",
         "asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz"]
VT = {"L": ("LVT", "L"), "SL": ("SLVT", "SL")}   # odb cell suffix -> (lib tag, lef tag)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def extra_vts(odb):
    data = Path(odb).read_bytes()
    out = []
    for t in ("L", "SL"):
        import re
        if re.search(rb"_ASAP7_75t_" + t.encode() + rb"(?![A-Za-z0-9_])", data):
            out.append(t)
    return out


class VerdictError(Exception):
    pass


def verdict_section(tcl_text):
    """the constraint section of a verdict STA Tcl (corner_sta.py / meas_resta.py form): every line from read_db up to
    the first report (puts "OT_CORNER ..."), without meas_resta's register census"""
    lines = tcl_text.splitlines()
    a = next((i for i, l in enumerate(lines) if l.startswith("read_db ")), None)
    b = next((i for i, l in enumerate(lines) if l.startswith('puts "OT_CORNER')), None)
    if a is None or b is None or b <= a:
        raise VerdictError("verdict Tcl has no read_db ... OT_CORNER section")
    sec = [l for l in lines[a:b] if l.strip() and "OT_REGS" not in l]
    if not any(l.startswith("read_sdc ") for l in sec) or not any(l.startswith("read_spef ") for l in sec):
        raise VerdictError("verdict Tcl section reads no SDC / SPEF")
    return sec


def section_files(sec):
    """[(command, container path)] of the files a section reads"""
    return [tuple(l.split()[:2]) for l in sec if re.match(r"(read_db|read_sdc|read_spef|source) /", l)]


def find_verdict(orfs, explicit=None):
    """the closure loop's routed-insertion verdict of the route at ORFS: newest <RUN>/cl/routed_ioref.a*.json"""
    if explicit is not None:
        if not Path(explicit).is_file():
            raise VerdictError(f"--verdict-json {explicit}: no such file")
        return Path(explicit).resolve()
    if len(orfs.parents) < 4:
        return None
    cl = orfs.parents[3] / "cl"                    # <RUN>/routes/<LABEL>/work/orfs
    if orfs.parents[2].name != "routes" or not cl.is_dir():
        return None
    c = sorted(cl.glob("routed_ioref.a*.json"), key=lambda p: p.stat().st_mtime)
    return c[-1].resolve() if c else None


def load_verdict(vj, orfs, base):
    """-> dict(json, meas, src, work, sec{ss,ff}, expect{tt,ff}, files) for a verdict timed on exactly BASE's odb+spef"""
    res = json.loads(vj.read_text())
    meas = vj.parent / (vj.stem + "_meas")
    exp = {}
    for corner, key in (("tt", "setup_tt"), ("ff", "hold_ff")):
        r = res.get(key) or {}
        if r.get("worst_slack_ps") is None or r.get("errors") or r.get("error") or r.get("rc") not in (0, None):
            raise VerdictError(f"{vj}: {key} is not a clean verdict ({json.dumps(r)[:200]})")
        exp[corner] = float(r["worst_slack_ps"])
    sec = {}
    for c in ("ss", "ff"):
        f = meas / f"meas_{c}.tcl"
        if not f.is_file():
            raise VerdictError(f"{f}: verdict Tcl missing")
        sec[c] = verdict_section(f.read_text())
    src = vj.parent.parent / "src"
    used = {p for s in sec.values() for _, p in section_files(s)}
    bad = sorted(p for p in used if not p.startswith(("/work/", "/src/", "/meas/")))
    if bad:
        raise VerdictError(f"verdict Tcl reads outside /work /src /meas: {bad}")
    # the ORFS dir the verdict was timed in: recorded by meas_resta (orfs), else the installed hold-ECO dir, else the
    # route's own; only one whose 6_final odb + spef ARE the exported ones qualifies
    cands = ([Path(res["orfs"])] if res.get("orfs") else []) + [vj.parent / "eco" / "orfs", orfs]
    want = {n: sha(base / n) for n in ("6_final.odb", "6_final.spef")}
    why = []
    for w in dict.fromkeys(c.resolve() for c in cands if c.is_dir()):
        roots = {"/work/": w, "/src/": src, "/meas/": meas}
        host = {p: next(r / p[len(k):] for k, r in roots.items() if p.startswith(k)) for p in used}
        miss = [p for p, h in host.items() if not h.is_file()]
        if miss:
            why.append(f"{w}: missing {miss[:3]}")
            continue
        stale = [p for p, h in host.items() if h.name in want and sha(h) != want[h.name]]
        if stale or not all(any(h.name == n for h in host.values()) for n in want):
            why.append(f"{w}: verdict timed another {' / '.join(Path(p).name for p in stale) or 'db'}")
            continue
        return dict(json=vj, meas=meas, src=src, work=w, sec=sec, expect=exp,
                    files={p: dict(host=str(h), sha256=sha(h)) for p, h in sorted(host.items())})
    raise VerdictError(f"{vj}: the verdict is not of the ODB / SPEF being exported (stale verdict) -- " + "; ".join(why))


def corner_sta_sections(orfs):
    """no routed_ioref verdict (spec opt-out / unavailable): the route's own corner_sta Tcl (w18_sta_{ss,ff}.tcl, /work =
    the ORFS dir, /src = <RUN>/src) IS the sign-off sequence.  None unless every file it reads is there (then legacy)."""
    try:
        sec = {c: verdict_section((orfs / f"w18_sta_{c}.tcl").read_text()) for c in ("ss", "ff")}
    except (OSError, VerdictError):
        return None
    src = orfs.parents[3] / "src"
    host = {}
    for p in {p for s in sec.values() for _, p in section_files(s)}:
        h = orfs / p[6:] if p.startswith("/work/") else src / p[5:] if p.startswith("/src/") else None
        if h is None or not h.is_file():
            return None
        host[p] = dict(host=str(h), sha256=sha(h))
    return dict(sec=sec, src=src, work=orfs, files=dict(sorted(host.items())))


def ws_ps(line):
    m = re.match(r"OT_WS max (\S+) min (\S+)", line or "")
    return (float(m.group(1)) * 1e12, float(m.group(2)) * 1e12) if m else (None, None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--interface-sdc", type=Path)
    ap.add_argument("--macro-view", action="append", default=[], type=Path)
    ap.add_argument("--corners", default="ss,ff,tt")
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--tmp-dir", type=Path)
    ap.add_argument("--verdict-json", type=Path, help="routed_ioref verdict json to replay (default: the run's newest)")
    ap.add_argument("--no-verdict", action="store_true", help="never replay a verdict (interface extraction)")
    ap.add_argument("--sdc-name", default="6_final.sdc", help="routed SDC under the base dir (--post-sdc sequence)")
    ap.add_argument("--post-sdc", action="append", default=[], type=Path,
                    help="read after the routed SDC, SPEF and set_propagated_clock, in order (corner_sta.py's order)")
    ap.add_argument("--verdict-tol", type=float, default=0.05, help="ps; export session slack vs the verdict")
    ap.add_argument("--pin-only-tech", action="store_true", help="snapshot exact read-tech LEF for M6 contact-via audit")
    a = ap.parse_args()
    orfs, out = a.orfs_dir.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = base.relative_to(orfs)
    mounts = []
    if a.tmp_dir is not None:
        a.tmp_dir.mkdir(parents=True, exist_ok=True)
        mounts += ["-v", f"{a.tmp_dir.resolve()}:/tmp", "-e", "TMPDIR=/tmp"]
    recp = out / "abstract.json"
    rec = json.loads(recp.read_text()) if recp.exists() else dict(name=a.name, orfs_dir=str(orfs), corners={})
    rec.setdefault("corners", {})
    if a.interface_sdc is not None:
        isdc = a.interface_sdc.resolve()
        mounts += ["-v", f"{isdc}:/interface.sdc:ro"]
        rec["interface_sdc"] = dict(path=str(isdc), sha256=sha(isdc),
                                    purpose="interface timing extraction, not a new leaf signoff verdict")
    vd = None
    for k in ("verdict", "sdc_sequence"):
        rec.pop(k, None)
    try:
        vj = None if a.no_verdict else find_verdict(orfs, a.verdict_json)
        if vj is not None:
            vd = load_verdict(vj, orfs, base)
    except (VerdictError, OSError, ValueError) as ex:
        # a route WITH a verdict whose sequence cannot be reproduced exports nothing: a view at other constraints
        # than the sign-off is the bug this guards (never fall back silently)
        rec.update(ok=False, verdict=dict(error=str(ex)))
        recp.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"VIEW_EXPORT FAIL verdict sequence: {ex}")
        raise SystemExit(4)
    cs = None
    if vd is None and not a.no_verdict and len(orfs.parents) > 3 and (orfs.parents[3] / "cl").is_dir():
        cs = corner_sta_sections(orfs)
        if cs is not None:
            mounts += ["-v", f"{cs['work']}:/work:ro", "-v", f"{cs['src']}:/src:ro"]
            rec["verdict"] = dict(json=None, corner_sta_tcl=True, files=cs["files"],
                                  note="no routed_ioref verdict: the route's corner_sta sequence, unchecked")
    if vd is not None:
        mounts += ["-v", f"{vd['work']}:/work:ro", "-v", f"{vd['src']}:/src:ro", "-v", f"{vd['meas']}:/meas:ro"]
        rec["verdict"] = dict(json=str(vd["json"]), sha256=sha(vd["json"]), expect_ps=vd["expect"], tol_ps=a.verdict_tol,
                              work=str(vd["work"]), files=vd["files"], check={})
        if a.interface_sdc is not None:
            rec["interface_sdc"]["in_verdict_sequence"] = rec["interface_sdc"]["sha256"] in \
                {f["sha256"] for f in vd["files"].values()}
    elif a.post_sdc:
        for i, f in enumerate(a.post_sdc):
            mounts += ["-v", f"{f.resolve()}:/post{i}.sdc:ro"]
    rec["sdc_sequence"] = {}
    mv = []
    for i, d in enumerate(a.macro_view):
        d = d.resolve()
        mounts += ["-v", f"{d}:/mv{i}:ro"]
        mv.append((i, d.name))
    rec["macro_views"] = [str(d) for d in a.macro_view]
    vts = extra_vts(base / "6_final.odb")
    if vts:
        rec["vt_flavours_added"] = vts
    for c in a.corners.split(","):
        C = c.upper()
        libs = [f"read_liberty {PLAT}/lib/NLDM/{x.format(C=C)}" for x in CELLS]
        libs += [f"read_liberty {PLAT}/lib/NLDM/{x.format(C=C).replace('_RVT_', '_' + VT[v][0] + '_')}"
                 for v in vts for x in CELLS]
        libs += [f"read_liberty /mv{i}/{n}_{c}.lib" for i, n in mv]
        lefs = [f"read_lef {PLAT}/lef/asap7sc7p5t_28_{VT[v][1]}_1x_220121a.lef" for v in vts]
        lefs += [f"read_lef /mv{i}/{n}.lef" for i, n in mv]
        if vd is not None:
            # the verdict's own constraint section, verbatim (SS / TT = the setup session, FF = the hold session)
            seq, mode = list(vd["sec"]["ff" if c == "ff" else "ss"]), "verdict"
        elif cs is not None:
            seq, mode = list(cs["sec"]["ff" if c == "ff" else "ss"]), "corner_sta_tcl"
        elif a.post_sdc:
            seq, mode = [f"read_db /in/{rel}/6_final.odb", f"read_sdc /in/{rel}/{a.sdc_name}",
                         f"read_spef /in/{rel}/6_final.spef", "set_propagated_clock [all_clocks]",
                         *(f"read_sdc /post{i}.sdc" for i in range(len(a.post_sdc)))], "post_sdc"
        else:
            sdc = "/interface.sdc" if a.interface_sdc is not None else f"/in/{rel}/6_final.sdc"
            # Interface SDC derives its clock reference immediately; routed parasitics
            # must be loaded before it evaluates clock arrivals.
            seq, mode = [f"read_db /in/{rel}/6_final.odb", f"read_spef /in/{rel}/6_final.spef", f"read_sdc {sdc}",
                         "set_propagated_clock [all_clocks]"], "legacy"
        rec["sdc_sequence"][c] = dict(mode=mode, tcl=seq)
        tcl = "\n".join([f"read_lef {PLAT}/lef/asap7_tech_1x_201209.lef",
                         f"read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef", *lefs, *libs, *seq,
                         "puts \"OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]\"",
                         f"write_timing_model -library_name {a.name}_{c} /out/{a.name}_{c}.lib",
                         f"write_abstract_lef /out/{a.name}.lef" if c == "ss" else "",
                         f"file copy -force {PLAT}/lef/asap7_tech_1x_201209.lef /out/pin_only_tech.lef"
                         if c == "ss" and a.pin_only_tech else "",
                         "puts \"OT_EXPORT_DONE\"", "exit", ""])
        (out / f"export_{c}.tcl").write_text(tcl)
        cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/in:ro", "-v", f"{out}:/out", *mounts, a.image,
               "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit", f"/out/export_{c}.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (out / f"export_{c}.log").write_text(log)
        ws = [l for l in log.splitlines() if l.startswith("OT_WS")]
        done = "OT_EXPORT_DONE" in log
        if vd is not None and c in ("tt", "ff"):
            # the exported session IS the verdict session: TT setup / FF hold must reproduce the verdict's numbers
            got = ws_ps(ws[-1] if ws else None)[0 if c == "tt" else 1]
            want = vd["expect"][c]
            ok = got is not None and abs(got - want) <= a.verdict_tol + 0.005     # the verdict json is rounded to 0.01
            rec["verdict"]["check"][c] = dict(export_ps=got, verdict_ps=want, ok=ok)
            if not ok:
                print(f"VIEW_EXPORT FAIL {c}: export session {got} ps vs verdict {want} ps (tol {a.verdict_tol})")
            done = done and ok
        rec["corners"][c] = dict(returncode=p.returncode, done=done, ws=ws[-1] if ws else None,
                                 image=a.image, command=cmd)
    rec["files"] = {f.name: sha(f) for f in sorted(out.iterdir()) if f.suffix in (".lef", ".lib")}
    want = [f"{a.name}.lef"] + [f"{a.name}_{c}.lib" for c in ("ss", "ff", "tt")]
    rec["ok"] = all(v.get("done") for v in rec["corners"].values()) and all(w in rec["files"] for w in want)
    recp.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({k: rec[k] for k in ("name", "ok", "files")}))
    raise SystemExit(0 if all(rec["corners"][c]["done"] for c in a.corners.split(",")) else 1)


if __name__ == "__main__":
    main()
