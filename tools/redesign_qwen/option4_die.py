#!/usr/bin/env python3
"""qwen-1010/a 2026-10-10: the option-4 control plane composed from the ACTUAL die masters on the Qwen3-8B L0-L2
token-exact chain (tools/exactness/qwen_rom_fulltoken.py vehicle; fixtures on ot-epyc1tb).

split_ctrl.py measured option 4 with the two controllers emitted INSIDE the vehicle's core (stations as delay
lines).  This tool replaces them with the committed masters, unmodified except where noted:

  u_seq_su  rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_boundary.sv, byte-for-byte (die master qfd_seq_su_boundary:
            TP sequencer + SU-side controller + program / descriptor stores + SU issue shell, IS / OS pin stations).
            It REPLACES the die's ot_qwen_tp_seq_w12 and the core's SU-side controller.
  u_ctlm    ot_qfd_tt_ctlm (rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm.sv) with ONE mechanical cut: its ot_qfd_tt_ctl
            instance (the tree-top control element: band selects / scale requests / argmax top) is removed and the
            nets that instance drove / read (the in-tile ME issue / status after the DCU_M / DUC_M stations) become
            ports xme_*, because the vehicle's matrix engine (ot_qwen_me_spine_w12) contains that control element.
            Everything else -- pin stations, program-store copy, ME-side controller (FQ_HEAD 1, XREG 1), issue
            shell, in-tile stations, the engine-side accepted counter and the snapshot OS -- is the master's text.
            (sb_tts_* proved ot_qfd_tt_ctl + 4 x band_upper == the tree top; the token chain proves the controller.)
  SU        the vehicle's stream unit (ot_hdc_vstream_rt + ot_qfd_su_embed) wrapped with the SU master's pin stations
            (IS 1 / OS 1 of ot_qfd_sp_su64_sfu_bv_acc) and its ENDPOINT accepted counter (counted at the unit's go,
            leaving with idle / progress through the same OS: tools/redesign_qwen/endpoint_accept_gate.py proves the
            master's counter); the constant ROM answers at ML 7 (the SU-local constant buffer).
  die wires the SU <-> TT snapshots (both ways), the per-layer ME start (seq_su me_*_o -> ctlm h_start / token /
            pos / prog_base) and the seq_su <-> SU issue / status as die relay chains of R stations (registered,
            between the masters' own pin flops: a crossing costs OS + R + IS).

The program store copies (seq_su and ctlm) are preloaded with the die's program image by the host (the die writes them
through pw_* in operation; the preload is the same contents before the token starts).  XMUT 1 (mutant: the ctlm's
ME-side controller ignores SU dependencies) must FAIL.

usage: option4_die.py build --build DIR [--jobs 16] [--x-s2m R] [--x-m2s R] [--dst R] [--dcu-s R] [--duc-s R]
                            [--su-ml 7] [--xmut 0|1]
       option4_die.py run --build DIR --work DIR --stages L3
       option4_die.py emit --out DIR       (generated sources only, for lint)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "redesign_qwen"))
import split_ctrl as S  # noqa: E402

F, P = S.F, S.P
S4 = F.S4
RQ = ROOT / "rtl/qwen_sys/redesign_qwen"
# master variants: (file, module, emitter)
CTLMS = {"ctlm": (RQ / "ot_qfd_tt_ctlm.sv", "ot_qfd_tt_ctlm", S.emit_tt_ctlm),
         "i": (RQ / "ot_qfd_tt_ctlm_i.sv", "ot_qfd_tt_ctlm_i", S.emit_tt_ctlm_i)}
SEQS = {"boundary": (RQ / "ot_qfd_seq_su_boundary.sv", "ot_qfd_seq_su_boundary", lambda: S.emit_seq_su(boundary=True)),
        "bi": (RQ / "ot_qfd_seq_su_bi.sv", "ot_qfd_seq_su_bi", S.emit_seq_su_bi)}
VAR = dict(ctlm="ctlm", seq="boundary")
SPM = ROOT / "rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv"
# die relay stations between the masters' pin flops (r22ko4 counts replace these defaults)
CFG = dict(x_s2m=15, x_m2s=15, dst=15, dcu_s=0, duc_s=0, su_ml=7, xmut=0)
LIT = {"NW": "18", "AW": "24", "(G >> SMIN)": "48"}


def one(t, old, new):
    if t.count(old) != 1:
        raise SystemExit(f"anchor x{t.count(old)}: {old[:80]!r}")
    return t.replace(old, new)


def cut_between(t, start, end):
    i = t.index(start)
    j = t.index(end, i) + len(end)
    return t[:i] + t[j:], t[i:j]


def ctlm_xme(xmut: int = 0) -> str:
    """the committed ctlm master (VAR ctlm) with its tt_ctl instance cut out (its nets as ports xme_*)"""
    path, mod, emitter = CTLMS[VAR["ctlm"]]
    text = path.read_text()
    if text != emitter():
        raise SystemExit(f"committed {path.name} is stale against its emitter")
    k = text.index(f"module {mod} #(")
    ctrl, m = text[:k], text[k:]
    m = one(m, f"module {mod} #(", "module ot_qfd_tt_ctlm_xme #(")
    ports = []
    for p, ex, kind, w in P.ME:
        if p == "clk":
            continue
        ww = LIT.get(w, w)
        if kind == "out":
            ports.append(f"    output wire [{ww}-1:0] xme_{p},")
        elif kind == "in" and p not in P.ME_LOCAL:
            ports.append(f"    input  wire [{ww}-1:0] xme_{p},")
    m, old_ports = cut_between(m, "    // ot_qfd_tt_ctl's non-issue ports\n", "    output wire [16*32-1:0] mx_data\n")
    m = one(m, "    output wire [18-1:0] kvd_pos, output wire me_clk_en, output wire c_fault,\n",
            "    output wire [18-1:0] kvd_pos, output wire me_clk_en, output wire c_fault,\n"
            "    // qwen-1010/a: the cut tt_ctl instance's nets (the engine side of the in-tile ME stations)\n"
            "    output wire xme_clk,\n" + "\n".join(ports).rstrip(",") + "\n")
    m, tt = cut_between(m, "    ot_qfd_tt_ctl #(", ".progress(u_me_progress), .fault(u_me_fault));\n")
    m = one(m, "    assign u_me_mx_we = 1'b0; assign u_me_o_we = '0;\n", "")
    glue = ["    assign xme_clk = c_me_clk;"]
    for p, ex, kind, w in P.ME:
        if p == "clk":
            continue
        if kind == "out":
            glue.append(f"    assign xme_{p} = u_me_{p};")
        elif kind == "in" and p not in P.ME_LOCAL:
            glue.append(f"    assign u_me_{p} = xme_{p};")
    m = m.replace("\nendmodule", "\n" + "\n".join(glue) + "\nendmodule", 1)
    # every cut tt_ctl connection is one of: an issue / status net (now xme_*) or a non-issue port (cut with the ports)
    for conn in re.findall(r"\.(\w+)\(([^()]*)\)", tt[tt.index(") u_tt ("):]):
        net = conn[1].strip()
        if net.startswith("u_me_") or net in ("c_me_clk", "rs"):
            continue
        if not re.search(r"\b%s\b" % re.escape(net), old_ports):
            raise SystemExit(f"cut tt_ctl connection {conn} is neither an issue net nor a cut port")
    m = one(m, ".OWN(1), .XW(XW), .XMUT(0),", f".OWN(1), .XW(XW), .XMUT({xmut}),")
    return ctrl + m


def rst_stn() -> str:
    t = SPM.read_text()
    a = t.index("module ot_qfd_rst_stn")
    return t[a:t.index("endmodule", a) + len("endmodule")] + "\n"


SEQ_CONN_IN = {"start", "token", "pos", "vm_rq", "c_ready", "r_valid", "r_data", "r_last", "r_rank", "r_err"}
SEQ_CONN_OUT = {"done", "next_token", "next_val", "fault", "coll_busy", "core_start", "core_token", "core_pos",
                "prog_base", "vm_re", "vm_raddr", "vm_we", "vm_waddr", "vm_wdata", "c_valid", "c_data", "c_last",
                "c_mode", "c_tag"}
SEQ_DROP = {"clk", "rst_n", "core_done", "core_next_token", "core_next_val", "core_fault", "desc_re", "desc_addr",
            "desc_q"}
SEQ_W = dict(start="1", token="NW", pos="NW", done="1", next_token="NW", next_val="32", fault="1", coll_busy="1",
             core_start="1", core_token="NW", core_pos="NW", prog_base="12", vm_re="1", vm_raddr="8", vm_rq="512",
             vm_we="1", vm_waddr="8", vm_wdata="512", c_valid="1", c_ready="1", c_data="512", c_last="1", c_mode="1",
             c_tag="32", r_valid="1", r_data="512", r_last="1", r_rank="2", r_err="1")
CTRL_NETS = S.CTRL_NETS


def compose(core: str, c: dict) -> str:
    """ot_qfd_o4_core: the core's ports + the sequencer's (sq_*), built from the masters"""
    params, port_text = P.header(core)
    ports = P.ports_of(port_text)
    pnames = re.findall(r"parameter\s+integer\s+(\w+)", params)
    L = ["// GENERATED by tools/redesign_qwen/option4_die.py: the option-4 control plane from the actual die masters",
         "// (u_seq_su = qfd_seq_su_boundary, u_ctlm = qfd_tt_ctlm minus its tt_ctl instance) + the vehicle's engine /",
         "// stream unit, die relay chains between the masters' pin flops.",
         params.replace("module ot_qwen_rom_core #(", "module ot_qfd_o4_core #(", 1)
         + "".join(f",\n    parameter integer {k.upper()} = {v}" for k, v in c.items()), ") ("]
    for d, w, n in ports:
        L.append(f"    {d} wire {w} {n},")
    for n, w in SEQ_W.items():
        d = "input " if n in SEQ_CONN_IN else "output"
        L.append(f"    {d} wire [{w}-1:0] sq_{n},")
    L[-1] = L[-1].rstrip(",")
    L += [");", "    localparam integer DSU = DCU_S + 1;        // seq_su OS (inside) + die relays + the SU master's IS",
          "    localparam integer USU = 1 + DUC_S;        // the SU master's OS + die relays (+ seq_su IS inside)"]
    for unit, table in (("me", P.ME), ("su", P.SU)):
        for p, ex, k, w in table:
            if k in ("out", "in"):
                L.append(f"    wire [{w}-1:0] c_{unit}_{p}, u_{unit}_{p};")
    L += ["    wire [SW-1:0] su_kv_we;", "    wire c_su_asrc_raw, u_su_asrc_raw;",
          "    wire [NW-1:0] c_tok, u_tok; wire [15:0] c_escale, u_escale;", "    wire u_su_efault;",
          "    wire c_me_clk_w; wire m_fault;"]
    # ---- the SU-side master ----
    sq = [".clk(clk)", ".rst_n(rst_n)", ".h_start(sq_start)", ".tp_token(sq_token)", ".tp_pos(sq_pos)",
          ".kv_write_drained(kv_write_drained)", ".vm_rq(sq_vm_rq)", ".c_ready(sq_c_ready)", ".r_valid(sq_r_valid)",
          ".r_data(sq_r_data)", ".r_last(sq_r_last)", ".r_rank(sq_r_rank)", ".r_err(sq_r_err)",
          ".pw_v(1'b0)", ".pw_addr(10'd0)", ".pw_data(64'd0)", ".dw_v(1'b0)", ".dw_addr(3'd0)", ".dw_data(64'd0)"]
    for p, ex, k, w in P.SU:
        if k in ("in", "dir_ok") and not P._local("su", p):
            sq.append(f".pi_su_{p}(d_su_{p})")
    sq += [".x_oacc(xm_acc)", ".x_oidle(xm_idle)", ".x_oprog(xm_prog)", ".x_ofin(xm_fin)", ".x_fidx(xm_fidx)",
           ".x_fval(xm_fval)", ".pi_su_acc(d_su_acc)",
           ".s_done(sq_done)", ".seq_ntok(sq_next_token)", ".seq_nval(sq_next_val)", ".s_fault(sq_fault)",
           ".core_fault(sq_core_fault)", ".coll_busy(sq_coll_busy)", ".kv_write_flush(kv_write_flush)",
           ".vm_re(sq_vm_re)", ".vm_raddr(sq_vm_raddr)", ".vm_we(sq_vm_we)", ".vm_waddr(sq_vm_waddr)",
           ".vm_wdata(sq_vm_wdata)", ".c_valid(sq_c_valid)", ".c_data(sq_c_data)", ".c_last(sq_c_last)",
           ".c_mode(sq_c_mode)", ".c_tag(sq_c_tag)", ".rom_fault(sq_rom_fault)", ".su_asrc(c_su_asrc_raw)",
           ".su_tok(c_tok)"]
    for p, ex, k, w in P.SU:
        if k == "out" and p != "va_q":
            sq.append(f".po_su_{p}(c_su_{p})")
    sq += [".me_start_o(s_me_start)", ".me_token_o(s_me_token)", ".me_pos_o(s_me_pos)",
           ".me_prog_base_o(s_me_prog_base)", ".su_acc_o(s_su_acc)", ".su_idle_o(s_su_idle)", ".su_prog_o(s_su_prog)",
           ".su_rows_o(s_su_rows)"]
    L += ["    wire sq_core_fault, sq_rom_fault; wire s_me_start; wire [NW-1:0] s_me_token, s_me_pos; wire [11:0] s_me_prog_base;",
          "    wire [23:0] s_su_acc; wire s_su_idle; wire [15:0] s_su_prog, s_su_rows;",
          "    wire [23:0] xm_acc; wire xm_idle, xm_fin; wire [15:0] xm_prog; wire [NW-1:0] xm_fidx; wire [31:0] xm_fval;",
          "    wire [23:0] xs_acc; wire xs_idle; wire [15:0] xs_prog, xs_rows;",
          "    wire m_start; wire [NW-1:0] m_token, m_pos; wire [11:0] m_prog_base;",
          "    wire [23:0] me_acc_o, d_su_acc; wire me_idle_o, m_fin_o; wire [15:0] me_prog_o; wire [NW-1:0] m_fidx_o; wire [31:0] m_fval_o;"]
    for p, ex, k, w in P.SU:
        if k in ("in", "dir_ok") and not P._local("su", p):
            L.append(f"    wire [{w}-1:0] d_su_{p};")
    L.append(f"    {SEQS[VAR['seq']][1]} #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SW(SW), .LV(LV), .D(4), .SMIN(SMIN),"
             " .SMAX(SMAX), .TCUT(TCUT), .IS(1), .OS(1), .RT(4 + DCU_S + DUC_S)) u_seq_su (\n        "
             + ",\n        ".join(sq) + ");")
    # taps for the vehicle die (KV-service layer start, cycles, program base): the sequencer's own nets
    L += ["    assign sq_core_start = u_seq_su.core_start;", "    assign sq_core_token = u_seq_su.core_tokw;",
          "    assign sq_core_pos = u_seq_su.core_pos;", "    assign sq_prog_base = u_seq_su.prog_base;",
          "    assign done = u_seq_su.core_done; assign next_token = u_seq_su.core_ntok; assign next_val = u_seq_su.core_nval;",
          "    assign cycles = u_seq_su.u_ctrl.cycles;", "    assign fault = sq_core_fault | m_fault;",
          "    assign prog_re = 1'b0; assign prog_addr = '0; assign wrom_re = sq_rom_fault; assign wrom_addr = '0;",
          "    assign int8_wrom_re = 1'b0; assign int8_wrom_addr = '0;",
          "    assign wrom_su = 1'b0; assign wd_v = 1'b0; assign wd_wbase = '0; assign wd_sbase = '0; assign wd_tiles = '0;",
          "    assign wd_k = '0; assign wd_nout = '0;",
          "    // embedding scale: the SU master fetches it itself (ea_kind); the vehicle reads the die's embedding ROM on",
          "    // the sequencer's own token-start strobe and delivers it through the SU path (OS + relays + IS)",
          "    assign embed_scale_re = u_seq_su.es_re_w; assign embed_scale_addr = u_seq_su.core_tokw;",
          "    reg es_pend; reg [15:0] es_hold;",
          "    always @(posedge clk or negedge rst_n) if (!rst_n) es_pend <= 1'b0; else es_pend <= embed_scale_re;",
          "    always @(posedge clk) if (es_pend) es_hold <= embed_scale_q;",
          "    assign c_escale = es_hold;"]

    def stn(name, w, d, clk, src, dst, rst=""):
        L.append(f"    ot_hdc_delay #(.W({w}), .D({d}){rst}) u_{name} (.clk({clk}), .rst_n(rst_n), .d({src}), .q({dst}));")
    # ---- seq_su <-> SU: die relays + the SU master's pin stations ----
    for p, ex, k, w in P.SU:
        if k == "out" and p != "va_q":
            stn(f"sd_su_{p}", w, "DSU", "clk", f"c_su_{p}", f"u_su_{p}", ", .RESET(1)" if p == "go" else "")
        elif k == "in" and p not in P.SU_LOCAL:
            src = "u_su_fault | u_su_efault" if p == "fault" else f"u_su_{p}"
            stn(f"su_su_{p}", w, "USU", "clk", src, f"d_su_{p}", P._rst(w))
    stn("sd_asrc", "1", "DSU", "clk", "c_su_asrc_raw", "u_su_asrc_raw")
    stn("sd_tok", "NW", "DSU", "clk", "c_tok", "u_tok")
    stn("sd_escale", "16", "1 + DSU", "clk", "c_escale", "u_escale")
    stn("su_kvwe", "SW", "USU", "clk", "su_kv_we", "d_su_kv_we", ", .RESET(1)")
    # the SU master's endpoint accepted counter (go accepted at the unit), leaving with idle / progress
    L += ["    reg [23:0] su_acc;",
          "    always @(posedge clk or negedge rst_n) if (!rst_n) su_acc <= 24'd0; else if (u_su_go) su_acc <= su_acc + 1'b1;"]
    stn("su_acc", "24", "USU", "clk", "su_acc", "d_su_acc", ", .RESET(1)")
    # ---- the snapshots and the ME start across the die (between the masters' pin flops) ----
    stn("xs", "24 + 1 + 32", "X_S2M", "clk", "{s_su_acc, s_su_idle, s_su_prog, s_su_rows}", "{xs_acc, xs_idle, xs_prog, xs_rows}", ", .RESET(1)")
    stn("xm", "24 + 1 + 16 + 1", "X_M2S", "clk", "{me_acc_o, me_idle_o, me_prog_o, m_fin_o}", "{xm_acc, xm_idle, xm_prog, xm_fin}", ", .RESET(1)")
    stn("xmf", "NW + 32", "X_M2S", "clk", "{m_fidx_o, m_fval_o}", "{xm_fidx, xm_fval}")
    stn("dst", "1", "DST", "clk", "s_me_start", "m_start", ", .RESET(1)")
    stn("dtp", "2*NW + 12", "DST", "clk", "{s_me_token, s_me_pos, s_me_prog_base}", "{m_token, m_pos, m_prog_base}")
    # ---- the ME-side master (tt_ctl cut) ----
    cm = [".clk(clk)", ".rst_n(rst_n)", ".h_start(m_start)", ".token(m_token)", ".pos(m_pos)", ".prog_base(m_prog_base)",
          ".pw_v(1'b0)", ".pw_addr(10'd0)", ".pw_data(64'd0)", ".x_oacc(xs_acc)", ".x_oidle(xs_idle)", ".x_oprog(xs_prog)",
          ".x_orows(xs_rows)", ".kv_ok(kv_ok)", ".kv_write_drained(kv_write_drained)", ".me_mem_ok(me_mem_ok)",
          ".me_acc_o(me_acc_o)", ".me_idle_o(me_idle_o)", ".me_prog_o(me_prog_o)", ".m_fin_o(m_fin_o)",
          ".m_fidx_o(m_fidx_o)", ".m_fval_o(m_fval_o)"] + \
         [f".kvd_{n}(kvd_{n})" for n in ("v", "wbase", "ts", "ks", "js", "wcs", "split", "jsh", "tiles", "k", "nout",
                                          "kindk", "pos")] + \
         [".me_clk_en(me_clk_en)", ".c_fault(m_fault)", ".xme_clk(c_me_clk_w)"]
    for p, ex, k, w in P.ME:
        if p != "clk" and (k == "out" or (k == "in" and p not in P.ME_LOCAL)):
            cm.append(f".xme_{p}(u_me_{p})")
    L.append("    ot_qfd_tt_ctlm_xme #(.DCU_M(2), .DUC_M(2), .XW(24), .IS(1), .OS(1)) u_ctlm (\n        "
             + ",\n        ".join(cm) + ");")
    L += ["    assign vw_me_we = u_me_o_we & {(G >> SMIN){me_clk_en}};",
          "    assign vw_mx_we = u_me_mx_we & me_clk_en;"]
    sp = []
    for p, ex, k, w in P.ME:
        if p == "clk":
            sp.append(".clk(c_me_clk_w)")
        elif k in ("out", "in"):
            sp.append(f".{p}(u_me_{p})")
        elif k == "rst":
            sp.append(f".{p}(rst_n)")
        else:
            sp.append(f".{p}({ex})")
    L.append("    ot_qwen_me_spine_w12 #(.W(W), .IL(IL), .AW(AW), .NW(NW), .INT8_SCALE_WCS_BASE(INT8_SCALE_WCS_BASE),\n"
             "        .GT(G), .TG(4), " + ", ".join(f".{p}({p})" for p in F.EMIT.SPINE_PARAMS) + ") u_me (\n        "
             + ",\n        ".join(sp) + ");")
    L += ["    ot_qfd_su_embed #(.SW(SW), .AW(AW), .NW(NW), .HID(HID), .EMB_CODE_LANES(EMB_CODE_LANES),",
          "        .EMB_ADDR_BASE(EMB_ADDR_BASE), .QWEN_FULLSHAPE(QWEN_FULLSHAPE), .INT8_EMBED(INT8_EMBED)) u_emb (",
          "        .clk(clk), .rst_n(rst_n), .go(u_su_go), .a_src(u_su_asrc_raw), .tok(u_tok), .scale(u_escale),",
          "        .su_va_re(u_su_va_re), .su_va_addr(u_su_va_addr), .su_va_q(u_su_va_q), .va_re(va_re), .va_addr(va_addr),",
          "        .va_q(va_q), .embed_code_re(embed_code_re), .embed_code_addr(embed_code_addr), .embed_code_q(embed_code_q),",
          "        .fault(u_su_efault));"]
    SU_MEM = {"va_q": "SW*32", "vb_q": "SW*32", "vc_q": "SW*32", "wrom_q": "W*16", "crom_q": "SW*64"}
    su_ml = c["su_ml"]
    su = []
    for p, ex, k, w in P.SU:
        if su_ml and p in SU_MEM:
            src = f"u_su_{p}" if k in ("out", "in") else ex
            L.append(f"    wire [{SU_MEM[p]}-1:0] ml_{p};")
            L.append(f"    ot_hdc_delay #(.W({SU_MEM[p]}), .D({su_ml})) u_ml_{p} (.clk(clk), .rst_n(rst_n), .d({src}), .q(ml_{p}));")
            su.append(f".{p}(ml_{p})")
        elif k in ("out", "in"):
            su.append(f".{p}(u_su_{p})")
        elif k in ("rst", "clk"):
            su.append(f".{p}({ex})")
        elif k == "dir_ok":
            su.append(f".{p}(su_kv_we)")
        else:
            su.append(f".{p}({ex})")
    L.append(f"    ot_hdc_vstream_rt #(.SW(SW), .LV(LV), .WR(W), .AW(AW), .NW(NW), .KV_FP8(KV_FP8), .ML({su_ml})) u_su (\n        "
             + ",\n        ".join(su) + ");")
    L += ["    assign kv_we = su_kv_we;", "endmodule"]
    return "\n".join(L) + "\n"


def patch_die(t: str) -> str:
    """the die: its sequencer instance goes (u_seq_su holds the sequencer); the core instance becomes ot_qfd_o4_core
    and takes the sequencer's die connections as sq_*"""
    t, seq = cut_between(t, "    ot_qwen_tp_seq_w12 #(", ".r_rank(r_rank),.r_err(r_err));\n")
    conns = re.findall(r"\.(\w+)\(([^()]*(?:\([^()]*\)[^()]*)*)\)", seq[seq.index(") seq ("):])
    names = {n for n, _ in conns}
    want = SEQ_CONN_IN | SEQ_CONN_OUT | SEQ_DROP
    if names != want:
        raise SystemExit(f"die sequencer connections changed: extra {names - want}, missing {want - names}")
    sq = [f".sq_{n}({e})" for n, e in conns if n not in SEQ_DROP]
    t = one(t, "    ot_qwen_rom_core #(.W(W)", "    ot_qfd_o4_core #(.W(W)")
    t = one(t, ".me_mem_ok(me_mem_ok_svc),.me_clk_en(me_clk_en));",
            ".me_mem_ok(me_mem_ok_svc),.me_clk_en(me_clk_en),\n        " + ",".join(sq) + ");\n"
            "    assign desc_re = 1'b0; assign desc_addr = 6'd0;   // option 4: the descriptor store is inside u_seq_su")
    for net in CTRL_NETS:
        t = re.sub(rf"\bcore\.{net}\b", f"core.u_seq_su.u_ctrl.{net}", t)
    return t


