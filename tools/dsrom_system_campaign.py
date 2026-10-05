#!/usr/bin/env python3
"""DeepSeek-V4.1 ROM reduced-array SYSTEM gate (stream claude/dsrom-system-rtl-20261003).

Runs rtl/test/dsrom_sys/tb_dsrom_system.sv -- the successor of the all-unit
array bench with the system blocks closed: ot_dsrom_link_rt on every link
(typed in-package UCIe / board light-FEC, CRC error injection on board links),
ot_dsrom_stage_guard on every inbound stream, ot_dsrom_host_cq as the host
binding (prompts, LAUNCH, tagged completions with back-pressure, watchdog),
ot_dsrom_stall_export per package, and the attention KV in attached HBM
(kv_prefetch + shared K stacks + timed refresh-aware HBM model).  The ISA
pipeline (exact against hdc_golden_v41) supplies the expected tokens, logits
and final KV / vector-memory state, exactly as tools/rtl_hdc_v41x_array_campaign.py.

Usage: python3 tools/dsrom_system_campaign.py --only sys_b2 --scratch DIR --output FILE [--prepare-only]
"""
import argparse, hashlib, json, os, subprocess, sys, time, threading
from pathlib import Path

for flag in ("--all-unit", "--kv-hbm"):          # the array campaign reads these at import
    if flag not in sys.argv:
        sys.argv.append(flag)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_array_campaign as AC  # noqa: E402
import numpy as np  # noqa: E402

A, P, I, V, core, ximg = AC.A, AC.P, AC.I, AC.V, AC.core, AC.ximg
TB = ROOT / "rtl/test/dsrom_sys/tb_dsrom_system.sv"
HARNESS = ROOT / "rtl/test/dsrom_sys/dsrom_system_harness.cpp"
SYS_RTL = [ROOT / f"rtl/dsrom_sys/{m}.sv" for m in
           ("ot_dsrom_link_chan", "ot_dsrom_link_rt", "ot_dsrom_link_sel", "ot_dsrom_stage_guard", "ot_dsrom_host_cq",
            "ot_dsrom_stall_export")] + [ROOT / "rtl/link/ot_link_crc32.sv"]
# name: body packages, head parts, package of each node, users, link STALL %, prompt, generated
CONFIGS = {
    # two single-die packages: both ring links are board links
    "sys_b2": dict(body=2, hp=0, pkg=[0, 1], users=1, stall=5, plen=3, ngen=1),
    # 3 body stages + 2 chained lm_head parts on 5 dies in 3 packages {0,1} {2,3} {4}:
    # links 0->1 and 2->3 in-package UCIe, 1->2, 3->4, 4->0 board
    "sys_b5": dict(body=3, hp=2, pkg=[0, 0, 1, 1, 2], users=1, stall=5, plen=2, ngen=1),
    # two users through the same 5-die array: per-user KV / index namespaces, interleaved stage handoffs
    "sys_b5_u2": dict(body=3, hp=2, pkg=[0, 0, 1, 1, 2], users=2, stall=5, plen=2, ngen=1),
    # deeper decode: positions 0..3, two generated tokens fed back through the host queue
    "sys_b5_p3g2": dict(body=3, hp=2, pkg=[0, 0, 1, 1, 2], users=1, stall=5, plen=3, ngen=2),
    # five body dies (8 layers each, the last carries the whole lm_head) in packages {0,1} {2,3} {4}:
    # links 0->1, 2->3 UCIe; 1->2, 3->4, 4->0 board
    "sys_d5": dict(body=5, hp=0, pkg=[0, 0, 1, 1, 2], users=1, stall=5, plen=2, ngen=1),
    "sys_d5_u2": dict(body=5, hp=0, pkg=[0, 0, 1, 1, 2], users=2, stall=5, plen=2, ngen=1),
    "sys_d5_p3g2": dict(body=5, hp=0, pkg=[0, 0, 1, 1, 2], users=1, stall=5, plen=3, ngen=2),
}


def config_svh(plan, lay, pkg):
    n = plan.n
    cls = [int(pkg[k] != pkg[(k + 1) % n]) for k in range(n)]
    return AC.config_svh(plan, lay, "p2p") + AC.fn("C_LCLASS", cls), cls


