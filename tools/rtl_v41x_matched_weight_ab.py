#!/usr/bin/env python3
"""Matched weight-source A/B on the V4.1x two-package all-unit reduced array.

One ISA program, one set of images, one three-token workload, two builds of the
unmodified all-unit bench (rtl/test/tb_hdc_v41x_array.sv) that differ only in
the build define HDC_W_HBM:

  arm A  W_HBM=0  the QE reads its quantised weights from the ROM image qrom.hex;
  arm B  W_HBM=1  the QE reads the SAME weights, laid out as hbm_q.hex sectors,
                  through ot_hdc_qstream and the timed ot_hdc_hbm_model.

Everything else (X_HE/ME/ATT/SEL/EG/SU=1, X_IDX=2 with the timed pooled
index-key HBM, the p2p link at 60 cycles, sim-only DPI floating point,
Verilator flags) follows tools/rtl_hdc_v41x_array_campaign.py --all-unit
--only b2_p2p, which is imported, not edited.  The bench is wrapped by the
observation-only rtl/test/tb_v41x_matched_weight_ab.sv, which counts the
weight-supply issue stalls and (arm B) the weight-HBM statistics.

Subcommands:
  prepare --scratch D          images + manifest (hashes, ISA verdict, ROM/HBM weight equivalence)
  arm --whbm 0|1 --images D --scratch S [--jobs 8]   build and run one arm (peak memory sampled)
  combine --images D --arm-a S --arm-b S [--output results/rtl/hdc_v41x_matched_weight_ab.json]

No cycle delta is reported unless both arms pass every check.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
# The array campaign decides its all-unit arithmetic contract at import time
# from sys.argv; import it exactly as `--all-unit` would.
_argv, sys.argv = sys.argv, [sys.argv[0], "--all-unit"]
import rtl_hdc_v41x_array_campaign as AC  # noqa: E402
sys.argv = _argv
assert AC.ALL_UNIT and os.environ["HDC_V41_ARITH"] == "chunk8" and os.environ["HDC_V41_IDX_FUSED"] == "1"

OUT = ROOT / "results/rtl/hdc_v41x_matched_weight_ab.json"
REFERENCE = ROOT / "results/rtl/hdc_v41x_array_allunit_b2_o1fast_full.json"
AB_TB = ROOT / "rtl/test/tb_v41x_matched_weight_ab.sv"
AB_HARNESS = ROOT / "rtl/test/v41x_matched_weight_ab_harness.cpp"
TOP = "tb_v41x_matched_weight_ab"
CONFIG = "b2_p2p"
LINK_CH = 60
OPT_MAKEFLAGS = "OPT_FAST=-O1 OPT_GLOBAL=-O1"   # the reference record's optimized binary flags
REF_TOKENS = [2815, 3537, 2047]
ARMS = {0: "A_rom_weights", 1: "B_qe_weight_hbm"}

ABTOK = re.compile(r"ABTOK pos=(\d+) cycle=(\d+) qe_issues=(\d+),(\d+) qrom_reads=(\d+),(\d+) "
                   r"qgate_wait=(\d+),(\d+) qgate_low=(\d+),(\d+)")
ABNODE = re.compile(r"ABNODE node=(\d+) qe_issues=(\d+) qrom_reads=(\d+) qgate_wait=(\d+) qgate_low=(\d+)")
ABWHBM = re.compile(r"ABWHBM node=(\d+) sector_reads=(\d+) activates=(\d+) row_hits=(\d+) row_conflicts=(\d+) "
                    r"refreshes=(\d+) req_backpressure_cycles=(\d+) rd_lat_sum_ps=(\d+) rd_lat_max_ps=(\d+) "
                    r"fetched=(\d+) consumed=(\d+) fault_why=(\d+)")
HBM_NODE = re.compile(r"HBM_NODE node=(\d+) q_bad=(\d+) q_words=(\d+) q_reads=(\d+) q_fault=(\d+) "
                      r"idx_records=(\d+) idx_writes=(\d+) idx_read_stalls=(\d+) idx_writer_stalls=(\d+) "
                      r"idx_refresh=(\d+)")
FAIL_MARKERS = ("MISMATCH", "LOGIT pkg", "KV pkg", "VM pkg", "FAULT core", "QSTREAM_FAIL", "IDXHBM_FAIL",
                "IDXHBM_USER_FAIL", "TIMEOUT", "%Error", "%Fatal")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def sources():
    """Every source the builds, images and this A/B read (campaign list + the wrapper + this tool)."""
    return sorted({*map(Path, AC.sources()), AB_TB, AB_HARNESS, Path(__file__).resolve()},
                  key=lambda p: str(p))


def source_hashes():
    return {rel(p): sha(p) for p in sources()}


def tree_hashes(d: Path):
    return {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob("*")) if p.is_file()}


def git_head():
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None


def git_dirty():
    r = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"],
                       capture_output=True, text=True)
    return [line for line in r.stdout.splitlines() if line.strip()]


# -- peak memory of a process tree (the job container has no /usr/bin/time) -------------
class TreePeak:
    """Samples the summed VmRSS of a process and all its descendants every `period` s."""

    def __init__(self, pid, period=0.5):
        self.pid, self.period, self.peak_kb, self.samples = pid, period, 0, 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _tree_rss(self):
        kids, rss = {}, {}
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                st = open(f"/proc/{d}/stat").read()
                ppid = int(st[st.rfind(")") + 2:].split()[1])
                kids.setdefault(ppid, []).append(int(d))
                for line in open(f"/proc/{d}/status"):
                    if line.startswith("VmRSS:"):
                        rss[int(d)] = int(line.split()[1])
                        break
            except (OSError, ValueError, IndexError):
                continue
        tot, todo = 0, [self.pid]
        while todo:
            p = todo.pop()
            tot += rss.get(p, 0)
            todo.extend(kids.get(p, []))
        return tot

    def _run(self):
        while not self._stop.is_set():
            self.peak_kb = max(self.peak_kb, self._tree_rss())
            self.samples += 1
            self._stop.wait(self.period)

    def stop(self):
        self._stop.set()
        self._t.join()
        return self.peak_kb


def measured(cmd, log_path: Path, cwd=None):
    """Run cmd with output to log_path; return (rc, wall s, peak tree RSS GiB, largest single process GiB)."""
    import resource
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    t0 = time.time()
    with open(log_path, "w") as fh:
        p = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=cwd)
        tp = TreePeak(p.pid)
        rc = p.wait()
        peak = tp.stop()
    single = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return dict(returncode=rc, wall_seconds=round(time.time() - t0, 1),
                peak_tree_rss_gib=round(peak / 2**20, 3), tree_samples=tp.samples,
                max_single_process_rss_gib=round(max(single, before) / 2**20, 3))


# -- prepare -----------------------------------------------------------------------------
def weight_equivalence(lay, roms: Path) -> dict:
    """Arm B's HBM sectors decode, word for word, to arm A's ROM words (both read from the files)."""
    import hdc_program_v41 as P
    fmt = P.qe_word_formats(lay)
    q = (roms / "qrom.hex").read_text().split()
    s = (roms / "hbm_q.hex").read_text().split()
    nw = len(lay.qcodes)
    assert len(q) == nw, (len(q), nw)
    pos, bad, n4 = 0, 0, 0
    lane4, lane8 = 128 + 16, P.QLANE_BITS
    for w in range(nw):
        spw = P.QSPW4 if fmt[w] else P.QSPW8
        word = 0
        for j in range(spw):
            word |= int(s[pos + j], 16) << (P.QSEC * j)
        pos += spw
        if fmt[w]:
            n4 += 1
            rom = 0
            for ln in range(P.BL):
                lane = (word >> (lane4 * ln)) & ((1 << lane4) - 1)
                codes = sum(((lane >> (4 * c)) & 0xF) << (8 * c) for c in range(32))
                rom |= (codes | ((lane >> 128) & 0xFFFF) << 256) << (lane8 * ln)
            word = rom
        bad += word != int(q[w], 16)
    return dict(rom_words=nw, fp4_words=n4, fp8_words=nw - n4, hbm_sectors=len(s),
                hbm_sectors_consumed_by_decode=pos, word_mismatches=bad,
                pass_=bad == 0 and pos == len(s))


def prepare(scratch: Path) -> dict:
    import numpy as np
    V, I, P, A, ximg = AC.V, AC.I, AC.P, AC.A, AC.ximg
    scratch.mkdir(parents=True, exist_ok=True)
    body, hp, hmc, shared, fabric, users, fewer, stall, plen, ngen, links = AC.CONFIGS[CONFIG]
    assert (users, stall, plen, ngen, links) == (1, 0, 3, 1, (LINK_CH,))
    t0 = time.time()
    model = V.Model()
    lay = P.Layout(model)
    A.place_head_parts(lay)
    roms = scratch / "roms"
    A.write_roms(roms, lay)
    ximg.write_banked(roms / "hbank.hex", ximg.hbank_image(lay, 8), 32, 8)
    ximg.write(roms, lay, hhw=8, mg=8)
    sectors, first = P.qe_hbm_image(lay)
    (roms / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    gold = A.golden_runs(model, ngen, scratch / "gold.json", plen)
    plan = A.Plan(lay, A.split(model, body), hp, hmc, shared)
    progs = [A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    recs, states = A.run_pipeline(plan, progs, base, gold)
    img = scratch / f"cfg_{CONFIG}"
    steps = A.write_config(img, plan, progs, gold, states)
    qlists = []
    for k, prog in enumerate(progs):
        ents = P.qe_fetch_list(lay, prog, first)
        (img / f"qlist_stage{k:02d}.hex").write_text(P.hexwords(P.encode_list(ents), P.LIST_BITS))
        qlists.append(dict(stage=k, entries=len(ents)))
        if not ents and k < plan.nb:
            raise RuntimeError(f"body stage {k}: empty QE HBM fetch list")
    isa_ok = all(r["logits_bit_exact_every_step"] and r["argmax_and_value_every_step"] for r in recs)
    if not isa_ok:
        raise RuntimeError(f"ISA pipeline is not bit-exact with the golden: {recs}")
    svh = AC.config_svh(plan, lay, fabric)
    assert plan.n == 2, "the observation wrapper is written for two packages"
    (scratch / "v41_array_cfg.svh").write_text(svh)
    heads = sum(plan.role(k)["head"] is not None for k in range(plan.n))
    equiv = weight_equivalence(lay, roms)
    equiv["pass"] = equiv.pop("pass_")
    if not equiv["pass"]:
        raise RuntimeError(f"ROM and HBM weight images differ: {equiv}")
    images = {**{f"roms/{k}": v for k, v in tree_hashes(roms).items()},
              **{f"cfg_{CONFIG}/{k}": v for k, v in tree_hashes(img).items()},
              "v41_array_cfg.svh": sha(scratch / "v41_array_cfg.svh")}
    ref = json.loads(REFERENCE.read_text())["image_sha256"] if REFERENCE.exists() else {}
    same = sorted(k for k in ref if images.get(k) == ref[k])
    manifest = {
        "schema": "opentallas.v41x-matched-weight-ab.images.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_commit": git_head(), "source_tracked_dirty": git_dirty(),
        "configuration": CONFIG, "packages": plan.n, "lm_head_packages": heads, "users": users,
        "prompt_tokens": plen, "generated_tokens": ngen, "token_steps": steps, "link_channel_cycles": LINK_CH,
        "prompts": [g["prompt"] for g in gold], "golden_argmax": [s["argmax"] for s in gold[0]["steps"]],
        "isa_pipeline": recs, "program_instructions": [len(p) for p in progs], "qe_fetch_lists": qlists,
        "weight_equivalence": equiv,
        "model_checkpoint_sha256": sha(V.CHECKPOINT), "model_config_sha256": sha(V.CONFIG),
        "image_sha256": images,
        "reference_record_image_match": {"files_compared": len(ref), "identical": len(same),
                                         "differing": sorted(set(ref) - set(same))},
        "source_sha256": source_hashes(),
        "wall_seconds": round(time.time() - t0, 1),
    }
    (scratch / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    return manifest


# -- one arm -----------------------------------------------------------------------------
def verilator_cmd(obj: Path, images: Path, whbm: int, jobs: int):
    """AC.build()'s command for the all-unit bench, with the arm's HDC_W_HBM and the wrapper top."""
    core, I = AC.core, AC.I
    return ["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
            "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN", "-Wno-TIMESCALEMOD",
            "-Wno-MODDUP", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT", "-Wno-PINMISSING",
            "--top-module", TOP,
            "-GUSERS=1", "-GSTALL=0", "-Mdir", str(obj), f"-I{obj}", f"-I{core.SVH.parent}",
            str(core.VLT),
            f"+define+HDC_SW={I.SU_LANES}",
            *[f"+define+HDC_X_{x}={2 if x == 'IDX' else 1}" for x in ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")],
            f"+define+HDC_W_HBM={whbm}", *(["+define+AB_WHBM_PROBE"] if whbm else []),
            *map(str, core.rtl_sources(True)),
            *map(str, AC.BENCH_AUX_RTL),
            str(AC.LINK), str(AC.ROUTER), str(AC.CTRL), str(AC.TB), str(AB_TB), str(AB_HARNESS),
            "-CFLAGS", "-O1", "-MAKEFLAGS", OPT_MAKEFLAGS, "-j", str(jobs)]


def ints(m, names):
    return dict(zip(names, map(int, m.groups())))


def parse(out: str, whbm: int, man: dict) -> dict:
    """Every verdict the bench prints, plus the wrapper's counters; `pass` needs all of them."""
    m = AC.RES.search(out)
    res = ints(m, ("packages", "users", "generated", "token_mismatches", "logit_mismatches",
                   "lm_head_checks", "state_mismatches", "total_cycles")) if m else {}
    toks = [dict(zip(("user", "position", "token", "cycle"), map(int, t))) for t in AC.TOK.findall(out)]
    nodes = sorted((ints(x, ("package", "busy", "side_wait", "tx_wait", "starved", "jobs", "state_mismatches"))
                    for x in AC.NODE.finditer(out)), key=lambda d: d["package"])
    hbm = sorted((ints(x, ("package", "q_bad", "q_words", "q_reads", "q_fault", "idx_records", "idx_writes",
                           "idx_read_stalls", "idx_writer_stalls", "idx_refresh"))
                  for x in HBM_NODE.finditer(out)), key=lambda d: d["package"])
    probe = sorted((ints(x, ("package", "qe_issues", "qrom_reads", "qgate_wait", "qgate_low"))
                    for x in ABNODE.finditer(out)), key=lambda d: d["package"])
    whbm_st = sorted((ints(x, ("package", "sector_reads", "activates", "row_hits", "row_conflicts", "refreshes",
                               "req_backpressure_cycles", "rd_lat_sum_ps", "rd_lat_max_ps", "streamer_fetched",
                               "streamer_consumed", "streamer_fault_why"))
                      for x in ABWHBM.finditer(out)), key=lambda d: d["package"])
    snaps = [dict(zip(("position", "cycle", "qe_issues", "qrom_reads", "qgate_wait", "qgate_low"),
                      (int(t[0]), int(t[1]), [int(t[2]), int(t[3])], [int(t[4]), int(t[5])],
                       [int(t[6]), int(t[7])], [int(t[8]), int(t[9])]))) for t in ABTOK.findall(out)]
    done = AC.DONE.search(out)
    stalls = AC.STALLS.search(out)
    idx_users = re.search(r"IDXHBM_USERS read=([01]+) wrote=([01]+)", out)
    fails = sorted({f for f in FAIL_MARKERS if f in out})
    steps, npk, heads = man["token_steps"], man["packages"], man["lm_head_packages"]
    expect = man["golden_argmax"]
    checks = {
        "pass_marker": bool(re.search(r"^PASS$", out, re.M)) and not re.search(r"^FAIL$", out, re.M),
        "no_failure_markers": not fails,
        "summary_present": bool(m),
        "token_mismatches_zero": res.get("token_mismatches") == 0,
        "logit_mismatches_zero": res.get("logit_mismatches") == 0,
        "all_lm_head_steps_checked": res.get("lm_head_checks") == heads * steps,
        "state_mismatches_zero": res.get("state_mismatches") == 0 and len(nodes) == npk
        and all(n["state_mismatches"] == 0 for n in nodes),
        "tokens_exact": [t["token"] for t in toks] == expect == REF_TOKENS
        and [t["position"] for t in toks] == list(range(steps)),
        "users_done": bool(done) and int(done.group(1)) == 1,
        "generated": res.get("generated") == man["generated_tokens"],
        "index_hbm_clean": len(hbm) == npk and all(h["idx_records"] > 0 and h["idx_writes"] == 12 * h["idx_records"]
                                                  for h in hbm) and bool(idx_users)
        and idx_users.group(1) == "1" and idx_users.group(2) == "1",
        "qe_weight_faults_zero": len(hbm) == npk and all(h["q_fault"] == 0 and h["q_bad"] == 0 for h in hbm)
        and all(w["streamer_fault_why"] == 0 for w in whbm_st),
        "probe_present": len(probe) == npk and len(snaps) == steps and "ABPROBE_DONE whbm=%d" % whbm in out,
        "weight_path_as_armed": (all(h["q_reads"] > 0 and h["q_words"] > 0 for h in hbm) and len(whbm_st) == npk
                                 if whbm else all(h["q_reads"] == 0 and h["q_words"] == 0 for h in hbm)
                                 and not whbm_st and all(p["qgate_wait"] == 0 for p in probe)),
    }
    cyc = [t["cycle"] for t in toks]
    per_step = [c - p for c, p in zip(cyc, [0] + cyc[:-1])]
    snap_wait = [sum(s["qgate_wait"]) for s in snaps]
    return {
        "whbm": whbm, "arm": ARMS[whbm], "checks": checks, "pass": all(checks.values()),
        "failure_markers": fails, "summary": res, "tokens": toks,
        "token_cycles": cyc, "cycles_per_token_step": per_step,
        "qgate_wait_per_token_step": [c - p for c, p in zip(snap_wait, [0] + snap_wait[:-1])],
        "per_package": nodes, "hbm_node": hbm, "probe": probe, "probe_token_snapshots": snaps,
        "weight_hbm": whbm_st, "link_credit_stalls": int(stalls.group(1)) if stalls else None,
    }


