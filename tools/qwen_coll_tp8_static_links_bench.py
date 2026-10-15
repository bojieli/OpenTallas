#!/usr/bin/env python3
"""qwen-coll-io r5 2026-10-14 (OWNER 0ah static cycle schedule; OWNER 19:12 all on-chip execution real hardware):
COMPOSED bench of the static TP8 collective on the REAL static link RTL, rtl/test/tb_coll_tp8_static_links.sv.

8 dies, each: ot_coll_cmd_issue (compiler commands over the program-write face, issued by ot_qwen_fixed_issue) ->
ot_coll_tp8_static (or the die-name master) -> ot_coll_static_linkcal (IO calendar) -> qfd_io_xfifo_static (static
CDC) -> qfd_io_ucie_static / qfd_io_serdes_static x3 (static codecs, CRC32) -> fixed-latency PHY models (the only
modelled part).  The scheduler is tools/qwen_coll_tp8_static_bench.schedule (same compiler model) at the COMPOSED
latencies LU / LS; this script also writes the stage program (pw.hex) the issuer executes.

Composed latency (link roots mesochronous with the core root, PHI 0 same edge / PHI 1 link edge after the core edge):
  L_min = KC + KW + 17 + PHY   (UCIe: LU = 4 + 2 + 17 + 14 = 37;  SerDes: LS = 4 + 2 + 17 + 339 = 362)
the --tight case runs L_min - 1 and must FAIL (publication fault), proving the priced value is the minimum.
Exit 0 iff every case meets its expectation."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from qwen_coll_tp8_static_bench import schedule, vectors, ND, GC  # noqa: E402

KC, KW, PU, PS = 4, 2, 14, 339
DEPTH, START = 8, 40
SRC = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
    "rtl/rom/ot_coll_fold_slice.sv", "rtl/rom/ot_coll_rst_leaf.sv", "rtl/lib/ot_reset_sync.sv",
    "physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v",
    "physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v",
    "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
    "rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv", "rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv",
    "rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv",
    "rtl/physical/ot_qfd_static_transport.sv", "rtl/physical/ot_qfd_io_xfifo_static.sv",
    "rtl/physical/ot_qfd_io_links_static.sv", "rtl/physical/ot_qfd_coll_static_face.sv", "rtl/physical/ot_qfd_ucie_static_share.sv", "rtl/physical/ot_qfd_ucie_six_five.sv", "rtl/physical/ot_qfd_collective_static_io.sv", "rtl/physical/ot_qfd_collective_static_io_production.sv",
    "rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv",
    "rtl/rom/ot_coll_tp8_static.sv", "rtl/physical/ot_qfd_io_collective_static.sv",
    "rtl/rom/ot_coll_static_linkcal.sv", "rtl/rom/ot_coll_cmd_issue.sv",
    "rtl/test/tb_coll_tp8_static_links.sv")]
RES = re.compile(r"TP8SL dies=8 .* mismatches=(\d+) extra=(\d+) out_err=(\d+) cmd_bad=(\d+) coll_fault=([01]+) "
                 r"issuer_fault=([01]+) die_fault=([01]+) words_out=(\d+) meas_lu=(-?\d+) meas_ls=(-?\d+) "
                 r"pr_overlap=(\d+) issuer_done=([01]+)")

# name, msgs, words, modes, expectation, plusargs
UNIT = [
    ("reduce_8w_x7", 7, 8, "r", "pos", {}),
    ("reduce_1w_x7_odd", 7, 1, "r", "pos", {}),
    ("gather_4w_x4", 4, 4, "g", "pos", {}),
    ("mixed_8w_x7", 7, 8, "m", "pos", {}),
    ("fault_drop_word", 4, 8, "r", "drop", {"DROP": 1}),
    ("fault_serdes_crc", 4, 8, "m", "corrupt", {"CORRUPT": 3}),
]
PRODUCTION = [
    ("qwen_ar_256w", 1, 256, "r", "pos", {}),
    ("qwen_layer_2x256w", 2, 256, "r", "pos", {}),
    ("qwen_argmax_1w", 1, 1, "g", "pos", {}),
    ("qwen_layer_2x256w_argmax", 3, 256, "rrg1", "pos", {}),
]


def program_words(prog, nwords, cmd_pin_stages=0):
    """Stage program for ot_coll_cmd_issue: rows {cycle, words, mode}, tags, END row, seal (see its header)."""
    pw, rows = [], []
    for k, p in enumerate(prog):
        x = p["cmd_cycle"] - START - 1 - cmd_pin_stages
        assert x >= 4, "first command too close to the stage start"
        rows.append((x, nwords[k], p["mode"], 0, k))
    last = prog[-1]
    last_slot = last["cmd_cycle"] + 1 + (GC if last["mode"] else 1) * (nwords[-1] - 1)
    xe = last_slot + 2 - START - 1
    rows.append((xe, 0, 0, 1, 0))
    assert len(rows) <= DEPTH
    for k, (x, w, m, e, tag) in enumerate(rows):
        pw.append((2 * k, (e << 49) | (m << 48) | (w << 32) | x))
        pw.append((2 * k + 1, tag))
    pw.append((2 * DEPTH, (0x434C << 48) | (len(rows) << 32) | xe))
    return pw


def build(out: Path, lu, ls, xu, xs, phi, define=None, qfd=False, parent=False, relays=(0,0,0,0), shared=False, six_five=False):
    obj = out / f"obj_u{lu}_s{ls}_xu{xu}_xs{xs}_phi{phi}{'_qfd' if qfd else ''}{('_' + define) if define else ''}"
    h = out / f"harness_phi{phi}.cpp"
    step = ("t->clk = 1; t->lck = 1; t->eval(); t->clk = 0; t->lck = 0; t->eval();" if phi == 0 else
            "t->clk = 1; t->eval(); t->lck = 1; t->eval(); t->clk = 0; t->eval(); t->lck = 0; t->eval();")
    if six_five:
        step="bool ce=(tick%5==0),fe=(tick%6==fphi),be=(tick%30==0);t->clk=ce;t->lck=ce;t->fdi_ck=fe;t->blk_ck=be;t->eval();t->clk=0;t->lck=0;t->fdi_ck=0;t->blk_ck=0;t->eval();tick++;"
    old_h = h.read_text() if h.exists() else None
    h.write_text('#include "Vtb_coll_tp8_static_links.h"\n#include "verilated.h"\n'
                 "#include <cstring>\n#include <cstdlib>\nint main(int argc, char** argv) { Verilated::commandArgs(argc, argv);\n"
                 "  unsigned tick=0;int fphi=0;for(int i=1;i<argc;i++)if(!strncmp(argv[i],\"+FDIPHI=\",8))fphi=atoi(argv[i]+8);\n"
                 "  auto* t = new Vtb_coll_tp8_static_links; t->clk = 0; t->lck = 0; t->fdi_ck=0; t->blk_ck=0; t->eval();\n"
                 f"  while (!Verilated::gotFinish()) {{ {step} }}\n"
                 "  t->final(); delete t; return 0; }\n")
    cmd = ["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "-Wno-UNOPTFLAT", "--top-module", "tb_coll_tp8_static_links",
           f"-GLATU={lu}", f"-GLATS={ls}", f"-GPU={PU}", f"-GPS={PS}", f"-GKC={KC}", f"-GKW={KW}", f"-GXU={xu}",
           f"-GXS={xs}", "-Mdir", str(obj)] + ([f"+define+{define}"] if define else []) + [str(s) for s in SRC] + \
          [str(h), "-CFLAGS", "-O1", "-j", "16"]
    if six_five:cmd += ["+define+OT_TP8S_PRODUCTION_WRAPPER"]
    if parent:
        cmd += [f"-GSHARED={int(shared)}",f"-GSIXFIVE={int(six_five)}", "+define+OT_TP8S_PARENT"] + [f"-G{p}={v}" for p,v in zip(("RU","RS0","RS1","RS2"),relays)]
    if qfd:
        cmd += ["+define+OT_TP8S_QFD", f"+define+OT_QFDS_LU={lu}", f"+define+OT_QFDS_LS={ls}"]
    # Reuse only the exact source/executable/driver/profile previously recorded
    # in this output directory. FDIphase is a runtime argument, not a build.
    receipt=out/"record.json"
    exe=obj/"Vtb_coll_tp8_static_links"
    if receipt.exists() and exe.exists() and old_h==h.read_text():
        prior=json.loads(receipt.read_text())
        exact_sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC}
        if (prior.get("source_sha256")==exact_sources and
            prior.get("executable_sha256")==hashlib.sha256(exe.read_bytes()).hexdigest() and
            all(prior.get(k)==v for k,v in dict(latu=lu,lats=ls,xu=xu,xs=xs,phi=phi,
              phy_ucie=PU,phy_serdes=PS,die_name_master=qfd,production_parent=parent,
              relays=list(relays),shared_ucie=shared,six_five=six_five,mutant=define).items())):
            return exe
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"build failed:\n{r.stdout[-4000:]}{r.stderr[-4000:]}")
    return obj / "Vtb_coll_tp8_static_links"


def main():
    global PU
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--latu", type=int, default=KC + KW + 17 + PU)
    ap.add_argument("--lats", type=int, default=KC + KW + 17 + PS)
    ap.add_argument("--xu", type=int, default=0)
    ap.add_argument("--xs", type=int, default=0)
    ap.add_argument("--phi", type=int, default=0, choices=(0, 1))
    ap.add_argument("--production", action="store_true")
    ap.add_argument("--expect-fail", action="store_true", help="negative control: some positive case must FAIL")
    ap.add_argument("--mutant-define", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--qfd", action="store_true")
    ap.add_argument("--relays",type=int,nargs=4,default=[0,0,0,0],metavar=("U","S0","S1","S2"))
    ap.add_argument("--parent",action="store_true",help="actualproduction collective+fiveface parent")
    ap.add_argument("--shared-ucie",action="store_true")
    ap.add_argument("--six-five",action="store_true")
    ap.add_argument("--fdi-phase",type=int,choices=range(6),default=0)
    ap.add_argument("--unsafe-shared-calendar",action="store_true")
    a = ap.parse_args()
    if a.six_five:
        a.parent=True;a.shared_ucie=True
        PU=20  # r10 200 MHz block-stage gearbox: 19 core edges + registered codec pin
    if a.parent:a.qfd=True
    a.out = a.out.resolve()
    a.out.mkdir(parents=True, exist_ok=True)
    cases = PRODUCTION if a.production else UNIT
    if a.only:
        cases = [c for c in cases if re.search(a.only, c[0])]
    if a.xu or a.xs:
        cases = [("phy_longer_than_compiled", 4, 8, "m", "link", {})]
    if a.expect_fail:
        cases = [c for c in cases if c[4] == "pos"]
    exe = build(a.out, a.latu, a.lats, a.xu, a.xs, a.phi, a.mutant_define, a.qfd, a.parent, a.relays, a.shared_ucie, a.six_five)
    bad, records = [], []
    for i, (name, nmsg, words, mk, kind, extra) in enumerate(cases):
        rng = np.random.default_rng(100 + i)
        if mk == "rrg1":
            modes, nw = [0, 0, 1], [words, words, 1]
        else:
            modes = {"r": [0] * nmsg, "g": [1] * nmsg, "m": [int(x) for x in rng.integers(0, 2, nmsg)]}[mk]
            nw = [words] * nmsg
        prog = schedule(modes, nw, a.latu, a.lats, start=START + 6, shared_ucie=a.shared_ucie and not a.unsafe_shared_calendar)
        vec = a.out / f"vec_{name}"
        vectors(vec, nw, prog, 1000 + i)
        pw = program_words(prog, nw, cmd_pin_stages=int(a.qfd))
        (vec / "pw.hex").write_text("".join(f"{ad:03x}{d:016x}\n" for ad, d in pw))
        args = [str(exe), f"+VEC={vec}", f"+NMSG={nmsg}", f"+NPW={len(pw)}", f"+START={START}", f"+FDIPHI={a.fdi_phase}"] + \
               [f"+{k}={v}" for k, v in extra.items()]
        run = subprocess.run(args, capture_output=True, text=True)
        txt = run.stdout
        (a.out / f"{name}.log").write_text(txt + run.stderr)
        m = RES.search(txt)
        passed = run.returncode == 0 and bool(m) and any(l.strip() == "PASS" for l in txt.splitlines())
        ok = (not passed) if a.expect_fail else passed
        g = m.groups() if m else None
        span = max(p["last_out"] for p in prog) - prog[0]["first_slot"] + 1
        print(f"case {name} kind={kind} latu={a.latu} lats={a.lats} phi={a.phi} xu={a.xu} xs={a.xs} "
              f"mutant={a.mutant_define or '-'} {'PASS' if passed else 'FAIL'}"
              f"{' (expected FAIL)' if a.expect_fail else ''} " +
              (f"mismatches={g[0]} extra={g[1]} out_err={g[2]} cmd_bad={g[3]} coll_fault={g[4]} issuer_fault={g[5]} "
               f"die_fault={g[6]} words_out={g[7]} meas_lu={g[8]} meas_ls={g[9]} pr_overlap={g[10]} "
               f"compiled_span={span}" if g else "no result: " + txt.strip()[-400:]), flush=True)
        records.append(dict(name=name, kind=kind, passed=passed, messages=nmsg, words_per_message=nw, modes=modes,
                            program=prog, program_words=[[ad, f"{d:016x}"] for ad, d in pw],
                            compiled_span_cycles=span, result=dict(zip(
                                ["mismatches", "extra", "out_err", "cmd_bad", "coll_fault", "issuer_fault",
                                 "die_fault", "words_out", "meas_lu", "meas_ls", "pr_overlap", "issuer_done"], g))
                            if g else None))
        if not ok:
            bad.append(name)
    (a.out / "record.json").write_text(json.dumps(dict(
        schema="opentallas.qwen.tp8.collective.static_links.v1", ranks=ND, latu=a.latu, lats=a.lats, kc=KC, kw=KW,
        phy_ucie=PU, phy_serdes=PS, xu=a.xu, xs=a.xs, phi=a.phi, die_name_master=a.qfd, production_parent=a.parent, relays=a.relays, shared_ucie=a.shared_ucie, six_five=a.six_five, FDI_phase_ticks=a.fdi_phase, unsafe_shared_calendar=a.unsafe_shared_calendar, mutant=a.mutant_define,
        expect_fail=a.expect_fail, production=a.production, issuer_depth=DEPTH, stage_start=START, cmd_pin_stages=int(a.qfd),
        modelled="PHY frame pipes only (fixed latency); all on-chip blocks are the real RTL masters",
        mechanism="compiler program -> fixed-issue core -> collective tokens -> IO calendar slots; no credits/ready/"
                  "backpressure; observed validity, CRC and publication are fault-only checks",
        cases=records, source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SRC},
        helper_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in
          ("tools/qwen_coll_tp8_static_links_bench.py","tools/qwen_coll_tp8_static_bench.py","tools/qwen_coll_tp8_bench.py","tools/hdc_golden.py")},
        executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), native_layer_qualified=False,
        physical_qualified=False), indent=2) + "\n")
    if bad:
        print(f"COLL_TP8SL FAIL failed={','.join(bad)}")
        sys.exit(1)
    print(f"COLL_TP8SL {'NEGATIVE-CONTROL ' if a.expect_fail else ''}PASS cases={len(cases)} latu={a.latu} lats={a.lats}")


if __name__ == "__main__":
    main()