def sources():
    return [*core.rtl_sources(True), *AC.BENCH_AUX_RTL, *AC.KV_HBM_RTL, AC.LINK, AC.ROUTER, AC.CTRL,
            *SYS_RTL, TB, HARNESS, core.SVH, core.VLT]


def build(obj: Path, svh: str, c: dict) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    (obj / "v41_array_cfg.svh").write_text(svh)
    cmd = ["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
           "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN", "-Wno-TIMESCALEMOD",
           "-Wno-MODDUP", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT", "-Wno-PINMISSING",
           "--top-module", "tb_dsrom_system", f"-GUSERS={c['users']}", f"-GSTALL={c['stall']}",
           *[f"-G{g}" for g in os.environ.get("OT_SYS_GPARAMS", "").split()],
           *(["-GMBAW_P=18"] if c["hp"] > 0 else []),
           "-Mdir", str(obj), f"-I{obj}", f"-I{core.SVH.parent}", str(core.VLT),
           f"+define+HDC_SW={I.SU_LANES}",
           *[f"+define+HDC_X_{x}={2 if x == 'IDX' else 1}" for x in ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")],
           "+define+HDC_W_HBM=1", "+define+HDC_KV_HBM=1",
           *map(str, core.rtl_sources(True)), *map(str, AC.BENCH_AUX_RTL), *map(str, AC.KV_HBM_RTL),
           str(AC.LINK), str(AC.ROUTER), str(AC.CTRL), *map(str, SYS_RTL), str(TB), str(HARNESS),
           "-CFLAGS", "-O1", "-MAKEFLAGS", os.environ.get("OT_SYS_MAKEFLAGS", "OPT_FAST=-O1 OPT_GLOBAL=-O1"),
           "-j", os.environ.get("OT_SYS_JOBS", "16")]
    (obj / "build_cmd.json").write_text(json.dumps(cmd))
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (obj / "build.log").write_text(r.stdout[-200000:] + r.stderr[-200000:])
    if r.returncode:
        raise RuntimeError(f"build failed, see {obj/'build.log'}\n{r.stderr[-3000:]}")
    return obj / "Vtb_dsrom_system", time.time() - t0


def prepare(name, scratch: Path):
    c = CONFIGS[name]
    model = V.Model()
    lay = P.Layout(model)
    A.place_head_parts(lay)
    roms = scratch / "roms"
    if not (roms / "hbm_q.hex").exists():
        A.write_roms(roms, lay)
        ximg.write_banked(roms / "hbank.hex", ximg.hbank_image(lay, 8), 32, 8)
        ximg.write(roms, lay, hhw=8, mg=8)
        sectors, _ = P.qe_hbm_image(lay)
        (roms / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    gold = A.golden_runs(model, c["ngen"], scratch / "gold.json", c["plen"])
    plan = A.Plan(lay, A.split(model, c["body"]), c["hp"], False, "relay")
    progs = [A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    recs, states = A.run_pipeline(plan, progs, base, gold)
    if not all(r["logits_bit_exact_every_step"] and r["argmax_and_value_every_step"] for r in recs):
        raise RuntimeError(f"ISA pipeline not bit-exact with the golden: {recs}")
    if c["hp"] > 0:
        # The weight-tile bank image (mbank) of hdc_images_v41x covers only the ME ops of the
        # single-core program, whose lm_head is whole.  Split lm_head parts read
        # lay.mat[("head", parts, k)], so the bank must cover the union of every stage
        # program's ME ops (found 2026-10-03: sys_b5 head parts read unwritten bank lines).
        mb, me_xs = ximg.mbank_image(lay, [f for prog in progs for f in prog], 8)
        ximg.write_words(roms / "mbank.hex", mb, 32)
        ik = min(a for n_, a in lay.kv.map.items() if n_.startswith("IK")) // I.W_LANES
        (roms / "cfg.hex").write_text(f"{ik:06x}\n{me_xs:06x}\n")
    img = scratch / f"cfg_{name}"
    steps = A.write_config(img, plan, progs, gold, states)
    sectors, first = P.qe_hbm_image(lay)
    for k, prog in enumerate(progs):
        ents = P.qe_fetch_list(lay, prog, first)
        (img / f"qlist_stage{k:02d}.hex").write_text(P.hexwords(P.encode_list(ents), P.LIST_BITS))
    svh, cls = config_svh(plan, lay, c["pkg"])
    return dict(plan=plan, recs=recs, gold=gold, img=img, roms=roms, steps=steps, svh=svh, link_class=cls)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", required=True, choices=sorted(CONFIGS))
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--prepared", action="store_true",
                    help="reuse images, ROMs, golden and svh a --prepare-only run left in --scratch "
                         "(hosts without the golden's tokenizer dependency)")
    ap.add_argument("--all-unit", action="store_true"); ap.add_argument("--kv-hbm", action="store_true")
    a = ap.parse_args()
    a.scratch.mkdir(parents=True, exist_ok=True)
    c = CONFIGS[a.only]
    t0 = time.time()
    if a.prepared:
        prep = json.loads((a.scratch / f"prep_{a.only}.json").read_text())
        gold = json.loads(next(a.scratch.glob("gold_*.json")).read_text())
        ctx = dict(recs=prep["isa_pipeline"], link_class=prep["link_class_per_link"],
                   gold=[dict(prompt=p, generated=g) for p, g in zip(prep["golden_prompts"], prep["golden_generated"])],
                   img=a.scratch / f"cfg_{a.only}", roms=a.scratch / "roms",
                   steps=c["plen"] + c["ngen"] - 1, svh=(a.scratch / f"svh_{a.only}.svh").read_text())
        assert all(r["logits_bit_exact_every_step"] for r in ctx["recs"]), "prepared ISA pipeline not exact"
    else:
        ctx = prepare(a.only, a.scratch)
    rec = {"schema": "opentallas.rtl.dsrom_system_gate.v1", "config_name": a.only, "config": c,
           "link_class_per_link": ctx["link_class"], "isa_pipeline": ctx["recs"],
           "golden_prompts": [g["prompt"] for g in ctx["gold"]],
           "golden_generated": [g["generated"] for g in ctx["gold"]],
           "prepare_seconds": round(time.time() - t0, 1),
           "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sources()}}
    if a.prepare_only:
        (a.scratch / f"svh_{a.only}.svh").write_text(ctx["svh"])
        a.output.write_text(json.dumps(rec, indent=1) + "\n")
        (a.scratch / f"prep_{a.only}.json").write_text(json.dumps(rec, indent=1) + "\n")
        return 0
    tag = os.environ.get("OT_SYS_TAG", "")
    rec["gparams"] = os.environ.get("OT_SYS_GPARAMS", "")
    exe, bs = build(a.scratch / f"obj_{a.only}{tag}", ctx["svh"], c)
    rec["build_seconds"] = round(bs, 1)
    rec["prepared_from_scratch"] = bool(a.prepared)
    rec["verilator"] = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    log = a.scratch / f"out_{a.only}{tag}.txt"
    cmd = [str(exe), f"+DIR={ctx['img']}", f"+ROMS={ctx['roms']}", f"+NUSERS={c['users']}",
           f"+NPROMPT={c['plen']}", f"+NGEN={c['ngen']}", "+HB=100000"]
    rec["execution_command"] = cmd
    t1 = time.time()
    with open(log, "w") as fh:
        rc = subprocess.run(["stdbuf", "-oL", *cmd], stdout=fh, stderr=subprocess.STDOUT).returncode
    out = log.read_text()
    rec["run_seconds"] = round(time.time() - t1, 1)
    rec["returncode"] = rc
    try:
        rec["parsed"] = AC.parse(out, c["users"], ctx["steps"], c["ngen"])
    except Exception as e:  # noqa: BLE001
        rec["parse_error"] = str(e)
    rec["sys_lines"] = [l for l in out.splitlines() if l.split(" ")[0] in
                        ("LINK", "GUARD", "STALLX", "HOSTCQ", "CPL", "SYS_FAULT", "HOSTCQ_FAIL", "STUCK",
                         "WATCHDOG", "KVHBM", "TOK", "HDC41_ARRAY", "PASS", "FAIL", "NODE", "HBM_NODE",
                         "CPL_MISMATCH", "MISMATCH", "LOGIT", "KVHBM_FAIL", "FAULT")]
    rec["log_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    rec["pass"] = rc == 0 and out.rstrip().splitlines()[-2:].count("PASS") >= 0 and "\nPASS\n" in out + "\n" \
        and rec.get("parsed", {}).get("pass", False) and "HOSTCQ_FAIL" not in out and "SYS_FAULT" not in out
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print("PASS" if rec["pass"] else "FAIL", a.only)
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
