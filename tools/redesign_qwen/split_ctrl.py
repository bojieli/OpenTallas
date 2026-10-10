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
    ap.add_argument("phase", choices=("build", "run", "emit", "emit-tile", "emit-seq-su"))
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
    if a.phase == "emit-tile":
        a.out.write_text(emit_tt_ctlm())
        return
    if a.phase == "emit-seq-su":
        a.out.write_text(emit_seq_su())
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



# ---------------------------------------------------------------------------------------------------------------------
# The tree-top control tile WITH the ME-side controller (die master qfd_tt_ctlm): ot_qfd_tt_ctl (control element,
# AMR / SPRE) + ot_qwen_rom_core_ctrl_x OWN 1 + its program-store copy (64 x 1,024 b configuration flops, written by the
# same pw_* broadcast as the sequencer's) + the local issue shell (RT_M = DCU_M + DUC_M edges inside the tile).  The
# ME issue / status bus (380 + 98 b over 37 relays each way in r22k) is now INSIDE the tile; what crosses the die is:
#   in : the token start (h_start / token / pos / prog_base), the program writes (pw_*), the SU status snapshot
#        (x_oacc / x_oidle / x_oprog / x_orows), kv_ok, kv_write_drained, me_mem_ok
#   out: the ME status snapshot (me_acc / me_idle / me_prog / m_fin / m_fidx / m_fval), the KV descriptor kvd_*, the
#        engine clock enable, fault
# plus every non-issue port of ot_qfd_tt_ctl (bands / VM / port elements / lanes) unchanged.
TT_PARAMS = dict(W=16, IL=8, AW=24, NW=18, GT=6144, TG=4, SMIN=7, SMAX=11, TCUT=7, XD=105, XVM=15, ORD=7, ACC_LAT=7,
                 TREE_LAT=7, MUL_LAT=6, FAST_ISSUE=1, KV_PREP=3, SCALE_LAT=6, IS=1, OS=1, LANDED=1, BAND=1, LNK=0,
                 CLNK=0, AMR=1, SPRE=2)


