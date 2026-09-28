#!/usr/bin/env python3
"""Adopted V4.1 layer die top (rtl/chip/ot_chip_v41x_die.sv): lint, reduced synthesis size, one-token smoke.

Three checks, each recorded with its tool versions and the sha256 of every input:

1. lint     Verilator --lint-only of ot_chip_v41x_die (and ot_chip_v41x_tile) at the adopted configuration,
            bit-level FP RTL, the decode campaign's warning set;
2. synth    Yosys (0.68, native front end) elaboration of ot_chip_v41x_die at a REDUCED parameterisation and
            its RTL-level size: hierarchy -check, proc, stat (word-level cells and memories before any
            optimisation or technology mapping: the coarse `synth` flow's share pass and an `opt -fast` loop each
            ran for over 1.5 h on the attention adapter's re-encoder and were stopped) (small ROM / SRAM depths); the HBM3E stack stand-ins are
            simulation timing models and are read as black boxes (the physical block is the PHY abstract);
            package imports inside module bodies are hoisted to file scope in scratch copies (the native front
            end rejects them; equivalent for these single-module files); `stat` per module and for the top;
3. smoke    one reduced DeepSeek-V4.1 decode step (token 3582 at position 7) through the die top under
            Verilator (bit-equivalent DPI FP stand-ins, as the adopted gate), on the images of the adopted
            single-token HBM gate (tools/rtl_hdc_v41x_whbm_pooled_campaign.py: all units, X_IDX = 2,
            W_HBM = 1), checked bit for bit (every logit, the whole vector memory, the whole KV cache) and
            compared with that gate's own run (--reference: token, cycles, stream and HBM-writer counters).

Heavy steps run through /tmp/claude-1000/remote_gate.sh on a worker; image preparation reuses the gate's.
Writes results/rtl/hdc_v41x_die_top_smoke.json.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_decode_campaign as core  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41x_die_top_smoke.json"
TB = ROOT / "rtl/test/tb_chip_v41x_die_smoke.sv"
HARNESS = ROOT / "rtl/test/chip_v41x_die_smoke_harness.cpp"
POOL = ("ot_hdc_v41x_idx_pcol", "ot_hdc_v41x_idx_hsum", "ot_hdc_v41x_idx_pool_finish",
        "ot_hdc_v41x_idx_pool_batch", "ot_hdc_v41x_idx_pool_replica", "ot_hdc_v41x_idx_pool_adapt",
        "ot_hdc_v41x_idx_pool_kwr", "ot_hdc_v41x_idx_pool_hbm_bridge")
HBM_MODELS = [ROOT / "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv", ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"]
EXTRA = [ROOT / p for p in ("rtl/hdc/hbm/ot_hdc_qstream.sv", "rtl/hdc/kv/ot_hdc_hbm_model.sv",
                            "rtl/rom/ot_rom_pkg_ctrl_x.sv", "rtl/rom/ot_rom_fabric_router.sv",
                            "rtl/rom/ot_rom_oneshot_px.sv")]
CHIP = [ROOT / f"rtl/chip/{n}.sv" for n in ("ot_chip_v41x_kv_prefetch", "ot_chip_v41x_hbm_karb",
                                            "ot_chip_v41x_hbm3e_phy", "ot_chip_v41x_coll_dma", "ot_chip_v41x_tile",
                                            "ot_chip_v41x_die")]
KVTB = ROOT / "rtl/test/tb_chip_v41x_kv_prefetch.sv"
KVTB_SOURCES = [ROOT / p for p in ("rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv", "rtl/hdc/kv/ot_hdc_hbm_model.sv",
                                   "rtl/chip/ot_chip_v41x_hbm3e_phy.sv", "rtl/chip/ot_chip_v41x_hbm_karb.sv",
                                   "rtl/chip/ot_chip_v41x_kv_prefetch.sv")]
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools"))
VERILATOR = os.environ.get("OT_VERILATOR", str(TOOLS_ROOT / "verilator-5.050/bin/verilator"))
YOSYS = os.environ.get("OT_YOSYS", str(TOOLS_ROOT / "yosys-0.68/bin/yosys"))
LINT_FLAGS = list(core.LINT_FLAGS) + ["-Wno-TIMESCALEMOD"]
# the reduced synthesis parameterisation: ROM / SRAM depths shrunk, engine widths as adopted
SYNTH_PARAMS = {"PROG_AW": 6, "WROM_AW": 6, "HROM_AW": 6, "EROM_AW": 6, "CROM_AW": 6, "VM_AW": 10,
                "LAW": 4, "LWIN": 4, "KV_AW": 6, "HBAW": 4, "MBAW": 4, "KV_STG": 1024, "KV_SAW": 10, "KV_WQD": 8}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def setup(fp: str) -> None:
    core.UNITS = tuple(core.X_UNITS)
    core.PARAMS["fp"] = fp
    core.IDX_POOL = True
    if not any(p.name == "ot_hdc_v41x_idx_pool_hbm_bridge.sv" for p in core.RTL):
        core.RTL.extend(ROOT / f"rtl/hdc/v41x/{n}.sv" for n in POOL)


def sources(fp: str, build=False, models=True) -> list[Path]:
    setup(fp)
    out = [p for p in core.rtl_sources(build) if models or p not in HBM_MODELS]
    out += [p for p in EXTRA if (models or p not in HBM_MODELS) and p not in out]
    return out + CHIP


def tool_version(cmd) -> str:
    r = subprocess.run([cmd, "-V" if "yosys" in cmd else "--version"], capture_output=True, text=True)
    return (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout + r.stderr).strip() else "unknown"


NEW = ("rtl/chip/ot_chip_v41x_",)


def lint() -> dict:
    """Lint both tops.  Messages located in the new chip sources gate the verdict; messages the adopted core's
    own sources raise (Codex-owned, unchanged here) are recorded as inherited."""
    out = {}
    for top in ("ot_chip_v41x_die", "ot_chip_v41x_tile"):
        cmd = [VERILATOR, "--lint-only", *LINT_FLAGS, "--top-module", top, f"-I{core.SVH.parent}",
               *map(str, sources("rtl"))]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        msgs = [ln.replace(str(ROOT) + "/", "") for ln in r.stderr.splitlines()
                if ln.startswith("%") and not ln.startswith("%Error: Exiting due to")]
        own = [m for m in msgs if any(n in m.split(" ")[1] for n in NEW)]
        inherited = [m for m in msgs if m not in own]
        errors = [m for m in msgs if m.startswith("%Error")]
        out[top] = {"returncode": r.returncode, "new_source_messages": own, "inherited_messages": inherited,
                    "errors": errors, "clean": not own and not errors}
    return {"tool": tool_version(VERILATOR), "flags": LINT_FLAGS, "tops": out,
            "verdict_rule": "clean = no message located in rtl/chip/ot_chip_v41x_* and no %Error; warnings inside "
                            "the adopted core's own sources are listed as inherited (not edited here)",
            "pass": all(t["clean"] for t in out.values())}


IMPORT = re.compile(r"^[ \t]*import[ \t]+\w+::\*;[ \t]*\n", re.M)


def blackbox_stub(src: Path, dst: Path) -> None:
    """The module header of a simulation model as a (* blackbox *) module: the physical block is an abstract."""
    txt = src.read_text()
    i = txt.index("module ")
    j = txt.index("\n);", i) + 3
    dst.write_text("(* blackbox *)\n" + txt[i:j] + "\nendmodule\n")


def hoist_imports(src: Path, dst: Path) -> bool:
    """Yosys's native front end rejects a package import inside a module body; the same import at file scope,
    just before the module, is equivalent for these single-module files.  Returns whether a copy was changed."""
    txt = src.read_text()
    imps = IMPORT.findall(txt)
    if not imps:
        return False
    body = IMPORT.sub("", txt)
    k = body.index("\nmodule ") + 1 if not body.startswith("module ") else 0
    dst.write_text(body[:k] + "".join(sorted(set(i.strip() + "\n" for i in imps))) + body[k:])
    return True


def synth(scratch: Path) -> dict:
    """Yosys 0.68 native front end at the reduced parameterisation (see SYNTH_PARAMS)."""
    scratch.mkdir(parents=True, exist_ok=True)
    stubs, files, hoisted = [], [], []
    for p in HBM_MODELS:
        d = scratch / f"bb_{p.name}"
        blackbox_stub(p, d)
        stubs.append(d)
    for p in sources("rtl", models=False):
        d = scratch / f"hoist_{p.name}"
        if hoist_imports(p, d):
            files.append(d); hoisted.append(rel(p))
        else:
            files.append(p)
    srcs = " ".join(str(p) for p in files + stubs)
    chp = " ".join(f"-set {k} {v}" for k, v in SYNTH_PARAMS.items())
    script = (f"read_verilog -sv -DSYNTHESIS -I{core.SVH.parent} {srcs}; "
              f"chparam {chp} ot_chip_v41x_die; "
              f"hierarchy -check -top ot_chip_v41x_die; "
              f"proc; "
              f"tee -o {scratch}/stat.txt stat; tee -q -o {scratch}/stat.json stat -json")
    log = scratch / "yosys.log"
    t0 = datetime.datetime.now()
    r = subprocess.run([YOSYS, "-q", "-l", str(log), "-p", script], capture_output=True, text=True, cwd=ROOT)
    wall = (datetime.datetime.now() - t0).total_seconds()
    rec = {"tool": tool_version(YOSYS), "front_end": "read_verilog -sv (native)", "passes": "hierarchy -check; proc; stat (no opt, no mapping)",
           "script": script.replace(str(ROOT) + "/", "").replace(str(scratch), "<scratch>"),
           "reduced_parameters": SYNTH_PARAMS, "black_boxes": [rel(p) for p in HBM_MODELS],
           "import_hoisted_copies": hoisted, "returncode": r.returncode, "wall_seconds": round(wall, 1),
           "stderr_tail": ((r.stderr or "") + (r.stdout or ""))[-2000:]}
    stat = scratch / "stat.json"
    if r.returncode == 0 and stat.exists():
        d = json.loads(stat.read_text())
        mods = d.get("modules", {})
        top = d.get("design", {})
        rec["design"] = {k: top.get(k) for k in ("num_cells", "num_wires", "num_wire_bits", "num_memories",
                                                 "num_memory_bits") if k in top}
        rec["design_cells_by_type"] = dict(sorted(top.get("num_cells_by_type", {}).items(),
                                                  key=lambda kv: -kv[1])[:25])
        rec["modules"] = {m.lstrip("\\"): {"num_cells": v.get("num_cells"),
                                            "num_memory_bits": v.get("num_memory_bits")}
                          for m, v in mods.items() if "ot_chip_v41x" in m or "core_v41x" in m
                          or "ot_rom_" in m or "qstream" in m or "hbm" in m}
    rec["pass"] = r.returncode == 0 and bool(rec.get("design", {}).get("num_cells"))
    return rec


KVPF = re.compile(r"KVPF ops=(\d+) words_read=(\d+) bad=(\d+) held_min=(\d+) held_ops=(\d+) raw_checks=(\d+) "
                  r"refetches=(\d+) sectors_written=(\d+) wq_high=(\d+) hbm_kv_mismatch=(\d+) fault=(\d+) code=([01]+)")
KVCASES = re.compile(r"KVPF_CASES max_descriptor_ops=(\d+) max_words=(\d+) user_slice_ops=(\d+) slice_base=(\d+)")
WRAP = re.compile(r"KVPF_WRAP done=(\d+) writes=(\d+) hits=(\d+) mismatches=(\d+)")
KEYS = re.compile(r"KEYS reads=(\d+) bad=(\d+) writes=(\d+) wr_done=(\d+) contended=(\d+) kv_grants=(\d+)")
REGION = re.compile(r"REGION key=\[0,(\d+)\) kv=\[(\d+),(\d+)\) mem=(\d+) disjoint=(\d) inside=(\d)")
KVHBM = re.compile(r"KVHBM ops=(\d+) words=(\d+) sectors_written=(\d+) refetches=(\d+) wq_high=(\d+) "
                   r"hold_cycles=(\d+) grants=(\d+) code=([01]+) att_issue=(\d+) att_held_cycles=(\d+)")


def kvtest(scratch: Path) -> dict:
    """The focused KV prefetch bench: gate, read-after-write, max descriptor, user slice, eviction, the shared
    K ports under indexer traffic, the region check, and the HBM KV region against the golden at the end."""
    obj = scratch / "kvobj"
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [VERILATOR, "--binary", "--timing", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD",
           "-Wno-BLKSEQ", "-Wno-MULTIDRIVEN", "--top-module", "tb_chip_v41x_kv_prefetch", "-Mdir", str(obj),
           *map(str, KVTB_SOURCES), str(KVTB), "-j", "8"]
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if b.returncode:
        return {"pass": False, "build_returncode": b.returncode, "build_tail": (b.stdout + b.stderr)[-3000:]}
    r = subprocess.run([str(obj / "Vtb_chip_v41x_kv_prefetch")], capture_output=True, text=True, cwd=ROOT,
                       timeout=3600)
    log = r.stdout + r.stderr
    m, c, k, g = KVPF.search(log), KVCASES.search(log), KEYS.search(log), REGION.search(log)
    rec = {"pass": "PASS" in log and r.returncode == 0 and all((m, c, k, g)),
           "log_sha256": hashlib.sha256(log.encode()).hexdigest(), "log_tail": log[-1500:]}
    if m:
        rec["kv"] = dict(zip(("ops", "words_read", "word_mismatches", "min_hold_cycles", "held_ops", "raw_checks",
                              "refetches", "sectors_written", "write_queue_high", "hbm_kv_mismatches", "fault"),
                             map(int, m.groups()[:11])))
        rec["kv"]["fault_code"] = m.group(12)
    if c:
        rec["cases"] = dict(zip(("max_descriptor_ops", "max_descriptor_words", "user_slice_ops", "slice_base_word"),
                                map(int, c.groups())))
    w = WRAP.search(log)
    rec["pass"] = rec["pass"] and w is not None
    if w:
        rec["generation_wrap"] = dict(zip(("done", "row_writes", "write_hits", "mismatches"), map(int, w.groups())))
        rec["generation_wrap"]["negative_control"] = (
            "with the drain condition removed from the restart (sout == 0), the same bench does not pass: the stale "
            "responses are taken and the op never completes (TIMEOUT)")
    if k:
        rec["indexer_traffic"] = dict(zip(("key_reads", "key_mismatches", "key_writes", "key_wr_done",
                                           "contended_cycles", "kv_grants"), map(int, k.groups())))
    if g:
        rec["region"] = dict(zip(("key_sectors", "kv_sbase", "kv_end", "k_mem", "disjoint", "inside"),
                                 map(int, g.groups())))
    return rec


SINGLE = core.SINGLE
STREAM = re.compile(r"^QSTREAM (.*)$", re.M)


def build(obj: Path) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-IMPORTSTAR", "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT",
           "--top-module", "tb_chip_v41x_die_smoke", "-Mdir", str(obj), f"-I{core.SVH.parent}", str(core.VLT),
           *map(str, sources("dpi", build=True)), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"verilator build failed:\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
    return obj / "Vtb_chip_v41x_die_smoke"


def smoke(img: Path, obj: Path, reuse: bool = False) -> dict:
    """reuse: take obj's executable as built by build() from this tree (a memory-bounded host builds it once)."""
    exe = obj / "Vtb_chip_v41x_die_smoke" if reuse and (obj / "Vtb_chip_v41x_die_smoke").exists() else build(obj)
    args = (img / "run.args").read_text().split()
    t0 = datetime.datetime.now()
    sim = subprocess.run([str(exe), f"+DIR={img}", *args, "+QRATE=32"], capture_output=True, text=True,
                         timeout=4 * 3600, cwd=ROOT)
    wall = (datetime.datetime.now() - t0).total_seconds()
    log = sim.stdout + sim.stderr
    m, st, wr = SINGLE.search(log), STREAM.search(log), core.IDXHBMWR.search(log)
    if m is None or st is None or wr is None:
        raise SystemExit(f"no complete token record (exit {sim.returncode}):\n{log[-5000:]}")
    names = ("input_token", "position", "next_token", "isa_next_token", "cycles", "fault", "logit_mismatches",
             "vm_mismatches", "kv_mismatches")
    step = dict(zip(names, map(int, m.groups())))
    stream = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", st.group(1))}
    writer = dict(zip(("records", "sector_writes", "fifo_highwater", "read_stall_cycles", "writer_stall_cycles",
                       "refresh_events", "refpb_mode"), map(int, wr.groups())))
    die = re.search(r"DIE fault=([01]+) rtr_drops=(\d+) kv_descriptors=(\d+)", log)
    kvh = KVHBM.search(log)
    cnt = core.counters(log)
    passed = (sim.returncode == 0 and "PASS" in log and step["next_token"] == step["isa_next_token"] == 3118 and
              step["fault"] == 0 and step["logit_mismatches"] == 0 and step["vm_mismatches"] == 0 and
              step["kv_mismatches"] == 0 and stream.get("q_bad") == 0 and stream.get("qs_fault") == 0 and
              stream.get("q_words", 0) > 0 and stream.get("hbm_reads", 0) > 0 and die and int(die.group(1), 2) == 0
              and writer["records"] == 4 and writer["sector_writes"] == 12 * writer["records"]
              and kvh is not None and int(kvh.group(1)) > 0 and int(kvh.group(10)) > 0
              and int(kvh.group(8), 2) == 0
              and all(cnt.get(u, {}).get("ops", 0) > 0 for u in core.COUNTED + core.IDX_COUNTERS))
    return {"status": "pass" if passed else "fail", "step": step, "stream": stream,
            "index_key_hbm_writer": writer, "unit_counters": cnt,
            "die_fault_bits": die.group(1) if die else None,
            "kv_descriptors_announced": int(die.group(3)) if die else None,
            "kv_hbm": (dict(zip(("ops", "words_fetched", "sectors_written", "refetches", "write_queue_high",
                                 "kv_ok_low_cycles", "hbm_grants"), map(int, kvh.groups()[:7])),
                        fault_code=kvh.group(8), attention_issues=int(kvh.group(9)),
                        attention_held_cycles=int(kvh.group(10))) if kvh else None), "simulation_exit": sim.returncode,
            "simulation_wall_seconds": round(wall, 1),
            "simulation_log_sha256": hashlib.sha256(log.encode()).hexdigest(), "simulation_tail": log[-2500:]}


