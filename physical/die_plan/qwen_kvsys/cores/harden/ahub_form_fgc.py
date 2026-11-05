#!/usr/bin/env python3
"""AHUB form fgc (DIE-KV-70 11-04, activated by DIE-KV-74 11-05): applied to the seven-role core text in ahub_clock7.prepare.

Three edits, all 0 added cycles at any pin:
  1. edge_age_q: e_next from a parallel register holding the same value on every cycle (form a).
  2. nblk_c[0:2]: one kept copy of nblk_q per consumer (u_dn, u_d1, zmask), 60 flops (form p). One edge later than nblk_q, so it needs
     Z_IN_AGE >= 3 and Z_START_AGE >= 2 (proved, dkv70ahub prove2-4); the compiler gives Z_IN_AGE >= 482, Z_START_AGE >= 779.
  3. gqv_groups: same-edge split of the fault capture (ahub_fault_groups.py, form a).
Every edit must match exactly once, else no kit is made. Result is byte-equal to the signed kit's RTL (test_ahub_form_fgc.py checks the sha).
"""
from __future__ import annotations

import ahub_fault_groups

MODULE = "qkd_ahub_static_core_la_ck7"

SUBS = [
    ("    wire [16:0] e_next=(MUT==4)?{1'b0,age}+17'd1:(active && age!=16'hffff)?{1'b0,age}+17'd2:{1'b0,age}+17'd1;\n",
     "    // AHUB lookahead recurrence: parallel state, same edge_age value on every cycle.\n"
     "    (* keep *) reg [16:0] edge_age_q;\n"
     "    always @(posedge clk or negedge rn[0])\n"
     "        if (!rn[0]) edge_age_q <= 17'd1;\n"
     "        else if (start) edge_age_q <= (MUT == 4) ? 17'd1 : 17'd2;\n"
     "        else if (active && age != 16'hffff && ((MUT == 4) || age != 16'hfffe))\n"
     "            edge_age_q <= edge_age_q + 17'd1;\n"
     "    wire [16:0] e_next = edge_age_q;\n"),
    ("if(k<nblk_q[5*s+:5])zmask[4*k+s]=1'b1;", "if(k<nblk_c[2][5*s+:5])zmask[4*k+s]=1'b1;"),
]
NBLK_DECL = ("    (* keep *) reg [19:0] nblk_c[0:2];\n"
             "    always @(posedge clk)for(integer c=0;c<3;c=c+1)nblk_c[c]<=nblk_q;\n")
NBLK_ANCHOR = "            nblk_q[5*s+:5]<=(T>14'(128*s))?5'(((T-14'(128*s)-14'd1)>>9)+14'd1):5'd0;\n"
CONSUMER = ".RZ_PUBLISH_AGE(RZ_PUBLISH_AGE),.nblk_v(nblk_q),"


def apply_fgc(core7: str) -> str:
    text = ahub_fault_groups.factor_fault_capture(core7, MODULE)
    for old, new in SUBS:
        if text.count(old) != 1:
            raise ValueError("AHUB form fgc: edit does not match once: " + old[:60])
        text = text.replace(old, new, 1)
    if text.count(NBLK_ANCHOR) != 1:
        raise ValueError("AHUB form fgc: nblk_q register not found once")
    text = text.replace(NBLK_ANCHOR, NBLK_ANCHOR + NBLK_DECL, 1)
    if text.count(CONSUMER) != 2:
        raise ValueError("AHUB form fgc: expected two nblk consumers")
    for c in range(2):
        text = text.replace(CONSUMER, f".RZ_PUBLISH_AGE(RZ_PUBLISH_AGE),.nblk_v(nblk_c[{c}]),", 1)
    return text

