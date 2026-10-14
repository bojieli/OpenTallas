#!/usr/bin/env python3
"""Qwen TP8 VM leaf gates at the ROUTED parameters: the whole record with one command.

  tools/qwen_tp8/vm_leaf_gate_set.py [--only name,name] [--hosts a,b] [--collect]

Syncs the sources to ~/claude-vm-verif-1013/G on the fleet hosts, launches every run of RUNS in parallel, ONE
`ot-run --mem` per bench (ot-run picks the host; nothing is built on localhost), fetches the logs and writes
results/rtl/qwen_tp8_vm_plane_20261013/leaf_gate/{record.json,<name>.log}.  Exit 0 only when every PASS-expected run
printed PASS (rc 0) and every mutant printed a real FAIL line (rc 1; a build failure is not a killed mutant).
--collect launches nothing: it keeps the runs of the committed record (their sources must still hash the same) and
re-evaluates the leaf table against the current system record.
The runner is tools/qwen_tp8/vm_leaf_gate.sh (also the command of the composition gates qfd_vm_region_prod /
qfd_vm_xplane_prod in tools/ref_tile/composition_gates.json).  LEAVES below is the qualification table of the closed
VM leaves: routed module + parameters, what the closed job's own bench list ran, and the runs that bind it here.
"""
import argparse, concurrent.futures as cf, datetime, hashlib, json, os, re, shlex, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REC = "results/rtl/qwen_tp8_vm_plane_20261013/leaf_gate"
RDIR = "claude-vm-verif-1013/G"
SYNC = ["rtl/qwen_sys/vm_me_20261008", "rtl/qwen_sys/vm_plane_20261013", "rtl/qwen_sys/vm_die_split_20261012",
        "rtl/qwen_sys/rtl_finish_20261007", "rtl/hdc/ot_hdc_delay.sv", "rtl/physical/ot_qwen_tree_delay.sv",
        "rtl/physical/ot_qwen_tree_delay_tiles.sv", "tools/qwen_tp8/vm_leaf_gate.sh"]
HASH = ["rtl/qwen_sys/vm_plane_20261013/tb_qfd_vm_xplane.sv", "rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv",
        "rtl/qwen_sys/vm_plane_20261013/tb_qfd_vm_region_leaf.sv", "rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_region_leaf.sv",
        "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_region_quarter.sv",
        "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_answer_tiles.sv",
        "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_xfifo8_t.sv",
        "rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv", "rtl/hdc/ot_hdc_delay.sv",
        "rtl/physical/ot_qwen_tree_delay.sv", "rtl/physical/ot_qwen_tree_delay_tiles.sv", "tools/qwen_tp8/vm_leaf_gate.sh"]
TREE = "+define+OT_QFD_VM_DELAY1_MOD=ot_qwen_tree_delay1_t +define+OT_QFD_VM_DELAY2_MOD=ot_qwen_tree_delay2_t"


def run(name, kind, args, expect, what):
    return dict(name=name, kind=kind, args=args, expect=expect, what=what)


