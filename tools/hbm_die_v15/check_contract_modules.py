#!/usr/bin/env python3
"""Every module a die contract instantiates resolves to a COMMITTED file (H-NETLIST/COLL 2026-10-16).

For each contract master (instances[*].master, source + rtl_deps) walk the instantiation hierarchy through the module
definitions found in git-tracked RTL (`git ls-files rtl physical` *.sv/*.v at --rev) and report every module name that
no tracked file defines.  Missing = SYNTH would fail (H-DIE d4f SYNTH 59a003354: qso_n1s0_b1 / qso_n2s1_b1).
    check_contract_modules.py --contract results/arch/hbm_die_v16_d4f_tp192/contract.json.gz [--rev HEAD] [--json OUT]
Exit 0 all resolved, 1 missing modules."""
import argparse, gzip, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KW = set("""always always_comb always_ff always_latch and assign begin buf bufif0 bufif1 case casex casez cmos deassign default
defparam disable edge else end endcase endfunction endmodule endprimitive endspecify endtable endtask event for force forever
fork function highz0 highz1 if ifnone initial inout input integer join large macromodule medium module nand negedge nmos nor
not notif0 notif1 or output parameter pmos posedge primitive pull0 pull1 pulldown pullup rcmos real realtime reg release
repeat rnmos rpmos rtran rtranif0 rtranif1 scalared small specify specparam strong0 strong1 supply0 supply1 table task time
tran tranif0 tranif1 tri tri0 tri1 triand trior trireg vectored wait wand weak0 weak1 while wire wor xnor xor genvar
generate endgenerate localparam logic bit byte int automatic return assert property sequence unique priority final
import export typedef struct union enum packed signed unsigned string void var const static""".split())


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout


def strip(t):
    t = re.sub(r"(?m)^\s*`(define|ifdef|ifndef|else|endif|elsif|include|timescale|default_nettype|undef).*$", " ", t)
    t = re.sub(r"`\w+", " ", t)
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"//[^\n]*", " ", t)
    t = re.sub(r'"[^"\n]*"', '""', t)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--json")
    a = ap.parse_args()
    op = gzip.open if a.contract.endswith(".gz") else open
    c = json.load(op(ROOT / a.contract if not a.contract.startswith("/") else a.contract, "rt"))
    files = [f for f in git("ls-tree", "-r", "--name-only", a.rev, "rtl", "physical").split("\n")
             if f.endswith((".sv", ".v")) and "/views/" not in f]
    defs, body = {}, {}
    # one git cat-file --batch for every tracked file (git show per file is minutes)
    pr = subprocess.run(["git", "-C", str(ROOT), "cat-file", "--batch"], input="".join(f"{a.rev}:{f}\n" for f in files).encode(),
                        capture_output=True, check=True).stdout
    texts, pos = {}, 0
    for f in files:
        nl = pr.index(b"\n", pos); hdr = pr[pos:nl].split(); pos = nl + 1
        if len(hdr) < 3 or hdr[1] != b"blob":
            continue
        size = int(hdr[2]); texts[f] = pr[pos:pos + size].decode("utf-8", "replace"); pos += size + 1
    for f, raw in texts.items():
        if re.search(r"\bmodule\b", raw) is None:
            continue
        t = strip(raw)
        for m in re.finditer(r"\b(?:module|macromodule|primitive)\s+(\w+)(.*?)\bend(?:module|primitive)\b", t, re.S):
            defs.setdefault(m.group(1), []).append(f)
            body.setdefault(m.group(1), m.group(2))
    # an instantiation starts a statement: line start (after optional begin/label/else/`;`), NAME [#(...)] INST [range] (
    inst_re = re.compile(r"(?:^|;|\bbegin\b(?:\s*:\s*\w+)?|\belse\b|\bend\b)[ \t]*([A-Za-z_]\w*)\b[ \t]*(?:#\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\s*)?([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)?\(", re.M)
    masters = {}
    for n, i in c["instances"].items():
        masters.setdefault(i["master"], (i.get("source"), i.get("rtl_deps", [])))
    missing, asserts, seen, tracked_src = {}, {}, set(), set(files)
    stack = [(m, m) for m in masters]
    src_missing = sorted({s for s, d in masters.values() for s in [s] + list(d) if s and s not in tracked_src})
    while stack:
        mod, root = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        if mod not in defs:
            if re.search(r"_(must|requires)_|_requires$", mod):
                asserts.setdefault(mod, set()).add(root)   # static elaboration-assert module (never defined on purpose)
            else:
                missing.setdefault(mod, set()).add(root)
            continue
        for m in inst_re.finditer(body[mod]):
            sub, inst = m.group(1), m.group(2)
            if sub in KW or inst in KW or sub.startswith("$") or re.search(r"_ASAP7_75t_[RLS]L?$", sub):
                continue   # keywords, system tasks, ASAP7 standard cells (physical library, not RTL)
            if sub not in defs and not re.search(r"\b" + re.escape(sub) + r"\s*(?:#|\w)", body[mod]):
                continue
            stack.append((sub, root))
    # names that look like instantiations but are e.g. function calls / types are only reported if never defined
    out = dict(contract=a.contract, rev=git("rev-parse", "--short=9", a.rev).strip(), masters=len(masters),
               modules_walked=len(seen), static_assert_modules=sorted(asserts), missing={k: sorted(v) for k, v in sorted(missing.items())},
               source_files_not_tracked=src_missing)
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    print(f"CONTRACT_MODULES {'PASS' if not missing and not src_missing else 'FAIL'} rev={out['rev']} masters={len(masters)} "
          f"modules={len(seen)} missing={len(missing)} untracked_sources={len(src_missing)}")
    for k, v in out["missing"].items():
        print(f"  MISSING {k} (under {', '.join(v[:4])})")
    for s in src_missing:
        print(f"  UNTRACKED {s}")
    sys.exit(1 if missing or src_missing else 0)


if __name__ == "__main__":
    main()