def emit_tt_ctlm() -> str:
    core = BASE_EMIT(F.EMIT.CORE.read_text())
    ctrl = P.inline_include(ctrl_x(P.emit_ctrl(core)))
    params, port_text = P.header(core)
    names = [n for _, _, n in P.ports_of(port_text)]
    dirs = {n: d for d, _, n in P.ports_of(port_text)}
    sp = P.SEQ_PARAMS
    tp = TT_PARAMS
    cpar = ("W(16), .G(%d), .AW(24), .NW(%d), .PAW(12), .SU_VEC(1), .SW(%d), .LV(%d), .KV_FP8(1), .INT8_WEIGHT(1), "
            ".INT8_SCALE_WCS_BASE(1), .INT8_EMBED(1), .QWEN_FULLSHAPE(%d), .HID(4096), .HALF(64), .HD(128), "
            ".EMB_CODE_LANES(64), .EMB_ADDR_BASE(0), .KV_HBM(1), .KV_VEC_WRITE_BRIDGE(1), .ME_STALL(1), "
            ".ME_IDLE_GATE(1), .SMIN(%d), .SMAX(%d), .TCUT(%d), .FQ_HEAD(1)"
            % (sp["G"], sp["NW"], sp["SW"], sp["LV"], sp["QWEN_FULLSHAPE"], sp["SMIN"], sp["SMAX"], sp["TCUT"]))
    NW, AW, W, GT, SMIN = tp["NW"], tp["AW"], tp["W"], tp["GT"], tp["SMIN"]
    LG = (GT - 1).bit_length()
    NPG = GT >> SMIN
    NPE = NPG // 4
    FW = 1 + 1 + 1 + 1 + 4 + AW + AW + 3 * (NW + 1)
    # issue fields of the spine (ME table order) -> tt_ctl ports
    fields = [(p, w) for p, ex, k, w in P.ME if k == "out" and p not in ("clk", "go")]
    L = ["`timescale 1ns/1ps",
         "// GENERATED by tools/redesign_qwen/split_ctrl.py emit_tt_ctlm(): die master qfd_tt_ctlm -- the tree-top control",
         "// tile with the ME-side controller inside (see the comment above emit_tt_ctlm).",
         "module ot_qfd_tt_ctlm #(",
         "    parameter integer DCU_M = 2, parameter integer DUC_M = 2,   // in-tile issue / status stations",
         "    parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1",
         ") (",
         "    input  wire clk, input wire rst_n,",
         "    // token start, program writes (the program-store copy), the SU snapshot, KV / supply readiness",
         f"    input  wire h_start, input wire [{NW}-1:0] token, input wire [{NW}-1:0] pos, input wire [11:0] prog_base,",
         "    input  wire pw_v, input wire [9:0] pw_addr, input wire [63:0] pw_data,",
         "    input  wire [XW-1:0] x_oacc, input wire x_oidle, input wire [15:0] x_oprog, input wire [15:0] x_orows,",
         "    input  wire kv_ok, input wire kv_write_drained, input wire me_mem_ok,",
         "    // the ME snapshot, the KV descriptor, the engine clock enable",
         f"    output wire [XW-1:0] me_acc_o, output wire me_idle_o, output wire [15:0] me_prog_o, output wire m_fin_o,",
         f"    output wire [{NW}-1:0] m_fidx_o, output wire [31:0] m_fval_o,",
         f"    output wire kvd_v, output wire [{AW}-1:0] kvd_wbase, kvd_ts, kvd_ks, kvd_js, kvd_wcs, output wire [3:0] kvd_split,",
         f"    output wire [2:0] kvd_jsh, output wire [{NW}-1:0] kvd_tiles, kvd_k, kvd_nout, output wire kvd_kindk,",
         f"    output wire [{NW}-1:0] kvd_pos, output wire me_clk_en, output wire c_fault,",
         "    // ot_qfd_tt_ctl's non-issue ports",
         "    input  wire up_fault, input wire [15:0] land_cnt,",
         f"    output wire scale_re, output wire [{NPG}-1:0] scale_gre, output wire [{NPG}*{AW}-1:0] scale_addr,",
         f"    input  wire x_rdy, output wire x_dv, output wire [{AW}-1:0] x_dc, x_dcs, output wire [3:0] x_dsp,",
         f"    output wire [{LG}:0] t_sel_e, t_tv_e, input wire [{W}-1:0] tr_fault,",
         f"    output wire p_v_e2, output wire [{FW}-1:0] p_f_e2, input wire [{NPE}*{1 + 32 + NW}-1:0] p_am,",
         f"    input  wire [{NPE}-1:0] p_fault, input wire fab_fault,",
         f"    output wire ov, output wire mx_we, output wire [{AW}-1:0] mx_addr, output wire [{W}-1:0] mx_mask,",
         f"    output wire [{W}*32-1:0] mx_data",
         ");"]
    L += ["    wire rs;", "    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));",
          "    // die-facing input pin stations (registered boundary); kv_ok / kv_write_drained / me_mem_ok stay direct (readiness",
          "    // the controller pairs with its own same-edge state, and the ICG enable path)",
          f"    wire q_h_start; wire [{NW}-1:0] q_token, q_pos; wire [11:0] q_prog_base; wire q_pw_v; wire [9:0] q_pw_addr; wire [63:0] q_pw_data;",
          "    wire [XW-1:0] q_x_oacc; wire q_x_oidle; wire [15:0] q_x_oprog, q_x_orows;",
          "    ot_hdc_delay #(.W(3), .D(IS), .RESET(1)) u_is1 (.clk(clk), .rst_n(rst_n), .d({h_start, pw_v, x_oidle}), .q({q_h_start, q_pw_v, q_x_oidle}));",
          f"    ot_hdc_delay #(.W(2*{NW} + 12 + 10 + 64 + XW + 32), .D(IS)) u_isd (.clk(clk), .rst_n(rst_n),",
          "        .d({token, pos, prog_base, pw_addr, pw_data, x_oacc, x_oprog, x_orows}),",
          "        .q({q_token, q_pos, q_prog_base, q_pw_addr, q_pw_data, q_x_oacc, q_x_oprog, q_x_orows}));",
          "    // program-store copy (the sequencer master's semantics)",
          "    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q; reg [1023:0] prog_mem [0:63];",
          "    wire [11:0] prog_a = q_prog_base + prog_addr;",
          "    always @(posedge clk) begin",
          "        if (q_pw_v) prog_mem[q_pw_addr[9:4]][q_pw_addr[3:0]*64 +: 64] <= q_pw_data;",
          "        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;",
          "    end"]
    # controller <-> tile issue / status nets with the in-tile stations
    for p, ex, k, w in P.ME:
        if k in ("out", "in"):
            L.append(f"    wire [{w}-1:0] c_me_{p}, u_me_{p};")
    L += ["    wire s_me_ready, s_me_idle; wire [15:0] s_me_progress; wire m_fin; wire [NW-1:0] m_fidx; wire [31:0] m_fval;"
          .replace("NW", str(NW))]
    cc = []
    for n in names:
        d = dirs[n]
        m = {"clk": "clk", "rst_n": "rs", "start": "q_h_start", "token": "q_token", "pos": "q_pos", "prog_q": "prog_q",
             "prog_re": "prog_re", "prog_addr": "prog_addr", "kv_ok": "kv_ok", "kv_write_drained": "kv_write_drained",
             "me_mem_ok": "me_mem_ok", "me_clk_en": "me_clk_en", "fault": "c_fault", "w_ok": "1'b1", "emb_ok": "1'b1",
             "fab_fault": "1'b0"}
        if n in m:
            cc.append(f".{n}({m[n]})")
        elif n.startswith("kvd_"):
            cc.append(f".{n}({n})")
        elif d == "output":
            cc.append(f".{n}()")
        else:
            cc.append(f".{n}('0)")
    for unit, table in (("me", P.ME), ("su", P.SU)):
        for p, ex, k, w in table:
            if k == "out":
                cc.append(f".po_{unit}_{p}({'c_me_' + p if unit == 'me' else ''})")
            elif k in ("in", "dir_ok"):
                if unit == "su" or p in P.ME_LOCAL:
                    cc.append(f".pi_{unit}_{p}('0)")
                elif p in P.SHELL_ME:
                    cc.append(f".pi_me_{p}(s_me_{p})")
                else:
                    cc.append(f".pi_me_{p}(c_me_{p})")
    cc += [".po_su_asrc_raw()", ".x_oacc(q_x_oacc)", ".x_oidle(q_x_oidle)", ".x_oprog(q_x_oprog)", ".x_orows(q_x_orows)",
           ".x_ofin(1'b1)", ".x_fidx('0)", ".x_fval('0)", ".o_fin(m_fin)", ".o_fidx(m_fidx)", ".o_fval(m_fval)"]
    L.append(f"    ot_qwen_rom_core_ctrl_x #(.OWN(1), .XW(XW), .XMUT(0), .{cpar}) u_ctrl_me (\n        "
             + ",\n        ".join(cc) + ");")
    L += ["    ot_qfd_issue_shell #(.RT_ME(DCU_M + DUC_M), .RT_SU(0), .COMP(1)) u_shell_me (.clk(clk), .rst_n(rs),",
          "        .me_go(c_me_go), .su_go(1'b0), .me_en(me_clk_en), .su_sfu(3'd0), .me_amax(c_me_i_amax),",
          "        .d_me_ready(c_me_ready), .d_me_idle(c_me_idle), .d_me_progress(c_me_progress),",
          "        .d_su_ready(1'b0), .d_su_idle(1'b0), .d_su_active(1'b0), .d_su_inflight(8'd0), .d_su_progress(16'd0), .d_su_rows(16'd0),",
          "        .c_me_ready(s_me_ready), .c_me_idle(s_me_idle), .c_me_progress(s_me_progress),",
          "        .c_su_ready(), .c_su_idle(), .c_su_progress(), .c_su_rows());"]
    for p, ex, k, w in P.ME:
        if k == "out" and p != "clk":
            L.append(f"    ot_hdc_delay #(.W({w}), .D(DCU_M){', .RESET(1)' if p == 'go' else ''}) u_sd_me_{p} (.clk(c_me_clk), "
                     f".rst_n(rst_n), .d(c_me_{p}), .q(u_me_{p}));")
        elif k == "in" and p not in P.ME_LOCAL:
            L.append(f"    ot_hdc_delay #(.W({w}), .D(DUC_M){P._rst(w)}) u_su_me_{p} (.clk(c_me_clk), .rst_n(rst_n), "
                     f".d(u_me_{p}), .q(c_me_{p}));")
    L = [x.replace("(NW)", f"({NW})").replace("(AW)", f"({AW})").replace("[NW-1", f"[{NW}-1").replace("[AW-1", f"[{AW}-1")
         .replace("(G >> SMIN)", f"({GT} >> {SMIN})") for x in L]
    # the engine-side status the snapshot carries (counted at the engine's accept)
    L += ["    reg [XW-1:0] me_acc;",
          "    always @(posedge c_me_clk or negedge rst_n) if (!rst_n) me_acc <= {XW{1'b0}}; else if (u_me_go) me_acc <= me_acc + 1'b1;",
          "    ot_hdc_delay #(.W(XW + 18), .D(OS), .RESET(1)) u_os_snap (.clk(clk), .rst_n(rs), .d({me_acc, u_me_idle, u_me_progress, m_fin}),",
          "        .q({me_acc_o, me_idle_o, me_prog_o, m_fin_o}));",
          f"    ot_hdc_delay #(.W({NW} + 32), .D(OS)) u_os_f (.clk(clk), .rst_n(rs), .d({{m_fidx, m_fval}}), .q({{m_fidx_o, m_fval_o}}));"]
    ttp = ", ".join(f".{k}({v})" for k, v in tp.items() if k not in ("IS", "OS")) + ", .IS(0), .OS(OS)"
    L += [f"    ot_qfd_tt_ctl #({ttp}) u_tt (",
          "        .clk(c_me_clk), .rst_n(rs), .up_fault(up_fault), .land_cnt(land_cnt), .go(u_me_go), .ready(u_me_ready),",   # registered reset (ctlm PREROUTE: rst_n port -> 32k flops)
          "        .idle(u_me_idle), " + ", ".join(f".{p}(u_me_{p})" for p, _ in fields if p.startswith("i_")) + ",",
          "        .wrom_re(u_me_wrom_re), .wrom_addr(u_me_wrom_addr), .kv_re(),",
          "        .scale_re(scale_re), .scale_gre(scale_gre), .scale_addr(scale_addr),",
          "        .x_rdy(x_rdy), .x_dv(x_dv), .x_dc(x_dc), .x_dcs(x_dcs), .x_dsp(x_dsp),",
          "        .t_sel_e(t_sel_e), .t_tv_e(t_tv_e), .tr_fault(tr_fault),",
          "        .p_v_e2(p_v_e2), .p_f_e2(p_f_e2), .p_am(p_am), .p_fault(p_fault), .fab_fault(fab_fault),",
          "        .ov(ov), .am_idx(u_me_am_idx), .am_val(u_me_am_val), .am_any(u_me_am_any),",
          "        .mx_we(mx_we), .mx_addr(mx_addr), .mx_mask(mx_mask), .mx_data(mx_data),",
          "        .progress(u_me_progress), .fault(u_me_fault));",
          "    assign u_me_mx_we = 1'b0; assign u_me_o_we = '0;",
          "endmodule"]
    return ctrl + "\n" + "\n".join(L) + "\n"



