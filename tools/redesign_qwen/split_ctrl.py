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
CFG = dict(dcu_s=7, duc_s=7, dcu_m=2, duc_m=2, x_m2s=37, x_s2m=44, dstart=37, su_ml=7, xmut=0, xw=24, chl=0, chl_d=2, xreg=0, fqh=0)
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
                     "    parameter integer XMUT = 0,       // negative controls (split_ctrl.py MUT)\n"
                     "    parameter integer XREG = 0,       // 1: the snapshot comparisons registered (o_cnt next vs the snapshot; 1 edge later)", 1)
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
            "    wire osync_c = (o_dif == {XW{1'b0}});      // the other unit accepted exactly its earlier ops\n"
            "    wire opast_c = !osync_c && !o_dif[XW-1];   // ... and the one at NEXT\n"
            "    //: XREG: compare the snapshot with the NEXT edge's count, registered (the snapshot only climbs toward the count while\n"
            "    //: a dependent instruction waits, so a one-edge-old snapshot is conservative)\n"
            "    reg osync_r, opast_r;\n"
            "    wire osync = (XREG != 0) ? osync_r : osync_c;\n"
            "    wire opast = (XREG != 0) ? opast_r : opast_c;\n"
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
            "        else if (skip) o_cnt <= o_cnt + 1'b1;\n"
            "    wire [XW-1:0] o_dif_n = x_oacc - (o_cnt + {{(XW-1){1'b0}}, skip});\n"
            "    always @(posedge clk or negedge rst_n)\n"
            "        if (!rst_n) begin osync_r <= 1'b1; opast_r <= 1'b0; end\n"
            "        else begin osync_r <= (o_dif_n == {XW{1'b0}}); opast_r <= (o_dif_n != {XW{1'b0}}) && !o_dif_n[XW-1]; end\n")
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