def arm(whbm: int, images: Path, scratch: Path, jobs: int) -> dict:
    if not 1 <= jobs <= 8:
        raise SystemExit("--jobs must be 1..8 (at most half of a 28-core host with both arms running)")
    man = json.loads((images / "manifest.json").read_text())
    now = {k: sha(images / k) for k in man["image_sha256"]}
    if now != man["image_sha256"]:
        raise SystemExit(f"image hashes changed since prepare: {sorted(k for k in now if now[k] != man['image_sha256'][k])}")
    src = source_hashes()
    if src != man["source_sha256"]:
        raise SystemExit(f"sources differ from the prepared tree: "
                         f"{sorted(k for k in set(src) | set(man['source_sha256']) if src.get(k) != man['source_sha256'].get(k))}")
    scratch.mkdir(parents=True, exist_ok=True)
    obj = scratch / "obj"
    obj.mkdir(parents=True, exist_ok=True)
    (obj / "v41_array_cfg.svh").write_bytes((images / "v41_array_cfg.svh").read_bytes())
    cmd = verilator_cmd(obj, images, whbm, jobs)
    ver = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    b = measured(cmd, scratch / "build.log")
    if b["returncode"]:
        tail = (scratch / "build.log").read_text()[-3000:]
        rec = dict(whbm=whbm, arm=ARMS[whbm], pass_=False, build=b, error=f"build failed\n{tail}")
        (scratch / "arm.json").write_text(json.dumps(rec, indent=1) + "\n")
        raise SystemExit(rec["error"])
    exe = obj / f"V{TOP}"
    run_cmd = [str(exe), f"+DIR={images / f'cfg_{CONFIG}'}", f"+ROMS={images / 'roms'}", "+NUSERS=1",
               f"+NPROMPT={man['prompt_tokens']}", f"+NGEN={man['generated_tokens']}", f"+LINK_CH={LINK_CH}",
               "+HB=100000"]
    exe_sha = sha(exe)
    r = measured(["stdbuf", "-oL", *run_cmd], scratch / "run.log")
    out = (scratch / "run.log").read_text()
    res = parse(out, whbm, man)
    res["checks"]["simulator_exit_zero"] = r["returncode"] == 0
    res["checks"]["binary_unchanged_after_run"] = sha(exe) == exe_sha
    res["pass"] = all(res["checks"].values())
    peak = max(b["peak_tree_rss_gib"], r["peak_tree_rss_gib"])
    cg = Path("/sys/fs/cgroup/memory.peak")
    rec = {
        **res,
        "host": os.uname().nodename, "verilator": ver, "build_command": cmd, "run_command": run_cmd,
        "build": {**b, "make_jobs": jobs, "makeflags": OPT_MAKEFLAGS,
                  "log_sha256": sha(scratch / "build.log")},
        "run": {**r, "log_sha256": sha(scratch / "run.log"), "log_bytes": len(out.encode())},
        "binary_sha256": exe_sha,
        "peak_tree_rss_gib": peak,
        "container_cgroup_memory_peak_gib": (round(int(cg.read_text()) / 2**30, 3) if cg.exists() else None),
        "recommended_gate_min_gb": int(-(-peak * 1.3 // 1)),
        "source_sha256": src, "image_sha256": now,
    }
    (scratch / "arm.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"arm {ARMS[whbm]}: {'PASS' if rec['pass'] else 'FAIL'} tokens={rec['token_cycles']} "
          f"total={res['summary'].get('total_cycles')} build {b['wall_seconds']} s / {b['peak_tree_rss_gib']} GiB, "
          f"run {r['wall_seconds']} s / {r['peak_tree_rss_gib']} GiB")
    return rec


# -- combine -----------------------------------------------------------------------------
def pct(d, base):
    return round(100.0 * d / base, 4) if base else None


def combine(images: Path, arm_a: Path, arm_b: Path, output: Path) -> dict:
    man = json.loads((images / "manifest.json").read_text())
    a = json.loads((arm_a / "arm.json").read_text())
    b = json.loads((arm_b / "arm.json").read_text())
    assert a["whbm"] == 0 and b["whbm"] == 1
    # each arm builds in its own scratch directory; compare with that path normalised
    ca = [x.replace(str(arm_a), "ARM") for x in a["build_command"]]
    cb = [x.replace(str(arm_b), "ARM") for x in b["build_command"]]
    matched = {
        "same_source_sha256": a["source_sha256"] == b["source_sha256"] == man["source_sha256"],
        "same_image_sha256": a["image_sha256"] == b["image_sha256"] == man["image_sha256"],
        "rom_and_hbm_weights_equivalent": man["weight_equivalence"]["pass"],
        "build_commands_differ_only_in_arm_defines":
            [x for x in ca if x not in cb] == ["+define+HDC_W_HBM=0"]
            and [x for x in cb if x not in ca] == ["+define+HDC_W_HBM=1", "+define+AB_WHBM_PROBE"]
            and [x for x in ca if not x.startswith("+define+HDC_W_HBM")]
            == [x for x in cb if not x.startswith("+define+HDC_W_HBM") and x != "+define+AB_WHBM_PROBE"],
        "same_run_arguments": a["run_command"][1:] == b["run_command"][1:],
        "same_qe_weight_issues": [p["qe_issues"] for p in a.get("probe", [])]
        == [p["qe_issues"] for p in b.get("probe", [])],
        "same_qe_weight_words_read": [p["qrom_reads"] for p in a.get("probe", [])]
        == [p["qrom_reads"] for p in b.get("probe", [])],
    }
    both = a.get("pass") and b.get("pass") and all(matched.values())
    rec = {
        "schema": "opentallas.rtl.hdc_v41x_matched_weight_ab.v1",
        "status": "pass" if both else "fail",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claim_boundary": (
            "Matched same-program memory-source A/B on the reduced two-package all-unit DeepSeek-V4.1x bench "
            "(one user, three token steps, p2p link 60 cycles, X_HE/ME/ATT/SEL/EG/SU=1, X_IDX=2 with the timed "
            "pooled index-key HBM in both arms). Arm A reads the quantised QE weights from the ROM image "
            "(W_HBM=0); arm B reads the same weights through the QE streamer from the timed behavioural "
            "weight-HBM model (W_HBM=1). Same ISA program, images and workload; builds differ only in the "
            "W_HBM define (and the observation wrapper's weight-HBM counters). Behavioural memories, delay-line "
            "link PHY and simulation-only DPI floating point. This is a reduced-bench cycle delta, not chip "
            "throughput and not a full-model or production-rate claim."),
        "configuration": {"packages": man["packages"], "users": man["users"],
                          "prompt_tokens": man["prompt_tokens"], "generated_tokens": man["generated_tokens"],
                          "token_steps": man["token_steps"], "link_channel_cycles": LINK_CH,
                          "X_HE": 1, "X_ME": 1, "X_ATT": 1, "X_IDX": 2, "X_SEL": 1, "X_EG": 1, "X_SU": 1,
                          "arm_A": {"W_HBM": 0, "weights": "roms/qrom.hex (ROM port)"},
                          "arm_B": {"W_HBM": 1, "weights": "roms/hbm_q.hex via ot_hdc_qstream + ot_hdc_hbm_model"},
                          "verilator_makeflags": OPT_MAKEFLAGS},
        "reference_record": {"path": rel(REFERENCE), "sha256": sha(REFERENCE),
                             "image_match": man["reference_record_image_match"]},
        "matching": matched,
        "images": {k: man[k] for k in ("source_commit", "source_tracked_dirty", "isa_pipeline",
                                        "program_instructions", "qe_fetch_lists", "weight_equivalence",
                                        "model_checkpoint_sha256", "model_config_sha256", "prompts",
                                        "golden_argmax")},
        "manifest_sha256": sha(images / "manifest.json"),
        # the tool that combined the arms (source_sha256 holds the one that prepared, built and ran them)
        "combine_tool_sha256": sha(Path(__file__).resolve()),
        "image_sha256": man["image_sha256"],
        "source_sha256": man["source_sha256"],
        "arms": {"A": a, "B": b},
    }
    if both:
        ca, cb = a["cycles_per_token_step"], b["cycles_per_token_step"]
        ta, tb = a["summary"]["total_cycles"], b["summary"]["total_cycles"]
        wait_b = sum(p["qgate_wait"] for p in b["probe"])
        rec["delta"] = {
            "definition": "B (QE weight-HBM) minus A (ROM weights); percent of A",
            "per_token_step": [{"position": i, "A_cycles": x, "B_cycles": y, "delta_cycles": y - x,
                                "delta_percent": pct(y - x, x),
                                "B_weight_gate_wait_cycles": b["qgate_wait_per_token_step"][i]}
                               for i, (x, y) in enumerate(zip(ca, cb))],
            "total": {"A_cycles": ta, "B_cycles": tb, "delta_cycles": tb - ta, "delta_percent": pct(tb - ta, ta)},
            "B_weight_gate_wait_cycles_total": wait_b,
            "B_weight_gate_wait_share_of_delta": round(wait_b / (tb - ta), 4) if tb != ta else None,
            "B_weight_hbm": {
                "sector_reads": sum(w["sector_reads"] for w in b["weight_hbm"]),
                "weight_words_delivered": sum(h["q_words"] for h in b["hbm_node"]),
                "activates": sum(w["activates"] for w in b["weight_hbm"]),
                "row_hits": sum(w["row_hits"] for w in b["weight_hbm"]),
                "row_conflicts": sum(w["row_conflicts"] for w in b["weight_hbm"]),
                "refreshes": sum(w["refreshes"] for w in b["weight_hbm"]),
                "request_backpressure_cycles": sum(w["req_backpressure_cycles"] for w in b["weight_hbm"]),
                "read_latency_max_ps": max(w["rd_lat_max_ps"] for w in b["weight_hbm"]),
                "mean_read_latency_ps": round(sum(w["rd_lat_sum_ps"] for w in b["weight_hbm"])
                                              / max(1, sum(w["sector_reads"] for w in b["weight_hbm"])), 1),
            },
            "index_hbm_refreshes": {"A": sum(h["idx_refresh"] for h in a["hbm_node"]),
                                    "B": sum(h["idx_refresh"] for h in b["hbm_node"])},
        }
    else:
        rec["delta"] = None
        rec["failure"] = {"A_pass": a.get("pass"), "B_pass": b.get("pass"),
                          "A_failed_checks": sorted(k for k, v in a.get("checks", {}).items() if not v),
                          "B_failed_checks": sorted(k for k, v in b.get("checks", {}).items() if not v),
                          "matching_failed": sorted(k for k, v in matched.items() if not v)}
    output.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--scratch", type=Path, required=True)
    p = sub.add_parser("arm")
    p.add_argument("--whbm", type=int, choices=(0, 1), required=True)
    p.add_argument("--images", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--jobs", type=int, default=8)
    p = sub.add_parser("combine")
    p.add_argument("--images", type=Path, required=True)
    p.add_argument("--arm-a", type=Path, required=True)
    p.add_argument("--arm-b", type=Path, required=True)
    p.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    if args.cmd == "prepare":
        m = prepare(args.scratch)
        print(json.dumps({k: m[k] for k in ("isa_pipeline", "weight_equivalence", "reference_record_image_match",
                                            "golden_argmax", "wall_seconds")}, indent=1))
        return 0
    if args.cmd == "arm":
        return 0 if arm(args.whbm, args.images, args.scratch, args.jobs)["pass"] else 1
    rec = combine(args.images, args.arm_a, args.arm_b, args.output)
    print(rec["status"], json.dumps(rec["delta"]["total"] if rec["delta"] else rec["failure"]))
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
