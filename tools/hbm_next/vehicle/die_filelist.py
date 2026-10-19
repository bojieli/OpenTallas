#!/usr/bin/env python3
"""TOKEN-PASS-HBMDS (10-18): Verilator file list of a d4g die contract at a git revision.

Walks every contract master (source + rtl_deps) through the module definitions of git-tracked rtl/ + physical/ *.sv/*.v
at --rev (the walk of tools/hbm_die_v15/check_contract_modules.py) and resolves each module to ONE defining file:
the master's own source / rtl_deps first, else the only definer, else the definer nearest the instantiating file
(longest common directory prefix; ties and every multi-definer are listed in 'ambiguous').  Writes
  OUT/files.f     one tracked path a line, dependency order irrelevant (Verilator resolves)
  OUT/incdirs.f   +incdir+ of every directory that holds a selected file or a tracked .svh/.vh
  OUT/filelist.json  modules, file per module, ambiguous, missing, blackboxes (modules defined only under (* blackbox *))
    die_filelist.py --contract pre.json[.gz] --repo /home/ubuntu/OpenTallas --rev 7c124deae --out DIR
"""
import argparse, gzip, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hbm_die_v15"))


def strip(t):
    t = re.sub(r"(?m)^\s*`(define|ifdef|ifndef|else|endif|elsif|include|timescale|default_nettype|undef).*$", " ", t)
    t = re.sub(r"`\w+", " ", t)
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", " ", t)
    t = re.sub(r'"[^"\n]*"', '""', t)
    return t


KW = set("""always always_comb always_ff always_latch and assign begin buf case casex casez default defparam disable else end
endcase endfunction endmodule for force forever fork function generate endgenerate if initial inout input integer join
localparam logic module nand negedge nor not or output parameter posedge reg repeat return wire while xor xnor genvar
assert property sequence unique priority final import export typedef struct union enum packed signed unsigned string void
var const static bit byte int automatic""".split())
INST = re.compile(r"(?:^|;|\bbegin\b(?:\s*:\s*\w+)?|\belse\b|\bend\b)[ \t]*([A-Za-z_]\w*)\b[ \t]*(#\s*\((?:[^()]|\((?:[^()]|"
                  r"\([^()]*\))*\))*\)\s*)?([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)?\(", re.M)


