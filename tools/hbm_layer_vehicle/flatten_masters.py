#!/usr/bin/env python3
"""TOKEN-PASS-HBMDS (10-18): one module NAMESPACE per hard die master for a flat simulation of the die netlist.

The die's masters are hardened separately, each with its own preprocessor defines (views.json env DEFINES=..., the die
SYNTH flow's) and its own module variants, so one flat compile of all RTL is not the die.  For every master M this
preprocesses M's subtree (master_files.json) with M's defines (`verilator -E -P`), renames every module it defines
X -> X_m<k> (M itself keeps its name: die.v instantiates it) and writes masters/<M>.sv.  Run inside a bundle:
    flatten_masters.py --bundle . --views views.json [--verilator BIN]
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path


def mark_hier(t, j):
    """insert /*verilator hier_block*/ after the header of the module whose name ends at index j"""
    for _ in range(2):                      # optional #( parameters ) then ( ports ): skip balanced groups
        k = re.match(r"\s*#?\s*\(", t[j:])
        if not k:
            break
        j += k.end()
        d = 1
        while d:
            d += {"(": 1, ")": -1}.get(t[j], 0)
            j += 1
    semi = t.index(";", j) + 1
    return t[:semi] + " /*verilator hier_block*/" + t[semi:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", default=".")
    ap.add_argument("--views", required=True)
    ap.add_argument("--hier", type=int, default=1, help="mark each master /*verilator hier_block*/")
    ap.add_argument("--nohier", default="", help="comma list of masters NOT marked hier_block (a bench reaches inside them)")
    ap.add_argument("--inner-hier", default="ot_hgi_coll_tkm_tile,ot_hgi_coll_tkm_tile_e86",
                    help="comma list of modules INSIDE a master also marked hier_block (nested), e.g. the TKM tiles: "
                         "flattening tkm_m_tp192's 32 tile bodies OOMs at 480 GB (as the TKM-3 tp192 gate found, tkm_tp192_hier.vlt)")
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    a = ap.parse_args()
    B = Path(a.bundle)
    mf = json.loads((B / "master_files.json").read_text())
    views = json.loads(Path(a.views).read_text())
    inc = (B / "incdirs.f").read_text().split()
    out = B / "masters"
    out.mkdir(exist_ok=True)
    rec = {}
    for k, (m, files) in enumerate(sorted(mf.items())):
        v = views.get(m) or {}
        env = v.get("env") or ""
        dm = re.search(r"DEFINES=(\S+)", env)
        defs = [d for d in (dm.group(1).split(",") if dm else []) if d]
        cmd = [a.verilator, "-E", "-P", *[f"+define+{d}" for d in defs], *inc, *files]
        p = subprocess.run(cmd, cwd=B, capture_output=True, text=True)
        if p.returncode != 0:
            print(f"FLATTEN_FAIL {m}: {p.stderr[:800]}")
            return 1
        t = p.stdout
        names = sorted(set(re.findall(r"\bmodule\s+([A-Za-z_]\w*)", t)) - {m}, key=len, reverse=True)
        # single underscore: Verilator 5.050 encodes "__" in a hier-block name as "___05F" and then does NOT substitute the
        # block in its parent (X__m82 nested hier blocks were silently flattened: tkm_m_tp192's 32 e86 tile bodies -> sw2
        # memcg OOM at 240 GB, 10-18 09:51; with _m82 the parent pass is 207 MB, probe6 10-18 12:40).
        tag = f"_m{k}"
        if names:
            alt = "|".join(re.escape(n) for n in names)
            t = re.sub(r"\b(module\s+)(" + alt + r")\b", lambda x: x.group(1) + x.group(2) + tag, t)
            t = re.sub(r"(?<![\w$.])(" + alt + r")\b(?=\s*(?:#|[A-Za-z_]\w*\s*(?:\[[^\]]*\]\s*)?\())",
                       lambda x: x.group(1) + tag, t)
        if a.hier and m not in set(a.nohier.split(",")) and not m.startswith(("hbfd_rly_", "hfd_ckgen")) and "blackbox" not in t[:20000]:
            # Verilator hierarchical verilation: every hard master is verilated on its own (memory bounded per master,
            # as the die is hardened per master); the whole-die flat elaboration exceeded 380 GB (10-18)
            mm = re.search(r"\bmodule\s+" + re.escape(m) + r"\b", t)
            if "__" in m:
                print(f"HIER_NAME_WARN {m}: '__' in a hier-block name (Verilator 5.050 will not substitute it)")
            t = mark_hier(t, mm.end())
        if a.hier:
            for im in [x for x in a.inner_hier.split(",") if x]:
                for mm in list(re.finditer(r"\bmodule\s+" + re.escape(im + tag) + r"\b", t))[::-1]:
                    t = mark_hier(t, mm.end())
        (out / f"{m}.sv").write_text(t)
        rec[m] = dict(tag=tag, defines=defs, files=len(files), modules=len(names) + 1)
    (out / "flatten.json").write_text(json.dumps(rec, indent=1) + "\n")
    (B / "masters.f").write_text("\n".join(f"masters/{m}.sv" for m in sorted(mf)) + "\n")
    print(f"FLATTEN_OK masters={len(rec)} with_defines={sum(1 for r in rec.values() if r['defines'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
