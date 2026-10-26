#!/usr/bin/env python3
"""RTL-vs-RTL LEC of the qb loop-variable re-scope (S81-CORE-LAT-R2/LV 2026-10-26).

    python3 lec_lv.py REPO OLD_SHA NEW_ROOT WORK [--fe verilog,slang]     exit 0 = every pair EQUIVALENT

OLD = the q-element source list (rtl_list.txt) at OLD_SHA, every module renamed *_old (mk_old.sh); NEW = the same list
under NEW_ROOT.  lv_top (lec_top.sv) instantiates both q elements at the S81 die parameters, so every module is
elaborated at its in-context parameters.  Per frontend (Yosys read_verilog -sv, and read_slang: two independent HDL
frontends), per module pair (old paramod <-> new paramod with the same parameters) of the five changed / containing
modules: flatten both, memory_map, remove unused wires (including public loop integers), async2sync, equiv_make old new, equiv_simple -seq, equiv_struct (ROM black boxes
merged once their input pins are proved equal; the merged cell's outputs then become one shared free $anyseq input),
equiv_simple -seq, equiv_induct -seq, equiv_status.
Verdict per pair: EQUIVALENT (every $equiv proved) / NOT_PROVEN (equiv_status lists the unproven signals).
Defines: SYNTHESIS (as the kit synthesis reads them).  Results: WORK/lec_lv.json.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

TARGETS = ["ot_v41_segtree6", "ot_v41_chain4", "ot_v41_bterm5_w10", "ot_v41_rom_elem_qx_pq_w10",
           "ot_v41_rom_elem_q_qxpq_w10"]
D = Path(__file__).resolve().parent
YOSYS = os.environ.get("YOSYS", os.path.expanduser("~/.local/opentallas-tools/bin/yosys"))


TOPF, TOP = "lec_top.sv", "lv_top"


def read_cmds(fe, files):
    stubs, top = D / "lec_stubs.v", D / TOPF
    if fe == "verilog":
        c = ["verilog_defaults -add -DSYNTHESIS", f"read_verilog -sv {stubs}"]
        c += [f"read_verilog -defer -sv {f}" for f in files] + [f"read_verilog -defer -sv {top}"]
        c += [f"hierarchy -check -top {TOP}"]
    else:
        c = [f"read_slang --keep-hierarchy --compat=vcs --ignore-assertions -DSYNTHESIS --top {TOP} {stubs} "
             + " ".join(map(str, files)) + f" {top}", "setattr -unset init", f"hierarchy -check -top {TOP}"]
    return c + ["proc"]


def yosys(script, log):
    t = time.time()
    p = subprocess.run([YOSYS, "-q", "-l", str(log), "-s", str(script)], capture_output=True, text=True)
    return p.returncode, time.time() - t


def base(name):
    """module base name of a paramod (read_verilog: $paramod\\M\\P=..; $paramod$hash\\M; slang: M$N or M)."""
    n = name.lstrip("\\")
    m = re.match(r"^\$paramod\$[0-9a-f]+\\(\w+)$", n) or re.match(r"^\$paramod\\(\w+)\\", n) or re.match(r"^(\w+?)(\$\S*)?$", n)
    return m.group(1) if m else n


def main():
    global TARGETS, TOPF, TOP
    a = sys.argv[1:]
    if "--top" in a:      # --top FILE:MODULE:TARGET[,TARGET..] (another wrapper in this directory)
        i = a.index("--top"); TOPF, TOP, tg = a[i + 1].split(":"); TARGETS = tg.split(","); del a[i:i + 2]
    fes = ["verilog", "slang"]
    if "--fe" in a:
        i = a.index("--fe"); fes = a[i + 1].split(","); del a[i:i + 2]
    repo, old, new_root, work = a[0], a[1], Path(a[2]).resolve(), Path(a[3]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(D / "mk_old.sh"), repo, old, str(work / "old")], check=True)
    lst = (D / "rtl_list.txt").read_text().split()
    files = [new_root / f for f in lst] + [work / "old" / f for f in lst]
    ver = subprocess.run([YOSYS, "-V"], capture_output=True, text=True).stdout.strip()
    res = {"yosys": ver, "old_sha": old, "wrapper": f"{TOPF}:{TOP}", "frontends": {}}
    rc_all = 0
    for fe in fes:
        w = work / fe; w.mkdir(exist_ok=True)
        s1 = w / "elab.ys"
        s1.write_text("\n".join(read_cmds(fe, files) + [f"tee -q -o {w}/mods.txt ls"]) + "\n")
        rc, dt = yosys(s1, w / "elab.log")
        fr = {"elab_rc": rc, "elab_s": round(dt, 1), "pairs": []}
        res["frontends"][fe] = fr
        if rc != 0:
            fr["verdict"] = "ELAB_FAIL"; rc_all = 1; continue
        mods = [l.strip() for l in (w / "mods.txt").read_text().splitlines() if l.startswith("  ")]
        todo = []
        # pair: new module M (base in TARGETS) with old module whose name is the same with M -> M_old
        for t in TARGETS:
            news = [m for m in mods if base(m) == t]
            olds = [m for m in mods if base(m) == t + "_old"]
            pairs = []
            if fe == "verilog":   # $paramod$<param hash>\M / $paramod\M\P=.. / M: the old twin is <name>_old
                pairs = [(n + "_old", n) for n in news if n + "_old" in olds]
            else:                 # slang names each instance's module <M>$<instance path>: pair u_old* <-> u_new*
                pairs = [(o, o.replace(t + f"_old${TOP}.u_old", t + f"${TOP}.u_new", 1)) for o in olds]
                pairs = [(o, n) for o, n in pairs if n in news]
            if not pairs or len(pairs) != len(news) or len(pairs) != len(olds):
                fr["pairs"].append({"module": t, "verdict": "NO_PAIR", "old": olds, "new": news}); rc_all = 1
                continue
            for k, (o, n) in enumerate(pairs):
                todo.append((t, f"{t}_{k}", o, n))
        # one script: elaborate once, then per pair load the elaborated design and check it
        cmds = read_cmds(fe, files) + ["design -save elab"]
        for t, tag, o, n in todo:
            cmds += ["design -load elab", "setattr -mod -unset keep_hierarchy", f"rename {o} lv_gold", f"rename {n} lv_gate", "flatten lv_gold lv_gate",
                     "memory -nomap lv_gold lv_gate", "memory_map lv_gold lv_gate", "opt_clean -purge lv_gold lv_gate",
                     "async2sync lv_gold lv_gate", "equiv_make lv_gold lv_gate lv_eq",
                     "equiv_simple -seq 5 lv_eq", "equiv_struct lv_eq",
                     # the merged (shared) ROM macro cell -> a free per-cycle input ($anyseq) so equiv_induct has a SAT
                     # model; the ROM input-pin $equiv cells stay compare points.  An unmerged gate-side ROM gets its
                     # own $anyseq and fails the proof (never a false pass).
                     f"tee -q -o {w}/{tag}.roms select -count lv_eq/t:ot_rom_*", "cd lv_eq", "delete t:ot_rom_*",
                     "setundef -undriven -anyseq", "cd ..", "equiv_simple -seq 5 lv_eq",
                     "equiv_induct -seq 5 lv_eq", f"tee -o {w}/{tag}.status equiv_status lv_eq"]
        s = w / "check.ys"
        s.write_text("\n".join(cmds) + "\n")
        rc, dt = yosys(s, w / "check.log")
        fr["check_rc"], fr["check_s"] = rc, round(dt, 1)
        for t, tag, o, n in todo:
            st = (w / f"{tag}.status").read_text() if (w / f"{tag}.status").exists() else ""
            m = re.search(r"Found (\d+) \$equiv cells.*?Of those cells (\d+) are proven and (\d+) are unproven", st, re.S)
            v = "EQUIVALENT" if rc == 0 and m and m.group(3) == "0" and int(m.group(1)) > 0 else "NOT_PROVEN"
            if v != "EQUIVALENT":
                rc_all = 1
            fr["pairs"].append({"module": t, "old": o, "new": n, "verdict": v,
                                "equiv_cells": int(m.group(1)) if m else None,
                                "proven": int(m.group(2)) if m else None,
                                "unproven": int(m.group(3)) if m else None})
            print(fe, tag, v, fr["pairs"][-1]["equiv_cells"], fr["pairs"][-1]["unproven"], flush=True)
    res["verdict"] = "EQUIVALENT" if rc_all == 0 else "NOT_PROVEN"
    (work / "lec_lv.json").write_text(json.dumps(res, indent=1) + "\n")
    print("LEC_LV", res["verdict"])
    return rc_all


if __name__ == "__main__":
    sys.exit(main())