def balanced(t, i):
    """text of the parenthesised group that starts just before index i (t[i-1] == '(')"""
    d, j = 1, i
    while j < len(t) and d:
        d += {"(": 1, ")": -1}.get(t[j], 0)
        j += 1
    return t[i:j]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--repo", default="/home/ubuntu/OpenTallas")
    ap.add_argument("--rev", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    git = lambda *x: subprocess.run(["git", "-C", a.repo, *x], capture_output=True, text=True, check=True).stdout
    c = json.load((gzip.open if a.contract.endswith(".gz") else open)(a.contract, "rt"))
    allf = [f for f in git("ls-tree", "-r", "--name-only", a.rev, "rtl", "physical").split("\n") if f]
    files = [f for f in allf if f.endswith((".sv", ".v")) and "/views/" not in f and "/tb" not in f.lower().split("/")[-1][:3]]
    hdrs = [f for f in allf if f.endswith((".svh", ".vh"))]
    pr = subprocess.run(["git", "-C", a.repo, "cat-file", "--batch"], input="".join(f"{a.rev}:{f}\n" for f in files).encode(),
                        capture_output=True, check=True).stdout
    texts, pos = {}, 0
    for f in files:
        nl = pr.index(b"\n", pos); hdr = pr[pos:nl].split(); pos = nl + 1
        if len(hdr) < 3 or hdr[1] != b"blob":
            continue
        n = int(hdr[2]); texts[f] = pr[pos:pos + n].decode("utf-8", "replace"); pos += n + 1
    defs, body, bb, bbmods = {}, {}, set(), {}
    for f, raw in texts.items():
        if "module" not in raw:
            continue
        t = strip(raw)
        for m in re.finditer(r"\b(?:module|macromodule)\s+(\w+)(.*?)\bendmodule\b", t, re.S):
            defs.setdefault(m.group(1), []).append(f)
            body[(m.group(1), f)] = m.group(2)
            if re.search(r"\(\*\s*blackbox\s*\*\)\s*module\s+" + m.group(1) + r"\b", raw) or f.endswith("_bb.v"):
                bb.add(m.group(1))
                bbmods.setdefault(f, set()).add(m.group(1))
    masters = {}
    for i in c["instances"].values():
        masters.setdefault(i["master"], [s for s in [i.get("source")] + list(i.get("rtl_deps", [])) if s])
    pick, amb, missing, asserts = {}, {}, {}, set()

    BAD = re.compile(r"(^rtl/test/|/tb_|^tb_|/ref_tile/[^/]+/src/|/pinned/|/oracle_pinned/|val_bad|_simstub|_bb\.v$|"
                     r"_sim\.sv$|_beh\.sv$|_dpi\.sv$|arithmetic_blackboxes|sram_models\.sv|/epilogue/tb_)")

    def rank(mod, f, nd):
        return (mod in bbmods.get(f, ()), bool(BAD.search(f)), not f.startswith(("rtl/", "physical/asap7_memory_macros/")),
                -len(os.path.commonpath([nd, os.path.dirname(f)])) if nd else 0, "_v2/" in f, f)

    def fits(mod, f, need):
        b = body[(mod, f)]
        return all(re.search(r"\b" + n + r"\b", b) for n in need)

    def choose(mod, near, pref, need=()):
        d = defs[mod]
        if need:
            ok = [f for f in d if fits(mod, f, need)]
            d = ok or d
        for p in pref:
            if p in d:
                return p
        if len(d) == 1:
            return d[0]
        nd = os.path.dirname(near or "")
        best = sorted(d, key=lambda f: rank(mod, f, nd))
        amb[mod] = dict(chosen=best[0], all=d, near=near)
        return best[0]

    # walk keyed by (module, chosen file): the same module name may resolve to different files under different
    # instantiating files (hard masters are synthesised separately, so variants with one name coexist on the die)
    CAND = re.compile(r"\b([A-Za-z_]\w*)\s*(?=#\s*\(|[A-Za-z_]\w*\s*(?:\[[^\]]*\]\s*)?\()")

    def children(bt):
        """{sub: needed param/port names} of every instantiation of a known module in a body (nested-paren safe)"""
        needs = {}
        for m in CAND.finditer(bt):
            sub = m.group(1)
            if sub not in defs or sub in KW:
                continue
            j = m.end()
            txt = ""
            if bt[j] == "#":
                k = bt.index("(", j) + 1
                ptxt = balanced(bt, k)
                txt += ptxt
                j = k + len(ptxt)
            mm = re.match(r"\s*([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)?\(", bt[j:])
            if not mm or mm.group(1) in KW:
                continue
            txt += balanced(bt, j + mm.end())
            needs.setdefault(sub, set()).update(re.findall(r"\.(\w+)\s*\(", txt))
        return needs

    visited, inst_pick, master_files = set(), {}, {}
    for root, src in masters.items():
        stack, mv = [(root, None, src, ())], set()
        while stack:
            mod, near, pref, need = stack.pop()
            if mod not in defs:
                if re.search(r"_(must|requires)_|_requires$", mod):
                    asserts.add(mod)
                else:
                    missing[mod] = near
                continue
            f = choose(mod, near, pref if near is None else [], need)
            inst_pick[(near, mod)] = f
            pick.setdefault(mod, f)
            if (mod, f) in mv:
                continue
            mv.add((mod, f))
            for sub, nd in children(body[(mod, f)]).items():   # one variant per (instantiating file, module)
                stack.append((sub, f, [], tuple(sorted(nd))))
        visited |= mv
        master_files[root] = sorted({f for (_, f) in mv})
    sel_set = {f for (_, f) in visited}
    # every module name defined by more than one selected file is UNIQUIFIED: definition M -> M__u<k> in file k and every
    # instantiation of M in a selected file I -> the variant the walk chose under I
    defs_sel = {}
    for (mod, f) in [(m, f) for m, fs in defs.items() for f in fs if f in sel_set]:
        defs_sel.setdefault(mod, []).append(f)
    conflicts = {m: sorted(fs) for m, fs in defs_sel.items() if len(set(fs)) > 1}
    tag = {(m, f): f"{m}__u{k}" for m, fs in conflicts.items() for k, f in enumerate(fs)}
    renames = {}
    for f in sel_set:
        r = {}
        for m in conflicts:
            if f in conflicts[m]:
                r[("def", m)] = tag[(m, f)]
            if (f, m) in inst_pick:
                r[("inst", m)] = tag[(m, inst_pick[(f, m)])]
            elif any(re.search(r"(?m)^\s*" + m + r"\b", body.get((mm, f), "")) for mm in [x for x, ff in visited if ff == f]):
                # instantiated in f but not walked from f (generate branch the walk skipped): nearest variant
                r[("inst", m)] = tag[(m, choose(m, f, []))]
        if r:
            renames[f] = {f"{k[0]}:{k[1]}": v for k, v in r.items()}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    sel = sorted(sel_set)
    (out / "renames.json").write_text(json.dumps(renames, indent=1) + "\n")
    (out / "master_files.json").write_text(json.dumps(master_files, indent=1) + "\n")
    (out / "files.f").write_text("\n".join(sel) + "\n")
    dirs = sorted({os.path.dirname(f) for f in sel} | {os.path.dirname(h) for h in hdrs if any(os.path.dirname(h) == os.path.dirname(f) for f in sel)})
    (out / "incdirs.f").write_text("\n".join(f"+incdir+{d}" for d in dirs) + "\n")
    hsel = sorted(h for h in hdrs if os.path.dirname(h) in set(dirs))
    (out / "headers.f").write_text("\n".join(hsel) + "\n")
    rec = dict(contract=a.contract, rev=a.rev, masters=len(masters), modules=len(pick), files=len(sel),
               blackboxes=sorted({m for (m, f) in visited if m in bbmods.get(f, ())}), static_asserts=sorted(asserts), missing=missing,
               uniquified=conflicts,
               ambiguous=amb, module_file=pick)
    (out / "filelist.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"DIE_FILELIST modules={len(pick)} files={len(sel)} ambiguous={len(amb)} missing={len(missing)} "
          f"uniquified={len(conflicts)} blackboxes={rec['blackboxes']}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
