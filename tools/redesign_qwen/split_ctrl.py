#!/usr/bin/env python3
"""redesign-qwen 2026-10-09: the Qwen ROM die's sequencer <-> tree-top relay (r22k: 37 / 37 ME stations, 7 / 7 SU) as
TWO controllers on one instruction stream -- owner options 3 (ME issue unit with its instruction queue at the tree top)
and 4 (split controller: an ME-side controller by the tree top, an SU-side one by the stream unit).

Both are the SAME RTL (only the station counts differ, i.e. where the SU-side controller sits):

  u_ctrl     (OWN = 2) the SU-side controller: fetches the program, issues the stream-unit ops, owns done / next_token /
             cycles / the KV write flush / the embedding scale read.  Option 3: at the sequencer (SU 7 / 7 stations);
             option 4: by the SU (SU 2 / 2).
  u_ctrl_me  (OWN = 1) the ME-side controller IN the tree-top tile: its own copy of the program stream (prog2 port: the
             replicated program ROM / the stream relayed ahead of use), issues the matrix-engine ops with the engine's
             own ready (ME 2 / 2: the tile's registered boundary), owns the argmax fold, the KV descriptor and the engine
             clock enable.

Each controller decodes EVERY instruction in program order (same NEXT / FIFO / DYN logic as ot_qwen_rom_core_ctrl):
  * an instruction of its own unit issues as in the base core, except that every condition on the OTHER unit
    (barrier / chase / wait_<other>) is evaluated on the other unit's STATUS SNAPSHOT {accepted-op count, idle, progress,
    rows} that crosses the die (X stations) -- and only when that count equals the number of other-unit instructions
    before this one (the other unit has accepted exactly its earlier ops: the base's in-order view);
  * an instruction of the other unit is passed at once, unless it depends on THIS unit (barrier, chase, or wait on
    this unit): then the controller holds there until the other side has accepted it (its count moved past), so this
    unit can never run ahead of a status sample the other side still has to take.  Independent ops of the two units
    overlap (the base's issue order between units is kept only where the program states a dependency).
  * END: both controllers drain (own unit idle, other unit's snapshot synchronised and idle); the SU-side controller's
    done also waits for the ME-side controller's own END (its argmax fold is final) and takes next_token / next_val
    from it.
Status crosses as monotone counters + registered status, so a stale snapshot is conservative (never premature).

usage: split_ctrl.py build --build DIR [--jobs 16] --opt 3|4 [--x-m2s N --x-s2m N --dcu-s N --duc-s N --dcu-m N
                           --duc-m N --dstart N] [--su-ml 7] [--xmut N]
       split_ctrl.py run --build DIR --work DIR --stages L3
MUT (negative controls, must FAIL the exact gate): 1 = cross dependencies ignored at the ME side (an ME op waiting
on the SU issues on its own ready), 2 = the dependency hold is dropped (the other side runs ahead of a pending sample).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "exactness"))
sys.path.insert(0, str(ROOT / "tools" / "qwen_missing"))
import qwen_rom_fulltoken as F  # noqa: E402
import emit_partition as P  # noqa: E402

BASE_EMIT = F.EMIT.emit
SPLIT_RTL = ROOT / "rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv"
CFG = dict(dcu_s=7, duc_s=7, dcu_m=2, duc_m=2, x_m2s=37, x_s2m=44, dstart=37, su_ml=7, xmut=0, xw=24)
OPTS = {  # r22k: seq <-> TT 37 stations a way, seq <-> SU 7; SU <-> TT 21 (centre to centre, 430.56-um pitch + pins)
    "3": dict(dcu_s=7, duc_s=7, dcu_m=2, duc_m=2, x_m2s=37, x_s2m=44, dstart=37),
    "4": dict(dcu_s=2, duc_s=2, dcu_m=2, duc_m=2, x_m2s=21, x_s2m=21, dstart=37),
}


def one(t, old, new, n=1):
    if t.count(old) != n:
        raise SystemExit(f"anchor x{t.count(old)} (want {n}): {old[:90]!r}")
    return t.replace(old, new)


def ctrl_x(ctrl: str) -> str:
    """ot_qwen_rom_core_ctrl (emit_partition.emit_ctrl) -> ot_qwen_rom_core_ctrl_x #(OWN)"""
    t = ctrl.replace("module ot_qwen_rom_core_ctrl #(", "module ot_qwen_rom_core_ctrl_x #(\n"
                     "    parameter integer OWN = 2,        // redesign-qwen: this controller's unit (1 ME, 2 SU)\n"
                     "    parameter integer XW = 24,        // other-unit op counter width\n"
                     "    parameter integer XMUT = 0,       // negative controls (split_ctrl.py MUT)", 1)
    t = one(t, "    output wire [1-1:0] po_su_asrc_raw\n);",
            "    output wire [1-1:0] po_su_asrc_raw,\n"
            "    // -- redesign-qwen two-controller ports --\n"
            "    input  wire [XW-1:0] x_oacc,          // other unit: ops accepted (snapshot)\n"
            "    input  wire          x_oidle,\n"
            "    input  wire [15:0]   x_oprog,\n"
            "    input  wire [15:0]   x_orows,\n"
            "    input  wire          x_ofin,          // ME side reached END (its fold final): SU side only\n"
            "    input  wire [NW-1:0] x_fidx,\n"
            "    input  wire [31:0]   x_fval,\n"
            "    output wire          o_fin,\n"
            "    output wire [NW-1:0] o_fidx,\n"
            "    output wire [31:0]   o_fval\n);")
    t = one(t, "    wire chased = ((d_unit == 2'd1) ? (d_chase_rows ? su_rows : su_progress) : me_progress) >= d_chase_n;\n",
            "    // redesign-qwen two controllers: own / other unit, the other side's snapshot, the dependency hold\n"
            "    reg  [XW-1:0] o_cnt;                       // other-unit instructions passed so far\n"
            "    wire own = (d_unit == OWN[1:0]);\n"
            "    wire oth = (d_unit != 2'd0) && !own;\n"
            "    wire [XW-1:0] o_dif = x_oacc - o_cnt;\n"
            "    wire osync = (o_dif == {XW{1'b0}});        // the other unit accepted exactly its earlier ops\n"
            "    wire opast = !osync && !o_dif[XW-1];       // ... and the one at NEXT\n"
            "    wire own_idle = (OWN == 1) ? me_idle : su_idle;\n"
            "    wire o_drained = osync && x_oidle;\n"
            "    wire x_drained = own_idle && o_drained && (!KV_VEC_WRITE_BRIDGE || kv_write_drained);\n"
            "    wire [15:0] x_och = (OWN == 1) ? (d_chase_rows ? x_orows : x_oprog) : x_oprog;\n"
            "    wire chased = osync && (x_och >= d_chase_n);\n"
            "    wire wait_o = (OWN == 1) ? d_wait_su : d_wait_me;\n"
            "    wire wait_u = (OWN == 1) ? d_wait_me : d_wait_su;\n"
            "    wire xdep_ok = (XMUT == 1 && OWN == 1) ? 1'b1 :\n"
            "                   (d_barrier ? x_drained : ((!d_chase || chased) && (!wait_u || own_idle) && (!wait_o || o_drained)));\n"
            "    wire odep = (XMUT == 2) ? 1'b0 : (d_barrier || d_chase || ((OWN == 1) ? d_wait_me : d_wait_su));\n"
            "    wire skip = (st == S_RUN) && nx_v && oth && (!odep || opast);\n")
    t = one(t, "    wire issue = (st == S_RUN) && nx_v && (d_unit != 2'd0) &&\n"
               "                 (d_barrier ? drained : ((!d_chase || chased) && (!d_wait_me || me_idle) && (!d_wait_su || su_idle)))\n"
               "                 && unit_ready && kv_gate && w_gate;\n",
            "    wire issue = (st == S_RUN) && nx_v && own && xdep_ok\n"
            "                 && unit_ready && kv_gate && w_gate;\n")
    t = one(t, "    wire fin = (st == S_RUN) && nx_v && (d_unit == 2'd0) && drained;\n",
            "    wire fin = (st == S_RUN) && nx_v && (d_unit == 2'd0) && x_drained && ((OWN == 1) || x_ofin);\n"
            "    reg fin_seen;                              // this controller reached END in this run\n"
            "    always @(posedge clk or negedge rst_n)\n"
            "        if (!rst_n) fin_seen <= 1'b0;\n"
            "        else if (start && st == S_IDLE) fin_seen <= 1'b0;\n"
            "        else if (fin) fin_seen <= 1'b1;\n"
            "    assign o_fin = fin_seen;\n"
            "    always @(posedge clk or negedge rst_n)\n"
            "        if (!rst_n) o_cnt <= {XW{1'b0}};\n"
            "        else if (skip) o_cnt <= o_cnt + 1'b1;\n")
    t = one(t, "&& (!nx_v || issue);", "&& (!nx_v || issue || skip);")
    t = one(t, "                    if (issue) pc <= pc + 1'b1;\n                    if (load) nx_v <= 1'b1;\n"
               "                    else if (issue) nx_v <= 1'b0;",
            "                    if (issue || skip) pc <= pc + 1'b1;\n                    if (load) nx_v <= 1'b1;\n"
            "                    else if (issue || skip) nx_v <= 1'b0;")
    t = one(t, "done <= 1'b1; next_token <= fin_idx; next_val <= fin_val;",
            "done <= 1'b1; next_token <= (OWN == 2) ? x_fidx : fin_idx; next_val <= (OWN == 2) ? x_fval : fin_val;")
    t = one(t, "    wire [31:0] fin_val = am_wins ? am_val : run_val;\n",
            "    wire [31:0] fin_val = am_wins ? am_val : run_val;\n    assign o_fidx = fin_idx; assign o_fval = fin_val;\n")
    return t