def ctrl_icut(t: str) -> str:
    """qwen-1010/a ICUT for the two-controller ctrl_x (the struct-close ICUT of ot_qfd_sp_constants_sequencer_sys,
    ported): the seq_su routes fail post-CTS at -434 .. -870 ps on ONE cone -- the issue: the SU status input stations
    -> issue shell (ready from inflight) -> unit_ready / own_idle -> issue -> load -> the 1,024-b head / decode enables
    (and d_chase_n -> chase compare -> issue -> hq).  ICUT = 1: the whole readiness of the op that holds NEXT after this
    edge is a REGISTER (ready_q), evaluated one edge ahead (the head word's fields when loading) against the status
    predicted after the edge: the own unit issued on this edge reads busy (idle / ready 0, kv_write_drained 0 for an SU
    issue); the other unit's snapshot is taken with the NEXT edge's count (o_dif_n, as XREG) -- the hold rule keeps the
    other unit from accepting a later op while this op reads its status, so its status only improves.  ready_q implies
    the live issue condition (assertion off SYNTHESIS); an issue can be one edge later than live, never earlier.  Op
    order unchanged.  me_en / kv_gate / w_gate stay live.  Needs XREG 1."""
    t = re.sub(r"(    parameter integer XREG = 0,[^\n]*\n)", r"\1    parameter integer ICUT = 0,       // qwen-1010/a: registered readiness (ctrl_icut)\n", t, count=1)
    t = one(t, "    wire issue = (st == S_RUN) && nx_v && own && xdep_ok\n                 && unit_ready && kv_gate && w_gate;\n",
            "    wire issue_live = (st == S_RUN) && nx_v && own && xdep_ok\n                 && unit_ready && kv_gate && w_gate;\n"
            "    reg ready_q;\n"
            "    wire issue = (ICUT == 0) ? issue_live :\n"
            "                 ((st == S_RUN) && nx_v && own && ready_q && (d_unit != 2'd1 || me_en) && kv_gate && w_gate);\n")
    t = one(t, "    wire push = (st == S_RUN) && pend1;\n",
            "    wire push = (st == S_RUN) && pend1;\n"
            "    // ICUT: the readiness of the op at NEXT after this edge, against the status predicted after this edge\n"
            "    wire own_ready = (OWN == 1) ? me_ready : su_ready;\n"
            "    wire own_idle_n = own_idle && !issue;\n"
            "    wire own_ready_n = own_ready && !issue;\n"
            "    wire kd_n = kv_write_drained && !(issue && OWN == 2);\n"
            "    wire osync_n = (o_dif_n == {XW{1'b0}});\n"
            "    wire o_drained_n = osync_n && x_oidle;\n"
            "    function automatic rdy_x(input [1:0] u, input bar, input ch, input chr, input [15:0] chn, input wme, input wsu);\n"
            "        reg chd, wo, wu, xd;\n"
            "        begin\n"
            "            chd = osync_n && ((OWN == 1 && chr) ? (x_orows >= chn) : (x_oprog >= chn));\n"
            "            wo = (OWN == 1) ? wsu : wme;\n"
            "            wu = (OWN == 1) ? wme : wsu;\n"
            "            xd = (XMUT == 1 && OWN == 1) ? 1'b1 :\n"
            "                 (bar ? (own_idle_n && o_drained_n && (!KV_VEC_WRITE_BRIDGE || kd_n)) :\n"
            "                        ((!ch || chd) && (!wu || own_idle_n) && (!wo || o_drained_n)));\n"
            "            rdy_x = (u == OWN[1:0]) && xd &&\n"
            "                    ((OWN == 1) ? own_ready_n : (own_ready_n && (!KV_VEC_WRITE_BRIDGE || (own_idle_n && kd_n))));\n"
            "        end\n"
            "    endfunction\n"
            "    generate if (ICUT != 0) begin : g_icut\n"
            "`ifdef OT_ICUT_MUT_NOPRED\n"
            "        // mutant: the own unit's status NOT predicted (it still reads ready / idle after its own go)\n"
            "        wire r_load = rdy_x(`F(UNIT), `F(BARRIER), `F(CHASE), `F(CHASE_ROWS), `F(CHASE_N), `F(WAIT_ME), `F(WAIT_SU)) ||\n"
            "                      ((`F(UNIT) == OWN[1:0]) && issue);\n"
            "`else\n"
            "        wire r_load = rdy_x(`F(UNIT), `F(BARRIER), `F(CHASE), `F(CHASE_ROWS), `F(CHASE_N), `F(WAIT_ME), `F(WAIT_SU));\n"
            "`endif\n"
            "        wire r_hold = rdy_x(d_unit, d_barrier, d_chase, d_chase_rows, d_chase_n, d_wait_me, d_wait_su);\n"
            "        always @(posedge clk or negedge rst_n)\n"
            "            if (!rst_n) ready_q <= 1'b0;\n"
            "            else ready_q <= load ? r_load : r_hold;\n"
            "`ifndef SYNTHESIS\n"
            "        always @(posedge clk) if (rst_n && issue && !issue_live) begin\n"
            "            $display(\"ICUT_ILLEGAL_ISSUE t=%0t own=%0d\", $time, OWN);\n"
            "            $fatal(1, \"ICUT issue without the live issue condition\");\n"
            "        end\n"
            "`endif\n"
            "    end else begin : g_noicut\n"
            "        always @(posedge clk) ready_q <= 1'b0;\n"
            "    end endgenerate\n")
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
          "    wire [NW-1:0] xm_fidx; wire [31:0] xm_fval; wire [15:0] xl_prog;",
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
            cc += [".x_oacc(xm_acc)", ".x_oidle(xm_idle)", ".x_oprog((CHL != 0) ? xl_prog : xm_prog)", ".x_orows(16'd0)", ".x_ofin(xm_fin)",
                   ".x_fidx(xm_fidx)", ".x_fval(xm_fval)", ".o_fin(s_fin)", ".o_fidx(s_fidx)", ".o_fval(s_fval)"]
        else:
            cc += [".x_oacc(xs_acc)", ".x_oidle(xs_idle)", ".x_oprog(xs_prog)", ".x_orows(xs_rows)", ".x_ofin(1'b1)",
                   ".x_fidx('0)", ".x_fval('0)", ".o_fin(m_fin)", ".o_fidx(m_fidx)", ".o_fval(m_fval)"]
        own_n = 1 if side == "me" else 2
        return (f"    ot_qwen_rom_core_ctrl_x #(.OWN({own_n}), .XW(XW), .XMUT(XMUT), .XREG(XREG), "
                + ", ".join(f".{p}({p})" for p in pnames) + (", .FQ_HEAD(1)" if c.get("fqh") else "")
                + f") u_ctrl{'_me' if side == 'me' else ''} (\n        "
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
          "    // CHL (chase-local): the SU side reads the ME's landed progress where the results land (the vector memory, next to",
          "    // the SU: land_cnt - the op's start mark, the mark crossing early with the snapshot) CHL_D edges after the engine",
          "    // computes it, instead of the X_M2S-station snapshot.  Valid for the chase: the hold rule keeps the engine on the op",
          "    // whose progress a pending SU sample reads.",
          "    ot_hdc_delay #(.W(16), .D(CHL_D), .RESET(1)) u_xl (.clk(clk), .rst_n(rst_n), .d(u_me_progress), .q(xl_prog));",
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
    ap.add_argument("phase", choices=("build", "run", "emit", "emit-tile", "emit-seq-su", "emit-seq-su-boundary",
                                      "emit-seq-su-bi", "emit-tile-i"))
    ap.add_argument("--build", type=Path)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--stages", choices=("L0", "L3", "full"), default="L3")
    ap.add_argument("--threads", type=int, default=16)
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--opt", choices=sorted(OPTS), default="4")
    for k in ("dcu_s", "duc_s", "dcu_m", "duc_m", "x_m2s", "x_s2m", "dstart", "su_ml", "xmut", "chl", "chl_d", "xreg", "fqh"):
        ap.add_argument("--" + k.replace("_", "-"), type=int, default=None)
    ap.add_argument("--max-cycles", type=int, default=0)
    ap.add_argument("--out", type=Path, help="emit: write the generated core here")
    ap.add_argument("--no-psram", action="store_true", help="emit-tile-i: the pre-PSRAM/HQ2 ctlm_i text (pw2 flop store only)")
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
    if a.phase == "emit-seq-su-bi":
        a.out.write_text(emit_seq_su_bi())
        return
    if a.phase == "emit-tile-i":
        a.out.write_text(emit_tt_ctlm_i(psram=not a.no_psram))
        return
    if a.phase in ("emit-seq-su", "emit-seq-su-boundary"):
        a.out.write_text(emit_seq_su(boundary=a.phase == "emit-seq-su-boundary"))
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
    L.append(f"    ot_qwen_rom_core_ctrl_x #(.OWN(1), .XW(XW), .XMUT(0), .XREG(1), .{cpar}) u_ctrl_me (\n        "
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
def emit_seq_su(boundary: bool = False) -> str:
    core = BASE_EMIT(F.EMIT.CORE.read_text())
    ctrl = P.inline_include(ctrl_x(P.emit_ctrl(core)))
    sp = P.SEQ_PARAMS
    drop = P.SEQ_DROP | {"kv_ok", "me_mem_ok", "me_clk_en"}
    ins = [x for x in P.SEQ_IN if x[0] not in drop] + \
          [(f"pi_su_{p}", w) for p, _, k, w in P.SU if k in ("in", "dir_ok") and not P._local("su", p)] + \
          [("x_oacc", "24"), ("x_oidle", "1"), ("x_oprog", "16"), ("x_ofin", "1"), ("x_fidx", "NW"), ("x_fval", "32")]
    outs = [x for x in P.SEQ_OUT if x[0] not in drop and not x[0].startswith("kvd_")] + P.SEQ_EXTRA_OUT + \
           [(f"po_su_{p}", w) for p, _, k, w in P.SU if k == "out" and p != "va_q"]
    if boundary:
        # Mandatory endpoint-owned count: go issued by this master is not acceptance.
        ins += [("pi_su_acc", "24")]
        outs += [("me_start_o", "1"), ("me_token_o", "NW"), ("me_pos_o", "NW"), ("me_prog_base_o", "12"),
                 ("su_acc_o", "24"), ("su_idle_o", "1"), ("su_prog_o", "16"), ("su_rows_o", "16")]
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
    L.append(f"    ot_qwen_rom_core_ctrl_x #(.OWN(2), .XW(24), .XMUT(0), .XREG(1), .{cpar}) u_ctrl (\n        " + ",\n        ".join(cc) + ");")
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
    if boundary:
        # All outputs traverse the same OS pin station. The start is per layer,
        # generated by tp_seq after its collective, never the package h_start.
        L[-1:-1] = [
            "    assign b_me_start_o = core_start;",
            "    assign b_me_token_o = core_tokw;",
            "    assign b_me_pos_o = core_pos;",
            "    assign b_me_prog_base_o = prog_base;",
            "    assign b_su_acc_o = q_pi_su_acc;",
            "    assign b_su_idle_o = q_pi_su_idle;",
            "    assign b_su_prog_o = q_pi_su_progress;",
            "    assign b_su_rows_o = q_pi_su_progress_rows;",
        ]
    text = ctrl + "\n" + "\n".join(L).replace("wire core_tok_w;\n", "") + "\n"
    if boundary:
        text = text.replace("ot_qfd_seq_su #(", "ot_qfd_seq_su_boundary #(")
        text = text.replace("ot_qwen_rom_core_ctrl_x", "ot_qwen_rom_core_ctrl_x_boundary")
        # These represent a coherent control/status record and must reset together.
        for name in ("pi_su_acc", "pi_su_progress", "pi_su_progress_rows", "su_acc_o", "su_prog_o", "su_rows_o"):
            stage = "IS" if name.startswith("pi_") else "OS"
            text = re.sub(r"(\.D\("+stage+r"\))(\) u_[io]_"+name+r"\b)", r"\1, .RESET(1)\2", text)
    return text


TP_SEQ = ROOT / "rtl/rom/ot_qwen_tp_seq_w12.sv"


def tp_seq_vrl(cred: bool = False) -> str:
    """ot_qwen_tp_seq_w12_vrl: the TP sequencer with its vector-memory read latency a parameter (VRL edges vre -> vrq;
    the base assumes 1).  Root cause of the masters' token-chain mismatch (qwen-1010/a 10-10): inside a stationed die
    master the read leaves through the output station and the word returns through the input station, so the base
    queued the word of an earlier read (every all-reduce partial wrong).  The read queue grows to 8 words when VRL > 1
    so the reads in flight keep the stream rate (QD = 2^ceil(log2(VRL + 4))).  VRL 1 is the base."""
    t = TP_SEQ.read_text()
    t = one(t, "module ot_qwen_tp_seq_w12 #(", "module ot_qwen_tp_seq_w12_vrl #(\n    parameter integer VRL = 1,     // vre -> vrq edges")
    # the read queue covers the whole round trip (reads in flight + 4 queued words): one word a cycle at any VRL
    t = one(t, "    localparam integer QD = 4;", "    localparam integer QB = (VRL > 1) ? $clog2(VRL + 4) : 2;   // queue address bits\n"
               "    localparam integer QD = 1 << QB;")
    t = one(t, "    reg [1:0]    q_w, q_r;", "    reg [QB-1:0] q_w, q_r;")
    t = one(t, "    reg [2:0]    q_n;", "    reg [QB:0]   q_n;")
    t = one(t, "    reg          rd_v;", "    reg [VRL-1:0] rd_p;                 // reads in flight, oldest at VRL-1\n    wire          rd_v = rd_p[VRL-1];\n"
               "    integer       rd_i, rd_n;\n    always @(*) begin rd_n = 0; for (rd_i = 0; rd_i < VRL; rd_i = rd_i + 1) rd_n = rd_n + rd_p[rd_i]; end")
    t = one(t, "(q_n + rd_v) < QD;", "(q_n + rd_n) < QD;")
    t = one(t, "rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_v <= 1'b0;", "rd_k <= 0; tx_k <= 0; rx_k <= 0; rd_p <= {VRL{1'b0}};")
    t = one(t, "            rd_v <= rd_go;", "            rd_p <= (VRL > 1) ? {rd_p, rd_go} : rd_go;")
    if not cred:
        return t
    # CRED > 0: the collective port is credit based (ot_rom_oneshot_die_m in_cr): c_ready carries one pulse per freed
    # input-buffer slot; the sender holds CRED credits (the receiver's buffer, >= the round trip through the stations)
    t = one(t, "    parameter integer VRL = 1,     // vre -> vrq edges",
            "    parameter integer VRL = 1,     // vre -> vrq edges\n    parameter integer CRED = 0,    // 0: c_ready = ready (base); > 0: c_ready = credit return pulse, CRED credits")
    t = one(t, "    assign c_valid = (st == S_COLL) && (q_n != 0);",
            "    reg [7:0] c_cred;   // credit mode: a word leaves only with a credit (valid = send)\n"
            "    assign c_valid = (st == S_COLL) && (q_n != 0) && (CRED == 0 || c_cred != 8'd0);")
    t = one(t, "    wire   c_fire  = c_valid && c_ready;",
            "    wire   c_fire  = c_valid && ((CRED == 0) ? c_ready : 1'b1);\n"
            "    always @(posedge clk or negedge rst_n)\n"
            "        if (!rst_n) c_cred <= 8'(CRED);\n"
            "        else if (CRED != 0) c_cred <= c_cred - (c_fire ? 8'd1 : 8'd0) + (c_ready ? 8'd1 : 8'd0);")
    return t


def ctrl_skipmux(t: str) -> str:
    """qwen-1010/a: the next-edge snapshot comparison without skip in its arithmetic (seq_su_bi_b-e261d6e89 post-CTS -468 on
    d_wait_su -> odep -> skip -> 24-b o_cnt + skip -> subtract -> compare -> ready_q / osync_r).  Both candidates (count
    and count + 1, the latter a register kept in step) are compared in parallel from registers; skip only selects.
    Same values on every edge."""
    t = one(t, "        else if (skip) o_cnt <= o_cnt + 1'b1;\n",
            "        else if (skip) o_cnt <= o_cnt + 1'b1;\n"
            "    reg [XW-1:0] o_cnt1;                       // o_cnt + 1, kept in step\n"
            "    always @(posedge clk or negedge rst_n)\n"
            "        if (!rst_n) o_cnt1 <= {{(XW-1){1'b0}}, 1'b1};\n"
            "        else if (skip) o_cnt1 <= o_cnt1 + 1'b1;\n"
            "    wire [XW-1:0] o_dif0 = x_oacc - o_cnt, o_dif1 = x_oacc - o_cnt1;\n"
            "    wire o_eq0 = (o_dif0 == {XW{1'b0}}), o_eq1 = (o_dif1 == {XW{1'b0}});\n"
            "    wire o_pa0 = !o_eq0 && !o_dif0[XW-1], o_pa1 = !o_eq1 && !o_dif1[XW-1];\n")
    t = one(t, "        else begin osync_r <= (o_dif_n == {XW{1'b0}}); opast_r <= (o_dif_n != {XW{1'b0}}) && !o_dif_n[XW-1]; end\n",
            "        else begin osync_r <= skip ? o_eq1 : o_eq0; opast_r <= skip ? o_pa1 : o_pa0; end\n")
    t = one(t, "    wire osync_n = (o_dif_n == {XW{1'b0}});", "    wire osync_n = skip ? o_eq1 : o_eq0;")
    return t


def ctrl_prl(t: str) -> str:
    """qwen-1010/a PRL: program read latency a parameter (prog_re -> prog_q edges; the base is 1).  The masters' program
    store is 64 x 1,024 configuration flops: seq_su_bi_b post-CTS -476 ps on prog_base -> add -> 64:1 x 1,024 read mux
    -> prog_q.  PRL 2 lets the master register the read address (the fetch runs ahead of issue, so a segment start pays
    one edge)."""
    t = re.sub(r"(    parameter integer ICUT = 0,[^\n]*\n)", r"\1    parameter integer PRL = 1,        // qwen-1010/a: program read latency (ctrl_prl)\n", t, count=1)
    t = one(t, "    reg        pend1;                     // a program read whose word arrives this cycle\n",
            "    reg        pend1;                     // a program read whose word arrives this cycle\n    reg        pend2;                     // PRL 2: ... the cycle after\n")
    t = one(t, "    wire push = (st == S_RUN) && pend1;", "    wire push = (st == S_RUN) && ((PRL > 1) ? pend2 : pend1);")
    t = t.replace("pend1 <= 1'b0;", "pend1 <= 1'b0; pend2 <= 1'b0;")
    t = one(t, "            pend1 <= prog_re && (st != S_IDLE);\n",
            "            pend1 <= prog_re && (st != S_IDLE);\n            pend2 <= (PRL > 1) && pend1 && (st != S_IDLE);\n")
    t = one(t, "+ prog_re + pend1 < NFQ)", "+ prog_re + pend1 + ((PRL > 1) ? pend2 : 1'b0) < NFQ)")
    return t


def master_prl(t: str, base: str) -> str:
    """the master's program store read with a registered address (PRL 2)"""
    t = one(t, f"    wire [11:0] prog_a = {base} + prog_addr;\n",
            f"    wire [11:0] prog_a = {base} + prog_addr;\n"
            "    reg prog_re_r; reg [11:0] prog_a_r;                 // PRL 2: the read address registered\n"
            "    always @(posedge clk or negedge rs) if (!rs) prog_re_r <= 1'b0; else prog_re_r <= prog_re;\n"
            "    always @(posedge clk) prog_a_r <= prog_a;\n")
    t = one(t, "        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;\n",
            "        if (prog_re_r) prog_q <= (prog_a_r < 64) ? prog_mem[prog_a_r[5:0]] : 1024'd0;\n")
    return t


def master_pw2(t: str) -> str:
    """qwen-1010/a: the program-store write with registered one-hot row / word selects (seq_su_bi_b-955329f22 routed: the
    q_pw_addr -> 64 x 16 decode -> 65,536 write enables path); the write lands one edge later (configuration time)"""
    t = one(t, "    always @(posedge clk) prog_a_r <= prog_a;\n",
            "    always @(posedge clk) prog_a_r <= prog_a;\n    reg [63:0] pw_row2; reg [15:0] pw_word2; reg [63:0] pw_d2; integer pw_r, pw_w;\n")
    return one(t, "        if (q_pw_v) prog_mem[q_pw_addr[9:4]][q_pw_addr[3:0]*64 +: 64] <= q_pw_data;\n",
               "        if (pw_row2 != 64'd0) for (pw_r = 0; pw_r < 64; pw_r = pw_r + 1) for (pw_w = 0; pw_w < 16; pw_w = pw_w + 1)\n"
               "            if (pw_row2[pw_r] && pw_word2[pw_w]) prog_mem[pw_r][pw_w*64 +: 64] <= pw_d2;\n"
               "    end\n"
               "    // program writes: one-hot row / word selects registered one edge before the store (65,536 enables)\n"
               "    always @(posedge clk) begin\n"
               "        pw_row2 <= q_pw_v ? (64'd1 << q_pw_addr[9:4]) : 64'd0;\n"
               "        pw_word2 <= 16'd1 << q_pw_addr[3:0];\n"
               "        pw_d2 <= q_pw_data;\n")


KVD_FIELDS = [("v", "1"), ("wbase", "AW"), ("ts", "AW"), ("ks", "AW"), ("js", "AW"), ("wcs", "AW"), ("split", "4"),
              ("jsh", "3"), ("tiles", "NW"), ("k", "NW"), ("nout", "NW"), ("kindk", "1"), ("pos", "NW")]


def seq_kvd_out(t: str) -> str:
    """qwen-1010/a: the KV-die launch descriptor (kvd_*) leaves seq_su, not the control tile: the SU-side controller decodes
    every instruction too, and seq_su sits 25 relay stages from the link end (the q word's path) against the control tile's
    41 -- so the KV-die step starts no later than the bench's q / CTL assumption.  Out through the OS pin stations."""
    t = one(t, "    output wire [16-1:0] su_rows_o\n);",
            "    output wire [16-1:0] su_rows_o,\n" +
            ",\n".join(f"    output wire [{w}-1:0] kvd_{n}" for n, w in KVD_FIELDS) + "\n);")
    st = []
    for n, w in KVD_FIELDS:
        st.append(f"    wire [{w}-1:0] b_kvd_{n};")
        st.append(f"    ot_hdc_delay #(.W({w}), .D(OS){', .RESET(1)' if w == '1' else ''}) u_o_kvd_{n} (.clk(clk), .rst_n(rs), "
                  f".d(b_kvd_{n}), .q(kvd_{n}));")
    t = one(t, "    wire [16-1:0] b_su_rows_o;\n", "    wire [16-1:0] b_su_rows_o;\n" + "\n".join(st) + "\n")
    t = one(t, "        .kvd_v(),\n", "        .kvd_v(b_kvd_v),\n")
    for n, _ in KVD_FIELDS[1:]:
        t = one(t, f"        .kvd_{n}(),\n", f"        .kvd_{n}(b_kvd_{n}),\n")
    return t


STAGE_GATE = """
// qwen-1010/a: the stage start waits for the SU-local constant buffer (ot_qfd_su_cbuf_g st_rdy / st_rdy_stage): a stage
// (one layer program, or HEAD) starts only when the buffer reports that stage resident.  The prefetcher fills stage s + 1
// during stage s, so the wait is normally only at the token's first stage.  MUT 1 (NOWAIT): starts without the buffer.
module ot_qfd_stage_gate #(parameter integer SW_ = 6, parameter integer NW = 18, parameter integer MUT = 0) (
    input  wire clk, input wire rst_n,
    input  wire h_start, input wire [SW_-1:0] stage, input wire [NW-1:0] token, input wire [NW-1:0] pos,
    input  wire st_rdy, input wire [SW_-1:0] st_rdy_stage,
    output wire go, output reg [NW-1:0] go_token, output reg [NW-1:0] go_pos,
    output reg [SW_-1:0] cur_stage, output wire tok_start
);
    reg pend;
    assign go = pend && !h_start && ((MUT != 0) || (st_rdy && st_rdy_stage == cur_stage));
    assign tok_start = h_start && (stage == {SW_{1'b0}});
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pend <= 1'b0; cur_stage <= {SW_{1'b0}}; end
        else if (h_start) begin pend <= 1'b1; cur_stage <= stage; end
        else if (go) pend <= 1'b0;
    always @(posedge clk) if (h_start) begin go_token <= token; go_pos <= pos; end
endmodule
"""


def seq_stage_gate(t: str) -> str:
    """qwen-1010/a: wire the SU-local constant buffer's readiness into the seq_su stage start (owner rule: every path)"""
    t = one(t, "    input  wire [1-1:0] h_start,\n",
            "    input  wire [1-1:0] h_start,\n    input  wire [5:0] stage_in,           // the stage (layer / HEAD) this start runs\n"
            "    input  wire [1-1:0] cb_st_rdy,        // constant buffer: stage cb_st_rdy_stage resident\n"
            "    input  wire [5:0] cb_st_rdy_stage,\n"
            "    output wire [5:0] cb_stage,           // to every constant-buffer group: the stage the SU runs\n"
            "    output wire [1-1:0] cb_tok_start,\n    output wire [NW-1:0] cb_tpos,\n")
    gate = ("    wire [5:0] q_stage_in, q_cb_st_rdy_stage; wire q_cb_st_rdy;\n"
            "    ot_hdc_delay #(.W(12), .D(IS)) u_i_cbs (.clk(clk), .rst_n(rs), .d({stage_in, cb_st_rdy_stage}), .q({q_stage_in, q_cb_st_rdy_stage}));\n"
            "    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_i_cbr (.clk(clk), .rst_n(rs), .d(cb_st_rdy), .q(q_cb_st_rdy));\n"
            "    wire sg_go, sg_tok; wire [NW-1:0] sg_token, sg_pos; wire [5:0] sg_stage;\n"
            "    ot_qfd_stage_gate #(.SW_(6), .NW(NW)) u_sgate (.clk(clk), .rst_n(rs), .h_start(q_h_start), .stage(q_stage_in),\n"
            "        .token(q_tp_token), .pos(q_tp_pos), .st_rdy(q_cb_st_rdy), .st_rdy_stage(q_cb_st_rdy_stage), .go(sg_go),\n"
            "        .go_token(sg_token), .go_pos(sg_pos), .cur_stage(sg_stage), .tok_start(sg_tok));\n"
            "    ot_hdc_delay #(.W(6 + 1 + NW), .D(OS)) u_o_cb (.clk(clk), .rst_n(rs), .d({sg_stage, sg_tok, q_tp_pos}), .q({cb_stage, cb_tok_start, cb_tpos}));\n")
    t = one(t, "        .clk(clk), .rst_n(rs), .start(q_h_start), .token(q_tp_token), .pos(q_tp_pos), .done(b_s_done),",
            "        .clk(clk), .rst_n(rs), .start(sg_go), .token(sg_token), .pos(sg_pos), .done(b_s_done),")
    i = t.index("    ot_qwen_tp_seq_w12 #(.N(D),")
    return t[:i] + gate + t[i:] + STAGE_GATE


def ctrl_hq2(t: str) -> str:
    """hardcore-1010 fe-h HQ2: the controller's FIFO head as two words with a register-only fill enable (FQ_HEAD 2; 3 = the
    bench negative control, a third fill overwrites an unread head word).  seq_su fba TT -131 / fbb post-CTS -537 on
    st -> skip/issue -> load -> hq_fill -> the 1,024-b hq enable; fill now depends on fq_n / hc only.  Same words, same
    edges as FQ_HEAD 1 (lockstep benches)."""
    t = one(t, "    parameter integer FQ_HEAD = 0,   // safe-qwen S-A6: registered FIFO head word (decode reads a flop)\n",
            "    parameter integer FQ_HEAD = 0,   // safe-qwen S-A6: registered FIFO head word (decode reads a flop)\n"
            "                                     // 2 (hardcore-1010 fe-h): two head words written in turn while fewer than 2 are held\n"
            "                                     // (fill enable from registers only: fq_n, hc), decode reads hq / hq1 by a registered\n"
            "                                     // pointer.  Same words, same edges as FQ_HEAD 1 (lockstep bench)\n")
    t = one(t, "    wire [INSTR_BITS-1:0] ir = (FQ_HEAD != 0) ? hq : fq[fq_rd]; // FIFO head: the word decode reads\n",
            "    reg  [INSTR_BITS-1:0] hq1;           // FQ_HEAD 2: second head word\n"
            "    reg                   h_rd, h_wr;    // FQ_HEAD 2: head read / write pointers\n"
            "    reg  [1:0]            hc;            // FQ_HEAD 2: head words held\n"
            "    wire                  hv = (FQ_HEAD >= 2) ? (hc != 2'd0) : hq_v;\n"
            "    wire [INSTR_BITS-1:0] ir = (FQ_HEAD >= 2) ? (h_rd ? hq1 : hq) : (FQ_HEAD != 0) ? hq : fq[fq_rd]; // FIFO head: the word decode reads\n")
    t = one(t, "((FQ_HEAD != 0) ? hq_v : (fq_n != 0)) && (!nx_v || issue || skip);",
            "((FQ_HEAD != 0) ? hv : (fq_n != 0)) && (!nx_v || issue || skip);")
    t = one(t, "    wire hq_fill = (FQ_HEAD != 0) && (st == S_RUN) && (fq_n != 0) && (!hq_v || load);\n",
            "    wire hq_fill = (FQ_HEAD >= 2) ? ((st == S_RUN) && (fq_n != 0) && (hc != ((FQ_HEAD == 3) ? 2'd3 : 2'd2))) :\n"
            "                  (FQ_HEAD != 0) && (st == S_RUN) && (fq_n != 0) && (!hq_v || load);\n")
    t = one(t, "            fq_rd <= 0; fq_wr <= 0; fq_n <= 0; nx_v <= 1'b0; hq_v <= 1'b0;\n",
            "            fq_rd <= 0; fq_wr <= 0; fq_n <= 0; nx_v <= 1'b0; hq_v <= 1'b0; hc <= 2'd0; h_rd <= 1'b0; h_wr <= 1'b0;\n")
    t = one(t, "pend1 <= 1'b0; pend2 <= 1'b0; hq_v <= 1'b0;\n",
            "pend1 <= 1'b0; pend2 <= 1'b0; hq_v <= 1'b0;\n                    hc <= 2'd0; h_rd <= 1'b0; h_wr <= 1'b0;\n")
    t = one(t, "{1'b0, fq_n} + ((FQ_HEAD != 0) ? hq_v : 1'b0) + prog_re",
            "{1'b0, fq_n} + ((FQ_HEAD >= 2) ? hc : (FQ_HEAD != 0) ? {1'b0, hq_v} : 2'd0) + prog_re")
    t = one(t, "                    if (hq_fill) begin hq <= fq[fq_rd]; hq_v <= 1'b1; end\n",
            "                    if (FQ_HEAD >= 2) begin\n"
            "                        if (hq_fill && !h_wr) hq <= fq[fq_rd];\n"
            "                        if (hq_fill && h_wr) hq1 <= fq[fq_rd];\n"
            "                        if (hq_fill) h_wr <= !h_wr;\n"
            "                        if (load) h_rd <= !h_rd;\n"
            "                        hc <= hc + (hq_fill ? 2'd1 : 2'd0) - (load ? 2'd1 : 2'd0);\n"
            "                    end else if (hq_fill) begin hq <= fq[fq_rd]; hq_v <= 1'b1; end\n")
    return t


def ctrl_icut_nonfatal(t: str) -> str:
    """OT_ICUT_NONFATAL (sim define, lockstep benches): count the ICUT illegal-issue check instead of stopping (the real ME
    unit's readiness falls without a go under random programs; the check fires identically in both lockstep copies)"""
    return one(t, "            $fatal(1, \"ICUT issue without the live issue condition\");\n",
               "`ifndef OT_ICUT_NONFATAL\n            $fatal(1, \"ICUT issue without the live issue condition\");\n`endif\n")


SRAM_PM = ("            ot_sram_1r1w_64x512_m1_r2c2 u_pm (.clk(clk), .r_ce_in(p_rce), .r_addr_in(p_ra), .rd_out(p_rd[512*m +: 512]),\n"
           "                .w_ce_in(w_ce), .w_addr_in({wa}), .wd_in({{8{{{wd}}}}}), .w_mask_in(w_mask),\n"
           "                .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));\n")
PSRAM_RD = ("        reg rng_r;                                       // the read word is inside the store (else prog_q = 0)\n"
            "        always @(posedge clk) rng_r <= (PMUT != 0) ? (prog_a_r < 64) : (prog_a < 64);\n"
            "        wire [1023:0] p_rd;\n"
            "        wire p_rce = (PMUT != 0) ? prog_re_r : prog_re;\n"
            "        wire [5:0] p_ra = (PMUT != 0) ? prog_a_r[5:0] : prog_a[5:0];\n")
PSRAM_Q = ("        if (PMUT != 0) begin : g_pmut\n"
           "            reg pre_rr;\n"
           "            always @(posedge clk or negedge rs) if (!rs) pre_rr <= 1'b0; else pre_rr <= prog_re_r;\n"
           "            always @(posedge clk) if (pre_rr) prog_q <= rng_r ? p_rd : 1024'd0;\n"
           "        end else begin : g_pq\n"
           "            always @(posedge clk) if (prog_re_r) prog_q <= rng_r ? p_rd : 1024'd0;\n"
           "        end\n")
PW2_BODY = ("        if (pw_row2 != 64'd0) for (pw_r = 0; pw_r < 64; pw_r = pw_r + 1) for (pw_w = 0; pw_w < 16; pw_w = pw_w + 1)\n"
            "            if (pw_row2[pw_r] && pw_word2[pw_w]) prog_mem[pw_r][pw_w*64 +: 64] <= pw_d2;\n"
            "    end\n"
            "    // program writes: one-hot row / word selects registered one edge before the store (65,536 enables)\n"
            "    always @(posedge clk) begin\n"
            "        pw_row2 <= q_pw_v ? (64'd1 << q_pw_addr[9:4]) : 64'd0;\n"
            "        pw_word2 <= 16'd1 << q_pw_addr[3:0];\n"
            "        pw_d2 <= q_pw_data;\n")


def tile_psram(t: str) -> str:
    """fe-push-qwen-1010 F1 (ctlm_i PSRAM + HQ2, route top ot_qfd_tt_ctlm_i_fp): applied to the master_pw2 tile.  PSRAM 1:
    the 64 x 1,024 program store as two ot_sram_1r1w_64x512_m1_r2c2 macros, every macro write pin from a register (valid,
    row, bank, one-hot 64-bit slice; one edge after q_pw_v like the pw2 selects), read issued at prog_re with the
    unregistered address and captured in prog_q one edge later (= PRL 2, 0 cycles).  PSRAM 0 = the pw2 flop store
    unchanged.  HQ2 selects FQ_HEAD 2 (3 at HQ2 = 2) on the ME-side controller.  Defaults (0 / 0 / 0) = the old tile."""
    t = one(t, "    parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1\n) (",
            "    parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1,\n"
            "    // PSRAM = 1 (fe-push-qwen-1010, port of the seq_su_bi hardcore-1010 PSRAM; 0 = unchanged): the 64 x 1,024 program\n"
            "    // store is two ot_sram_1r1w_64x512_m1_r2c2 macros (bit-masked 64-bit writes) instead of 65,536 flops; the read is\n"
            "    // issued at the prog_re edge with the unregistered address, the macro output captured in prog_q one edge later = the\n"
            "    // PRL 2 timing of the flop store (0 cycles).  Writes come from registered macro pins (valid, row, bank, one-hot\n"
            "    // 64-bit slice) one edge after q_pw_v, as the flop store's registered selects.  Contract: the store is written\n"
            "    // only while no program read of the same word is in flight (boot load; read-before-write macro).\n"
            "    // PMUT = 1: bench negative control (the read issued one edge late, with the registered address).\n"
            "    // HQ2 = 1: the controller's FIFO head as two words with a register-only fill enable (FQ_HEAD 2; seq_su fea/feb\n"
            "    // f3e3d6b6f: feb TT +95.26 after fbb post-CTS -537 on st -> load -> hq_fill -> 1,024-b hq enable).\n"
            "    // HQ2 = 2: bench negative control (FQ_HEAD 3: a third fill overwrites an unread head word).\n"
            "    parameter integer PSRAM = 0, parameter integer PMUT = 0, parameter integer HQ2 = 0\n) (")
    t = one(t, "    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q; reg [1023:0] prog_mem [0:63];\n",
            "    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q;\n")
    t = one(t, "    always @(posedge clk) prog_a_r <= prog_a;\n    reg [63:0] pw_row2; reg [15:0] pw_word2; reg [63:0] pw_d2; integer pw_r, pw_w;\n"
            "    always @(posedge clk) begin\n" + PW2_BODY +
            "        if (prog_re_r) prog_q <= (prog_a_r < 64) ? prog_mem[prog_a_r[5:0]] : 1024'd0;\n    end\n",
            "    always @(posedge clk) prog_a_r <= prog_a;\n"
            "    generate if (PSRAM != 0) begin : g_psram\n"
            "        //: the program store as two 64 x 512 SRAM macros; every macro write pin from a register (no decode at the pins)\n"
            "        reg pw_v2, pw_b2; reg [5:0] pw_row2; reg [7:0] pw_sl2; reg [63:0] pw_d2;\n"
            "        always @(posedge clk or negedge rs) if (!rs) pw_v2 <= 1'b0; else pw_v2 <= q_pw_v;\n"
            "        always @(posedge clk) begin\n"
            "            pw_b2 <= q_pw_addr[3]; pw_row2 <= q_pw_addr[9:4]; pw_sl2 <= 8'd1 << q_pw_addr[2:0]; pw_d2 <= q_pw_data;\n"
            "        end\n" + PSRAM_RD +
            "        wire [511:0] w_mask;\n"
            "        genvar m, s;\n"
            "        for (s = 0; s < 8; s = s + 1) begin : g_s\n"
            "            assign w_mask[64*s +: 64] = {64{pw_sl2[s]}};\n"
            "        end\n"
            "        for (m = 0; m < 2; m = m + 1) begin : g_m\n"
            "            wire w_ce = pw_v2 && (pw_b2 == ((m != 0) ? 1'b1 : 1'b0));\n"
            + SRAM_PM.format(wa="pw_row2", wd="pw_d2") +
            "        end\n" + PSRAM_Q +
            "    end else begin : g_pflop\n"
            "        reg [1023:0] prog_mem [0:63];\n"
            "        reg [63:0] pw_row2; reg [15:0] pw_word2; reg [63:0] pw_d2; integer pw_r, pw_w;\n"
            "        always @(posedge clk) begin\n"
            + "".join("    " + ln + "\n" for ln in PW2_BODY.splitlines()) +
            "            if (prog_re_r) prog_q <= (prog_a_r < 64) ? prog_mem[prog_a_r[5:0]] : 1024'd0;\n"
            "        end\n"
            "    end endgenerate\n")
    t = one(t, ".TCUT(7), .FQ_HEAD(1)) u_ctrl_me (", ".TCUT(7), .FQ_HEAD((HQ2 >= 2) ? 3 : (HQ2 != 0) ? 2 : 1)) u_ctrl_me (")
    return t


def seq_psram(t: str) -> str:
    """hardcore-1010 D fallback (2026-10-10) PSRAM + fe-h HQ2 on seq_su_bi, applied to the master_pw2 text (the routed
    seq_su fea/feb-f3e3d6b6f closures).  PSRAM 1: the program store as two ot_sram_1r1w_64x512_m1_r2c2 macros (write pins
    straight from q_pw_*, as routed); PSRAM 0: the pw2 flop store.  HQ2 selects FQ_HEAD 2 (3 at HQ2 = 2) on u_ctrl."""
    t = one(t, "    parameter integer RLY = 0, parameter integer CRED = 0\n) (",
            "    parameter integer RLY = 0, parameter integer CRED = 0,\n"
            "    // PSRAM = 1 (hardcore-1010 D fallback, 2026-10-10; 0 = unchanged): the 64 x 1,024 program store is two\n"
            "    // ot_sram_1r1w_64x512_m1_r2c2 macros (64 x 512, bit-masked 64-bit writes) instead of 65,536 flops; the read is\n"
            "    // issued at the prog_re edge with the unregistered address (12-bit add -> macro address pins), the macro output is\n"
            "    // captured in prog_q one edge later = the PRL 2 timing of the flop store (0 cycles).  Contract: the store is\n"
            "    // written only while no program read of the same word is in flight (boot load; read-before-write macro).\n"
            "    // PMUT = 1: bench negative control (the read issued one edge late, with the registered address).\n"
            "    parameter integer PSRAM = 0, parameter integer PMUT = 0,\n"
            "    // HQ2 = 1 (hardcore-1010 fe-h): the controller's FIFO head as two words with a register-only fill enable (FQ_HEAD 2):\n"
            "    // fba-0ef4d7781 TT -131 / fbb post-CTS -537 on u_ctrl.st -> skip/issue -> load -> hq_fill -> hq[1023:0] enable (26 lv)\n"
            "    // HQ2 = 2: bench negative control (FQ_HEAD 3: a third fill overwrites an unread head word)\n"
            "    parameter integer HQ2 = 0\n) (")
    t = one(t, "    reg [1023:0] prog_mem [0:63];\n    reg [63:0] desc_mem [0:7];\n",
            "    reg [1023:0] prog_mem [0:63];                       // PSRAM 0 (the flop store)\n    reg [63:0] desc_mem [0:7];\n")
    t = one(t, "    always @(posedge clk) begin\n" + PW2_BODY +
            "        if (q_dw_v) desc_mem[q_dw_addr] <= q_dw_data;\n"
            "        if (prog_re_r) prog_q <= (prog_a_r < 64) ? prog_mem[prog_a_r[5:0]] : 1024'd0;\n"
            "        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;\n    end\n",
            "    always @(posedge clk) begin\n"
            "        if (q_dw_v) desc_mem[q_dw_addr] <= q_dw_data;\n"
            "        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;\n    end\n"
            "    generate if (PSRAM != 0) begin : g_psram\n"
            "        //: the program store as two 64 x 512 SRAM macros (bit-masked 64-bit slice writes); prog_q = the captured output\n"
            + PSRAM_RD +
            "        genvar m;\n"
            "        for (m = 0; m < 2; m = m + 1) begin : g_m\n"
            "            wire w_ce = q_pw_v && (q_pw_addr[3] == ((m != 0) ? 1'b1 : 1'b0));\n"
            "            wire [511:0] w_mask = {448'd0, {64{1'b1}}} << (64 * q_pw_addr[2:0]);\n"
            + SRAM_PM.format(wa="q_pw_addr[9:4]", wd="q_pw_data") +
            "        end\n" + PSRAM_Q +
            "    end else begin : g_pflop\n"
            "        always @(posedge clk) begin\n"
            + "".join("    " + ln + "\n" for ln in PW2_BODY.splitlines()) +
            "            if (prog_re_r) prog_q <= (prog_a_r < 64) ? prog_mem[prog_a_r[5:0]] : 1024'd0;\n"
            "        end\n"
            "    end endgenerate\n")
    t = one(t, ".TCUT(TCUT), .FQ_HEAD(1)) u_ctrl (", ".TCUT(TCUT), .FQ_HEAD((HQ2 >= 2) ? 3 : (HQ2 != 0) ? 2 : 1)) u_ctrl (")
    return t


# qwen-1010/a successors with ICUT (ctrl_icut) and locally registered station resets; the released / boundary masters
# above stay byte-identical.
def emit_seq_su_bi() -> str:
    """ot_qfd_seq_su_bi = ot_qfd_seq_su_boundary + ICUT + every pin station reset from the registered tile reset rs
    (the routes' rst_n -> u_i_* / u_o_* recovery failures, -52 .. -352 ps)"""
    t = ctrl_skipmux(ctrl_prl(ctrl_icut(emit_seq_su(boundary=True))))
    t = t.replace("ot_qwen_rom_core_ctrl_x_boundary", "ot_qwen_rom_core_ctrl_x_bi")
    t = seq_stage_gate(seq_kvd_out(master_pw2(master_prl(ctrl_hq2(t), "prog_base"))))
    t = one(t, "module ot_qfd_seq_su_boundary #(", "module ot_qfd_seq_su_bi #(")
    t = one(t, ".XMUT(0), .XREG(1), .W(W)", ".XMUT(0), .XREG(1), .ICUT(1), .PRL(2), .W(W)")
    t = re.sub(r"(ot_hdc_delay #\([^;]*?\) u_[io]_\w+ \(\.clk\(clk\), )\.rst_n\(rst_n\)", r"\1.rst_n(rs)", t)
    # the VM read leaves through OS and returns through IS (+ the memory's registered read): VRL = IS + OS + 1
    t = one(t, "    ot_qwen_tp_seq_w12 #(.N(D),", "    ot_qwen_tp_seq_w12_vrl #(.VRL(IS + OS + 1 + 2 * RLY), .CRED(CRED), .N(D),")
    # RLY: die relays each way to the VM; CRED: 0 = collective ready/valid (the token vehicle's model), > 0 = credit port
    # (ot_rom_oneshot_die_m in_cr, its input buffer IB >= CRED >= the round trip through the stations)
    t = one(t, "    parameter integer IS = 1, parameter integer OS = 1, parameter integer RT = 4",
            "    parameter integer IS = 1, parameter integer OS = 1, parameter integer RT = 4,\n"
            "    parameter integer RLY = 0, parameter integer CRED = 0")
    return seq_psram(t) + "\n" + tp_seq_vrl(cred=True)


def emit_tt_ctlm_i(psram: bool = True) -> str:
    """ot_qfd_tt_ctlm_i = ot_qfd_tt_ctlm + ICUT on its ME-side controller (+ HQ2 FQ_HEAD 2/3 in the controller); psram: the
    PSRAM / PMUT / HQ2 tile parameters (fe-push-qwen-1010 F1, defaults 0 = the flop-store tile); psram=False (--no-psram)
    = the pre-F1 tile text"""
    t = ctrl_skipmux(ctrl_prl(ctrl_icut(emit_tt_ctlm())))
    t = t.replace("ot_qwen_rom_core_ctrl_x", "ot_qwen_rom_core_ctrl_x_i")
    if psram:
        t = ctrl_icut_nonfatal(ctrl_hq2(t))
    t = master_pw2(master_prl(t, "q_prog_base"))
    if psram:
        t = tile_psram(t)
    t = one(t, "module ot_qfd_tt_ctlm #(", "module ot_qfd_tt_ctlm_i #(")
    t = one(t, ".XMUT(0), .XREG(1), .W(16)", ".XMUT(0), .XREG(1), .ICUT(1), .PRL(2), .W(16)")
    return t


if __name__ == "__main__":
    main()
