#!/usr/bin/env python3
"""Directed BOUNDARY-FAULT bench for the HHP c708 central OWN phase (TOK-ALL-14; COORD ruling: replaces Codex's random
81f3 bench as the acceptance proof).

DUT = the real rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge_b.sv (with its real embedding endpoint)
transformed by kvspc_phase_delivery.transform (c708; optional nface_ff).  For each transition (RISE = BOOT_END, FALL =
REOPEN) and each event class (writer word wes[0], slice word hes[0], controller er[0], completion_v) at every offset
T-3 .. T+4, one isolated directed case runs from reset; the bench records the sticky ownership fault (m_fault), the er
destination (endpoint er_e[0] / slice her[0]) and the completion destination (hcv).  Checks:
  1 exact price: every observation equals hhp_phase_guard.hw_predict(d = 1) (RTL mutant = c708 without the phase FF
    must FAIL this; the main d = 0 RTL is also run and must equal hw_predict(d = 0));
  2 guard soundness: every single-event schedule the typed guard admits is RTL-safe (no fault, correct destination);
  3 guard tightness on the three COORD constraints: the boundary case just below each bound is RTL-unsafe;
  4 guard mutants W/S/E (each bound weakened by one edge) each admit an RTL-unsafe case (CAUGHT).
    python3 tools/qwen_kv_die/hhp_phase_boundary_bench.py OUT [--nface-ff]
"""
import argparse, importlib.util, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "rtl/qwen_sys/static_embedding_20261014"
sys.path.insert(0, str(ROOT / "tools/qwen_kv_die"))
import hhp_phase_guard as G  # noqa: E402

spec = importlib.util.spec_from_file_location("kpd", ROOT / "physical/die_plan/qwen_kvsys/cores/harden/kvspc_phase_delivery.py")
KPD = importlib.util.module_from_spec(spec); spec.loader.exec_module(KPD)
CLS = ["writer", "slice", "er", "cv"]
OFFS = range(-3, 5)

TB = r"""`timescale 1ns/1ps
module tb;
  reg ck=0; always #5 ck=~ck;
  reg rst_n=0, ebr=0, emb_issue_v=0, cv=0, cw=0;
  reg [287:0] wes=0, hes=0; reg [260:0] er=0;
  wire [260:0] her; wire hcv, hcw; wire [287:0] es; wire fault;
  wire bv; wire [255:0] bd; wire [17:0] bt; wire [5:0] bw; wire bh, bs, cor, eo; wire [15:0] be;
  qkd_static_kv_pc_es_merge_b dut(.ck(ck),.rst_n(rst_n),.pc(5'd0),.cfg_stack(2'd0),.wes(wes),.emb_boot_ready(ebr),
    .emb_issue_v(1'b0),.emb_token(18'd0),.emb_word_index(6'd0),.emb_half(1'b0),.emb_scale(1'b0),.emb_epoch(16'd0),
    .emb_return_slot(1'b0),.hes(hes),.her(her),.completion_v(cv),.completion_we(cw),.hcv(hcv),.hcw(hcw),.es(es),.er(er),
    .beat_v(bv),.beat_data(bd),.beat_token(bt),.beat_word(bw),.beat_half(bh),.beat_scale(bs),.beat_epoch(be),
    .corrected(cor),.emb_outstanding(eo),.fault(fault));
  integer dir, c, off, t, mf, ep, sl, cs;
  initial begin
    for (dir=0; dir<2; dir=dir+1) for (c=0; c<4; c=c+1) for (off=-3; off<5; off=off+1) begin
      rst_n=0; ebr = dir ? 1 : 0; wes=0; hes=0; er=0; cv=0; cw=0;
      repeat(3) @(negedge ck); rst_n=1; repeat(6) @(negedge ck);
      ep=0; sl=0; cs=0;
      // edge index t = 0 is the first posedge that samples the new emb_boot_ready (= T)
      for (t=-4; t<8; t=t+1) begin
        if (t==0) ebr = dir ? 0 : 1;
        wes[0] = (c==0 && t==off); hes[0] = (c==1 && t==off); er[0] = (c==2 && t==off); cv = (c==3 && t==off);
        #1; if (c==2 && t==off) ep = dut.er_e[0];
        @(posedge ck); #1;
        if (her[0]) sl = sl + 1; if (hcv) cs = cs + 1;
        @(negedge ck);
      end
      wes=0; hes=0; er=0; cv=0; repeat(3) @(negedge ck);
      mf = dut.m_fault;
      $display("CASE %s %0d %0d fault=%0d ep=%0d slice=%0d cslice=%0d", dir ? "FALL" : "RISE", c, off, mf, ep, sl, cs);
    end
    $display("BENCH_DONE"); $finish;
  end
endmodule
"""


def run_rtl(out: Path, tag: str, d: int, mutant=False, nface_ff=False):
    w = out / tag; w.mkdir(parents=True, exist_ok=True)
    src = (RTL / "qkd_static_kv_pc_es_merge_b.sv").read_text()
    if d == 1:
        src = KPD.transform(src, mutant=mutant, nface_ff=nface_ff)
    (w / "qkd_static_kv_pc_es_merge_b.sv").write_text(src)
    (w / "tb.sv").write_text(TB)
    subprocess.run(["iverilog", "-g2012", "-o", str(w / "sim.vvp"), "-s", "tb", str(w / "tb.sv"), str(w / "qkd_static_kv_pc_es_merge_b.sv"),
                    str(RTL / "qkd_static_kv_pc_es_merge.sv"), str(RTL / "qkd_embedding_static_map.sv")], check=True)
    log = subprocess.run(["vvp", "-n", str(w / "sim.vvp")], capture_output=True, text=True, check=True).stdout
    (w / "sim.log").write_text(log)
    assert "BENCH_DONE" in log
    obs = {}
    for m in re.finditer(r"CASE (\w+) (\d) (-?\d+) fault=(\d) ep=(\d) slice=(\d+) cslice=(\d+)", log):
        dr, c, off = m.group(1), CLS[int(m.group(2))], int(m.group(3))
        f, ep, sl, cs = (int(m.group(i)) for i in range(4, 8))
        obs[(dr, c, off)] = (dict(fault=f) if c in ("writer", "slice") else dict(ep=ep, slice=min(sl, 1)) if c == "er" else dict(slice=min(cs, 1)))
    assert len(obs) == 2 * 4 * len(OFFS), len(obs)
    return obs