def ctrl_ports(core: str):
    """(direction, name) of the core's ports (the controller has the same set, then its partition ports)"""
    params, port_text = P.header(core)
    return [(d, n) for d, _, n in P.ports_of(port_text)], params


# core outputs the ME-side controller drives (everything else comes from the SU-side controller)
ME_OUTS = {"int8_wrom_re", "int8_wrom_addr", "kvd_v", "kvd_wbase", "kvd_ts", "kvd_ks", "kvd_js", "kvd_wcs", "kvd_split",
           "kvd_jsh", "kvd_tiles", "kvd_k", "kvd_nout", "kvd_kindk", "kvd_pos", "wd_v", "wd_wbase", "wd_sbase",
           "wd_tiles", "wd_k", "wd_nout", "me_clk_en"}


def emit_part_x(core: str, c: dict) -> str:
    """ot_qwen_rom_core (same ports + prog2_*) = two controllers + spine + stream unit"""
    params, port_text = P.header(core)
    ports = P.ports_of(port_text)
    names = [n for _, _, n in ports]
    dirs = {n: d for d, _, n in ports}
    pnames = re.findall(r"parameter\s+integer\s+(\w+)", params)
    L = ["// GENERATED by tools/redesign_qwen/split_ctrl.py: ot_qwen_rom_core as two controllers (SU side u_ctrl, ME side",
         "// u_ctrl_me in the tree-top tile) on one instruction stream + the spine + the stream unit.",
         params.replace("module ot_qwen_rom_core #(", "module ot_qwen_rom_core_part #(", 1)
         + "".join(f",\n    parameter integer {k.upper()} = {v}" for k, v in c.items()),
         ") (", re.sub(r"(me_clk_en)(\s*//[^\n]*)?\s*$", r"\1,\2", port_text.rstrip()),
         "    output wire              prog2_re,          // the ME-side controller's program stream",
         "    output wire [PAW-1:0]    prog2_addr,",
         "    input  wire [INSTR_BITS-1:0] prog2_q",
         ");",
         "    localparam integer RT_S = DCU_S + DUC_S;",
         "    localparam integer RT_M = DCU_M + DUC_M;"]
    for unit, table in (("me", P.ME), ("su", P.SU)):
        for p, ex, k, w in table:
            if k in ("out", "in"):
                L.append(f"    wire [{w}-1:0] c_{unit}_{p}, u_{unit}_{p}, z_{unit}_{p};")
    L += ["    wire [SW-1:0] su_kv_we, d_su_kv_we;", "    wire c_su_asrc_raw, u_su_asrc_raw;",
          "    wire [NW-1:0] c_tok, u_tok; wire [15:0] c_escale, u_escale;", "    wire u_su_efault;",
          "    wire s_me_ready, s_me_idle, s_su_ready, s_su_idle;",
          "    wire [15:0] s_me_progress, s_su_progress, s_su_progress_rows;",
          "    wire m_fin, s_fin; wire [NW-1:0] m_fidx, s_fidx; wire [31:0] m_fval, s_fval;",
          "    wire [XW-1:0] xs_acc, xm_acc; wire xs_idle, xm_idle, xm_fin; wire [15:0] xs_prog, xs_rows, xm_prog;",
          "    wire [NW-1:0] xm_fidx; wire [31:0] xm_fval;",
          "    wire s_fault, m_fault;"]
    dir_ports = {ex.split("[")[0] for _, ex, k, _ in P.ME + P.SU if k in ("dir_o", "dir_i")}
    own = {"kv_we", "va_re", "va_addr", "embed_code_re", "embed_code_addr", "vw_me_we", "vw_mx_we"}
    dir_i = {ex.split("[")[0] for _, ex, k, _ in P.ME + P.SU if k == "dir_i"}

    def inst(side: str) -> str:
        cc = []
        for n in names:
            d = dirs[n]
            if n in own or n in dir_ports:
                cc.append(f".{n}('0)" if n in dir_i else f".{n}()")
            elif side == "me" and n in ("start", "token", "pos"):
                cc.append(f".{n}(m_{n})")
            elif side == "me" and n in ("prog_re", "prog_addr", "prog_q"):
                cc.append(f".{n}({n.replace('prog', 'prog2')})")
            elif d == "output":
                if n == "fault":
                    cc.append(f".fault({side[0]}_fault)")
                elif (side == "me") == (n in ME_OUTS):
                    cc.append(f".{n}({n})")
                else:
                    cc.append(f".{n}()")
            else:
                cc.append(f".{n}({n})")
        for unit, table, local, shell in (("me", P.ME, P.ME_LOCAL, P.SHELL_ME), ("su", P.SU, P.SU_LOCAL, P.SHELL_SU)):
            mine = (unit == side)
            for p, ex, k, w in table:
                if k == "out":
                    cc.append(f".po_{unit}_{p}({'c' if mine else 'z'}_{unit}_{p})")
                elif k == "in":
                    if not mine or p in local:
                        cc.append(f".pi_{unit}_{p}('0)")
                    elif p in shell:
                        cc.append(f".pi_{unit}_{p}(s_{unit}_{p})")
                    else:
                        cc.append(f".pi_{unit}_{p}(c_{unit}_{p})")
                elif k == "dir_ok":
                    cc.append(f".pi_{unit}_{p}({'d_su_kv_we' if mine else chr(39) + '0'})")
        cc.append(f".po_su_asrc_raw({'c_su_asrc_raw' if side == 'su' else ''})")
        if side == "su":
            cc += [".x_oacc(xm_acc)", ".x_oidle(xm_idle)", ".x_oprog(xm_prog)", ".x_orows(16'd0)", ".x_ofin(xm_fin)",
                   ".x_fidx(xm_fidx)", ".x_fval(xm_fval)", ".o_fin(s_fin)", ".o_fidx(s_fidx)", ".o_fval(s_fval)"]
        else:
            cc += [".x_oacc(xs_acc)", ".x_oidle(xs_idle)", ".x_oprog(xs_prog)", ".x_orows(xs_rows)", ".x_ofin(1'b1)",
                   ".x_fidx('0)", ".x_fval('0)", ".o_fin(m_fin)", ".o_fidx(m_fidx)", ".o_fval(m_fval)"]
        own_n = 1 if side == "me" else 2
        return (f"    ot_qwen_rom_core_ctrl_x #(.OWN({own_n}), .XW(XW), .XMUT(XMUT), "
                + ", ".join(f".{p}({p})" for p in pnames) + f") u_ctrl{'_me' if side == 'me' else ''} (\n        "
                + ",\n        ".join(cc) + ");")
    # the ME-side controller's token start: the start / token / pos relayed to the tree-top tile
    L += ["    wire m_start; wire [NW-1:0] m_token, m_pos;",
          "    ot_hdc_delay #(.W(1), .D(DSTART), .RESET(1)) u_dst (.clk(clk), .rst_n(rst_n), .d(start), .q(m_start));",
          "    ot_hdc_delay #(.W(2*NW), .D(DSTART)) u_dtp (.clk(clk), .rst_n(rst_n), .d({token, pos}), .q({m_token, m_pos}));",
          inst("su"), inst("me"),
          "    assign fault = s_fault | m_fault;"]
    # issue shells (each unit by its own controller)
    L += ["    ot_qfd_issue_shell #(.RT_ME(RT_M), .RT_SU(0), .COMP(1)) u_shell_me (.clk(clk), .rst_n(rst_n),",
          "        .me_go(c_me_go), .su_go(1'b0), .me_en(me_clk_en), .su_sfu(3'd0), .me_amax(c_me_i_amax),",
          "        .d_me_ready(c_me_ready), .d_me_idle(c_me_idle), .d_me_progress(c_me_progress),",
          "        .d_su_ready(1'b0), .d_su_idle(1'b0), .d_su_active(1'b0), .d_su_inflight(8'd0), .d_su_progress(16'd0), .d_su_rows(16'd0),",
          "        .c_me_ready(s_me_ready), .c_me_idle(s_me_idle), .c_me_progress(s_me_progress),",
          "        .c_su_ready(), .c_su_idle(), .c_su_progress(), .c_su_rows());",
          "    ot_qfd_issue_shell #(.RT_ME(0), .RT_SU(RT_S), .COMP(1)) u_shell_su (.clk(clk), .rst_n(rst_n),",
          "        .me_go(1'b0), .su_go(c_su_go), .me_en(1'b1), .su_sfu(c_su_i_sfu), .me_amax(1'b0),",
          "        .d_me_ready(1'b0), .d_me_idle(1'b0), .d_me_progress(16'd0),",
          "        .d_su_ready(c_su_ready), .d_su_idle(c_su_idle), .d_su_active(c_su_rt_active), .d_su_inflight(c_su_rt_inflight),",
          "        .d_su_progress(c_su_progress), .d_su_rows(c_su_progress_rows),",
          "        .c_me_ready(), .c_me_idle(), .c_me_progress(),",
          "        .c_su_ready(s_su_ready), .c_su_idle(s_su_idle), .c_su_progress(s_su_progress), .c_su_rows(s_su_progress_rows));"]
    # per-token constants for the SU-side embedding decode (the SU-side controller's token start)
    L += ["    reg es_pend; reg [15:0] es_hold; reg [NW-1:0] tok_l;",
          "    always @(posedge clk or negedge rst_n) if (!rst_n) es_pend <= 1'b0; else es_pend <= embed_scale_re;",
          "    always @(posedge clk) begin if (es_pend) es_hold <= embed_scale_q; if (embed_scale_re) tok_l <= token; end",
          "    assign c_tok = tok_l; assign c_escale = es_hold;"]

    def stn(name, w, d, clk, src, dst, rst=""):
        L.append(f"    ot_hdc_delay #(.W({w}), .D({d}){rst}) u_{name} (.clk({clk}), .rst_n(rst_n), .d({src}), .q({dst}));")
    for p, ex, k, w in P.ME:
        if k == "out" and p != "clk":
            stn(f"sd_me_{p}", w, "DCU_M", "c_me_clk", f"c_me_{p}", f"u_me_{p}", ", .RESET(1)" if p == "go" else "")
        elif k == "in" and p not in P.ME_LOCAL:
            stn(f"su_me_{p}", w, "DUC_M", "c_me_clk", f"u_me_{p}", f"c_me_{p}", P._rst(w))
    for p, ex, k, w in P.SU:
        if k == "out" and p != "va_q":
            stn(f"sd_su_{p}", w, "DCU_S", "clk", f"c_su_{p}", f"u_su_{p}", ", .RESET(1)" if p == "go" else "")
        elif k == "in" and p not in P.SU_LOCAL:
            src = "u_su_fault | u_su_efault" if p == "fault" else f"u_su_{p}"
            stn(f"su_su_{p}", w, "DUC_S", "clk", src, f"c_su_{p}", P._rst(w))
    stn("sd_asrc", "1", "DCU_S", "clk", "c_su_asrc_raw", "u_su_asrc_raw")
    stn("sd_tok", "NW", "DCU_S", "clk", "c_tok", "u_tok")
    stn("sd_escale", "16", "DCU_S", "clk", "c_escale", "u_escale")
    stn("su_kvwe", "SW", "DUC_S", "clk", "su_kv_we", "d_su_kv_we", ", .RESET(1)")
    # ---- the status snapshots across the die: accepted-op counters (at the units) + registered status
    L += ["    reg [XW-1:0] me_acc, su_acc;",
          "    always @(posedge c_me_clk or negedge rst_n) if (!rst_n) me_acc <= {XW{1'b0}}; else if (u_me_go) me_acc <= me_acc + 1'b1;",
          "    always @(posedge clk or negedge rst_n) if (!rst_n) su_acc <= {XW{1'b0}}; else if (u_su_go) su_acc <= su_acc + 1'b1;",
          # ME -> SU side: the unit's count / idle / progress, plus the ME-side controller's END and its fold result
          "    ot_hdc_delay #(.W(XW + 1 + 16 + 1), .D(X_M2S), .RESET(1)) u_xm (.clk(clk), .rst_n(rst_n),",
          "        .d({me_acc, u_me_idle, u_me_progress, m_fin}), .q({xm_acc, xm_idle, xm_prog, xm_fin}));",
          "    ot_hdc_delay #(.W(NW + 32), .D(X_M2S)) u_xmf (.clk(clk), .rst_n(rst_n), .d({m_fidx, m_fval}), .q({xm_fidx, xm_fval}));",
          "    ot_hdc_delay #(.W(XW + 1 + 32), .D(X_S2M), .RESET(1)) u_xs (.clk(clk), .rst_n(rst_n),",
          "        .d({su_acc, u_su_idle, u_su_progress, u_su_progress_rows}), .q({xs_acc, xs_idle, xs_prog, xs_rows}));"]
    L += ["    assign vw_me_we = u_me_o_we & {(G >> SMIN){me_clk_en}};",
          "    assign vw_mx_we = u_me_mx_we & me_clk_en;"]
    sp = []
    for p, ex, k, w in P.ME:
        if p == "clk":
            sp.append(".clk(c_me_clk)")
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
    out = "\n".join(L) + "\n"
    # the core's own c_me_clk is the ME-side controller's po_me_clk
    return out


