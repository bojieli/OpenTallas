#!/usr/bin/env python3
"""Bit-plane VM SYSTEM bench set (tb_qfd_vm_bv_ports, XPR): the whole record with one command.

  tools/qwen_tp8/vm_plane_sysbench_set.py [--src ROOT] [--host ot-epyc1tb] [--only name,name] [--collect]

Syncs the needed sources of ROOT (default: this checkout) to <host>:~/claude-vm-rtl-1013/A/wt, launches every run
of RUNS in parallel there (each under `ot-heavy --mem`; nothing is built on localhost), fetches the run logs and
writes results/rtl/qwen_tp8_vm_plane_20261013/system/{record.json,<name>.log} into THIS checkout.
--collect skips the launch and rebuilds the record from the logs already on the host.
Exit status 0 only when record "ok" is true:
  every PASS-expected run prints PASS with exactly the stated counts, every FAIL-expected mutant prints FAIL
  (a real bench FAIL line with rc 0: a build failure or a crash is not a killed mutant), and the known system-bench
  gap (MUT=5) is killed by the committed leaf miter.
The -G sets are the predecessor's scratch command lines verbatim (recovered from each scratch build's
Vtb_qfd_vm_bv_ports__verFiles.dat); shape rule (parent comments): VMT x latency XVM = 12 + RV + RO + 7, SU answer
VL = 7 + RV + RO + 5, bit plane XVM += XPR + 1 - RO.  Bench defaults: RV 1, RO 2, SEED 5, NRB 16, ELEMS 16384.
"""
import argparse, hashlib, json, os, re, shlex, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REC = "results/rtl/qwen_tp8_vm_plane_20261013/system"
LEAF_REC = "results/rtl/qwen_tp8_vm_plane_20261013/leaf_miter/record.json"
RDIR = "claude-vm-rtl-1013/A"
COMMON = "-GCYCLES=40000 -GTSR=1 -GXQT=1 -GMEE=1 -GVMT=1"
BASE_FILES = [
    "rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv",
    "rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv",
    "rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv",
    "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv",
    "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv",
    "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv",
    "rtl/hdc/ot_hdc_delay.sv",
]
RQ_FILES = [
    "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_region_quarter.sv",
    "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_xfifo8_t.sv",
    "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_answer_tiles.sv",
]
RQ = "+define+OT_QFD_VM_TILE_MOD=ot_qfd_vm_region_quarter " + " ".join(RQ_FILES)
R21 = "-GSEED=7 -GRV=2 -GRO=1 -GVL=15"
N64 = "-GSEED=5 -GRV=1 -GRO=1 -GVL=14 -GNRB=64"
C_R21 = dict(NRB=16, SW=8, VL=15, su_reads=60170, row_reads=9427, tuples=2683, bursts=1612, land_steps=1603)
C_N64 = dict(NRB=64, SW=8, VL=14, su_reads=60313, row_reads=9296, tuples=2992, bursts=1635, land_steps=1625)


def run(name, args, expect, what, counts=None, extra="", mem=8, scratch=None):
    return dict(name=name, args=args, extra=extra, expect=expect, what=what, counts=counts, mem=mem, scratch=scratch,
                tile="ot_qfd_vm_region_quarter" if extra else "ot_qfd_vm_grp")