def price_mismatches(obs, d, nface_ff):
    return [(k, v, G.hw_predict(k[0], k[1], k[2], d, nface_ff)) for k, v in sorted(obs.items()) if v != G.hw_predict(k[0], k[1], k[2], d, nface_ff)]


def schedule(dr, cls, off, d, weaken=(), role=None):
    """Single-event schedule around one transition at T = 100 (RISE: BOOT_END = 100; FALL: window [20, 100])."""
    T = 100
    win = (G.PhaseWindow(boot_end=T),) if dr == "RISE" else (G.PhaseWindow(boot_end=20, reopen=T),)
    e = T + off
    if cls == "writer": ev = G.Event("writer", e)
    elif cls == "slice": ev = G.Event("slice", e)
    elif role == "emb": ev = G.Event("emb_return", e, issue=(T if dr == "RISE" else min(e, T) - 2 if dr == "FALL" else T))
    else: ev = G.Event("slice_return", e)
    return G.PhaseSchedule(windows=win, events=(ev,), phase_delay=d, weaken=tuple(weaken))


def rtl_safe(dr, cls, off, o, role=None):
    if cls in ("writer", "slice"):
        return o["fault"] == 0
    want_slice = 1 if role == "slice" else 0
    if cls == "er":
        return o["slice"] == want_slice and o["ep"] == 1 - want_slice
    return o["slice"] == want_slice


def cases():
    for dr in ("RISE", "FALL"):
        for cls in CLS:
            for off in OFFS:
                for role in ((None,) if cls in ("writer", "slice") else ("emb", "slice")):
                    yield dr, cls, off, role


def soundness(obs, d, weaken=()):
    bad = []
    for dr, cls, off, role in cases():
        if dr == "RISE" and cls in ("er", "cv") and role == "emb" and off < 0:
            continue  # an embedding issue cannot precede BOOT_END (issue edge would be outside the run window)
        s = schedule(dr, cls, off, d, weaken, role)
        if not G.check(s) and not rtl_safe(dr, cls, off, obs[(dr, cls, off)], role):
            bad.append(dict(dir=dr, cls=cls, off=off, role=role, rtl=obs[(dr, cls, off)]))
    return bad


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("out", type=Path); ap.add_argument("--nface-ff", action="store_true"); a = ap.parse_args()
    out = a.out; out.mkdir(parents=True, exist_ok=True); nf = a.nface_ff
    main_obs = run_rtl(out, "main_d0", 0)
    c708 = run_rtl(out, "c708_d1" + ("_nff" if nf else ""), 1, nface_ff=nf)
    mut = run_rtl(out, "mut_nophase", 1, mutant=True, nface_ff=nf)
    res = dict(schema="opentallas.token_pass.hhp_phase_boundary.v1", nface_ff=nf, cases_per_rtl=len(c708))
    res["price_main_d0_mismatch"] = len(price_mismatches(main_obs, 0, False))
    res["price_c708_mismatch"] = len(price_mismatches(c708, 1, nf))
    res["rtl_mutant_nophase_mismatch"] = len(price_mismatches(mut, 1, nf))
    res["guard_unsound_cases"] = soundness(c708, 1)
    # tightness: just below each of the three COORD bounds the RTL is unsafe
    tight = dict(
        W_writer_BOOT_END_plus1=not rtl_safe("RISE", "writer", 1, c708[("RISE", "writer", 1)]) and bool(G.check(schedule("RISE", "writer", 1, 1))),
        S_slice_REOPEN_plus0=not rtl_safe("FALL", "slice", 0, c708[("FALL", "slice", 0)]) and bool(G.check(schedule("FALL", "slice", 0, 1))),
        E_emb_return_BOOT_END_plus1=not rtl_safe("RISE", "er", 1, c708[("RISE", "er", 1)], "emb") and bool(G.check(schedule("RISE", "er", 1, 1, role="emb"))))
    res["tight"] = tight
    res["guard_mutants_caught"] = {m: len(soundness(c708, 1, (m,))) > 0 for m in ("W", "S", "E")}
    res["guard_mutant_witness"] = {m: (soundness(c708, 1, (m,)) or [None])[0] for m in ("W", "S", "E")}
    res["main_guard_d0_unsound"] = soundness(main_obs, 0)
    res["writer_REOPEN_plus1_flagged"] = c708[("FALL", "writer", 1)]["fault"] == 1
    ok = (res["price_main_d0_mismatch"] == 0 and res["price_c708_mismatch"] == 0 and res["rtl_mutant_nophase_mismatch"] > 0
          and not res["guard_unsound_cases"] and all(tight.values()) and all(res["guard_mutants_caught"].values())
          and not res["main_guard_d0_unsound"])
    res["verdict"] = "PASS" if ok else "FAIL"
    (out / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "guard_mutant_witness"}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