def part_core(text: str) -> str:
    core = BASE_EMIT(text)
    ctrl = P.emit_ctrl(core)
    part = emit_part_x(core, CFG).replace("module ot_qwen_rom_core_part #(", "module ot_qwen_rom_core #(", 1)
    return ctrl_x(ctrl) + "\n" + part + "\n" + SPLIT_RTL.read_text()


CTRL_NETS = ("st", "nx_v", "d_unit", "me_wsrc", "kv_gate", "su_ready", "su_idle", "me_idle", "d_barrier")


def patch_die(t: str) -> str:
    """the die's core instance gets the ME-side program port (prog2: the replicated program ROM)"""
    t = one(t, "    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q;",
            "    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q;\n"
            "    wire prog2_re; wire [11:0] prog2_addr; reg [1023:0] prog2_q;   // redesign-qwen: ME-side program port")
    t = one(t, ".prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),",
            ".prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),\n        .prog2_re(prog2_re),.prog2_addr(prog2_addr),.prog2_q(prog2_q),")
    t = one(t, "        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;\n",
            "        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;\n"
            "        if (prog2_re) prog2_q <= ((prog_base + prog2_addr) < 64) ? prog_mem[prog_base[5:0] + prog2_addr[5:0]] : 1024'd0;\n")
    for net in CTRL_NETS:
        t = re.sub(rf"\bcore\.{net}\b", f"core.u_ctrl.{net}", t)
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=("build", "run", "emit"))
    ap.add_argument("--build", type=Path)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--stages", choices=("L0", "L3", "full"), default="L3")
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--opt", choices=sorted(OPTS), default="4")
    for k in ("dcu_s", "duc_s", "dcu_m", "duc_m", "x_m2s", "x_s2m", "dstart", "su_ml", "xmut"):
        ap.add_argument("--" + k.replace("_", "-"), type=int, default=None)
    ap.add_argument("--max-cycles", type=int, default=0)
    ap.add_argument("--out", type=Path, help="emit: write the generated core here")
    a = ap.parse_args()
    if a.max_cycles:
        F.L0_MAX_CYCLES = a.max_cycles
    CFG.update(OPTS[a.opt])
    for k in list(CFG):
        v = getattr(a, k, None)
        if v is not None:
            CFG[k] = v
    if a.phase == "emit":
        a.out.write_text(part_core(F.EMIT.CORE.read_text()))
        return
    bld = a.build.resolve()
    if a.phase == "run":
        sys.exit(F.run(bld, a.work.resolve(), a.stages, a.threads))
    F.EMIT.emit = part_core
    orig = F.die_sources
    gen = ROOT / "build" / "redesign_qwen_split" / bld.name
    gen.mkdir(parents=True, exist_ok=True)

    def die_sources():
        out = []
        for f in orig():
            t = f.read_text()
            if ".prog_q(prog_q)" in t:
                g = gen / f.name
                g.write_text(patch_die(t))
                out.append(g)
            else:
                out.append(f)
        return out
    F.die_sources = die_sources
    F.build(bld, a.jobs)
    (bld / "SPLIT.json").write_text(json.dumps(dict(opt=a.opt, **CFG), indent=1) + "\n")


if __name__ == "__main__":
    main()
