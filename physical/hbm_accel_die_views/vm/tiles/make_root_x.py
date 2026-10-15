#!/usr/bin/env python3
"""ot_hfd_vm_root_x (views agent, r19 VM quadrant tiles, 2026-10-07): the multicast root (rtl/ot_hbm_die_vm_multicast_root.sv,
the yosys copy) with its 22 SRAMs moved out to the four tiles' column slices.  Edits, nothing else:
  * the SRAM instances go; the root drives one memory command per WRITE / VERIFY / READ cycle (same enables as the
    macros had: mem_cmd_v / we / bank / addr, mem_wd = the 2,816-bit write word) and receives the read row (mem_rd_v,
    mem_rd = the selected bank's 2,816 bits) whenever the tiles return it;
  * new state WAIT_RD (8) between VERIFY / READ and CAPTURE holds until mem_rd_v; CAPTURE samples the held row.
Same transactions, same order, same faults; latency + the memory round trip.     python3 make_root_x.py"""
from pathlib import Path
D = Path(__file__).resolve().parent
s = (D.parent / 'rtl/ot_hbm_die_vm_multicast_root.sv').read_text()
def rep(o, n, c=1):
    global s
    assert s.count(o) == c, (o, s.count(o)); s = s.replace(o, n)
rep('module ot_hbm_die_vm_multicast_root #(parameter integer ENABLE=0)(',
    'module ot_hfd_vm_root_x #(parameter integer ENABLE=0,parameter integer SEATP=0)(\n'
    ' output wire mem_cmd_v,output wire mem_cmd_we,output wire mem_cmd_bank,output wire [6:0] mem_cmd_addr,output wire [2815:0] mem_wd,\n'
    ' input wire mem_rd_v,input wire [2815:0] mem_rd,')
rep("  assign drained=1;assign fault=0;", "  assign drained=1;assign fault=0;\n  assign mem_cmd_v=0;assign mem_cmd_we=0;assign mem_cmd_bank=0;assign mem_cmd_addr=0;assign mem_wd=0;")
rep("localparam [3:0] IDLE=0,WRITE=1,VERIFY=2,CAPTURE=3,CHECK=4,WACK=5,READ=6,PUBLISH=7;",
    "localparam [3:0] IDLE=0,WRITE=1,VERIFY=2,CAPTURE=3,CHECK=4,WACK=5,READ=6,PUBLISH=7,WAIT_RD=8,LOAD=9;")
i0 = s.index('  for(genvar b=0;b<2;b=b+1)begin:banks'); i1 = s.index('  for(genvar t=0;t<4;t=t+1)begin:taps')
s = s[:i0] + ('  // SRAMs in the tiles (column slices): one command per WRITE / VERIFY / READ cycle, the macros\' enables\n'
              '  assign mem_cmd_v=(state==WRITE||state==VERIFY||state==READ)&&!fault;\n'
              '  assign mem_cmd_we=state==WRITE;assign mem_cmd_bank=bank;assign mem_cmd_addr=addr;\n'
              '  assign mem_wd={224\'b0,seat};\n'
              '  reg [2815:0] rd_hold;\n'
              '  always @(posedge clk) if(mem_rd_v) rd_hold<=mem_rd;\n') + s[i1:]
rep("    VERIFY,READ:next_state=CAPTURE;", "    VERIFY,READ:next_state=WAIT_RD;\n    WAIT_RD:if(mem_rd_v)next_state=CAPTURE;")
rep("    if(state==CAPTURE&&!fault)sampled<=bank?ram_q_flat[2816+:2816]:ram_q_flat[0+:2816];",
    "    if(state==CAPTURE&&!fault)sampled<=rd_hold;")
rep("  wire [2*2816-1:0] ram_q_flat;\n", "")
# ---- safe-hbm 2026-10-08 (REVIEW_20261008 D3, S-D3): SEATP=1 pipelines the seat select as a registered 2-level select.
# hbm_vm8_swn failed post-CTS TT -1,331..-1,421 on u_mr.on.seat -> decode -> fault / 2,303-bit CHECK compare -> next_sticky
# -> the load enable of all 2,592 seat flops.  SEATP=1:
#   level 1 (CHECK): the check verdict (sample UE / pad / compare) and the re-encoded sample are REGISTERED (chk_err_q,
#            smp_enc_q); the state goes to the new LOAD state;
#   level 2 (LOAD):  seat <= smp_enc_q (reads) / validity update (writes) under the registered select only; a registered
#            check error sets the sticky fault here (one edge later than CHECK did); then WACK / PUBLISH as before;
#   IDLE accept: the seat load enable uses the IDLE-equivalent fault (sticky / control / validity; the seat term is
#            gated by state != IDLE in the original, so this is the same function), not the seat decode.
# Cost +1 edge per transaction (CHECK -> LOAD).  SEATP=0 (default) is the original.  `MUT_SEATP` (bench negative): LOAD
# skips the seat load (taps publish the request seat).
rep("  wire wf=wr_v&&wr_ready,rf=rd_v&&rd_ready;",
    "  wire wf=wr_v&&wr_ready,rf=rd_v&&rd_ready;\n"
    "  wire fault_i=sticky||control_bad||(|valid_UE);   // = fault in IDLE\n"
    "  wire ld_w=SEATP?(state==IDLE&&!fault_i&&wr_v&&!rd_v):wf,ld_r=SEATP?(state==IDLE&&!fault_i&&rd_v&&!wr_v):rf;\n"
    "  reg chk_err_q;reg [36*72-1:0] smp_enc_q;   // smp_enc_q: data register (no reset), loaded in CHECK\n"
    "  always @(posedge clk)if(SEATP!=0&&state==CHECK)for(integer k=0;k<36;k=k+1)smp_enc_q[k*72+:72]<=encode64(sample_data[k*64+:64]);")
