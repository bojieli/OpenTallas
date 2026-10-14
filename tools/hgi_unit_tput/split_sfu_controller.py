#!/usr/bin/env python3
"""Append opt-in four-root S control graph after regenerating plain real c12 extraction."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/Path('rtl/hbm_accel/generic/peers/ot_hgi_sfu_ctl_extract.sv');s=p.read_text().replace('parameter integer ENABLE_NATIVE = 0,','parameter integer ENABLE_NATIVE = 0,\n    parameter integer SPLIT_S_PIPE = 0,');s=s.replace('    input  wire              rst_n,','    input  wire              rst_n,\n    input wire clk_s_ops_lo,clk_s_ops_hi,clk_s_meta_lo,clk_s_meta_hi,',1)
a=s.index('    ot_hdc_v41x_ins #(.W(WC), .K(7)');b=s.index('    // E2 in',a)
old=s[a:b];new='''    generate if(SPLIT_S_PIPE==0)begin:g_legacy_s
'''+old+'''    end else begin:g_split_s
        wire [74:0] ops_in={`CW_SFU(cwi),`CW_E1(cwi),`CW_IMM2(cwi),`CW_E2(cwi),`CW_IMM1(cwi),`CW_RND(cwi),`CW_DST(cwi)};
        wire [74:0] ops_hi,ops_lo;
        wire [59:0] meta_hi,meta_lo;
        wire ohv,olv,mhv,mlv,ohc,olc,mhc,mlc,ohb,olb,mhb,mlb;
        `ifdef OT_HARD_CHILDREN
        ot_hgi_sfu_ctl75hi u_oph
`else
        ot_hgi_sfu_ctl_chunk #(.W(75),.OFFSET(138),.PIN_CAPTURE(1),.STATUS_REG(1)) u_oph
`endif
            (.clk(clk_s_ops_hi),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(ops_in),.tail_d(75'd0),.tail_v(1'b0),.q(ops_hi),.vo(ohv),.coll(ohc),.busy(ohb));
        `ifdef OT_HARD_CHILDREN
        ot_hgi_sfu_ctl75lo u_opl
`else
        ot_hgi_sfu_ctl_chunk #(.W(75),.OFFSET(0),.PIN_CAPTURE(1),.STATUS_REG(1)) u_opl
`endif
            (.clk(clk_s_ops_lo),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(ops_in),.tail_d(ops_hi),.tail_v(ohv),.q(ops_lo),.vo(olv),.coll(olc),.busy(olb));
        `ifdef OT_HARD_CHILDREN
        ot_hgi_sfu_ctl60hi u_mth
`else
        ot_hgi_sfu_ctl_chunk #(.W(60),.OFFSET(138),.PIN_CAPTURE(1),.STATUS_REG(1)) u_mth
`endif
            (.clk(clk_s_meta_hi),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(cwi[59:0]),.tail_d(60'd0),.tail_v(1'b0),.q(meta_hi),.vo(mhv),.coll(mhc),.busy(mhb));
        `ifdef OT_HARD_CHILDREN
        ot_hgi_sfu_ctl60lo u_mtl
`else
        ot_hgi_sfu_ctl_chunk #(.W(60),.OFFSET(0),.PIN_CAPTURE(1),.STATUS_REG(1)) u_mtl
`endif
            (.clk(clk_s_meta_lo),.rst_n(rst_n),.v(vi),.sfu(i_s),.d(cwi[59:0]),.tail_d(meta_hi),.tail_v(mhv),.q(meta_lo),.vo(mlv),.coll(mlc),.busy(mlb));
        wire now=vi&&(i_s==SFU_NONE);
        wire [74:0] ops=now?ops_in:ops_lo;
        wire [59:0] meta=now?cwi[59:0]:meta_lo;
        wire [2:0] fn,e1;
        wire [31:0] imm2,imm1;
        wire [1:0] e2,dst;
        wire rnd;
        assign {fn,e1,imm2,e2,imm1,rnd,dst}=ops;
        assign cws={8'd0,4'd0,32'd0,3'd0,imm1,2'd0,3'd0,3'd0,imm2,fn,e1,e2,rnd,dst,meta};
        assign vs=now||olv;
        assign col_s=ohc||olc||mhc||mlc||(now&&olv);
        assign bz_s=ohb||olb||mhb||mlb;
        // Root data/valid edges unchanged. Registered status observation needs composed fault/idle qualification.
    end endgenerate
'''
s=s[:a]+new+s[b:];p.write_text(s)
