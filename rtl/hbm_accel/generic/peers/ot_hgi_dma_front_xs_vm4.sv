`timescale 1ns/1ps
`default_nettype none
// Native B2 formatter: metadata lookahead plus two payload capture edges after internal controller pick from held sector/selection to pin output.
// Output wd={mirror,sector15,data256,mask8}; v_o supplies the separate dq valid bit.
// Main sectors<32768 retain global sid; mirror32768..36863 targets all four copies.
// Sector>=36864 is flagged bad_o with zero mask: HCAP has a separate endpoint.
// Ownership transport and commit acknowledgements belong to the enclosing vehicle.
module ot_hgi_dma_front_xs_vm4 #(
    parameter integer NIN = 16,
    parameter integer NBS = 8,
    parameter integer MUT = 0,
    // PREG 1 (A3 HBM group A 2026-10-14, route hgi_dfmain13-src15-1a9409837 post-CTS TT -410 ps / 4,062 endpoints:
    // ls_* port -> 64-way lane/quarter AND-OR -> p_s with ~200 um of wire on each side, 10 logic levels, and a native
    // capture far over 190 ps): every ls bit lands in ONE pin flop (ls_q, unconditional); metadata is read from ls_q
    // (the same edge the old meta_* captured, so qsel is unchanged); the payload select and the conversion share one
    // edge from ls_q / qsel straight into the output register wl_d (the p_s stage is gone: -1 formatter edge, the root
    // stays < 15k: +4,432 pin flops -1,232 meta -2,224 p_*).  ls is held from the metadata edge until its registered
    // acknowledgment returns, so ls_q one edge later presents the same word.  PREG 0 = source15.
    parameter integer PREG = 1
) (
    input  wire                  clk,
    input  wire [NBS*NIN-1:0]    pick_d,
    input wire [(NIN/2)*277-1:0] ls_a,ls_b,
    output wire [NBS*280-1:0]    wd,
    output wire [NBS-1:0]       v_o,
    output wire [NBS-1:0]       bad_o
);
    wire [NIN*277-1:0] ls={ls_b,ls_a};
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    // conv: every slice is a constant (word w of quarter 0): no runtime part-select (src16c; the j argument was
    // always 2'd0 at every call site and is kept only so the call sites stay byte-identical).
    function automatic [255:0] conv(input [255:0] s, input [2:0] f, input [1:0] j);
        reg [255:0] o; reg [7:0] b; reg [15:0] h;
        begin
            o = 256'd0;
            for (int w = 0; w < 8; w = w + 1) begin
                case (f)
                    3'd1: begin h = (MUT == 1) ? s[(7 - w) * 16 +: 16] : s[w * 16 +: 16]; o[w*32 +: 32] = {h, 16'd0}; end
                    3'd2: begin b = s[w * 8 +: 8]; o[w*32 +: 32] = e4m3_f(b); end
                    3'd4: begin b = s[w * 8 +: 8]; o[w*32 +: 32] = i8_f(b); end
                    default: o[w*32 +: 32] = s[w*32 +: 32];
                endcase
            end
            conv = o;
        end
    endfunction

    generate if (PREG == 0) begin : g_src15
    // Metadata is captured with the controller's request/epoch input station.
        // A selected held packet cannot change until its registered acknowledgment
        // returns; data still enters a payload register before conversion/output FFs.
        reg [1:0] meta_low[0:NIN-1];reg [2:0] meta_f[0:NIN-1];
        reg [17:0] meta_sector[0:NIN-1][0:3];
        for(genvar i=0;i<NIN;i++)begin:metadata
          always @(posedge clk)begin
            meta_low[i]<=ls[i*277+256+:2];meta_f[i]<=ls[i*277+274+:3];
            for(integer q=0;q<4;q++)meta_sector[i][q]<=ls[i*277+256+:18]+18'(q);
          end
        end
        for(genvar b=0;b<NBS;b++)begin:bk
          reg [NIN*4-1:0] qsel;reg x_v,p_v,w_v,w_bad;
          reg [255:0] p_s;reg [2:0] p_f;reg [17:0] p_s18;reg [279:0] wl_d;
          assign wd[b*280+:280]=wl_d;assign v_o[b]=w_v;assign bad_o[b]=w_bad;
          always @(posedge clk)begin
            for(integer i=0;i<NIN;i++)for(integer q=0;q<4;q++)
              qsel[i*4+q]<=pick_d[b*NIN+i]&&(meta_low[i]==2'(b-q));
            x_v<=pick_d[b*NIN+:NIN]!='0;
          end
          always @(posedge clk)begin:word_capture
            reg [255:0] selected;reg [2:0] f;reg [17:0] sector;
            selected=0;f=0;sector=0;
            for(integer i=0;i<NIN;i++)begin
              if(qsel[i*4+:4]!='0)f=f|meta_f[i];
              for(integer q=0;q<4;q++)if(qsel[i*4+q])begin
                sector=sector|meta_sector[i][q];
                case(meta_f[i])
                  3'd1:if(q<2)selected=selected|{128'd0,ls[i*277+q*128+:128]};
                  3'd2,3'd4:selected=selected|{192'd0,ls[i*277+q*64+:64]};
                  default:selected=selected|ls[i*277+:256];
                endcase
              end
            end
            p_s<=selected;p_f<=f;p_s18<=sector;p_v<=x_v;
            w_v<=p_v;w_bad<=p_v&&p_s18>=18'd36864;
            wl_d<={(MUT==8)?1'b0:(p_s18>=18'd32768&&p_s18<18'd36864),p_s18[14:0],conv(p_s,p_f,2'd0),p_s18>=18'd36864 ? 8'h00 : 8'hff};
          end
        end
    end else begin : g_preg
        reg [NIN*277-1:0] ls_q;
        always @(posedge clk) ls_q <= ls;                      // one pin flop per ls bit, no enable
        // per lane x quarter: the format-selected payload word and the sector, computed ONCE and shared by the 8 banks
        wire [NIN*4*256-1:0] lw;
        wire [NIN*4*18-1:0]  ls_sec;
        for(genvar i=0;i<NIN;i++)begin:lane
          wire [2:0] lf=ls_q[i*277+274+:3];
          for(genvar q=0;q<4;q++)begin:quarter
            assign ls_sec[(i*4+q)*18+:18]=ls_q[i*277+256+:18]+18'(q);
            assign lw[(i*4+q)*256+:256]=(lf==3'd1)?((q<2)?{128'd0,ls_q[i*277+q*128+:128]}:256'd0):
                            (lf==3'd2||lf==3'd4)?{192'd0,ls_q[i*277+q*64+:64]}:ls_q[i*277+:256];
          end
        end
        for(genvar b=0;b<NBS;b++)begin:bk
          reg [NIN*4-1:0] qsel;reg x_v,w_v,w_bad;reg [279:0] wl_d;
          assign wd[b*280+:280]=wl_d;assign v_o[b]=w_v;assign bad_o[b]=w_bad;
          always @(posedge clk)begin
            for(integer i=0;i<NIN;i++)for(integer q=0;q<4;q++)
              qsel[i*4+q]<=pick_d[b*NIN+i]&&(ls_q[i*277+256+:2]==2'(b-q));
            x_v<=pick_d[b*NIN+:NIN]!='0;
          end
          always @(posedge clk)begin:word_out
            reg [255:0] selected;reg [2:0] f;reg [17:0] sector;
            selected=0;f=0;sector=0;
            // src16c: explicit AND-OR (mask, then OR) instead of if-guarded accumulation: synthesis sees a balanced
            // 64-input OR per bit, not a 64-deep priority mux chain feeding conv (src16/16b synthesis passed 2,700 s).
            for(integer i=0;i<NIN;i++)begin
              f=f|({3{qsel[i*4+:4]!='0}}&ls_q[i*277+274+:3]);
              for(integer q=0;q<4;q++)begin sector=sector|({18{qsel[i*4+q]}}&ls_sec[(i*4+q)*18+:18]);selected=selected|({256{qsel[i*4+q]}}&lw[(i*4+q)*256+:256]);end
            end
            w_v<=x_v;w_bad<=x_v&&sector>=18'd36864;
            wl_d<={(MUT==8)?1'b0:(sector>=18'd32768&&sector<18'd36864),sector[14:0],conv(selected,f,2'd0),sector>=18'd36864 ? 8'h00 : 8'hff};
          end
        end
    end endgenerate
endmodule
`default_nettype wire
