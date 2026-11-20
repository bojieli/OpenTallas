#!/usr/bin/env python3
"""QC-TTCTLM-1119 form (a): register the ROM read checks of the HP13 tt_ctlm core (+1 edge on two checks, data paths
unchanged).  Frontend-copy rewrite (frozen HP13 tree), applied on top of the R1 STARTREG tree.

tt_ctlm r1b CTS TT: the worst ends are ROM rd_out -> check logic -> register:
  calendar m1 rd_out[249] (= raw[515], the unused high word) -> |raw[531:512] -> fault   -106.1 ps (access 591 ps)
  leaf op ROM rd_out[49] -> bank select -> CTLM8 header check h_good_r -> h_good_q       -50.7 ps (access 520 ps)
Edits (each a new parameter, default 0 = unchanged, set to 1 in this frontend copy):
  qfd_dv_calendar_rom HIREG: raw[531:512] is captured (hiq) beside data; the nonzero-high-word fault is taken from
    hiq one edge later (mv2 && hiq != 0).  valid / data / out_* edges unchanged; that fault raises +1 edge later (the
    QW-CALR 10-20 mbad precedent).
  qfd_sys_face_mu_dhuser_p HDREG (PINREG 1 only): h_good_q is computed from rq (the ROM capture register) instead of
    rom_q, and the header is decoded on hw2 (one edge after hw).  The header read takes one more edge (bst 1 lasts one
    edge longer); entry reads, the fire edge (fc == t_rom) and op_v / op_* are unchanged.  Compiler rule: the first
    entry's t_rom must leave one more edge after the header (header -> first fire >= 1 extra edge).
Usage: hp13_romreg.py CAL_ROM.sv LEAF.sv
"""
import hashlib, sys
from pathlib import Path


def sub(t, old, new):
    assert t.count(old) == 1, (old[:80], t.count(old))
    return t.replace(old, new)


def main():
    cal, leaf = Path(sys.argv[1]), Path(sys.argv[2])
    c = cal.read_text()
    c = sub(c, "    parameter integer MUT=0\n)(", "    parameter integer MUT=0,\n    parameter integer HIREG=1   // QC-TTCTLM-1119 (a): high-word fault check one edge after the capture\n)(")
    c = sub(c, "    reg pv,mv,mbad;", "    reg pv,mv,mbad,mv2;reg [19:0] hiq;")
    c = sub(c, "        data<=(MUT==2)?{raw[255:0],raw[511:256]}:raw[511:0];",
            "        data<=(MUT==2)?{raw[255:0],raw[511:256]}:raw[511:0];\n        hiq<=raw[531:512];")
    c = sub(c, "        if(!rst_n)begin pv<=0;mv<=0;mbad<=0;valid<=0;fault<=0;end\n        else if(!r2)begin pv<=0;mv<=0;mbad<=0;valid<=0;fault<=0;end",
            "        if(!rst_n)begin pv<=0;mv<=0;mbad<=0;valid<=0;fault<=0;mv2<=0;end\n        else if(!r2)begin pv<=0;mv<=0;mbad<=0;valid<=0;fault<=0;mv2<=0;end")
    c = sub(c, "            pv<=req;mv<=pv;mbad<=pv&&bad;valid<=mv&&!mbad;",
            "            pv<=req;mv<=pv;mbad<=pv&&bad;valid<=mv&&!mbad;mv2<=mv;")
    c = sub(c, "            if(mv&&raw[531:512]!=0)fault<=1;",
            "            if((HIREG!=0)?(mv2&&hiq!=0):(mv&&raw[531:512]!=0))fault<=1;")
    cal.write_text(c)
    t = leaf.read_text()
    t = sub(t, "    parameter integer PINREG = 0 ",
            "    parameter integer HDREG = 1,                   // QC-TTCTLM-1119 (a): header check from rq, decoded on hw2\n    parameter integer PINREG = 0 ")
    t = sub(t, "        reg         hw;                            // PINREG: header in rq (decode edge)",
            "        reg         hw;                            // PINREG: header in rq (decode edge)\n        reg         hw2;                           // HDREG: header check registered from rq (decode edge)")
    t = sub(t, "        wire        hdec = bst == 2'd1 && (!PR || hw);",
            "        wire        hdec = bst == 2'd1 && (!PR || ((HDREG != 0) ? hw2 : hw));")
    t = sub(t, "            always @(posedge ck) h_good_q <= h_good_r;",
            "            always @(posedge ck) h_good_q <= (HDREG != 0) ? h_good_c : h_good_r;")
    t = sub(t, "                if (!rst_n) begin hw <= 1'b0; rd_p2 <= 1'b0; rd_nf2 <= 1'b0; end\n                else begin hw <= bst == 2'd1 && !hw;",
            "                if (!rst_n) begin hw <= 1'b0; hw2 <= 1'b0; rd_p2 <= 1'b0; rd_nf2 <= 1'b0; end\n                else begin hw <= bst == 2'd1 && !hw && !hw2; hw2 <= (HDREG != 0) && hw && bst == 2'd1;")
    t = sub(t, "            always @* begin rq = 72'd0; hw = 1'b0;", "            always @* begin rq = 72'd0; hw = 1'b0; hw2 = 1'b0;")
    leaf.write_text(t)
    for p in (cal, leaf):
        print(p.name, hashlib.sha256(p.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