# ---------------------------------------------------------------------------------------------------------------------
# Option 4's SU side as a die master (qfd_seq_su): the compact sequencer (ot_qwen_tp_seq_w12 + program / descriptor
# stores) with the SU-side controller (ot_qwen_rom_core_ctrl_x OWN 2) and the SU issue shell, placed BY the stream unit
# (2 + 2 stations).  The ME issue / status pins are gone (the ME side runs in qfd_tt_ctlm); the ME status snapshot
# (x_*) arrives over the SU <-> tree-top relays.
def emit_seq_su() -> str:
    core = BASE_EMIT(F.EMIT.CORE.read_text())
    ctrl = P.inline_include(ctrl_x(P.emit_ctrl(core)))
    sp = P.SEQ_PARAMS
    drop = P.SEQ_DROP | {"kv_ok", "me_mem_ok", "me_clk_en"}
    ins = [x for x in P.SEQ_IN if x[0] not in drop] + \
          [(f"pi_su_{p}", w) for p, _, k, w in P.SU if k in ("in", "dir_ok") and not P._local("su", p)] + \
          [("x_oacc", "24"), ("x_oidle", "1"), ("x_oprog", "16"), ("x_ofin", "1"), ("x_fidx", "NW"), ("x_fval", "32")]
    outs = [x for x in P.SEQ_OUT if x[0] not in drop and not x[0].startswith("kvd_")] + P.SEQ_EXTRA_OUT + \
           [(f"po_su_{p}", w) for p, _, k, w in P.SU if k == "out" and p != "va_q"]
    L = ["`timescale 1ns/1ps",
         "// GENERATED by tools/redesign_qwen/split_ctrl.py emit_seq_su(): die master qfd_seq_su (option 4 SU side).",
         "module ot_qfd_seq_su #(",
         "    parameter integer W = 16, parameter integer G = %d, parameter integer AW = 24, parameter integer NW = %d," % (sp["G"], sp["NW"]),
         "    parameter integer PAW = 12, parameter integer SW = %d, parameter integer LV = %d, parameter integer D = %d," % (sp["SW"], sp["LV"], sp["D"]),
         "    parameter integer SMIN = %d, parameter integer SMAX = %d, parameter integer TCUT = %d," % (sp["SMIN"], sp["SMAX"], sp["TCUT"]),
         "    parameter integer IS = 1, parameter integer OS = 1, parameter integer RT = 4",
         ") (", "    input  wire clk,", "    input  wire rst_n,"]
    L += [f"    input  wire [{w}-1:0] {n}," for n, w in ins]
    L += [f"    output wire [{w}-1:0] {n}," for n, w in outs]
    L[-1] = L[-1].rstrip(",")
    L += [");", "    wire rs;", "    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));"]
    for n, w in ins:
        L.append(f"    wire [{w}-1:0] q_{n};")
        L.append(f"    ot_hdc_delay #(.W({w}), .D(IS){', .RESET(1)' if w == '1' else ''}) u_i_{n} (.clk(clk), .rst_n(rst_n), .d({n}), .q(q_{n}));")
    for n, w in outs:
        L.append(f"    wire [{w}-1:0] b_{n};")
        L.append(f"    ot_hdc_delay #(.W({w}), .D(OS){', .RESET(1)' if w == '1' else ''}) u_o_{n} (.clk(clk), .rst_n(rst_n), .d(b_{n}), .q({n}));")
    L += ["    wire s_su_ready, s_su_idle; wire [15:0] s_su_progress, s_su_progress_rows; reg [NW-1:0] tok_l; wire es_re_w;",
          "    wire core_tok_w;",
          "    ot_qfd_issue_shell #(.RT_ME(0), .RT_SU(RT), .COMP(1)) u_shell (.clk(clk), .rst_n(rs),",
          "        .me_go(1'b0), .su_go(b_po_su_go), .me_en(1'b1), .su_sfu(b_po_su_i_sfu), .me_amax(1'b0),",
          "        .d_me_ready(1'b0), .d_me_idle(1'b0), .d_me_progress(16'd0),",
          "        .d_su_ready(q_pi_su_ready), .d_su_idle(q_pi_su_idle), .d_su_active(q_pi_su_rt_active),",
          "        .d_su_inflight(q_pi_su_rt_inflight), .d_su_progress(q_pi_su_progress), .d_su_rows(q_pi_su_progress_rows),",
          "        .c_me_ready(), .c_me_idle(), .c_me_progress(),",
          "        .c_su_ready(s_su_ready), .c_su_idle(s_su_idle), .c_su_progress(s_su_progress), .c_su_rows(s_su_progress_rows));",
          "    wire core_start, core_done, core_fault_w; wire [NW-1:0] core_tok, core_pos, core_ntok, core_tokw; wire [31:0] core_nval;",
          "    always @(posedge clk) if (es_re_w) tok_l <= core_tokw;",
          "    assign b_su_tok = tok_l;",
          "    wire prog_re; wire [11:0] prog_addr, prog_base; reg [1023:0] prog_q;",
          "    wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;",
          "    reg [1023:0] prog_mem [0:63];", "    reg [63:0] desc_mem [0:7];",
          "    wire [11:0] prog_a = prog_base + prog_addr;",
          "    always @(posedge clk) begin",
          "        if (q_pw_v) prog_mem[q_pw_addr[9:4]][q_pw_addr[3:0]*64 +: 64] <= q_pw_data;",
          "        if (q_dw_v) desc_mem[q_dw_addr] <= q_dw_data;",
          "        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;",
          "        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;",
          "    end",
          "    wire wrom_re_w; assign b_rom_fault = wrom_re_w; assign b_core_fault = core_fault_w;"]
    cpar = ("W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SU_VEC(1), .SW(SW), .LV(LV), .KV_FP8(1), .INT8_WEIGHT(1), "
            ".INT8_SCALE_WCS_BASE(1), .INT8_EMBED(1), .QWEN_FULLSHAPE(%d), .HID(4096), .HALF(64), .HD(128), "
            ".EMB_CODE_LANES(64), .EMB_ADDR_BASE(0), .KV_HBM(1), .KV_VEC_WRITE_BRIDGE(1), .ME_STALL(1), "
            ".ME_IDLE_GATE(1), .SMIN(SMIN), .SMAX(SMAX), .TCUT(TCUT), .FQ_HEAD(1)" % sp["QWEN_FULLSHAPE"])
    cc = [".clk(clk)", ".rst_n(rs)", ".start(core_start)", ".token(core_tokw)", ".pos(core_pos)", ".done(core_done)",
          ".next_token(core_ntok)", ".next_val(core_nval)", ".cycles()", ".fault(core_fault_w)",
          ".prog_re(prog_re)", ".prog_addr(prog_addr)", ".prog_q(prog_q)", ".wrom_re(wrom_re_w)", ".wrom_addr()",
          ".wrom_q('0)", ".int8_wrom_re()", ".int8_wrom_addr()", ".scale_re()", ".scale_gre()", ".scale_addr()",
          ".scale_q('0)", ".embed_code_re()", ".embed_code_addr()", ".embed_code_q('0)", ".embed_scale_re(es_re_w)",
          ".embed_scale_addr()", ".embed_scale_q('0)", ".crom_re()", ".crom_addr()", ".crom_q('0)", ".kv_re()", ".kv_we()",
          ".kv_waddr()", ".kv_wdata()", ".kv_write_drained(q_kv_write_drained)", ".kv_write_flush(b_kv_write_flush)",
          ".va_re()", ".va_addr()", ".va_q('0)", ".vb_re()", ".vb_addr()", ".vb_q('0)", ".vc_re()", ".vc_addr()", ".vc_q('0)",
          ".vw_me_we()", ".vw_me_addr()", ".vw_me_mask()", ".vw_me_data()", ".vw_su_we()", ".vw_su_addr()", ".vw_su_data()",
          ".vw_rd_we()", ".vw_rd_addr()", ".vw_rd_data()", ".vw_mx_we()", ".vw_mx_addr()", ".vw_mx_mask()", ".vw_mx_data()",
          ".me_ov()", ".kvd_v()"] + [f".kvd_{n}()" for n in ("wbase", "ts", "ks", "js", "wcs", "split", "jsh", "tiles", "k",
                                                              "nout", "kindk", "pos")]
    cc += [".kv_ok(1'b0)", ".wrom_su()", ".wd_v()", ".wd_wbase()", ".wd_sbase()", ".wd_tiles()", ".wd_k()", ".wd_nout()",
           ".vx_re()", ".vx_addr()", ".vx_q('0)", ".tgo()", ".tb()", ".xl_d()", ".t_lvl('0)", ".fab_fault(1'b0)",
           ".w_ok(1'b1)", ".emb_ok(1'b1)", ".me_mem_ok(1'b0)", ".me_clk_en()"]
    for u, tab in (("me", P.ME), ("su", P.SU)):
        for p, _, k, w in tab:
            if k == "out":
                cc.append(f".po_{u}_{p}({'b_po_su_' + p if u == 'su' and p != 'va_q' else ''})")
            elif k in ("in", "dir_ok"):
                if u == "me" or P._local(u, p):
                    cc.append(f".pi_{u}_{p}('0)")
                elif P._shell(u, p):
                    cc.append(f".pi_su_{p}(s_su_{p})")
                else:
                    cc.append(f".pi_su_{p}(q_pi_su_{p})")
    cc += [".po_su_asrc_raw(b_su_asrc)", ".x_oacc(q_x_oacc)", ".x_oidle(q_x_oidle)", ".x_oprog(q_x_oprog)",
           ".x_orows(16'd0)", ".x_ofin(q_x_ofin)", ".x_fidx(q_x_fidx)", ".x_fval(q_x_fval)", ".o_fin()", ".o_fidx()", ".o_fval()"]
    L.append(f"    ot_qwen_rom_core_ctrl_x #(.OWN(2), .XW(24), .XMUT(0), .{cpar}) u_ctrl (\n        " + ",\n        ".join(cc) + ");")
    L += ["    ot_qwen_tp_seq_w12 #(.N(D), .NW(NW), .PAW(PAW), .VWA(8), .DAW(6), .FW(512), .TAGW(32),",
          "        .QWEN_FULLSHAPE(%d), .ENABLE_AR256(%d)) u_seq (" % (sp["QWEN_FULLSHAPE"], sp["ENABLE_AR256"]),
          "        .clk(clk), .rst_n(rs), .start(q_h_start), .token(q_tp_token), .pos(q_tp_pos), .done(b_s_done),",
          "        .next_token(b_seq_ntok), .next_val(b_seq_nval), .fault(b_s_fault), .coll_busy(b_coll_busy),",
          "        .core_start(core_start), .core_token(core_tokw), .core_pos(core_pos), .core_done(core_done),",
          "        .core_next_token(core_ntok), .core_next_val(core_nval), .core_fault(core_fault_w), .prog_base(prog_base),",
          "        .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q), .vm_re(b_vm_re), .vm_raddr(b_vm_raddr),",
          "        .vm_rq(q_vm_rq), .vm_we(b_vm_we), .vm_waddr(b_vm_waddr), .vm_wdata(b_vm_wdata), .c_valid(b_c_valid),",
          "        .c_ready(q_c_ready), .c_data(b_c_data), .c_last(b_c_last), .c_mode(b_c_mode), .c_tag(b_c_tag),",
          "        .r_valid(q_r_valid), .r_data(q_r_data), .r_last(q_r_last), .r_rank(q_r_rank), .r_err(q_r_err));",
          "endmodule"]
    return ctrl + "\n" + "\n".join(L).replace("wire core_tok_w;\n", "") + "\n"


if __name__ == "__main__":
    main()
