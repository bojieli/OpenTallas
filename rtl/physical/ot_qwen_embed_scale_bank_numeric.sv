`timescale 1ns/1ps
// Default-unintegrated scale leaf. Three static instances cover the vocabulary.
// Fault-free ROM contract: payload has NO ECC/parity. Mutable row/credit/phase/
// pointer/lane/valid metadata is complement checked, and fail-stops publication.
module ot_qwen_embed_scale_bank_numeric #(
    parameter integer BANK_ID=0,
    parameter integer OCRED=4
)(input wire clk,rst_n,i_v, input wire [17:0] i_row,
  output reg i_cr, output reg o_v, output reg [15:0] o_data,
  input wire o_cr, output reg fault);
    localparam integer CW=$clog2(OCRED+1)+1;
    (* keep="true", dont_touch="true" *) reg fault_n;
    (* keep="true", dont_touch="true" *) wire iv_q,cr_q,iv_n,cr_n;
    (* keep="true", dont_touch="true" *) wire [17:0] row_q,row_n;
    // RTL integration vehicle. Physical adoption must bind the hardened island
    // view and keep this existing capture stage out of payload-leaf CTS.
    ot_qwen_embedding_ingress_numeric #(.AW(18)) u_ingress(
        .clk(clk),.rst_n(rst_n),.address(i_row),.valid(i_v),.credit(o_cr),
        .address_q(row_q),.address_n(row_n),.valid_q(iv_q),.valid_n(iv_n),
        .credit_q(cr_q),.credit_n(cr_n));
    (* keep="true", dont_touch="true" *) wire [17:0] fifo[0:1],fifo_n[0:1];
    // Stable mapped-net aliases for the already-required independent FIFO rails.
    genvar metadata_word;
    generate for(metadata_word=0;metadata_word<2;metadata_word=metadata_word+1) begin:g_metadata_fifo
        (* keep="true", dont_touch="true" *) reg [17:0] primary;
        assign fifo[metadata_word]=primary;
        (* keep="true", dont_touch="true" *) reg [17:0] shadow;
        assign fifo_n[metadata_word]=shadow;
        (* keep="true", dont_touch="true" *) always @(posedge clk)
            if(iv_q && !full && !fault && !bad && wp[0]==metadata_word) begin
                primary<=row_q;shadow<=~row_q;
            end
    end endgenerate
    (* keep="true", dont_touch="true" *) reg [1:0] wp,rp,wp_n,rp_n;
    (* keep="true", dont_touch="true" *) reg [CW-1:0] credits,credits_n;
    (* keep="true", dont_touch="true" *) reg phase,phase_n;
    wire empty=wp==rp;
    wire full=wp[0]==rp[0] && wp[1]!=rp[1];
    wire [17:0] head=fifo[rp[0]];
    wire row_bad=(row_q[17:16]!=BANK_ID || row_q>=151936 || row_n!=~row_q);
    (* keep="true", dont_touch="true" *) reg [3:0] valid_pipe,valid_n;
    (* keep="true", dont_touch="true" *) reg [3:0] lane_pipe[0:3],lane_n[0:3];
    wire meta_bad=(fault_n!=~fault)||(iv_n!=~iv_q)||(cr_n!=~cr_q)||(ce_n!=~ce_q)||
                  (ce_q && addr_n!=~addr_q)||(capture_en_q!={8{valid_pipe[2]}})||
                  (wp_n!=~wp)||(rp_n!=~rp)||(credits_n!=~credits)||
                  (phase_n!=~phase)||(valid_n!=~valid_pipe)||
                  (!empty && fifo_n[rp[0]]!=~head)||
                  (valid_pipe[0] && lane_n[0]!=~lane_pipe[0])||
                  (valid_pipe[1] && lane_n[1]!=~lane_pipe[1])||
                  (valid_pipe[2] && lane_n[2]!=~lane_pipe[2])||
                  (valid_pipe[3] && lane_n[3]!=~lane_pipe[3]);
    wire launch=!phase && !empty && credits!=0 && !fault && !meta_bad;
    wire [CW-1:0] next_credits=credits-launch+cr_q;
    wire bad=meta_bad || (iv_q && (full || row_bad)) || next_credits>OCRED;
    (* keep="true", dont_touch="true" *) reg [11:0] addr_q,addr_n;
    (* keep="true", dont_touch="true" *) reg ce_q,ce_n;
    wire [265:0] rom_data;
    ot_rom_4096x266_m8 u_scale(.clk(clk),.ce_in(ce_q),.addr_in(addr_q),.rd_out(rom_data));
    (* keep="true", dont_touch="true" *) reg [255:0] capture;
    (* keep="true",dont_touch="true" *) reg [7:0] capture_en_q;
    genvar g;
    generate for(g=0;g<8;g=g+1) begin:g_cap
        (* keep="true", dont_touch="true" *) always @(posedge clk or negedge rst_n)
            if(!rst_n) capture_en_q[g]<=0;
            else capture_en_q[g]<=valid_pipe[1];
        // Actual macro launch is one edge after launch; this capture is TWO
        // further edges later. Lane selection occurs on the following edge.
        always @(posedge clk) if(capture_en_q[g]) capture[g*32+:32]<=rom_data[g*32+:32];
    end endgenerate
    integer n;
    (* keep="true", dont_touch="true" *) always @(posedge clk) begin
        if(launch) begin addr_q<=head[15:4];addr_n<=~head[15:4];end
        if(valid_pipe[3] && !fault && !bad) o_data<=capture[lane_pipe[3]*16+:16];
    end
    (* keep="true", dont_touch="true" *) always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            wp<=0;wp_n<=2'b11;rp<=0;rp_n<=2'b11;
            credits<=OCRED;credits_n<=~OCRED;
            phase<=0;phase_n<=1;ce_q<=0;ce_n<=1;valid_pipe<=0;valid_n<=4'hf;
            o_v<=0;i_cr<=0;fault<=0;fault_n<=1;
            for(n=0;n<4;n=n+1) begin lane_pipe[n]<=0;lane_n[n]<=4'hf;end
        end else begin
            phase<=~phase;phase_n<=phase;
            valid_pipe<={valid_pipe[2:0],launch};valid_n<=~{valid_pipe[2:0],launch};
            lane_pipe[0]<=head[3:0];lane_n[0]<=~head[3:0];
            for(n=1;n<4;n=n+1) begin lane_pipe[n]<=lane_pipe[n-1];lane_n[n]<=lane_n[n-1];end
            ce_q<=launch;ce_n<=~launch;
            o_v<=valid_pipe[3] && !fault && !bad;i_cr<=launch;
            if(iv_q && !full && !fault && !bad) begin wp<=wp+1'b1;wp_n<=~(wp+2'd1);end
            if(launch) begin rp<=rp+1'b1;rp_n<=~(rp+2'd1);end
            credits<=next_credits;credits_n<=~next_credits;
            if(bad) begin fault<=1;fault_n<=0;end
        end
    end
endmodule