rep("    CHECK:begin\n", "    LOAD:begin\n     if(chk_err_q)next_sticky=1;else if(is_write)next_state=WACK;else next_state=PUBLISH;\n    end\n"
    "    CHECK:if(SEATP)next_state=LOAD;else begin\n")
rep("    control_code<=0;seat<=0;sampled<=0;validity<=0;", "    control_code<=0;seat<=0;sampled<=0;validity<=0;chk_err_q<=0;")
rep("    if(wf||rf)begin\n     raw=wf?", "    if(ld_w||ld_r)begin\n     raw=ld_w?")
rep("    if(state==CHECK&&!fault&&!is_write&&!next_sticky)\n",
    "    if(SEATP!=0&&state==CHECK&&!fault)\n"
    "     chk_err_q<=(|sample_UE)||(|sample_data[2303:2255])||(is_write?(sample_data!=seat_data):(sample_data[2063+:192]!=seat_data[2063+:192]));\n"
    "`ifndef MUT_SEATP\n"
    "    if(SEATP!=0&&state==LOAD&&!chk_err_q&&!is_write)seat<=smp_enc_q;\n"
    "`endif\n"
    "    if(SEATP!=0&&state==LOAD&&!chk_err_q&&is_write)begin\n"
    "     next_valid=valid_bits;next_valid[{bank,addr}]=1;\n"
    "     for(integer k=0;k<4;k=k+1)validity[k*72+:72]<=encode64(next_valid[k*64+:64]);\n"
    "    end\n"
    "    if(SEATP==0&&state==CHECK&&!fault&&!is_write&&!next_sticky)\n")
rep("    if(state==CHECK&&!fault&&is_write&&!next_sticky)begin\n", "    if(SEATP==0&&state==CHECK&&!fault&&is_write&&!next_sticky)begin\n")
# ---- vm8-seam 2026-10-09 (FREG, default 0): the SECDED integrity verdicts are REGISTERED before they reach the fault.
# hbm_vm8_swn (all variants, a5b5873d9 / c47843849 / SEATP 79315a431): TT -1,331..-1,536 ps, worst u_mr.on.seat ->
# 36 x decode64 -> seat_bad -> fault -> the CAPTURE enable of the 2,816 sampled flops (+ mem_cmd_v / tap_v / wr_ready).
# FREG=1: fault = sticky || bad_cv_q || (state != IDLE && seat_bad_q && !seat_ld_q), next_sticky likewise, where
#   bad_cv_q  <= control_bad || |valid_UE          (verdict of the previous cycle's control / validity code)
#   seat_bad_q <= seat_bad, seat_ld_q <= seat written at this edge (a written seat is encode64(..): it decodes clean,
#   so seat_bad == seat_bad_q && !seat_ld_q exactly).
# Every verdict is a code check of a register that only ever holds encode64() values (or the reset 0, also a codeword),
# so in RTL all of them are identically 0 and FREG=1 is cycle- and bit-exact.  The one difference is in silicon: a
# corrupted control / validity / seat register (an upset) raises the sticky fault ONE cycle later.  0 cycles.
rep(module_hdr := "module ot_hfd_vm_root_x #(parameter integer ENABLE=0,parameter integer SEATP=0)(",
    "module ot_hfd_vm_root_x #(parameter integer ENABLE=0,parameter integer SEATP=0,parameter integer FREG=0)(")
rep("  assign fault=sticky||control_bad||(|valid_UE)||(state!=IDLE&&seat_bad);",
    "  reg bad_cv_q,seat_bad_q,seat_ld_q;   // FREG registered verdicts (cold reset)\n"
    "  wire bad_cv=FREG?bad_cv_q:(control_bad||(|valid_UE));\n"
    "  wire seat_bad_e=FREG?(seat_bad_q&&!seat_ld_q):seat_bad;\n"
    "  assign fault=sticky||bad_cv||(state!=IDLE&&seat_bad_e);")
rep("  wire fault_i=sticky||control_bad||(|valid_UE);   // = fault in IDLE",
    "  wire fault_i=sticky||bad_cv;   // = fault in IDLE")
rep("next_sticky=sticky||control_bad||(|valid_UE)||(state!=IDLE&&seat_bad);",
    "next_sticky=sticky||bad_cv||(state!=IDLE&&seat_bad_e);")
rep("    control_code<=0;seat<=0;sampled<=0;validity<=0;chk_err_q<=0;",
    "    control_code<=0;seat<=0;sampled<=0;validity<=0;chk_err_q<=0;bad_cv_q<=0;seat_bad_q<=0;seat_ld_q<=0;")
rep("    if(ld_w||ld_r)begin\n",
    "    bad_cv_q<=control_bad||(|valid_UE);seat_bad_q<=seat_bad;\n"
    "    seat_ld_q<=(ld_w||ld_r)\n"
    "`ifndef MUT_SEATP\n"
    "     ||(SEATP!=0&&state==LOAD&&!chk_err_q&&!is_write)\n"
    "`endif\n"
    "     ||(SEATP==0&&state==CHECK&&!fault&&!is_write&&!next_sticky);\n"
    "    if(ld_w||ld_r)begin\n")
(D / 'ot_hfd_vm_root_x.sv').write_text('// GENERATED by make_root_x.py from ../rtl/ot_hbm_die_vm_multicast_root.sv (see there)\n' + s)
print('ok')
