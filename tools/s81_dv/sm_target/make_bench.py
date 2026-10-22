#!/usr/bin/env python3
"""Derive the operator-backed target bench from the unchanged SMS exact bench."""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
src = root / 'rtl/dsrom_sys/s81_dv/su_sm/test/tb_s81_su_sms.sv'
out = root / 'rtl/dsrom_sys/s81_dv/sm_target/test/tb_sm_so_target.sv'
s = src.read_text().replace('module tb_s81_su_sms;', 'module tb_sm_so_target;')
insert = r'''
    // Independent compiler-owned expectation. Set before SE starts, never from
    // a returned row/address/status. The SO operand generator obeys this base.
    reg cfg_v = 0;
    reg [19:0] target_owner = 0;
    reg [7:0] expected_se = 0, expected_so = 0;
    reg [13:0] target_base = 0;
    wire [1:0] gv, retired, re, tfault;
    wire [13:0] gi;
    wire [2047:0] gd;
    wire [39:0] go_owner, retire_owner;
    wire [1:0] group_o;
    wire [23:0] fc;
    integer target_mut = 0, target_beats = 0, target_retires = 0;
    integer target_bad_retires = 0, target_checks = 0;
    integer ref_count = 0;
    reg [255:0] reference_rows[0:1][0:31];
    reg [7:0] got[0:1];
    reg [13:0] previous_addr[0:1];
    reg [7:0] previous_mask[0:1];
    initial if (!$value$plusargs("TARGET_MUT=%d", target_mut)) target_mut=0;
    generate for (genvar th=0; th<2; th=th+1) begin: g_target
        wire so = qw_m[16*th+:16] != 16'hffff;
        wire inject = so && target_mut != 0;
        wire [15:0] tm = (inject && target_mut==1) ? ~qw_m[16*th+:16] : qw_m[16*th+:16];
        wire [13:0] ta = (inject && target_mut==2) ? (qw_a[14*th+:14] ^ 14'd8) : qw_a[14*th+:14];
        wire [7:0] tj = (inject && target_mut==3) ? (q_rj[8*th+:8] ^ 8'd1) : q_rj[8*th+:8];
        wire tv = qw_v[th] && !(so && target_mut==4);
        wire td = q_den[th] && target_mut != 5;
        dsdv_sm_so_target #(.HEAD(2*TI+th)) u_target (
            .clk(clk),.rst_n(rst),.cfg_v(cfg_v),.cfg_owner(target_owner),
            .cfg_se_jid(expected_se),.cfg_so_jid(expected_so),.cfg_obase(target_base),
            .cfg_first(16'd0),.cfg_last(16'd1200),.cfg_read(16'd1300),.cfg_retire(16'd1350),
            .op_st(q_st),.op_kind(q_kind),.op_jid(q_jid),
            .w_v(tv),.w_a(ta),.w_m(tm),.w_d(qw_d[512*th+:512]),
            .w_st({tj,td,q_al[th],q_fo[th],q_fu[th]}),
            .g_v(gv[th]),.g_idx(gi[7*th+:7]),.g_d(gd[1024*th+:1024]),
            .g_owner(go_owner[20*th+:20]),.g_group(group_o[th]),
            .retired(retired[th]),.retire_error(re[th]),.retire_owner(retire_owner[20*th+:20]),
            .fault(tfault[th]),.fault_code(fc[12*th+:12]));
    end endgenerate
    // Reference rows are from the independently instantiated real slab SM
    // operator, not the DUT target input and never a golden data responder.
    always @(posedge clk) if (rst) begin: target_monitor
        integer hh, bi, rr;
        reg [1023:0] want;
        if (cfg_v) begin
            ref_count=0; got[0]=0; got[1]=0;
        end
        if (dn_kind==5 && w_v[0]) begin
            if (ref_count >= 32) fail("target reference overflow",ref_count);
            else begin
                reference_rows[0][ref_count]=w_d[255:0];
                reference_rows[1][ref_count]=w_d[511:256];
                ref_count=ref_count+1;
            end
        end
        for (hh=0;hh<2;hh=hh+1) begin
            if (gv[hh]) begin
                target_beats=target_beats+1;
                bi=gi[7*hh+:7] % 8;
                if (target_mut != 0) fail("target mutant emitted healthy beat",target_mut);
                if (ref_count != 32 || got[hh][bi]) fail("target missing/duplicate identities",bi);
                got[hh][bi]=1;
                for (rr=0;rr<4;rr=rr+1) want[256*rr+:256]=reference_rows[hh][4*bi+rr];
                if (gd[1024*hh+:1024] !== want) fail("target real operator gather order",bi);
                if (gi[7*hh+:7] != 8*((2*TI+hh)%8)+bi ||
                    group_o[hh] != (2*TI+hh>=8) || go_owner[20*hh+:20] !== target_owner)
                    fail("target independent owner/group/index",hh);
                target_checks=target_checks+64;
            end
            if (retired[hh]) begin
                target_retires=target_retires+1;
                if (re[hh]) target_bad_retires=target_bad_retires+1;
                if (retire_owner[20*hh+:20] !== target_owner) fail("target retire owner",hh);
                if (target_mut==0 && (re[hh] || got[hh] != 8'hff || tfault[hh]))
                    begin fail("target base retirement",hh); $display("TARGET fault=%h",fc); end
                if (target_mut!=0 && (!re[hh] || !tfault[hh])) fail("target missed causal fault",target_mut);
            end
        end
    end
'''
s = s.replace('    // ------------------------------------------------------------------ logs', insert + '\n    // ------------------------------------------------------------------ logs')
s = s.replace('            np = (kd == 5) ? 5 : 2;', '''            if (kd==4) begin
                target_owner=20'h54100+jj;
                expected_se=jj; expected_so=jj+1;
                target_base=14'h300+14'(512*j);
                cfg_v=1; tick; cfg_v=0; repeat(2) tick;
            end
            np = (kd == 5) ? 5 : 2;''')
s = s.replace('            kinds.push_back(kd);', '''            if(kd==5) prm[0][13:0]=target_base;
            kinds.push_back(kd);''')
s = s.replace('            repeat (400) tick;', '''            repeat (400) tick;''')
s = s.replace('        end\n    endtask\n    initial begin', '''            if(kd==5) repeat(650) tick;
        end
    endtask
    initial begin''', 1)
s = s.replace('            if (err == 0) $display("SMS PASS', '''            if(target_retires != 2*NJOB) fail("target retire count",target_retires);
            if(target_mut==0 && target_beats != 16*NJOB) fail("target fullshape beat count",target_beats);
            if(target_mut!=0 && target_bad_retires != 2*NJOB) fail("target mutant retirement count",target_bad_retires);
            $display("TARGET stats mut=%0d beats=%0d retires=%0d bad_retires=%0d operator_elements=%0d",target_mut,target_beats,target_retires,target_bad_retires,target_checks);
            if(err==0 && target_mut!=0) $display("TARGET CAUGHT mut=%0d fault_code=%h",target_mut,fc);
            if (err == 0) $display("SMS PASS''')
out.write_text(s)
print(out)
