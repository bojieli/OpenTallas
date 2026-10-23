#!/usr/bin/env python3
"""STEWARD-HBMd/PINREG q9: write physical/ref_tile/hbm_wbk_q9{a,b}_1023/spec.json from the nd spec (1d2171e2e)."""
import json, sys, copy
from pathlib import Path
WT = Path(sys.argv[1]); BASE = WT / "physical/ref_tile/hbm_wbk_rv_fanout_nd/spec.json"
nd = json.loads(BASE.read_text())
MH, MW = 41.088, 94.824                      # abutted SRAM pitch (array height + 0.024) / width
LANES = lambda k: [2*k, 2*k+1, 2*k+8, 2*k+9, 2*k+16, 2*k+17, 2*k+24, 2*k+25]   # SRAM column k = lanes l[2:1] == k
KPORTS = {"w_k_addr": 30, "w_k_rdy": 1, "w_k_v": 1, "w_k_wdata": 256, "w_k_wr_done": 1}

def r2(x): return round(x, 4)

def macros(xs, y0s, orient):
    out = []
    for k, x in enumerate(xs):
        ls = LANES(k)
        for j, l in enumerate(ls):
            y = y0s[j // 4] + (j % 4) * MH
            out.append({"view": "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2", "count": 1,
                        "inst": f"*u_wb.g_lane?{l}?.u_payload", "at": [r2(x), r2(y)], "orient": orient, "at_exact": True})
    return out

def groups(W, H, gap_um):
    """PCs 0-7 on N (left -> right, a gap at the centre for hbm_clk / hbm_rst_n), PCs 8-15 on E (top -> bottom)"""
    g = []
    lo, hi = 2.16, W - 2.16
    seg = (hi - lo - gap_um) / 8
    for p in range(8):
        a = lo + p * seg + (gap_um if p >= 4 else 0)
        g.append({"face": "N", "range": [r2(a), r2(a + seg)],
                  "bits": {n: [p * w, p * w + w - 1] for n, w in KPORTS.items()}})
    clk = [r2(lo + 4 * seg), r2(lo + 4 * seg + gap_um)]
    lo, hi = 2.16, H - 2.16
    seg = (hi - lo) / 8
    for p in range(8, 16):
        i = 15 - p                                  # PC 8 at the top (next to the NE corner) ... PC 15 at the bottom
        a = lo + i * seg
        g.append({"face": "E", "range": [r2(a), r2(a + seg)],
                  "bits": {n: [p * w, p * w + w - 1] for n, w in KPORTS.items()}})
    return g, clk

def make(name, W, H, xs, y0s, orient, tag, role, other):
    s = copy.deepcopy(nd)
    s["name"] = name
    s["params"] = {**nd["params"], "KPREG": 1}
    s["outline"] = {"w": W, "h": H, "exact": True}
    s["pins"] = {"N": ["hbm_clk", "hbm_rst_n"], "S": nd["pins"]["S"]}
    g, clk = groups(W, H, 10.8)
    s["pin_bit_groups"] = g
    s["pin_ranges"] = {"hbm_clk": [clk[0], r2(clk[0] + 4.32)], "hbm_rst_n": [r2(clk[1] - 4.32), clk[1]]}
    s["macros"] = macros(xs, y0s, orient)
    xr = xs[-1] + MW + 10.8
    ytop = y0s[1] + 4 * MH + 5.4
    nk = sum(len(x["bits"]) and sum(b[1]-b[0]+1 for b in x["bits"].values()) for x in g[:8])
    s["reviewed_gray_fifo_extensions"]["why"] = ("quad is the quadrant identity strap (die constant); it is registered on both "
        "families (q_s stream, q_h hbm) and, with KPREG=1, is q_h's D (q_h_n) feeding the 16 per-PC folded-address flops a6 "
        "(XOR with the two ordinal ring heads' next values) so w_k_addr leaves a flop cycle-identically")
    s["pin_regs"] = {"enable": False, "clock": "stream_clk", "reason": (
        "RTL registers every pin (KPREG=1, q9): stream inputs land in the wbk_q pin flops (rb_q/fb_q/re_q/fe_q/rt_q/rbase_q/"
        "wd_q/stk_c/q_s), stream outputs are flops (wb_ready/wa/wbw_*/fault); K outputs leave flops: w_k_v = vq_pin, "
        "w_k_wdata / w_k_addr = the registered ring heads hd (+ per-PC folded-address flop a6), cycle-identical to the KPREG=0 "
        "one-hot ring mux (lockstep bench, 0 added edges); w_k_wr_done lands in done_q (plain flop, all 16 bits); named "
        "exception: w_k_rdy (16 inputs) stays the ring's direct fire AND (registering it changes the K valid/ready protocol); "
        "a kit flop stage would add an unpriced edge and put a raw flop in front of the CDC FIFOs")}
    s["structural_change"] = (f"STEWARD-HBMd/PINREG q9 {role} (10-23 coordinator tile review: 82% fill, 47% buf/inv, 4,593 pins w/o "
        "register on the 777.6 x 518.4 nd slot): KPREG=1 registered K ring heads (w_k_addr / w_k_wdata from flops, 0 added "
        "edges, lockstep-proven); outline sized from content at ~60-65% std fill and NOT squeezed; K ports split by bit range "
        "(pin_bit_groups): PCs 0-7 on N, PCs 8-15 on E, one pin segment per PC (its ring heads FIRM there by io_flop_at_pins); "
        f"32 SRAMs as 4 columns x 8 (one per stream_fifo_clk root, two abutted 4-stacks) at the W/centre, orient {orient}; "
        f"std-cell bands N {r2(H - ytop)} um, E {r2(W - xr)} um, S {r2(y0s[0] - 5.4)} um. RTL kq8 core otherwise = 1d2171e2e "
        "(source630 fanout repair + keep-without-dont_touch AND).")
    s["slot_change_request"] = (f"d4g wbk_<q> x4: slot 777.6 x 518.4 -> {W} x {H} ({role}; {other}); K ports of PCs 8-15 "
        "move from the N face to the E face (toward vmks_<q>2/3, right of / below wbk_<q>), PCs 0-7 stay on N (one segment "
        "per PC, PC 0 at the W end; E: PC 8 at the top); S face unchanged (DMA wd 2,312 + stream control toward hb_dbk_<q>); "
        "hbm_clk / hbm_rst_n at the N centre. Die notice: lanes/STEWARD-HBM.md NOTICE HBMd/CHAIN 10-23.")
    s["safe_design_checklist"] = {
        "1_pins": "Every output leaves a flop (K heads hd/a6 + vq_pin, stream outputs); every data input lands in a pin flop "
                  "(stream wd_q etc., K w_k_wr_done in done_q); resets land in 2 plain stages per own clock. Named exception: "
                  "w_k_rdy x16 (direct ready of the K valid/ready handshake). Pins <= 3.9/um on every face.",
        "2_reach": "K ring heads FIRM at their PC segment (io_flop_at_pins); SRAM column -> crossbar -> PC crossing FIFO -> ring "
                   "-> head stays inside the NE L-band, <= ~500 um at 833/1024 ps with the existing registered stages. RISK: "
                   "the gate's 3_4 long-wire (wire*) buffer count is the evidence; > 15% of cells -> structural q10.",
        "3_fanout": "kq8 census-safe slicing unchanged (native max 32); KPREG adds per-slice kept rpob (ring+1 select: rpo alone "
                    "would drive 33 loads), head D-mux selects <= 18 loads, w_k_rdy only selects the last head mux (fire).",
        "4_depth": "Head D = 3:1 AND-OR of ring entries (old output mux) + same-edge bypass mux + fire mux: the old pin-side "
                   "mux moved before the flop, one 2:1 mux deeper on an hbm (1024 ps) flop->flop path.",
        "5_storage": "32 x 128x256 SRAM payload macros (4 columns x 8 aligned to the 4 stream_fifo_clk roots), reviewed "
                     "<= 5-b ping-pong crossing FIFOs, 3-entry K rings + registered heads; no shift pipeline.",
        "6_floorplan": f"{W} x {H} sized from content (placed std 229.5k um2 of nd incl. long-wire buffers at ~60-65%), "
                       "enlarged, never squeezed; SRAM block at the W/centre, logic bands N/E (K) and S (wd landing).",
        "7_clock": "Six clock ports as before (stream, four stream FIFO roots, hbm); hbm_clk at the N centre feeding the N/E "
                   "K band; ~800-900 um span keeps the clock_span WARN -> measured pin-flop spread decides.",
        "8_schedule": "0 added edges on every path (KPREG lockstep: all outputs identical every stream and hbm edge); static "
                      "schedule, K valid/ready at the HBM controller boundary unchanged; reset landing unchanged."}
    j = s["job"]
    j.update(owner="STEWARD-HBMd/PINREG", branch="claude/hbmd-pinreg-wbk-q9-1023", tag=tag,
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
             purpose=("HBM die d4g wbk_<q> x4 = ot_hbm_svc_wb_kport_q (per-quadrant DMA write-back -> 16 HBM K ports, quad "
                      f"strap); q9 {role}: KPREG=1 registered K ring heads (every K data pin from a flop), outline from "
                      f"content {W} x {H} (~60-65% std fill), K PCs 0-7 N / 8-15 E, SRAM 4x8 columns W/centre"))
    R = "results/rtl/hbmd_pinreg_wbk_q9_1023"
    sh = "bash rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh {RUN}/bench/%s %s"
    def wb(n, exp, note, kind="wbq"):
        b = {"name": n, "cmd": sh % (n, n), "expect": exp, "threads": 8, "peak_ram_gb": 10 if kind == "kpl" else 8,
             "needs": ["verilator"], "note": note}
        if kind == "kpl":
            b["pass_regex"] = f"STK_KPL PASS {n}" if exp == "pass" else "^PASS tb_hbm_svc_wb_kq8_kpreg_lockstep"
            if exp == "pass":
                b["min_count_regex"] = r"^PASS tb_hbm_svc_wb_kq8_kpreg_lockstep .*sectors=(\d+)"
            else:
                b["fail_regex"] = "FAIL tb_hbm_svc_wb_kq8_kpreg_lockstep"
        else:
            b["pass_regex"] = f"STK_WBQ PASS {n}" if exp == "pass" else "^PASS tb_hbm_svc_wb_kshare_qh"
            if exp == "pass":
                b["min_count_regex"] = r"^PASS tb_hbm_svc_wb_kshare_qh .*sectors=(\d+)"
            else:
                b["fail_regex"] = "WB_INTEGRITY|FAIL tb_hbm_svc_wb_kshare_qh"
        b["pass_witness" if exp == "pass" else "fail_witness"] = f"{R}/{n}.log"
        return b
    j["benches"] = [wb("kpl_e", "pass", "KPREG 0 vs 1 lockstep, every output every edge (E quadrant)", "kpl"),
                    wb("kpl_w", "pass", "KPREG lockstep W quadrant", "kpl"),
                    wb("kpl_mut_stale", "fail", "KPREG mutant: head loads the stale slot on a fire", "kpl"),
                    wb("wbq_e_kp", "pass", "E quadrant lockstep vs GEN0 wb_kport, KPREG=1"),
                    wb("wbq_w_kp", "pass", "W quadrant, KPREG=1"),
                    wb("wbq_e_wopen_kp", "pass", "E quadrant WOPEN=1, KPREG=1"),
                    wb("wbq_mut_quad_kp", "fail", "fold ignores the quad strap"),
                    wb("wbq_mut_span_kp", "fail", "window total = ordinal total"),
                    wb("wbq_mut_premature_kp", "fail", "premature wa"),
                    wb("wbq_mut_ksaddr_kp", "fail", "kshare address mutant"),
                    wb("wbq_mut_slice_kp", "fail", "data slice 3 selects lane l^1"),
                    wb("wbq_mut_commit_kp", "fail", "watermark race"),
                    wb("wbq_mut_credit_kp", "fail", "arbiter ignores crossing credit"),
                    wb("wbq_mut_pp_kp", "fail", "ping-pong toggle stuck"),
                    wb("wbq_mut_lock_kp", "fail", "pop ignores K ring room"),
                    wb("wbq_mut_stale_kp", "fail", "KPREG head stale slot (end-to-end data check)")]
    j["extra_paths"] = ["rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh",
        "rtl/hbm_accel/loader/service_native/tb_hbm_svc_wb_kshare_qh.sv",
        "rtl/hbm_accel/loader/service_native/tb_hbm_svc_wb_kq8_kpreg_lockstep.sv",
        "rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_kport.sv",
        "rtl/hbm_accel/loader/service_native/ot_hbm_svc_vm_kshare.sv",
        "rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv",
        "rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_pipeline_leaves.sv",
        "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg.sv",
        "rtl/hbm_accel/loader/service_native/tb_hbm_svc_command_dram_pipeline_fixture.sv",
        "rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv", "rtl/lib/ot_rst_relay.sv",
        "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
        "rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_cutthrough_cdc.sv",
        "rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv",
        "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv", R + "/"]
    out = WT / f"physical/ref_tile/{name}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(name, W, H, "N band", r2(H - ytop), "E band", r2(W - xr), "S band", r2(y0s[0] - 5.4))

# MAIN q9a 799.2 x 691.2: columns pitch 151.2 from x 43.2, stacks y 64.8 / 280.8
make("hbm_wbk_q9a_1023", 799.2, 691.2, [43.2, 194.4, 345.6, 496.8], [64.8, 280.8], "MY", "q9a", "MAIN",
     "FB q9b 907.2 x 604.8")
# FB q9b 907.2 x 604.8: nd column pitch 172.8 from x 43.2, stacks y 64.8 / 280.8
make("hbm_wbk_q9b_1023", 907.2, 604.8, [43.2, 216.0, 388.8, 561.6], [64.8, 280.8], "MY", "q9b", "FALLBACK",
     "MAIN q9a 799.2 x 691.2")