def pub():
    s = SEQS[VAR["seq"]][1]
    return [f'public_flat_rw -module "{s}" -var "prog_mem"', f'public_flat_rw -module "{s}" -var "desc_mem"',
            'public_flat_rw -module "ot_qfd_tt_ctlm_xme" -var "prog_mem"']


def proxy_access(hpp: Path, header: Path):
    """rm_prog / rm_desc write every copy of the program / descriptor image (die arrays + the masters' stores)"""
    names = set(re.findall(r"(\w+__DOT__\w+)", header.read_text()))

    def hit(suffix):
        h = sorted(n for n in names if n.endswith(suffix))
        if len(h) != 1:
            raise SystemExit(f"{suffix}: {h}")
        return h[0]
    sp, sd, cp = hit("u_seq_su__DOT__prog_mem"), hit("u_seq_su__DOT__desc_mem"), hit("u_ctlm__DOT__prog_mem")
    t = hpp.read_text()
    mp = re.search(r"static inline auto& rm_prog\(Vdie___024root\* r\) \{ return r->(\w+); \}", t)
    md = re.search(r"static inline auto& rm_desc\(Vdie___024root\* r\) \{ return r->(\w+); \}", t)
    dp, dd = mp.group(1), md.group(1)
    t = t.replace(mp.group(0), (
        "struct RmProgW { Vdie___024root* r; int a, w; RmProgW& operator=(uint32_t v) {\n"
        f"    r->{dp}[a][w] = v; r->{sp}[a][w] = v; r->{cp}[a][w] = v; return *this; }} }};\n"
        "struct RmProgR { Vdie___024root* r; int a; RmProgW operator[](int w) { return RmProgW{r, a, w}; } };\n"
        "struct RmProg { Vdie___024root* r; RmProgR operator[](int a) { return RmProgR{r, a}; } };\n"
        "static inline RmProg rm_prog(Vdie___024root* r) { return RmProg{r}; }   // option4_die: all three copies"))
    t = t.replace(md.group(0), (
        "struct RmDescW { Vdie___024root* r; int a; RmDescW& operator=(uint64_t v) {\n"
        f"    r->{dd}[a] = v; r->{sd}[a] = v; return *this; }} }};\n"
        "struct RmDesc { Vdie___024root* r; RmDescW operator[](int a) { return RmDescW{r, a}; } };\n"
        "static inline RmDesc rm_desc(Vdie___024root* r) { return RmDesc{r}; }   // option4_die: both copies"))
    hpp.write_text(t)