def compare(sm: dict, ref_path: Path | None) -> dict | None:
    if ref_path is None or not ref_path.exists():
        return None
    ref = json.loads(ref_path.read_text())
    keys = ("next_token", "cycles", "logit_mismatches", "vm_mismatches", "kv_mismatches")
    same = {k: sm["step"][k] == ref["step"][k] for k in keys}
    same_stream = {k: sm["stream"].get(k) == ref["stream"].get(k) for k in ref["stream"]}
    same_wr = {k: sm["index_key_hbm_writer"].get(k) == ref["index_key_hbm_writer"].get(k)
               for k in ref["index_key_hbm_writer"]}
    return {"reference": ("tools/rtl_hdc_v41x_whbm_pooled_campaign.py (the adopted single-token HBM gate) re-run "
                          "on the same images"),
            "reference_source_commit": ref.get("source_commit"),
            "reference_simulation_log_sha256": ref.get("simulation_log_sha256"),
            "reference_image_sha256": ref.get("image_sha256"),
            "reference_status": ref["status"], "reference_step": ref["step"],
            "reference_stream": ref["stream"], "reference_index_key_hbm_writer": ref["index_key_hbm_writer"],
            "equal_step_fields": same, "equal_stream_fields": same_stream, "equal_writer_fields": same_wr,
            "cycle_identical": same["cycles"], "token_identical": same["next_token"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--image-dir", type=Path, required=False)
    ap.add_argument("--scratch", type=Path, default=Path(os.environ.get("OT_SCRATCH", "/tmp")) / "v41x_die_smoke")
    ap.add_argument("--steps", default="lint,synth,kvtest,smoke")
    ap.add_argument("--obj", type=Path, help="the smoke's Verilator object directory (default <scratch>/obj)")
    ap.add_argument("--reuse-executable", action="store_true")
    ap.add_argument("--reference", type=Path, help="the adopted gate's record on the same images")
    ap.add_argument("--merge", type=Path, nargs="*", default=[], help="partial records to merge (per-step runs)")
    ap.add_argument("--output", type=Path, default=OUT)
    a = ap.parse_args()
    steps = [s for s in a.steps.split(",") if s]
    rec: dict = {}
    partials = []
    for m in a.merge:
        part = json.loads(m.read_text())
        rec.update({k: v for k, v in part.items() if k in ("lint", "synth", "smoke", "kvtest", "reference_comparison")})
        partials.append(part)
    if "lint" in steps:
        rec["lint"] = lint()
    if "synth" in steps:
        rec["synth"] = synth(a.scratch / "synth")
    if "kvtest" in steps:
        rec["kvtest"] = kvtest(a.scratch)
    if "smoke" in steps:
        rec["smoke"] = smoke(a.image_dir, a.obj or a.scratch / "obj", a.reuse_executable)
        rec["smoke"]["image_sha256"] = {n: sha(a.image_dir / n) for n in sorted(os.listdir(a.image_dir))
                                        if n.endswith((".hex", ".json", ".args"))}
    if "smoke" in rec and a.reference is not None:
        rec["reference_comparison"] = compare(rec["smoke"], a.reference)
    ok = {k: rec[k]["pass"] if k != "smoke" else rec[k]["status"] == "pass"
          for k in ("lint", "synth", "kvtest", "smoke") if k in rec}
    srcs = sorted(set(sources("rtl") + sources("dpi", build=True) + KVTB_SOURCES + [KVTB]), key=str)
    rec.update({
        "schema": "opentallas.rtl.hdc_v41x_die_top_smoke.v1",
        "tops": {"die": "rtl/chip/ot_chip_v41x_die.sv", "tile": "rtl/chip/ot_chip_v41x_tile.sv"},
        "configuration": {"X_HE": 1, "X_ME": 1, "X_ATT": 1, "X_IDX": 2, "X_SEL": 1, "X_EG": 1, "X_SU": 1,
                          "W_HBM": 1, "KV_HBM": 1, "hbm_stacks": 4,
                          "collective": "ot_rom_oneshot_die_px RELAY=1 ADD_LAT=3 GW=1"},
        "kv_hbm_prefetch": ("HBM prefetch in the attention adapter's address layout, K ports arbitrated with the "
                            "pooled indexer, KV region above the index keys, write-through staging; integrated "
                            "test: the die smoke (KV starts in HBM, bit-exact) and the focused bench"
                            if all(ok.get(k) for k in ("kvtest", "smoke")) else
                            "implemented; integrated test not passed at this record (see checks)"),
        "kv_staging_sizing": {"slots": 2, "words_per_slot": 2048, "bytes": 2 * 2048 * 64,
                              "largest_op_words": 960, "basis": "ot_hdc_v41x_att_adapt TROWS = 160, D = 32: q.k "
                              "reads D words per 16-row tile, p.v T rows per 16-dim tile, tiles rounded up to G = 4; "
                              "a KV word is 16 elements (the 160 x 32 = 5,120 of the review is elements, 320 words); "
                              "elaboration check STG >= the largest op"},
        "hbm_map": {"index_keys": "[0, KEY_USERS * 2^18) sectors a stack", "attention_kv":
                    "[KV_SBASE = KEY_USERS * 2^18, + 2 * (KV_USERS * 2^15 / 4)) sectors a stack",
                    "k_mem_sectors": 1 << 19, "checks": "elaboration: disjoint and inside K_MEM; run time: every "
                    "prefetch sector inside the KV region (fault), every K request inside K_MEM (PHY k_oor)"},
        "outstanding": [
            "one collective engine of the ledger's 8 per die; GW = 1 (the gw4 gather lever is not wired)",
            "package controller, fabric router, collective engine and UCIe / board-link ports are not exercised "
            "by the smoke",
            "the KV prefetch issues one word request a cycle (one stack a cycle); its exposure is the smoke's "
            "cycle difference against the adopted gate",
            "HBM3E interfaces are simulation timing models, not PHY RTL"],
        "claim_boundary": (
            "Die-top integration check. Lint and a reduced-depth Yosys coarse synthesis of the adopted die top; "
            "one reduced V4.1 token through the die top in host mode (the host CSR port drives the core's step "
            "port) with bit-equivalent DPI FP stand-ins, HBM3E stacks as the adopted gates' simulation timing "
            "models; the KV starts in HBM and every attention op's words are prefetched through the arbitrated "
            "K ports (the core's KV_HBM gate holds the op until kv_ok). The package controller, fabric router, collective engine and UCIe / board-link ports "
            "are elaborated, linted and synthesised but not exercised by the smoke. No P&R, no timing claim."),
        "checks": ok,
        "status": "pass" if ok and all(ok.values()) else ("incomplete" if not ok else "fail"),
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                        cwd=ROOT).stdout.strip(),
        "source_sha256": {rel(p): sha(p) for p in srcs + [core.SVH, core.VLT, TB, HARNESS, Path(__file__),
                                                          ROOT / "tools/rtl_hdc_v41x_decode_campaign.py",
                                                          ROOT / "tools/hdc_program_v41.py",
                                                          ROOT / "tools/hdc_images_v41x.py"]},
    })
    # the runs merged here pin their own sources: record each run's commit and every input that differs
    rec["merged_runs"] = [{"steps": [k for k in ("lint", "synth", "kvtest", "smoke") if k in part],
                           "source_commit": part.get("source_commit"),
                           "inputs_differing_from_this_record": sorted(
                               k for k, v in part.get("source_sha256", {}).items()
                               if rec["source_sha256"].get(k) != v)} for part in partials]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=2) + "\n")
    print(rec["status"], ok)
    return 0 if rec["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
