`timescale 1ns/1ps
// Source-local mandatory controller cuts. No shared FP or delay primitive edits.
module ot_hdc_su_ctl_mul16 #(parameter integer W=24)(
    input wire clk, input wire [15:0] a, input wire [W-1:0] b, output wire [W-1:0] y
);
    reg [W-1:0] part [0:3];
    reg [W-1:0] lo, hi;
    wire [W-1:0] lo_sum, hi_sum;
    genvar n;
    generate for(n=0;n<4;n=n+1) begin : g_nibble
        always @(posedge clk) part[n] <= (a[n*4+:4] * b) << (n*4);
    end endgenerate
    ot_hdc_ksadd_k #(.W(W)) u_lo(.a(part[0]),.b(part[1]),.cin(1'b0),.s(lo_sum),.cout());
    ot_hdc_ksadd_k #(.W(W)) u_hi(.a(part[2]),.b(part[3]),.cin(1'b0),.s(hi_sum),.cout());
    always @(posedge clk) begin lo<=lo_sum; hi<=hi_sum; end
    ot_hdc_ksadd_k #(.W(W)) u_final(.a(lo),.b(hi),.cin(1'b0),.s(y),.cout());
endmodule

module ot_hdc_su_ctl_delay #(
    parameter integer LOCAL=0, W=32, D=1, RESET=0, WORD=16
)(input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q);
    generate if(LOCAL==0) begin : g_legacy
        ot_hdc_delay #(.W(W),.D(D),.RESET(RESET)) u(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
    end else if(D==0) begin : g_wire
        assign q=d;
    end else begin : g_local
        genvar b,s;
        for(b=0;b<(W+WORD-1)/WORD;b=b+1) begin : g_word
            localparam integer BW=(W-b*WORD<WORD)?W-b*WORD:WORD;
            wire [BW-1:0] stage [0:D];
            assign stage[0]=d[b*WORD+:BW];
            for(s=0;s<D;s=s+1) begin : g_stage
                (* keep *) reg [BW-1:0] data;
                wire [BW-1:0] capture;
                if(s==0) begin : g_first
                    assign capture=stage[s];
                end else begin : g_half_cycle
                    (* keep *) reg [BW-1:0] bridge;
                    if(RESET!=0) begin : g_reset
                        always @(negedge clk or negedge rst_n) if(!rst_n) bridge<=0;else bridge<=stage[s];
                    end else begin : g_data
                        always @(negedge clk) bridge<=stage[s];
                    end
                    assign capture=bridge;
                end
                if(RESET!=0) begin : g_reset
                    always @(posedge clk or negedge rst_n) if(!rst_n) data<=0;else data<=capture;
                end else begin : g_data
                    always @(posedge clk) data<=capture;
                end
                assign stage[s+1]=data;
            end
            assign q[b*WORD+:BW]=stage[D];
        end
    end endgenerate
endmodule

module ot_hdc_su_ctl_insert #(
    parameter integer LOCAL=0,W=32,K=2,
    parameter [16*K-1:0] DEPTHS={16'd3,16'd0},
    parameter integer DMAX=3,RESET_DATA=0,WORD=16
)(input wire clk,rst_n,v,input wire [K-1:0] sel,input wire [W-1:0] d,
  output wire vo,output wire [W-1:0] q,output wire coll,busy);
    generate if(LOCAL==0) begin : g_legacy
        ot_hdc_v41x_ins #(.W(W),.K(K),.DEPTHS(DEPTHS),.DMAX(DMAX),.RESET_DATA(RESET_DATA)) u(.*);
    end else if(DMAX==0) begin : g_wire
        assign vo=v;assign q=d;assign coll=1'b0;assign busy=1'b0;
    end else begin : g_local
        function automatic has(input integer p,input [K-1:0] choices);
            integer k;begin has=0;for(k=0;k<K;k=k+1) if(DEPTHS[k*16+:16]==p&&choices[k]) has=1;end
        endfunction
        // Preserve the original positive-edge identity, collision and busy
        // equations. Only the internal shift input crosses a half-cycle FF.
        wire [DMAX+1:1] valid_stage;
        wire [DMAX:1] collisions;
        assign valid_stage[DMAX+1]=0;
        genvar vstage;
        for(vstage=1;vstage<=DMAX;vstage=vstage+1) begin : g_valid
            wire load=v&&has(vstage,sel);
            wire shifted;
            (* keep *) reg item;
            if(vstage<DMAX) begin : g_half_cycle
                (* keep *) reg bridge;
                always @(negedge clk or negedge rst_n)
                    if(!rst_n) bridge<=0;else bridge<=valid_stage[vstage+1];
                assign shifted=bridge;
            end else begin : g_end
                assign shifted=0;
            end
            always @(posedge clk or negedge rst_n)
                if(!rst_n) item<=0;else item<=load||shifted;
            assign valid_stage[vstage]=item;
            assign collisions[vstage]=load&&valid_stage[vstage+1];
        end
        wire now=v&&has(0,sel);
        assign vo=now||valid_stage[1];
        assign coll=(|collisions)||(now&&valid_stage[1]);
        assign busy=|valid_stage[DMAX:1];
        localparam integer NW=(W+WORD-1)/WORD;
        genvar b,p;
        for(b=0;b<NW;b=b+1) begin : g_word
            localparam integer BW=(W-b*WORD<WORD)?W-b*WORD:WORD;
            wire [BW-1:0] stage [1:DMAX+1];
            assign stage[DMAX+1]=0;
            for(p=1;p<=DMAX;p=p+1) begin : g_stage
                wire load=v&&has(p,sel);
                (* keep *) reg [BW-1:0] data;
                wire [BW-1:0] shifted;
                if(p<DMAX) begin : g_half_cycle
                    (* keep *) reg [BW-1:0] bridge;
                    if(RESET_DATA!=0) begin : g_reset
                        always @(negedge clk or negedge rst_n) if(!rst_n) bridge<=0;else bridge<=stage[p+1];
                    end else begin : g_data
                        always @(negedge clk) bridge<=stage[p+1];
                    end
                    assign shifted=bridge;
                end else begin : g_end
                    assign shifted=0;
                end
                if(RESET_DATA!=0) begin : g_reset
                    always @(posedge clk or negedge rst_n) if(!rst_n) data<=0;
                        else data<=load?d[b*WORD+:BW]:shifted;
                end else begin : g_data
                    always @(posedge clk) data<=load?d[b*WORD+:BW]:shifted;
                end
                assign stage[p]=data;
            end
            assign q[b*WORD+:BW]=(v&&has(0,sel))?d[b*WORD+:BW]:stage[1];
        end
    end endgenerate
endmodule