def extras(c: dict, core: str) -> str:
    path, mod, emitter = SEQS[VAR["seq"]]
    seqb = path.read_text()
    if seqb != emitter():
        raise SystemExit(f"committed {path.name} is stale against its emitter")
    return "\n".join([rst_stn(), S.SPLIT_RTL.read_text(), ctlm_xme(c["xmut"]), seqb, compose(core, c)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=("build", "run", "emit"))
    ap.add_argument("--build", type=Path)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--stages", choices=("L0", "L3", "full"), default="L3")
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--jobs", type=int, default=16)
    for k in CFG:
        ap.add_argument("--" + k.replace("_", "-"), type=int, default=None)
    ap.add_argument("--ctlm", choices=sorted(CTLMS), default="ctlm")
    ap.add_argument("--seq", choices=sorted(SEQS), default="boundary")
    a = ap.parse_args()
    VAR.update(ctlm=a.ctlm, seq=a.seq)
    for k in CFG:
        if getattr(a, k) is not None:
            CFG[k] = getattr(a, k)
    if a.phase == "run":
        sys.exit(F.run(a.build.resolve(), a.work.resolve(), a.stages, a.threads))
    base_emit = F.EMIT.emit
    core = base_emit(F.EMIT.CORE.read_text())
    ext = extras(CFG, core)
    die_text = patch_die(F.TOP_SV.read_text())
    if a.phase == "emit":
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "ot_qwen_rom_core.sv").write_text(core + "\n" + ext)
        (a.out / F.TOP_SV.name).write_text(die_text)
        (a.out / "public.vlt").write_text(S4.VLT + "\n".join(pub()) + "\n")
        print(a.out)
        return
    bld = a.build.resolve()
    gen = ROOT / "build" / "redesign_qwen_o4" / bld.name
    gen.mkdir(parents=True, exist_ok=True)
    (gen / F.TOP_SV.name).write_text(die_text)
    F.EMIT.emit = lambda text: base_emit(text) + "\n" + ext
    orig = F.die_sources
    F.die_sources = lambda: [gen / F.TOP_SV.name if f == F.TOP_SV else f for f in orig()]
    S4.VLT = S4.VLT + "\n".join(pub()) + "\n"
    orig_link = F.link

    def link(b, steps, prefixes=("die", "coll", "tile")):
        proxy_access(b / "gen" / "rm_access.hpp", b / "die" / "Vdie___024root.h")
        return orig_link(b, steps, prefixes)
    F.link = link
    F.build(bld, a.jobs)
    (bld / "O4DIE.json").write_text(json.dumps(dict(CFG, ctlm=str(CTLMS[VAR["ctlm"]][0].relative_to(ROOT)),
                                                    seq_su=str(SEQS[VAR["seq"]][0].relative_to(ROOT))), indent=1) + "\n")


if __name__ == "__main__":
    main()
