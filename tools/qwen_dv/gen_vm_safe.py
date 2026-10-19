#!/usr/bin/env python3
"""Opt-in exact-two-edge VM candidate. Baseline source remains untouched.

Static bank/slot routing preserves priority even on faulty requests. Kept
registered onehot selects replace postcapture indexed data muxes. Parent
write-input fanout and native timing remain explicit closure obligations.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def generate():
    s=(ROOT/'rtl/qwen_dv/qfd_dv_vm.sv').read_text()
    a=s.index('    // write merge per bank')
    b=s.index('    // read requests:',a)
    s=s[:a]+r'''
    // Same combinational write edge, fixed destinations. Last active SU lane
    // wins a repeated low-slot address, including faulty schedules, as before.
    wire su_active=|su_we;
    wire [1:0] wb_we;
    wire [9:0] wb_row[0:1];
    wire [255:0] wb_d[0:1],wb_m[0:1];
    wire w_coll=(su_active && w1_we && su_waddr[3]==w1_addr[3]) ||
                (w16_we && (su_active || w1_we));
    wire [7:0] bad_su_lane;
    genvar wl;
    generate for(wl=0;wl<8;wl=wl+1) begin:g_write_check
        assign bad_su_lane[wl]=su_we[wl] &&
            ((su_waddr[24*wl+3+:21]!=su_waddr[3+:21]) || !su_we[0]);
    end endgenerate
    wire w_bad=(w1_we && w1_addr[23:14]!=0) ||
        (su_active && ((|bad_su_lane) || su_waddr[23:14]!=0)) ||
        (w16_we && (w16_addr[3:0]!=0 || w16_addr[23:14]!=0));
    genvar wb,ws,wi;
    generate for(wb=0;wb<2;wb=wb+1) begin:g_write_bank
        wire take_su=su_active && su_waddr[3]==wb;
        wire take_one=w1_we && w1_addr[3]==wb;
        assign wb_we[wb]=w16_we || take_su || take_one;
        assign wb_row[wb]=w16_we ? w16_addr[13:4] :
                            take_su ? su_waddr[13:4] :
                            take_one ? w1_addr[13:4] : 10'd0;
        for(ws=0;ws<8;ws=ws+1) begin:g_slot
            wire [7:0] hit,pick;
            for(wi=0;wi<8;wi=wi+1) begin:g_lane
                assign hit[wi]=su_we[wi] && su_waddr[24*wi+:3]==ws;
                if(wi==7) assign pick[wi]=hit[wi];
                else assign pick[wi]=hit[wi] && !(|(hit >> (wi+1)));
            end
            wire [31:0] sd=
                ({32{pick[0]}} & su_wdata[0+:32]) |
                ({32{pick[1]}} & su_wdata[32+:32]) |
                ({32{pick[2]}} & su_wdata[64+:32]) |
                ({32{pick[3]}} & su_wdata[96+:32]) |
                ({32{pick[4]}} & su_wdata[128+:32]) |
                ({32{pick[5]}} & su_wdata[160+:32]) |
                ({32{pick[6]}} & su_wdata[192+:32]) |
                ({32{pick[7]}} & su_wdata[224+:32]);
            wire one_slot=take_one && w1_addr[2:0]==ws;
            assign wb_d[wb][32*ws+:32]=w16_we ? w16_data[256*wb+32*ws+:32] :
                                      take_su ? sd : one_slot ? w1_data : 32'd0;
            assign wb_m[wb][32*ws+:32]={32{w16_we ||
                                      (take_su ? (|hit) : one_slot)}};
        end
    end endgenerate
''' +s[b:]
    a=s.index('    // stage 1 (macro read edge):')
    b=s.index('    // ------------------------------------------------------------------ CROM:',a)
    s=s[:a]+r'''
    // Stage1 captures per-lane address controls on the macro-read edge;
    // stage2 captures the macro outputs and onehot controls on the same edge.
    // Every select output drives <=32 data gates, with explicit kept identity.
    reg [3*512-1:0] cap;
    always @(posedge ck) cap<=vm_rd;
    wire [3*256-1:0] ext_q;
    genvar vo,vl,vs;
    generate for(vo=0;vo<3;vo=vo+1) begin:g_operand
        for(vl=0;vl<8;vl=vl+1) begin:g_lane
            wire [23:0] addr=(vo==0) ? a_addr[24*vl+:24] :
                               (vo==1) ? b_addr[24*vl+:24] : c_addr[24*vl+:24];
            wire [3:0] stage1;
            for(vs=0;vs<4;vs=vs+1) begin:g_s1
                // All lanes use lane0 bank, but each has its own kept copy.
                wire d=(vs==3) ? rq_a0[24*vo+3] : addr[vs];
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(1000+vo*128+vl*4+vs)) u_k
                    (.ck(ck),.d(d),.q(stage1[vs]));
            end
            wire [15:0] sel;
            wire [31:0] terms[0:15];
            for(vs=0;vs<16;vs=vs+1) begin:g_s2
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(2000+vo*128+vl*16+vs)) u_k
                    (.ck(ck),.d(stage1==vs),.q(sel[vs]));
                assign terms[vs]={32{sel[vs]}} & cap[512*vo+32*vs+:32];
            end
            assign ext_q[256*vo+32*vl+:32]=
                terms[0]|terms[1]|terms[2]|terms[3]|terms[4]|terms[5]|terms[6]|terms[7]|
                terms[8]|terms[9]|terms[10]|terms[11]|terms[12]|terms[13]|terms[14]|terms[15];
        end
    end endgenerate
    assign a_q=ext_q[0+:256];
    assign b_q=(MUT==5) ? ext_q[512+:256] : ext_q[256+:256];
    assign c_q=ext_q[512+:256];
''' +s[b:]
    a=s.index('    reg        c1_bank, c2_bank;')
    b=s.index('    // ------------------------------------------------------------------ BTAB:',a)
    s=s[:a]+r'''
    reg [1023:0] ccap;
    always @(posedge ck) ccap<=cr_rd;
    genvar cl,cs,ch;
    generate for(cl=0;cl<8;cl=cl+1) begin:g_c_lane
        wire [3:0] stage1;
        for(cs=0;cs<4;cs=cs+1) begin:g_s1
            wire d=(cs==3) ? cr_addr[3] : cr_addr[24*cl+cs];
            (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(3000+cl*4+cs)) u_k
                (.ck(ck),.d(d),.q(stage1[cs]));
        end
        wire [63:0] value;
        for(ch=0;ch<2;ch=ch+1) begin:g_half
            wire [15:0] sel;
            wire [31:0] terms[0:15];
            for(cs=0;cs<16;cs=cs+1) begin:g_s2
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(4000+cl*32+ch*16+cs)) u_k
                    (.ck(ck),.d(stage1==cs),.q(sel[cs]));
                assign terms[cs]={32{sel[cs]}} & ccap[512*(cs/8)+256*ch+32*(cs%8)+:32];
            end
            assign value[32*ch+:32]=
                terms[0]|terms[1]|terms[2]|terms[3]|terms[4]|terms[5]|terms[6]|terms[7]|
                terms[8]|terms[9]|terms[10]|terms[11]|terms[12]|terms[13]|terms[14]|terms[15];
        end
        assign cr_q[64*cl+:64]=(MUT==4) ? {value[31:0],value[63:32]} : value;
    end endgenerate
''' +s[b:]
    a=s.index('    reg [1:0] t1_bank, t2_bank, s1b_bank, s2b_bank;')
    b=s.index('    // ------------------------------------------------------------------ PROG:',a)
    s=s[:a]+r'''
    reg [1:0] t1_bank,s1b_bank;
    reg [2047:0] btcap;
    always @(posedge ck) begin
        t1_bank<=bt_word[1:0];s1b_bank<=bs_word[1:0];btcap<=bt_rd;
    end
    genvar tc,tg,ts;
    generate for(tc=0;tc<2;tc=tc+1) begin:g_bt_port
        for(tg=0;tg<8;tg=tg+1) begin:g_chunk
            wire [3:0] sel;
            wire [31:0] terms[0:3];
            for(ts=0;ts<4;ts=ts+1) begin:g_s2
                wire [1:0] bank=(tc==0) ? t1_bank : s1b_bank;
                (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(5000+tc*32+tg*4+ts)) u_k
                    (.ck(ck),.d(bank==ts),.q(sel[ts]));
                assign terms[ts]={32{sel[ts]}} & btcap[1024*tc+256*ts+32*tg+:32];
            end
            if(tc==0) assign bt_q[32*tg+:32]=terms[0]|terms[1]|terms[2]|terms[3];
            else assign bs_q[32*tg+:32]=terms[0]|terms[1]|terms[2]|terms[3];
        end
    end endgenerate
''' +s[b:]
    a=s.index('    reg p1_bank;')
    b=s.index('    // ------------------------------------------------------------------ faults',a)
    s=s[:a]+r'''
    reg p1_bank;
    reg [1023:0] pcap;
    always @(posedge ck) begin p1_bank<=p_idx[0];pcap<=p_rd;end
    genvar pg,ps;
    generate for(pg=0;pg<15;pg=pg+1) begin:g_p_chunk
        localparam integer CW=(457-32*pg<32) ? 457-32*pg : 32;
        wire [1:0] sel;
        wire [CW-1:0] term[0:1];
        for(ps=0;ps<2;ps=ps+1) begin:g_s2
            (* keep_hierarchy="yes" *) qfd_dv_vm_keep_bit #(.ID(6000+pg*2+ps)) u_k
                (.ck(ck),.d(p1_bank==ps),.q(sel[ps]));
            assign term[ps]={CW{sel[ps]}} & pcap[512*ps+32*pg+:CW];
        end
        assign p_q[32*pg+:CW]=term[0]|term[1];
    end endgenerate
''' +s[b:]
    # The baseline reused l/b across unrelated combinational blocks. Preserve
    # its remaining CROM table wiring loop variables after removing write loop.
    at=s.index('    // ------------------------------------------------------------------ read-side')
    s=s[:at]+'    integer b;\n'+s[at:]
    s+='''\n// Independent parameter identities preserve each physical select copy.\nmodule qfd_dv_vm_keep_bit #(parameter integer ID=0)(input wire ck,d, (* keep *) output reg q);\n    always @(posedge ck) q<=d;\nendmodule\n'''
    return '// GENERATED OPT-IN VM SAFE CANDIDATE; native qualification pending.\n'+s


def main():
    p=ROOT/'rtl/qwen_dv/qfd_dv_vm_safe.sv';p.write_text(generate());print(p)


if __name__=='__main__':main()