RUNS = [
    # ---- plane + relay leaves at the routed parameters (xplane_t NRB 64, xrelay_t W 512) ----
    run("xp_ok", "xplane", "", "PASS", "NRB 64 / ELEMS 177,808: 32 planes + 640 relays exact"),
    run("xp_ok_s2", "xplane", "-GSEED=2", "PASS", "NRB 64, SEED 2"),
    run("xp_p1", "xplane", "-GPMUT=1", "FAIL", "NRB 64 mutant: plane 5 fine rotation one bank off"),
    run("xp_p2", "xplane", "-GPMUT=2", "FAIL", "NRB 64 mutant: plane 5 element shift one off"),
    run("xp_p3", "xplane", "-GPMUT=3", "FAIL", "NRB 64 mutant: plane 5 ignores the in-range count (the parent's MUT 5: "
        "invisible to the system bench, killed only here)"),
    run("xp_r1", "xplane", "-GRMUT=1", "FAIL", "NRB 64 mutant: relay (stage 3, bank 9) free-runs"),
    # ---- the same bench at the bench shape: re-run of the committed leaf_miter record ----
    run("lf_ok", "xplane16", "", "PASS", "NRB 16 / ELEMS 16,384 (leaf_miter record shape)"),
    run("lf_ok_s2", "xplane16", "-GSEED=2", "PASS", "NRB 16, SEED 2"),
    run("lf_p1", "xplane16", "-GPMUT=1", "FAIL", "NRB 16 mutant: plane 5 fine rotation"),
    run("lf_p2", "xplane16", "-GPMUT=2", "FAIL", "NRB 16 mutant: plane 5 element shift"),
    run("lf_p3", "xplane16", "-GPMUT=3", "FAIL", "NRB 16 mutant: plane 5 range count"),
    run("lf_r1", "xplane16", "-GRMUT=1", "FAIL", "NRB 16 mutant: one relay free-runs"),
    # ---- the region built from leaves at the routed depths, delay leaves = the routed delay tiles ----
    run("rg_ok", "region", "", "PASS", "DEPTH 174 / LAW 8 / DEPTHS 695 / LAWS 10, routed delay tiles: exact every clock"),
    run("rg_ok_s2", "region", "-GSEED=2 -GOVFMODE=1", "PASS", "routed depths, SEED 2, pop-underflow overflow run"),
    run("rg_m1", "region", "-GLEAF_MUT=1", "FAIL", "routed depths mutant: rr4_t[0] slice 5 select replica one bank off"),
    run("rg_m2", "region", "-GLEAF_MUT=2", "FAIL", "routed depths mutant: rr4_t[1] row tag one edge short"),
    run("rg_m3", "region", "-GLEAF_MUT=3", "FAIL", "routed depths mutant: bctl_t 3 pop replica stuck"),
    run("rg_m4", "region", "-GLEAF_MUT=4", "FAIL", "routed depths mutant: bank_t 5 write-data pin one edge early (delay1 tile where the delay2 tile belongs)"),
    run("rg_m5", "region", "-GLEAF_MUT=5", "FAIL", "routed depths mutant: bank_t 2 q relay"),
    run("rg_m6", "region", "-GLEAF_MUT=6", "FAIL", "routed depths mutant: su_t write-data pin one edge early"),
    run("rg_m7", "region", "-GLEAF_MUT=7", "FAIL", "routed depths mutant: rr2_t central push one edge short"),
    run("rg_m8", "region", "-GLEAF_MUT=8", "FAIL", "routed depths mutant: sctl_t SU tag one edge short"),
    run("rg_m9", "region", "-GLEAF_MUT=9", "FAIL", "routed depths mutant: bctl_t 6 x tag one edge short"),
    run("rg_m10", "region", "-GLEAF_MUT=10", "FAIL", "routed depths mutant: sctl_t address relay one stage short"),
    run("rg_m11", "region", "-GLEAF_MUT=11", "FAIL", "routed depths mutant: bctl_t 1 address relay one stage short"),
    run("rg_m12", "region", "-GLEAF_MUT=12", "FAIL", "routed depths mutant: rr2_t row tag one edge short"),
    run("rg_row", "region", "-GROW_MUT=1", "FAIL", "routed depths mutant: rr2_t half select inverted (MUT 1)"),
    run("rg_su", "region", "-GSU_MUT=1", "FAIL", "routed depths mutant: su1024_t MUT 1"),
    # ---- the same bench at the bench shape: re-run of the committed region_leaf_miter record ----
    run("ok", "region8", "-GSEED=1", "PASS", "DEPTH 8 / LAW 3, soft delay leaves (region_leaf_miter record shape)"),
    run("ok_s2", "region8", "-GSEED=2 -GOVFMODE=1", "PASS", "DEPTH 8, SEED 2, pop-underflow overflow run"),
    run("ok_s3_tree", "region8", "-GSEED=3 " + TREE, "PASS", "DEPTH 8, SEED 3, delay leaves = the routed delay tiles"),
] + [run(f"mut{m}", "region8", f"-GLEAF_MUT={m}", "FAIL", f"DEPTH 8 mutant LEAF_MUT {m}") for m in range(1, 13)]