# expect: PASS | FAIL | GAP (a mutant the system bench is known not to kill: recorded, never counted as a mutant pass)
#         | INFO (recorded, not gated).  counts: required on the PASS line.  scratch: the scratch log's line (reference).
RUNS = [
    run("base_r21", R21 + " -GXVM=22", "PASS", "XPR=0 regression, vmt_r21 shape (RV 2 RO 1), tile ot_qfd_vm_grp", C_R21),
    run("bp_r21", R21 + " -GXVM=32 -GXPR=10", "PASS", "XPR=10, r21 (RV 2 RO 1)", C_R21),
    run("bp_s3", "-GSEED=3 -GXVM=31 -GVL=15 -GXPR=10", "PASS", "XPR=10, bench default RV 1 RO 2, stimulus SEED 3",
        dict(NRB=16, SW=8, VL=15, su_reads=59514, row_reads=8973, tuples=3016, bursts=1560, land_steps=1550)),
    run("bp_s9", "-GSEED=9 -GXVM=31 -GVL=15 -GXPR=10", "PASS", "XPR=10, bench default RV 1 RO 2, stimulus SEED 9",
        dict(NRB=16, SW=8, VL=15, su_reads=61202, row_reads=9670, tuples=2711, bursts=1583, land_steps=1574)),
    run("bp_r11", "-GSEED=5 -GRV=1 -GRO=1 -GXVM=31 -GVL=14 -GXPR=10", "PASS", "XPR=10, r11 (RV 1 RO 1), SEED 5",
        dict(NRB=16, SW=8, VL=14, su_reads=60240, row_reads=9406, tuples=2630, bursts=1606, land_steps=1597)),
    run("bp_nomee", "-GSEED=3 -GXVM=31 -GVL=15 -GXPR=10 -GMEE=0", "PASS", "XPR=10, MEE=0 (no early enable), RV 1 RO 2, SEED 3",
        dict(NRB=16, SW=8, VL=15, su_reads=59130, row_reads=8975, tuples=2835, bursts=1561, land_steps=1551)),
    run("bp_r21_x11", R21 + " -GXVM=33 -GXPR=11", "PASS", "XPR=11 (one more relay), r21", C_R21),
    run("bp_r21_m3", R21 + " -GXVM=32 -GXPR=10 -GMUT=3", "FAIL", "mutant: plane 5 fine rotation wrong", scratch="x=37438"),
    run("bp_r21_m4", R21 + " -GXVM=32 -GXPR=10 -GMUT=4", "FAIL", "mutant: plane 5 element shift wrong", scratch="x=38308"),
    run("bp_r21_m5", R21 + " -GXVM=32 -GXPR=10 -GMUT=5", "GAP",
        "mutant: plane 5 range count ignored. KNOWN SYSTEM-BENCH GAP: the bench never issues an x beat past ELEMS, "
        "so this mutant is invisible here; it is killed only by the leaf miter (lf_p3 in " + LEAF_REC + ")", C_R21),
    run("bp_r21_m6", R21 + " -GXVM=32 -GXPR=10 -GMUT=6", "FAIL", "mutant: one relay free-runs", scratch="x=1158"),
    run("bp_r21_m7", R21 + " -GXVM=32 -GXPR=10 -GMUT=7", "FAIL", "mutant: planes 0 and 1 swapped", scratch="x=38028"),
    run("bp_r21_lat9", R21 + " -GXVM=31 -GXPR=10", "INFO",
        "XVM one edge SHORT of the rule (31 instead of 32): the scratch run PASSED (row_reads 9422). XVM goes to both "
        "the DUT and the reference, so the bench does not pin the latency rule by itself; recorded, not gated",
        scratch="PASS row_reads=9422"),
    run("n64_base", N64 + " -GXVM=21", "PASS", "NRB=64 XPR=0, default tile ot_qfd_vm_grp (the scratch n64_base shape)",
        C_N64, mem=24),
    run("n64_base_rq", N64 + " -GXVM=21", "PASS", "NRB=64 XPR=0, region tile ot_qfd_vm_region_quarter", C_N64, RQ, 24),
    run("n64_bp_rq", N64 + " -GXVM=31 -GXPR=10", "PASS", "NRB=64 XPR=10, region tile", C_N64, RQ, 24),
    run("n64_bp_rq_m3", N64 + " -GXVM=31 -GXPR=10 -GMUT=3", "FAIL", "NRB=64 region tile, mutant: plane 5 fine rotation",
        None, RQ, 24, "x=38574"),
    run("n64_bp_rq_m6", N64 + " -GXVM=31 -GXPR=10 -GMUT=6", "FAIL", "NRB=64 region tile, mutant: one relay free-runs",
        None, RQ, 24, "x=249"),
]


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=ROOT)
    ap.add_argument("--host", default="ot-epyc1tb")
    ap.add_argument("--only", default="")
    ap.add_argument("--collect", action="store_true")
    a = ap.parse_args()
    src = os.path.abspath(a.src)
    runs = [r for r in RUNS if not a.only or r["name"] in a.only.split(",")]
    files = BASE_FILES + RQ_FILES
    out = os.path.join(ROOT, REC)
    os.makedirs(out, exist_ok=True)
    runner = os.path.join(HERE, "vm_plane_sysbench.sh")
    if not a.collect:
        sh(f"ssh {a.host} mkdir -p {RDIR}/wt {RDIR}/b", check=True)
        subprocess.run(["rsync", "-a", "--relative"] + files + [f"{a.host}:{RDIR}/wt/"], cwd=src, check=True)
        subprocess.run(["rsync", "-a", runner, f"{a.host}:{RDIR}/vm_plane_sysbench.sh"], check=True)
        lines = [f"cd ~/{RDIR} && rm -f b/*.line"]
        for r in runs:
            cmd = f"./vm_plane_sysbench.sh {r['name']} {shlex.quote(r['args'])} {r['extra']}"
            lines.append(f"( ot-heavy --mem {r['mem']} -- {cmd} > b/{r['name']}.line 2>b/{r['name']}.err ) &")
        lines.append("wait")
        p = subprocess.run(["ssh", a.host, "bash", "-s"], input="\n".join(lines) + "\n", text=True)
        if p.returncode:
            print("remote launch rc", p.returncode, file=sys.stderr)
    # the remote tree must be byte-identical to the hashed sources
    hashes = {f: sha(os.path.join(src, f)) for f in files}
    rh = sh(f"ssh {a.host} 'cd {RDIR}/wt && sha256sum {' '.join(files)}; sha256sum ../vm_plane_sysbench.sh; "
            f"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --version; hostname'").stdout.split("\n")
    remote = {l.split()[1]: l.split()[0] for l in rh if re.match(r"^[0-9a-f]{64} ", l)}
    tree_ok = all(remote.get(f) == h for f, h in hashes.items()) and remote.get("../vm_plane_sysbench.sh") == sha(runner)
    ver = next((l for l in rh if l.startswith("Verilator")), "?")
    host = [l for l in rh if l.strip()][-1] if rh else "?"
    commit = sh(f"git -C {shlex.quote(src)} rev-parse HEAD").stdout.strip()
    dirty = sh(f"git -C {shlex.quote(src)} status --porcelain -- {' '.join(files)}").stdout.strip()
    names = " ".join(r["name"] for r in runs)
    subprocess.run(f"cd {shlex.quote(out)} && for n in {names}; do scp -q {a.host}:{RDIR}/b/$n.log . 2>/dev/null; done",
                   shell=True)
    rl = sh(f"ssh {a.host} 'cd {RDIR}/b && for n in {names}; do echo \"@@ $n\"; cat $n.line 2>/dev/null; done'").stdout
    got = {}
    for blk in rl.split("@@ ")[1:]:
        n, _, rest = blk.partition("\n")
        got[n.strip()] = rest.strip()
    leaf = {}
    try:
        leaf = json.load(open(os.path.join(src, LEAF_REC)))["runs"]["lf_p3"]
    except Exception as e:  # noqa
        leaf = {"error": str(e)}
    leaf_kills = leaf.get("expect") == "FAIL" and leaf.get("got") == "FAIL"
    recs, bad = [], []
    for r in runs:
        line = got.get(r["name"], "")
        m = re.search(r"rc=(\S+) ((?:PASS|FAIL) .*?) maxrss_kb=(\d+) wall=([\d.]+) build_s=(\d+)", line)
        o = dict(name=r["name"], what=r["what"], args=f"{COMMON} {r['args']}", extra_verilator_args=r["extra"],
                 tile_module=r["tile"], expected=r["expect"], ot_heavy_mem_gb=r["mem"], scratch_reference=r["scratch"],
                 log=f"{r['name']}.log")
        if not m:
            o.update(observed="NO-RESULT", observed_line=line[:300], ok=False)
        else:
            res = m.group(2)
            cnt = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", res)} if res.startswith("PASS") else None
            o.update(observed=res.split()[0], observed_line=res, rc=int(m.group(1)), counts=cnt,
                     fail_counts=dict(re.findall(r"(\w+)=(\S+)", res)) if res.startswith("FAIL") else None,
                     maxrss_kb=int(m.group(3)), wall_s=float(m.group(4)), build_s=int(m.group(5)))
            exp_cnt = r["counts"]
            cnt_ok = exp_cnt is None or (cnt is not None and all(cnt.get(k) == v for k, v in exp_cnt.items()))
            o["expected_counts"] = exp_cnt
            if r["expect"] == "PASS":
                o["ok"] = o["observed"] == "PASS" and o["rc"] == 0 and cnt_ok
            elif r["expect"] == "FAIL":
                o["ok"] = o["observed"] == "FAIL" and o["rc"] == 0
                o["scratch_match"] = r["scratch"] in res if r["scratch"] else None
            elif r["expect"] == "GAP":
                # not a mutant-gate pass: the record stays ok only while the leaf miter kills this mutant
                o["mutant_killed_by_system_bench"] = o["observed"] == "FAIL"
                o["killed_by_leaf_miter"] = leaf_kills
                o["leaf_miter_run"] = leaf
                o["ok"] = leaf_kills
            else:
                o["ok"] = None
        if o["ok"] is False:
            bad.append(r["name"])
        recs.append(o)
    by = {o["name"]: o for o in recs}

    def same(x, y):
        return x in by and y in by and by[x].get("counts") is not None and by[x].get("counts") == by[y].get("counts")
    cross = {}
    if not a.only:
        cross = {"xpr0_eq_xpr10_r21": same("base_r21", "bp_r21"), "n64_base_rq_eq_bp_rq": same("n64_base_rq", "n64_bp_rq"),
                 "n64_grp_eq_region_tile": same("n64_base", "n64_base_rq")}
        bad += [k for k, v in cross.items() if not v]
    if not tree_ok:
        bad.append("remote-tree-differs-from-hashed-sources")
    if dirty:
        bad.append("sources-dirty-vs-commit")
    gate = lambda e: [o["name"] for o in recs if o["expected"] == e]  # noqa
    rec = {
        "record": "qwen_tp8_vm_plane_system_bench",
        "date": datetime.date.today().isoformat(),
        "ok": not bad and not a.only,
        "not_ok_because": bad + (["partial set (--only)"] if a.only else []),
        "bench": "rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv (top tb_qfd_vm_bv_ports), ELEMS 16384 (NOT the production 177808)",
        "host": host, "launcher": "ot-heavy --mem <ot_heavy_mem_gb> per run, all runs in parallel",
        "verilator": ver, "runner": "tools/qwen_tp8/vm_plane_sysbench.sh", "driver": "tools/qwen_tp8/vm_plane_sysbench_set.py",
        "source_commit": commit, "sources_clean_at_commit": not dirty, "remote_tree_matches_sha256": tree_ok,
        "sources_sha256": hashes, "runner_sha256": sha(runner),
        "summary": {"pass_expected": gate("PASS"), "fail_expected_mutants": gate("FAIL"),
                    "known_system_bench_gaps": gate("GAP"), "info_not_gated": gate("INFO"),
                    "pass_ok": sum(1 for o in recs if o["expected"] == "PASS" and o["ok"]),
                    "mutants_killed": sum(1 for o in recs if o["expected"] == "FAIL" and o["ok"]),
                    "cross_checks": cross},
        "known_gaps": ["MUT=5 (plane 5 ignores the in-range count) PASSES the system bench: no x beat past ELEMS is ever "
                       "issued. It is NOT counted as a mutant-gate pass; the kill is the leaf miter's lf_p3 (" + LEAF_REC + ")."],
        "runs": recs,
    }
    json.dump(rec, open(os.path.join(out, "record.json"), "w"), indent=1)
    for o in recs:
        print(f"{o['name']:14s} exp {o['expected']:4s} got {o['observed']:9s} ok={o['ok']} {o.get('observed_line', '')[:150]}"
              f" rss={o.get('maxrss_kb')} wall={o.get('wall_s')}")
    print("cross", cross, "OK" if rec["ok"] else f"NOT OK: {rec['not_ok_because']}")
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
