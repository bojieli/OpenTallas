# TOK-QK/S8 WHAT-IF (diagnostic only, never a deliverable RTL change): qfd_dv_s8_suvm_rp1 with the SU8 start delayed
# DLY edges behind the PROG read request, so the closed su8_rst3 accepts the program word on the edge it arrives.
import re, sys
src, dst, dly = sys.argv[1], sys.argv[2], int(sys.argv[3])
s = open(src).read()
s = s.replace("module qfd_dv_s8_suvm_rp1 ", "module qfd_dv_s8_suvm_rp1 ", 1)
old = "qfd_dv_s5_su8_rst3 u_su8(.ck(ck),.rst_n(rst_n),.start(su_cmd[9]),"
assert old in s
s = s.replace(old, f"reg [{dly-1}:0] wf_st; always @(posedge ck or negedge rst_n) if (!rst_n) wf_st <= 0; else wf_st <= {{wf_st, su_cmd[9]}};\n"
                   f"    qfd_dv_s5_su8_rst3 u_su8(.ck(ck),.rst_n(rst_n),.start(wf_st[{dly-1}]),")
open(dst, "w").write("// WHAT-IF DIAGNOSTIC COPY (TOK-QK/S8): SU8 start delayed %d edges vs su_cmd (PROG read); not RTL of record.\n" % dly + s)
