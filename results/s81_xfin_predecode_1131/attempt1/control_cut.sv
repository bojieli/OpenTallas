`timescale 1ns/1ps
// Fixed delay line: q is d delayed by D cycles (D = 0 is a wire).  Data lines
// carry no reset -- validity travels on a separate, reset delay line -- so a
// wide operand costs flops and no reset fan-out.
module ot_hdc_delay #(
    parameter integer W = 32,
    parameter integer D = 1,
    parameter integer RESET = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D == 0) begin : g_wire
            assign q = d;
        end else if (D == 1) begin : g_one
            reg [W-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {W{1'b0}};
                    else line <= d;
            end else begin : g_nrst
                always @(posedge clk) line <= d;
            end
            assign q = line;
        end else begin : g_line
            reg [W*D-1:0] line;
            if (RESET != 0) begin : g_rst
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) line <= {(W*D){1'b0}};
                    else line <= {line[W*(D-1)-1:0], d};
            end else begin : g_nrst
                always @(posedge clk) line <= {line[W*(D-1)-1:0], d};
            end
            assign q = line[W*D-1 -: W];
        end
    endgenerate
endmodule

module ot_hdc_vline #(parameter integer D = 1) (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       v,
    output wire [D:0] vd
);
    reg [D:1] line;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) line <= {D{1'b0}};
        else line <= {line[D-1:1], v};
    end
    assign vd = {line, v};
endmodule
module top #(parameter NV=80, LA=6, MUT=0)(input clk,rstn,input [$clog2(3*((NV<=1)?1:(1<<$clog2(NV))))-1:0] t_q,input f_q);
    localparam integer T   = 3;
    localparam integer NVP = (NV <= 1) ? 1 : (1 << $clog2(NV));
    localparam integer HB  = $clog2(NVP);
    localparam integer NC  = T * NVP;   // issue candidates (tree-major)
    localparam integer CW  = $clog2(NC);
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer isadd(input integer n);
        integer H;
        begin
            H = HB - ($clog2(n + 1) - 1);
            isadd = (n >= 1 && n < NVP && ((((2 * n + 1) << (H - 1)) - NVP) < NV)) ? 1 : 0;
        end
    endfunction

wire [CW-1:0] wr_n;
    ot_hdc_delay #(.W(CW), .D(LAV)) u_t (.clk(clk), .rst_n(rstn), .d(t_q), .q(wr_n));
wire [LAV:0] av;
ot_hdc_vline #(.D(LAV)) u_v(.clk(clk),.rst_n(rstn),.v(f_q),.vd(av));
wire wr_v=av[LAV];
wire [NC-1:0] early,late,newwrite;
genvar t,n;
generate for(t=0;t<T;t=t+1) begin:g_tree
 for(n=0;n<NVP;n=n+1) begin:g_node
  localparam C=t*NVP+n;
  if(n>=1 && isadd(n)) begin:g_live
   assign early[C]=(t_q==C);
   assign late[C]=wr_v && (wr_n==C);
  end else begin:g_dead
   assign early[C]=0;
   assign late[C]=0;
  end
 end
end endgenerate
wire [NC-1:0] delayed;
ot_hdc_delay #(.W(NC),.D(LAV)) u_oh(.clk(clk),.rst_n(rstn),.d(early),.q(delayed));
assign newwrite=delayed & {NC{wr_v}};
reg initialized=0;
always @(posedge clk) begin
 if(!rstn) initialized<=1;
 if(initialized) assert(late==(newwrite ^ ((MUT && wr_v)? {{(NC-2){1'b0}},2'b10}: {NC{1'b0}})));
end
endmodule
