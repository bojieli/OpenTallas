#!/usr/bin/env python3
"""Generate the missing GDS of archived jobs ON their fleet host (ORFS container: write_def from the accepted
6_final.odb when no DEF exists, then a KLayout stream-out as ORFS def2stream does, macro abstracts kept), and bring it
back zstd-compressed into the archive.  gen_gds.py [JOB...] (default: every manifest with gds.source pending-generation)
Writes only under <scratch root>/claude/closed-archive-gds/<job> on the fleet host; never deletes there."""
import concurrent.futures as cf
import glob
import json
import os
import shlex
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive  # noqa: E402

GT = os.path.join(archive.TOOLS, "gds")
PER_HOST = {"ot-epyc1tb": 2, "ot-epyc2": 2}
_sems, _copied = {}, set()
_lk = threading.Lock()


def sh_host(host, cmd, timeout=7200):
    if host == "localhost":
        return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout)
    return subprocess.run(archive.SSH + [host, cmd], capture_output=True, text=True, timeout=timeout)


def tools_on(host):
    with _lk:
        if host in _copied:
            return
        d = "$HOME/closed-archive-gds-tools"
        if host == "localhost":
            subprocess.run(f"mkdir -p {d} && cp {GT}/stream.py {GT}/gen_remote.sh {d}/", shell=True, check=True)
        else:
            subprocess.run(archive.SSH + [host, f"mkdir -p {d}"], check=True, timeout=60)
            subprocess.run(["rsync", "-a", "-e", " ".join(archive.SSH), f"{GT}/stream.py", f"{GT}/gen_remote.sh",
                            f"{host}:closed-archive-gds-tools/"], check=True, timeout=120)
        _copied.add(host)


def gen(mp):
    m = json.load(open(mp))
    host, run, fb = m["host"], m["run_dir"], m.get("final_base")
    with _sems.setdefault(host, threading.Semaphore(PER_HOST.get(host, 4))):
        tools_on(host)
        files = {e["path"] for e in m["files"]}
        odb = f"{run}/{fb}/6_final.odb"
        dfn = f"{fb}/6_final.def"
        deff = f"{run}/{dfn}" if dfn in files else "-"
        cfg = next((f"{run}/{f}" for f in sorted(files) if f.endswith("/config.mk") and "/routes/" in "/" + f), "-")
        root = run.split("/claude/")[0] + "/claude/closed-archive-gds" if "/claude/" in run else os.path.dirname(run) + "/closed-archive-gds"
        out = f"{root}/{m['job']}"
        r = sh_host(host, f"bash $HOME/closed-archive-gds-tools/gen_remote.sh {shlex.quote(run)} {shlex.quote(odb)} "
                          f"{shlex.quote(deff)} {shlex.quote(cfg)} {shlex.quote(out)}")
        ok = [x for x in r.stdout.splitlines() if x.startswith("GDS_OK")]
        dest = os.path.dirname(mp)
        if not ok:
            m["gds"] = dict(path=None, source="generation-failed", host_dir=out, err=(r.stdout + r.stderr)[-600:])
            archive.log(f"GDS FAIL {m['job']} on {host}: {(r.stdout + r.stderr)[-200:]}")
        else:
            gd = os.path.join(dest, "generated")
            os.makedirs(gd, exist_ok=True)
            items = [("6_final.gds", True)] + ([("6_final.def", True)] if deff == "-" else []) + \
                    [("stream.log", False), ("klayout.lyt", False), ("write_def.log", False)]
            stored = {}
            for fn, z in items:
                src = f"{out}/{fn}"
                if z:
                    s = sh_host(host, f"sha256sum {shlex.quote(src)}").stdout.split()
                    with open(os.path.join(gd, fn + ".zst"), "wb") as fo:
                        c = f"zstd -q -c -10 -T4 -- {shlex.quote(src)}"
                        rr = subprocess.run(["bash", "-c", c] if host == "localhost" else archive.SSH + [host, c], stdout=fo, timeout=7200)
                    if rr.returncode == 0:
                        stored[fn] = dict(stored="generated/" + fn + ".zst", sha256=s[0] if s else None,
                                          stored_size=os.path.getsize(os.path.join(gd, fn + ".zst")))
                else:
                    c = f"cat {shlex.quote(src)}"
                    rr = subprocess.run(["bash", "-c", c] if host == "localhost" else archive.SSH + [host, c], capture_output=True, timeout=600)
                    if rr.returncode == 0:
                        open(os.path.join(gd, fn), "wb").write(rr.stdout)
            log_txt = open(os.path.join(gd, "stream.log")).read() if os.path.exists(os.path.join(gd, "stream.log")) else ""
            abstract = next((ln.split()[1:] for ln in log_txt.splitlines() if ln.startswith("STREAM_ABSTRACT")), [])
            empty = next((ln.split()[1:] for ln in log_txt.splitlines() if ln.startswith("STREAM_EMPTY")), [])
            if "6_final.gds" in stored:
                fdir = os.path.join(dest, "final")
                for fn, e in stored.items():
                    ln = os.path.join(fdir, fn + ".zst")
                    if not os.path.lexists(ln):
                        os.symlink(os.path.relpath(os.path.join(dest, e["stored"]), fdir), ln)
                    m.setdefault("final", {})["final_" + fn.split(".", 1)[1]] = "final/" + fn + ".zst"
                    m["files"].append(dict(path="generated/" + fn, raw_size=None, sha256=e["sha256"], stored=e["stored"],
                                           stored_size=e["stored_size"], compression="zstd", role="final_" + fn.split(".", 1)[1],
                                           generated=True))
                m["gds"] = dict(path=m["final"]["final_gds"], source="generated", host=host, host_dir=out,
                                method="ORFS asap7lock: openroad write_def (if no DEF) + KLayout DEF stream-out with asap7 R/L/SL cell GDS",
                                abstract_macros=abstract, empty_cells=empty)
                m["total_stored_bytes"] = sum(e.get("stored_size") or 0 for e in m["files"])
                archive.log(f"GDS OK {m['job']} on {host} ({stored['6_final.gds']['stored_size'] / 1e6:.1f} MB zst, {len(abstract)} abstract macros)")
            else:
                m["gds"] = dict(path=None, source="generation-failed", host_dir=out, err="copy-back failed")
        json.dump(m, open(mp + ".tmp", "w"), indent=1)
        os.replace(mp + ".tmp", mp)


def main(names):
    mps = []
    for mp in glob.glob(os.path.join(archive.ROOT, "*", "*", "manifest.json")):
        try:
            m = json.load(open(mp))
        except ValueError:
            continue
        if m.get("status") != "archived" or (m.get("gds") or {}).get("path"):
            continue
        if names and m["job"] not in names:
            continue
        if not names and (m.get("gds") or {}).get("source") == "generation-failed":
            continue
        mps.append(mp)
    with cf.ThreadPoolExecutor(16) as ex:
        for f in [ex.submit(gen, mp) for mp in mps]:
            try:
                f.result()
            except Exception as e:  # noqa: BLE001
                archive.log(f"GDS ERROR: {e}")
    archive.build_index()


if __name__ == "__main__":
    main(sys.argv[1:])
