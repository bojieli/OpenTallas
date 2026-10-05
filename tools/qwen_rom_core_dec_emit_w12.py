#!/usr/bin/env python3
"""Emit the Qwen ROM decode core with the zero-latency decode restructure DEC_LA (default-off).

Applied to the output of tools/qwen_rom_verify_core_emit_w12.emit (itself over tools/qwen_rom_rt_core_emit_w12.emit;
both and the pinned rtl/hdc/ot_hdc_core_vector_weight.sv untouched).  Adds

  parameter DEC_LA = 0   0: the core is unchanged (every DEC_LA term is dead).
                         1: the same decode, cycle for cycle, with its timing restructured:

  * PREDECODE AT PUSH.  The program word is decoded when it enters the 4-entry fetch FIFO (from prog_q, the
    program ROM's registered output) instead of when it leaves it: the FIFO holds the decoded, DYN-adjusted fields
    (fqd_<field>), and LOAD only moves the head entry into the NEXT registers.  The decode is a pure function of
    the word, the token and the position, so the fields are identical; the FIFO's fq_rd mux, the load enable and
    the decode arithmetic are no longer one path.
  * REGISTERED TABLES, NO ADDED CYCLE.  The DYN tables (and VPOS's per-position tables) and every DYN_TTILES
    round count (one per position offset and split: (pos+o) >> (WT+GT-s) / ODD + 1, the ot_hdc_dyn_ttiles
    function) are computed by a four-stage pipeline that runs from pos_r / tok_r.  start loads pos_r at edge E0;
    the first program word can be pushed no earlier than E4 (S_DYN at E1, first fetch at E2, ROM data at E3), so
    the tables registered at E1..E3 are settled before their first use: the divider leaves the decode path and
    no cycle is added.
  * ISSUE.  The chase test (progress >= chase_n) is three kept log-depth comparators (su_rows, su_progress,
    me_progress) selected by the decoded unit, instead of a mux in front of one ripple comparator.

The fault term dyn_tiles_bad_instruction, kvd_v and wd_v read the predecoded bits of the head entry.
Records: results/rtl/qwen_core_decode_closure_20261004.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import qwen_rom_rt_core_emit_w12 as E
import qwen_rom_verify_core_emit_w12 as V

DEC_START = "    // Decode: every base and count may add one DYN value.\n    always @(posedge clk) if (load) begin\n"
DEC_END = "    end\n    `undef F\n"
DECL_START = "    // decoded, DYN-adjusted fields\n"
DECL_END = "\n    wire [15:0] su_progress"
# NEXT fields the issue logic reads: kept as registers loaded at LOAD; the rest are read from the FIFO entry.
CTRL = {"d_unit", "d_barrier", "d_chase", "d_chase_n", "d_wait_me", "d_wait_su", "d_chase_rows", "me_wsrc", "a_src"}


def _sub1(pattern: str, repl: str, s: str) -> str:
    if s.count(pattern) != 1:
        raise SystemExit(f"anchor not found once: {pattern[:80]!r}")
    return s.replace(pattern, repl)


def _widths(text: str) -> dict[str, str]:
    """name -> packed range text ('' for 1 bit) of the decoded NEXT registers."""
    i = text.index(DECL_START)
    block = text[i:text.index(DECL_END, i)]
    extra = re.findall(r"\n    reg\s+(?:\[[^\]]+\]\s*)?(d_chase_rows|me_kindk);", text)
    if sorted(extra) != ["d_chase_rows", "me_kindk"]:
        raise SystemExit("d_chase_rows / me_kindk declarations moved")
    out: dict[str, str] = {"d_chase_rows": "", "me_kindk": ""}
    for m in re.finditer(r"^\s*reg\s+(\[[^\]]+\])?\s*([^;]+);", block, re.M):
        for name in m.group(2).split(","):
            out[name.strip()] = m.group(1) or ""
    return out


def _statements(body: str) -> list[tuple[str, str]]:
    body = "\n".join(re.sub(r"//.*$", "", l) for l in body.splitlines())
    out = []
    for st in body.split(";"):
        st = " ".join(st.split())
        if not st:
            continue
        m = re.fullmatch(r"(\w+) <= (.+)", st)
        if not m:
            raise SystemExit(f"unexpected decode statement: {st!r}")
        out.append((m.group(1), m.group(2)))
    return out


def emit_dec(text: str) -> str:
    if "parameter integer VPOS = 0\n) (" not in text:
        raise SystemExit("apply over tools/qwen_rom_verify_core_emit_w12.emit")
    text = _sub1("    parameter integer VPOS = 0\n) (",
                 "    parameter integer VPOS = 0,\n    parameter integer DEC_LA = 0\n) (", text)
    widths = _widths(text)
    i = text.index(DEC_START)
    j = text.index(DEC_END, i)
    body = text[i + len(DEC_START):j]
    stmts = _statements(body)
    for name, _ in stmts:
        if name not in widths:
            raise SystemExit(f"no declaration for decoded field {name}")

    def pre(expr: str) -> str:
        e = re.sub(r"`DYNS\(`F\((\w+)\)\)", r"pq_dyn_\1", expr)
        e = e.replace("`F(", "`FP(").replace("ir[", "pq_r[")
        return e.replace("dyn_tiles_split", "pq_split_rounds")

    ctrl = CTRL
    data = [n for n, _ in stmts if n not in ctrl]

    def wexpr(rng: str) -> str:
        m = re.fullmatch(r"\[(.+)-1:0\]", rng)
        if m:
            return m.group(1)
        m = re.fullmatch(r"\[(\d+):0\]", rng)
        if m:
            return str(int(m.group(1)) + 1)
        if rng == "":
            return "1"
        raise SystemExit(f"width {rng}")

    def split_plus(expr: str):
        d = 0
        for k, ch in enumerate(expr):
            d += {"(": 1, ")": -1, "{": 1, "}": -1}.get(ch, 0)
            if d == 0 and expr[k:k + 3] == " + ":
                return expr[:k], expr[k + 3:]
        return None

    decl, push, cpush, load, adders, assigns = [], [], [], [], [], []
    dsel = sorted(set(re.findall(r"`DYNS\(`F\((\w+)\)\)", body)))
    dyn_txt = []
    for f in dsel:
        dyn_txt.append(f"""    reg  [AW-1:0] pq_dyn_{f};
    always @(posedge clk) if (DEC_LA != 0 && pend1)
        pq_dyn_{f} <= (prog_q[O_{f} +: W_{f}] == 3'd6) ? {{{{(AW-NW){{1'b0}}}}, la_rt[(VPOS != 0) ? {{pg_off, 4'd0}} : 7'd0]}}
                                                     : la_tab[((VPOS != 0) ? {{pg_off, 3'd0}} : 6'd0) + prog_q[O_{f} +: W_{f}]];""")
    for name, expr in stmts:
        w = widths[name]
        decl.append(f"    reg {w + ' ' if w else ''}fqd_{name} [0:7];")
        sp = split_plus(expr)
        if sp:
            adders.append(f"    wire {w + ' ' if w else ''}pa_{name};\n"
                          f"    ot_hdc_ksadd_k #(.W({wexpr(w)})) u_pa_{name} (.a({pre(sp[0])}), .b({pre(sp[1])}), .cin(1'b0), "
                          f".s(pa_{name}), .cout());")
            push.append(f"            for (lw = 0; lw < 8; lw = lw + 1) if (la_we[lw]) fqd_{name}[lw] <= pa_{name};")
        elif name in ctrl:
            cpush.append(f"            fqd_{name}[la_wr] <= {expr.replace('`F(', '`FQ(')};")
        else:
            push.append(f"            for (lw = 0; lw < 8; lw = lw + 1) if (la_we[lw]) fqd_{name}[lw] <= {pre(expr)};")
        if name in ctrl:
            load.append(f"            {name} <= fqd_{name}[la_rd];")
        else:
            assigns.append(f"    assign {name} = (DEC_LA != 0) ? fqd_{name}[la_nx] : {name}_q;")
    la = f"""
    // ---- DEC_LA (tools/qwen_rom_core_dec_emit_w12.py): predecode at push, pipelined registered tables ----
    function automatic integer la_tz(input integer value);
        integer n;
        begin
            n = 0;
            while ((value & 1) == 0 && value > 0) begin value = value >> 1; n = n + 1; end
            la_tz = n;
        end
    endfunction
    localparam integer LA_WT = la_tz(W), LA_GT = la_tz(G), LA_ODD = G >> la_tz(G);
    localparam integer LA_NO = (VPOS != 0) ? 8 : 1;         // position offsets
    localparam integer LA_SW = NW + 2;                       // rounds operand: shifted position + ODD
    localparam integer LA_H = LA_SW / 2 - 3;                 // divider split (low part: remainder + LA_H bits)
    // stage 1 (E1): pos_r + o and, for every (o, split), ((pos_r + o) >> (WT + GT - split)) + ODD
    //   (rounds = that / ODD), both through kept prefix adders
    // stage 2 (E2): high-half quotient and remainder; the other DYN entries
    // stage 3 (E3): rounds (0 for an invalid split).  The first program word reaches prog_q at E3 and is
    //   registered (pend1) at E4, when every table entry is settled.
    reg [NW-1:0]    la_po [0:LA_NO-1];
    reg [LA_SW-1:0] la_sh [0:LA_NO*16-1];
    reg [AW-1:0]    la_tokh;
    reg [LA_SW-1:0] la_qh [0:LA_NO*16-1];
    reg [LA_SW-1:0] la_lo [0:LA_NO*16-1];
    reg [AW-1:0]    la_tab [0:LA_NO*8-1];
    reg [NW-1:0]    la_rt [0:LA_NO*16-1];
    wire [15:0]  la_inv;
    wire [LA_NO*NW-1:0] la_po_n;            // packed: Yosys 0.68 asserts on an unpacked array bound to output ports
    wire [LA_NO*16*LA_SW-1:0] la_sh_n;
    genvar lap, las;
    generate for (las = 0; las < 16; las = las + 1) begin : g_la_inv
        assign la_inv[las] = (W != (1 << LA_WT)) || las > LA_GT || las > LA_WT + LA_GT;
    end endgenerate
    generate for (lap = 0; lap < LA_NO; lap = lap + 1) begin : g_la_po
        ot_hdc_ksadd_k #(.W(NW)) u_po (.a(pos_r), .b(lap), .cin(1'b0), .s(la_po_n[lap*NW +: NW]), .cout());
        for (las = 0; las < 16; las = las + 1) begin : g_s
            if (las > LA_GT || las > LA_WT + LA_GT) begin : g_inv
                assign la_sh_n[(lap*16+las)*LA_SW +: LA_SW] = {{LA_SW{{1'b0}}}};
            end else begin : g_ok
                ot_hdc_ksadd_k #(.W(LA_SW)) u_sh (.a({{2'b00, (la_po_n[lap*NW +: NW] >> (LA_WT + LA_GT - las))}}),
                                                 .b(LA_ODD), .cin(1'b0), .s(la_sh_n[(lap*16+las)*LA_SW +: LA_SW]), .cout());
            end
        end
    end endgenerate
    integer lo, ls;
    always @(posedge clk) if (DEC_LA != 0) begin
        la_tokh <= tok_r * HID;
        for (lo = 0; lo < LA_NO; lo = lo + 1) begin
            la_po[lo] <= la_po_n[lo*NW +: NW];
            for (ls = 0; ls < 16; ls = ls + 1)
                la_sh[lo*16+ls] <= la_sh_n[(lo*16+ls)*LA_SW +: LA_SW];
        end
        for (lo = 0; lo < LA_NO; lo = lo + 1) begin
            for (ls = 0; ls < 16; ls = ls + 1) begin
                la_qh[lo*16+ls] <= ((la_sh[lo*16+ls] >> LA_H) / LA_ODD) << LA_H;
                la_lo[lo*16+ls] <= (((la_sh[lo*16+ls] >> LA_H) % LA_ODD) << LA_H) | (la_sh[lo*16+ls] & ((1 << LA_H) - 1));
            end
            la_tab[lo*8+0] <= 0;
            la_tab[lo*8+1] <= la_tokh;
            la_tab[lo*8+2] <= la_po[lo] * HALF;
            la_tab[lo*8+3] <= (la_po[lo] >> LW) * (HD * W) + (la_po[lo] & (W - 1));
            la_tab[lo*8+4] <= la_po[lo] * HD;
            la_tab[lo*8+5] <= la_po[lo] + 1;
            la_tab[lo*8+6] <= 0;                                   // read from la_rt (split 0)
            la_tab[lo*8+7] <= 0;
        end
        for (lo = 0; lo < LA_NO * 16; lo = lo + 1)
            la_rt[lo] <= la_inv[lo % 16] ? {{NW{{1'b0}}}} : (la_qh[lo] | (la_lo[lo] / LA_ODD));
    end
    // the program word is staged one cycle (pq_r): the data fields of an entry are written one edge after its
    // push, which is no later than its LOAD edge, and they are read only after LOAD (from la_nx).  The table
    // lookups the word needs (its split rounds, its DYN values) are registered with it at pend1.
    reg [INSTR_BITS-1:0] pq_r;
    reg [2:0]     la_wr_r;
    reg           pq_v;
    reg  [7:0]    la_we;
    integer       lw;
    wire [2:0]    pg_off = (VPOS != 0) ? prog_q[{V.POS_OFF_LO} +: {V.POS_OFF_W}] : 3'd0;
    wire [6:0]    pg_rti = ((VPOS != 0) ? {{pg_off, 4'd0}} : 7'd0) + prog_q[O_ME_SPLIT +: 4];
    reg  [NW-1:0] pq_split_rounds;
    always @(posedge clk) if (DEC_LA != 0) begin
        pq_v <= pend1; la_wr_r <= la_wr;
        la_we <= pend1 ? (8'd1 << la_wr) : 8'd0;     // one-hot write strobes of the staged word's slot
        if (pend1) begin
            pq_r <= prog_q;
            pq_split_rounds <= la_rt[pg_rti];
        end
    end
    integer lq, lk;
{chr(10).join(dyn_txt)}
    wire          pq_split_bad = prog_q[O_ME_D_TILES +: W_ME_D_TILES] == 3'd6 && la_inv[prog_q[O_ME_SPLIT +: 4]];
    `define FP(name) pq_r[O_``name +: W_``name]
    `define FQ(name) prog_q[O_``name +: W_``name]
    // decoded-field FIFO: 8 entries, so the entry in NEXT (la_nx) is never overwritten while it is NEXT or
    // stale-NEXT (at most 4 entries are held or in flight behind it); the fetch throttle still counts fq_n.
    reg [2:0] la_wr, la_rd, la_nx;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin la_wr <= 3'd0; la_rd <= 3'd0; la_nx <= 3'd0; end
        else if (st == S_IDLE) begin if (start) begin la_wr <= 3'd0; la_rd <= 3'd0; end end
        else if (st == S_RUN) begin
            if (push) la_wr <= la_wr + 1'b1;
            if (load) begin la_rd <= la_rd + 1'b1; la_nx <= la_rd; end
        end
{chr(10).join(decl)}
    reg           fqd_bad [0:7];
    reg           fqd_kvd [0:7];
    reg           fqd_wd  [0:7];
{chr(10).join(adders)}
    // data fields from the staged word; control fields (below) from prog_q at pend1.  Written on pend1 (pq_v) alone:
    // outside S_RUN the slot la_wr is free (never NEXT, never held), so such a write is dead
    always @(posedge clk) if (DEC_LA != 0) begin
{chr(10).join(push)}
    end
    always @(posedge clk) if (DEC_LA != 0 && pend1) begin
{chr(10).join(cpush)}
            fqd_bad[la_wr] <= pq_split_bad;
            fqd_kvd[la_wr] <= prog_q[O_UNIT +: W_UNIT] == 2'd1 && prog_q[O_ME_WSRC];
            fqd_wd[la_wr]  <= (W_HBM != 0) && prog_q[O_UNIT +: W_UNIT] == 2'd1 && !prog_q[O_ME_WSRC];
    end
    `undef FP
    `undef FQ
    // NEXT: control fields are registers (issue reads them); data fields are the NEXT entry of the FIFO
{chr(10).join(assigns)}
"""
    # the decode block: DEC_LA loads the control fields, else the original decode (data fields into <name>_q)
    body_q = body
    for n in data:
        body_q, k = re.subn(rf"(^|[\s;])({n}) <=", rf"\1\2_q <=", body_q, flags=re.M)
        if k != 1:
            raise SystemExit(f"decode assignment of {n}: {k}")
    new_block = (DEC_START + "        if (DEC_LA != 0) begin\n" + "\n".join(load) + "\n        end else begin\n"
                 + body_q + "        end\n" + DEC_END)
    text = text[:i] + la + new_block + text[j + len(DEC_END):]
    # declarations: data fields become <name>_q registers plus <name> wires
    def redecl(m):
        rng, names = m.group(1) or "", [x.strip() for x in m.group(2).split(",")]
        regs = [x if x in ctrl or x not in data else x + "_q" for x in names]
        wires = [x for x in names if x in data]
        s = f"    reg {rng + ' ' if rng else ''}{', '.join(regs)};"
        if wires:
            s += f"\n    wire {rng + ' ' if rng else ''}{', '.join(wires)};"
        return s
    di = text.index(DECL_START)
    de = text.index(DECL_END, di)
    block = re.sub(r"^    reg\s+(\[[^\]]+\])?\s*([^;]+);", redecl, text[di:de], flags=re.M)
    text = text[:di] + block + text[de:]
    text = _sub1("    reg          me_kindk;\n", "    reg          me_kindk_q;\n    wire         me_kindk;\n", text)
    text = _sub1("                    fq_n <= fq_n + (push ? 3'd1 : 3'd0) - (load ? 3'd1 : 3'd0);\n",
                 "                    fq_n <= (DEC_LA != 0) ? (load ? la_fqn_l : la_fqn_nl)\n"
                 "                                          : fq_n + (push ? 3'd1 : 3'd0) - (load ? 3'd1 : 3'd0);\n", text)
    text = _sub1("    wire push = (st == S_RUN) && pend1;\n",
                 "    wire push = (st == S_RUN) && pend1;\n"
                 "    wire [2:0] la_fqn_nl = fq_n + (push ? 3'd1 : 3'd0);      // DEC_LA: fq_n without / with a LOAD\n"
                 "    wire [2:0] la_fqn_l  = fq_n + (push ? 3'd0 : 3'd7);\n", text)
    # the lm_head chunk argmax: a kept tree comparator on the order keys
    text = _sub1("    wire am_wins = am_any && (!run_any || okey(am_val) > run_key);\n",
                 "    wire la_am_gt;\n"
                 "    ot_qwen_core_key_gt u_la_am_gt (.a(okey(am_val)), .b(run_key), .gt(la_am_gt));\n"
                 "    wire am_wins = am_any && (!run_any || ((DEC_LA != 0) ? la_am_gt : (okey(am_val) > run_key)));\n", text)
    # the lm_head chunk argmax update: its own kept copy of issue (half the issue fan-out)
    text = _sub1("    assign me_go = issue && (d_unit == 2'd1);\n",
                 "    assign me_go = issue && (d_unit == 2'd1);\n"
                 "    (* keep *) wire la_issue_am = (st == S_RUN) && nx_v && (d_unit != 2'd0) &&\n"
                 "                 (d_barrier ? drained : ((!d_chase || chased) && (!d_wait_me || me_idle) && (!d_wait_su || su_idle)))\n"
                 "                 && unit_ready && kv_gate && w_gate;\n"
                 "    wire la_me_go_am = (DEC_LA != 0) ? (la_issue_am && (d_unit == 2'd1)) : me_go;\n", text)
    text = _sub1("        else if (me_go && me_amax) begin\n", "        else if (la_me_go_am && me_amax) begin\n", text)
    # the step cycle counter: a kept incrementer (it was the next ripple at 1.2 GHz once the decode closed)
    text = _sub1("            if (st != S_IDLE) cycles <= cycles + 1;\n",
                 "            if (st != S_IDLE) cycles <= (DEC_LA != 0) ? la_cycles1 : cycles + 1;\n", text)
    text = _sub1("    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin\n            st <= S_IDLE;",
                 "    wire [31:0] la_cycles1;\n"
                 "    ot_hdc_inc_k #(.W(32)) u_la_cycles (.a(cycles), .inc(1'b1), .y(la_cycles1), .co());\n"
                 "    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin\n            st <= S_IDLE;", text)
    # head-entry predecoded bits
    text = _sub1("            kvd_v <= load && ir[O_UNIT +: W_UNIT] == 2'd1 && ir[O_ME_WSRC];\n"
                 "            wd_v <= (W_HBM != 0) && load && ir[O_UNIT +: W_UNIT] == 2'd1 && !ir[O_ME_WSRC];\n",
                 "            kvd_v <= load && ((DEC_LA != 0) ? fqd_kvd[la_rd] : (ir[O_UNIT +: W_UNIT] == 2'd1 && ir[O_ME_WSRC]));\n"
                 "            wd_v <= load && ((DEC_LA != 0) ? fqd_wd[la_rd] : ((W_HBM != 0) && ir[O_UNIT +: W_UNIT] == 2'd1 && !ir[O_ME_WSRC]));\n",
                 text)
    text = _sub1("    wire dyn_tiles_bad_instruction = load && `F(ME_D_TILES) == 3'd6 && dyn_tiles_invalid;\n",
                 "    wire dyn_tiles_bad_instruction = load && ((DEC_LA != 0) ? fqd_bad[la_rd]\n"
                 "                                                            : (`F(ME_D_TILES) == 3'd6 && dyn_tiles_invalid));\n",
                 text)
    # chase test: three kept comparators selected by the decoded unit
    text = _sub1("    wire chased = ((d_unit == 2'd1) ? (d_chase_rows ? su_rows : su_progress) : me_progress) >= d_chase_n;\n",
                 "    wire ge_su_rows, ge_su_prog, ge_me_prog;\n"
                 "    ot_qwen_core_ge16 u_ge_rows (.a(su_rows), .b(d_chase_n), .ge(ge_su_rows));\n"
                 "    ot_qwen_core_ge16 u_ge_sup (.a(su_progress), .b(d_chase_n), .ge(ge_su_prog));\n"
                 "    ot_qwen_core_ge16 u_ge_mep (.a(me_progress), .b(d_chase_n), .ge(ge_me_prog));\n"
                 "    wire chased = (DEC_LA != 0) ? ((d_unit == 2'd1) ? (d_chase_rows ? ge_su_rows : ge_su_prog) : ge_me_prog)\n"
                 "                                : (((d_unit == 2'd1) ? (d_chase_rows ? su_rows : su_progress) : me_progress) >= d_chase_n);\n",
                 text)
    text += """
// a > b on 32-bit unsigned keys, log depth with kept levels (DEC_LA lm_head chunk argmax)
module ot_qwen_core_key_gt (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire        gt
);
    (* keep *) wire [7:0] g0, e0;
    (* keep *) wire [3:0] g1, e1;
    (* keep *) wire [1:0] g2, e2;
    genvar i;
    generate
        for (i = 0; i < 8; i = i + 1) begin : l0
            assign g0[i] = a[4*i +: 4] > b[4*i +: 4];
            assign e0[i] = a[4*i +: 4] == b[4*i +: 4];
        end
        for (i = 0; i < 4; i = i + 1) begin : l1
            assign g1[i] = g0[2*i+1] | (e0[2*i+1] & g0[2*i]);
            assign e1[i] = e0[2*i+1] & e0[2*i];
        end
        for (i = 0; i < 2; i = i + 1) begin : l2
            assign g2[i] = g1[2*i+1] | (e1[2*i+1] & g1[2*i]);
            assign e2[i] = e1[2*i+1] & e1[2*i];
        end
    endgenerate
    assign gt = g2[1] | (e2[1] & g2[0]);
endmodule

// a >= b on 16-bit unsigned values, log depth with kept levels (DEC_LA chase test)
module ot_qwen_core_ge16 (
    input  wire [15:0] a,
    input  wire [15:0] b,
    output wire        ge
);
    (* keep *) wire [3:0] g0, e0;
    (* keep *) wire [1:0] g1, e1;
    genvar i;
    generate
        for (i = 0; i < 4; i = i + 1) begin : l0
            assign g0[i] = a[4*i +: 4] > b[4*i +: 4];
            assign e0[i] = a[4*i +: 4] == b[4*i +: 4];
        end
        for (i = 0; i < 2; i = i + 1) begin : l1
            assign g1[i] = g0[2*i+1] | (e0[2*i+1] & g0[2*i]);
            assign e1[i] = e0[2*i+1] & e0[2*i];
        end
    endgenerate
    assign ge = g1[1] | (e1[1] & g1[0]) | (e1[1] & e1[0]);
endmodule
"""
    return text


def emit(core_text: str) -> str:
    return ("// GENERATED by tools/qwen_rom_core_dec_emit_w12.py (DEC_LA opt-in) over tools/qwen_rom_verify_core_emit_w12.py "
            f"(sha256 {hashlib.sha256(Path(V.__file__).read_bytes()).hexdigest()}).\n" + emit_dec(V.emit(core_text)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(emit(E.CORE.read_text()))
    print(args.out)


if __name__ == "__main__":
    main()