# Qualification table of the CLOSED VM leaves (closure-loop job state read 2026-10-13 18:20 PT, VM4: gctl_t / rowrd_t
# are dissolved into bctl_t / sctl_t / rr4_t / rr2_t; bench commands from
# physical/ref_tile/<kit>/job.json on main).  own_bench_at_routed: the job's own PASS + mutant ran the routed module
# at the routed parameters.  bound_here: the runs of this record (and of the system record) that close the gap.
SYS = "results/rtl/qwen_tp8_vm_plane_20261013/system/record.json"
LEAVES = [
    dict(leaf="ot_qfd_vm_bank_t", job="qfd_vm_bank_t-r6-b9e44cb62-g2", routed="DEPTH 174, LAW 8, USE_MACRO 1",
         job_benches="tb_qfd_vm_bv_ports vmt_s3 / s9 / r11 / r21 / nomee PASS, vmt_xmut (XQT 2) / vmt_smut (MUT 1) FAIL",
         job_shape="inside ot_qfd_vm_grp at NRB 16 / ELEMS 16,384: DEPTH 64, LAW 6; both mutants are PARENT mutants "
                   "(x beat count, SU lane select), none at the leaf",
         own_bench_at_routed=False, bound_here=["rg_ok", "rg_ok_s2", "rg_m4", "rg_m5"], system=["prod_tr", "prod_tr_m1"]),
    dict(leaf="ot_qfd_vm_su_t", job="qfd_vm_su_t-r6-b9e44cb62-g2", routed="NSB 1, DEPTHS 695, LAWS 10, USE_MACRO 1",
         job_benches="the same seven tb_qfd_vm_bv_ports runs as bank_t",
         job_shape="inside ot_qfd_vm_grp at NRB 16 / ELEMS 16,384: DEPTHS 64, LAWS 6; parent mutants only",
         own_bench_at_routed=False, bound_here=["rg_ok", "rg_ok_s2", "rg_m6"], system=["prod_tr", "prod_tr_m1"]),
    dict(leaf="ot_qfd_vm_bctl_t", job="qfd_vm_bctl_t-bc2-422b0e7ba", routed="LAW 8, MEREG 1, NRI 2, NRX 2",
         job_benches="tb_qfd_vm_region_leaf rl_ok PASS, rl_mut3 / 9 / 11 FAIL (the three bctl_t mutants)",
         job_shape="DEPTH 8 / LAW 3: the line-address width is NOT the routed 8",
         own_bench_at_routed=False, bound_here=["rg_ok", "rg_ok_s2", "rg_m3", "rg_m9", "rg_m11"], system=["prod_tr"]),
    dict(leaf="ot_qfd_vm_sctl_t", job="qfd_vm_sctl_t-sc2-422b0e7ba", routed="LAWS 10, NRI 2, NRS 1",
         job_benches="tb_qfd_vm_region_leaf rl_ok PASS, rl_mut8 / 10 FAIL (the two sctl_t mutants)",
         job_shape="DEPTHS 8 / LAWS 3: NOT the routed 10",
         own_bench_at_routed=False, bound_here=["rg_ok", "rg_ok_s2", "rg_m8", "rg_m10"], system=["prod_tr"]),
    dict(leaf="ot_qfd_vm_rr4_t", job="qfd_vm_rr4_t-r43-5078addc9", routed="NRI 2, NRX 2 (kept AND-OR tree)",
         job_benches="tb_qfd_vm_region_leaf rl_ok PASS, rl_mut1 / 2 FAIL (the two rr4_t mutants)",
         job_shape="the routed module at its parameters (no depth parameter); bench shape DEPTH 8",
         own_bench_at_routed=True, bound_here=["rg_ok", "rg_ok_s2", "rg_m1", "rg_m2"], system=["prod_tr"]),
    dict(leaf="ot_qfd_vm_rr2_t", job="qfd_vm_rr2_t-r21-d6fcb8405", routed="NPP 12, MEREG 1, NRI 2, NRX 2",
         job_benches="tb_qfd_vm_region_leaf rl_ok PASS, rl_mut7 / 12 and ROW_MUT 1 FAIL (the three rr2_t mutants)",
         job_shape="the routed module at its parameters; bench shape DEPTH 8",
         own_bench_at_routed=True, bound_here=["rg_ok", "rg_ok_s2", "rg_m7", "rg_m12", "rg_row"], system=["prod_tr"]),
    dict(leaf="ot_qfd_vm_xrelay_t", job="qfd_vm_xrelay_t-xr1-d1415868a", routed="W 512, MEREG 1",
         job_benches="tb_qfd_vm_xplane lf_ok PASS, lf_r1 (relay free-runs) FAIL",
         job_shape="W 512, MEREG 1 relays (16 banks x 10 stages): the routed module and parameters",
         own_bench_at_routed=True, bound_here=["xp_ok", "xp_r1"], system=["prod_tr", "prod_tr_m6", "prod_tr_m13"]),
    dict(leaf="ot_qfd_vm_xplane_t", job="qfd_vm_xplane_t-xp1-d1415868a", routed="NRB 64, MEREG 1",
         job_benches="tb_qfd_vm_xplane lf_ok PASS, lf_p1 / p2 / p3 FAIL",
         job_shape="NRB 16 / ELEMS 16,384: NOT the routed NRB 64",
         own_bench_at_routed=False, bound_here=["xp_ok", "xp_ok_s2", "xp_p1", "xp_p2", "xp_p3"],
         system=["prod_tr", "prod_tr_m3"]),
    dict(leaf="ot_qfd_vm_xfifo8_t", job="qfd_vm_xfifo8_codex-c8f12-18af5339c", routed="NPP 12, FSW 32, MEREG 1",
         job_benches="tb_qfd_vm_xfifo8_t fifo12_exact PASS, fifo12_mut (MUT 1) FAIL",
         job_shape="the routed module at its defaults = the routed parameters",
         own_bench_at_routed=True, bound_here=["rg_ok", "rg_ok_s2"], system=["prod_tr"]),
    dict(leaf="ot_qfd_vm_su1024_t", job="qfd_vm_su1024_codex-ans2-c9b9190ac", routed="no parameters",
         job_benches="tb_qfd_vm_su1024_t su1024_exact PASS (510 checks), su1024_mut (MUT 1) FAIL",
         job_shape="the routed module", own_bench_at_routed=True, bound_here=["rg_ok", "rg_su"], system=["prod_tr"]),
    dict(leaf="ot_qwen_tree_delay1_t (the VM's delay1_t)", job="qfd_tree_delay1_t-w17-499ba7b21", routed="DW 512, LAT 1",
         job_benches="tools/qwen_die_seam/tile_gate.sh 1 pass PASS, drop / flip FAIL",
         job_shape="the routed wrapper; its USE in the VM region (OT_QFD_VM_DELAY1_MOD) was one bench-shape run",
         own_bench_at_routed=True, bound_here=["rg_ok", "rg_m4", "rg_m5", "ok_s3_tree"], system=[]),
    dict(leaf="ot_qwen_tree_delay2_t (the VM's delay2_t)", job="qfd_tree_delay2_t-u52-baaa52fff", routed="DW 512, LAT 2",
         job_benches="tools/qwen_die_seam/tile_gate.sh 2 pass PASS, drop / flip FAIL",
         job_shape="the routed wrapper; its USE in the VM region (OT_QFD_VM_DELAY2_MOD) was one bench-shape run",
         own_bench_at_routed=True, bound_here=["rg_ok", "rg_m4", "rg_m6", "ok_s3_tree"], system=[]),
]


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def one(r, hosts):
    cmd = (f"ot-run --mem 4 --dir {RDIR} {('--hosts ' + hosts) if hosts else ''} -- bash tools/qwen_tp8/vm_leaf_gate.sh "
           f"$HOME/{RDIR}/b {r['kind']} {r['name']} {r['args']}")
    p = sh(cmd)
    m = re.search(r"ot-run: RAN on (\S+) .*exit (\d+)", p.stderr)
    line = next((l for l in p.stdout.split("\n") if l.startswith(r["name"] + " ")), "")
    return r["name"], (m.group(1) if m else None), (int(m.group(2)) if m else None), line, p.stderr.strip().split("\n")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--hosts", default="ot-epyc1tb,ot-epyc4,ot-agidock128,ot-pve1")
    ap.add_argument("--collect", action="store_true")
    a = ap.parse_args()
    runs = [r for r in RUNS if not a.only or r["name"] in a.only.split(",")]
    out = os.path.join(ROOT, REC)
    os.makedirs(out, exist_ok=True)
    hosts = []
    old = None
    if a.collect:
        old = json.load(open(os.path.join(out, "record.json")))
    for h in ([] if a.collect else a.hosts.split(",")):
        p = sh(f"ssh -o ConnectTimeout=10 {h} 'mkdir -p {RDIR}/b' && cd {shlex.quote(ROOT)} && "
               f"rsync -a --relative {' '.join(SYNC)} {h}:{RDIR}/")
        if p.returncode == 0:
            hosts.append(h)
        else:
            print("no sync to", h, p.stderr[-200:], file=sys.stderr)
    hashes = {f: sha(os.path.join(ROOT, f)) for f in HASH}
    recs, bad = [], []
    if a.collect:
        if old["sources_sha256"] != hashes:
            sys.exit("--collect: the sources changed since the recorded runs; run the set again")
        recs = old["runs"]
        bad = [o["name"] for o in recs if not o["ok"]]
        runs = []
    else:
        with cf.ThreadPoolExecutor(len(runs)) as ex:
            got = list(ex.map(lambda r: one(r, ",".join(hosts)), runs))
        by = {g[0]: g for g in got}
    for r in runs:
        _, host, rc, line, last = by[r["name"]]
        m = re.search(r"rc=(\S+) ((?:PASS|FAIL) .*?) maxrss_kb=(\d+) wall=([\d.]+) build_s=(\d+)", line)
        o = dict(name=r["name"], kind=r["kind"], args=r["args"], what=r["what"], expected=r["expect"], host=host,
                 ot_run=last, log=r["name"] + ".log")
        if host:
            sh(f"scp -q {host}:{RDIR}/b/{r['name']}.log {shlex.quote(out)}/")
            rh = sh(f"ssh {host} 'cd {RDIR} && sha256sum {' '.join(HASH)}'").stdout.split("\n")
            remote = {l.split()[1]: l.split()[0] for l in rh if re.match(r"^[0-9a-f]{64} ", l)}
            o["remote_tree_matches_sha256"] = all(remote.get(f) == h for f, h in hashes.items())
        if not m or not host:
            o.update(observed="NO-RESULT", observed_line=line[:300], ok=False)
        else:
            o.update(observed=m.group(2).split()[0], observed_line=m.group(2), gate_rc=rc, maxrss_kb=int(m.group(3)),
                     wall_s=float(m.group(4)), build_s=int(m.group(5)))
            o["ok"] = (o["observed"] == r["expect"] and rc == (0 if r["expect"] == "PASS" else 1)
                       and o["remote_tree_matches_sha256"])
        if not o["ok"]:
            bad.append(r["name"])
        recs.append(o)
    okn = {o["name"] for o in recs if o["ok"]}
    sysok = set()
    try:
        sj = json.load(open(os.path.join(ROOT, SYS)))
        sysok = {o["name"] for o in sj["runs"] if o.get("ok")} if sj.get("ok") else set()
    except Exception:  # noqa
        pass
    leaves = []
    for l in LEAVES:
        e = dict(l)
        e["bound_here_ok"] = all(n in okn for n in l["bound_here"])
        e["system_runs_ok"] = all(n in sysok for n in l["system"])
        e["bench_qualified_at_routed_parameters"] = e["bound_here_ok"] and e["system_runs_ok"] and not a.only
        if not e["bench_qualified_at_routed_parameters"] and not a.only:
            bad.append("leaf-not-bound:" + l["leaf"])
        leaves.append(e)
    commit = sh(f"git -C {shlex.quote(ROOT)} rev-parse HEAD").stdout.strip()
    dirty = sh(f"git -C {shlex.quote(ROOT)} status --porcelain -- {' '.join(HASH)}").stdout.strip()
    if dirty:
        bad.append("sources-dirty-vs-commit")
    rec = {
        "record": "qwen_tp8_vm_leaf_gate", "date": datetime.date.today().isoformat(),
        "ok": not bad and not a.only, "not_ok_because": bad + (["partial set (--only)"] if a.only else []),
        "what": "the closed VM leaves benched at their ROUTED parameters: plane / relay leaf miter at NRB 64, the region "
                "built from leaves against the flat region at DEPTH 174 / LAW 8 / DEPTHS 695 / LAWS 10 with the routed "
                "delay tiles; plus the re-run of the two bench-shape leaf miters",
        "not_covered": "USE_MACRO 1 (the routed leaves hold SRAM macros; every bench here uses the behavioural memory of "
                       "the same one-edge registered read), timing and the views: this record is the behavioural half of "
                       "the element gate only",
        "runner": "tools/qwen_tp8/vm_leaf_gate.sh", "driver": "tools/qwen_tp8/vm_leaf_gate_set.py",
        "launcher": "one `ot-run --mem 4` per bench, all in parallel", "source_commit": commit,
        "sources_clean_at_commit": not dirty, "sources_sha256": hashes,
        "summary": {"pass_ok": sum(1 for o in recs if o["expected"] == "PASS" and o["ok"]),
                    "pass_expected": sum(1 for o in recs if o["expected"] == "PASS"),
                    "mutants_killed": sum(1 for o in recs if o["expected"] == "FAIL" and o["ok"]),
                    "mutants_expected": sum(1 for o in recs if o["expected"] == "FAIL")},
        "system_record": SYS, "leaves": leaves, "runs": recs,
    }
    json.dump(rec, open(os.path.join(out, "record.json"), "w"), indent=1)
    for o in recs:
        print(f"{o['name']:11s} {o['kind']:8s} exp {o['expected']:4s} got {o['observed']:9s} ok={o['ok']} {o.get('host')} "
              f"{o.get('observed_line', '')[:150]}")
    for e in leaves:
        print(f"LEAF {e['leaf']:44s} own@routed={e['own_bench_at_routed']} bound={e['bound_here_ok']} sys={e['system_runs_ok']}")
    print("OK" if rec["ok"] else f"NOT OK: {rec['not_ok_because']}")
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
