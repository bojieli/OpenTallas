`timescale 1ns/1ps
// Own-flop output leaf. Every related input is captured at its actual boundary.
// One pending cell stage is included in empty; lp counts completed lines, not admission.
module ot_hgi_coll_tkm_packer #(parameter integer FW=512, MUT=0)(
 input wire clk,rst_n,start,
 input wire [12:0] cfg_nout,input wire [39:0] cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire cell_v,input wire [339:0] cell_t,input wire [1:0] cell_slot,input wire cell_last,
 input wire w_rdy,
 output reg w_v,output reg[39:0] w_addr,output reg[15:0] w_mask,output reg[FW-1:0] w_data,
 output wire[3:0] queued,output wire[9:0] lines_pushed,output wire empty
);
 localparam integer EW=85;
 wire[0:0] rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 wire rn=rr[0];
 reg start_q,cell_v_q,last_q; reg[1:0]slot_q; reg[339:0]cell_q;
 reg[12:0] nout_pin,nout_q,outn;reg[39:0]ob_pin,rb_pin,ob_q,rb_q;reg hr_pin,hr_q;
 reg[EW-1:0]lb[0:15];reg[9:0]lp;reg[8:0]line;
 reg[FW-1:0]lq_d[0:7];reg[39:0]lq_a[0:7];reg[15:0]lq_m[0:7];reg[3:0]lq_n;reg[2:0]lq_h,lq_t;
 wire lq_pop=(lq_n!=0)&&(!w_v||w_rdy);
 assign queued=lq_n;assign lines_pushed=lp;
 assign empty=(lq_n==0)&&!cell_v_q&&!w_v;
 integer i,s;
 always @(posedge clk)begin
   cell_q<=cell_t;slot_q<=cell_slot;last_q<=cell_last;
   nout_pin<=cfg_nout;ob_pin<=cfg_obase;rb_pin<=cfg_rbase;hr_pin<=cfg_has_r;
 end
 always @(posedge clk or negedge rn)begin
  if(!rn)begin start_q<=0;cell_v_q<=0;end
  else begin start_q<=start;cell_v_q<=cell_v;end
 end
    function automatic [31:0] unkey(input [31:0] k, input nz);
        unkey = nz ? 32'h8000_0000 : (k[31] ? (k & 32'h7FFF_FFFF) : ~k);
    endfunction
    function automatic [EW-1:0] tinv(input [EW-1:0] t);
        reg [81:0] b_;
        begin
            b_ = t[82:1];
            tinv = !t[84] ? {EW{1'b0}} : (!t[83] ? {1'b1, 1'b1, b_[49:18], b_[81:50], b_[17:0], t[0]} : {1'b0, 1'b1, b_, t[0]});
        end
    endfunction
 always @(posedge clk or negedge rn)begin
  if(!rn)begin
   w_v<=0;w_addr<=0;w_mask<=0;w_data<=0;
   nout_q<=1;ob_q<=0;rb_q<=0;hr_q<=0;
   outn<=0;line<=0;lp<=0;lq_n<=0;lq_h<=0;lq_t<=0;
  end else begin
            begin : pk
                reg [3:0] n_; reg [2:0] t_; reg [12:0] cnt_; reg [FW-1:0] od_, rd_; reg [15:0] m_; reg [EW-1:0] e_;
                reg [EW-1:0] lx [0:15];
                n_ = lq_n; t_ = lq_t;
                if (lq_pop) begin
                    w_v <= 1'b1; w_addr <= lq_a[lq_h]; w_mask <= lq_m[lq_h]; w_data <= lq_d[lq_h];
                    lq_h <= lq_h + 3'd1; n_ = n_ - 4'd1;
                end else if (w_v && w_rdy) w_v <= 1'b0;
                if (cell_v_q) begin
                    for (i = 0; i < 16; i = i + 1) lx[i] = lb[i];
                    for (s = 0; s < 4; s = s + 1) begin lx[4 * slot_q + s] = tinv(cell_q[EW*s +: EW]); lb[4 * slot_q + s] <= tinv(cell_q[EW*s +: EW]); end
                    
                    if (slot_q == 2'd3 || last_q) begin
                        cnt_ = ((nout_q - outn) >= 13'd16) ? 13'd16 : (nout_q - outn);
                        m_ = (cnt_ == 13'd16) ? 16'hFFFF : 16'((17'd1 << cnt_[4:0]) - 17'd1);
                        for (i = 0; i < 16; i = i + 1) begin
                            e_ = lx[i];
                            od_[32*i +: 32] = (13'(i) < cnt_) ? ((MUT == 1) ? e_[50:19] : ~e_[50:19]) : 32'd0;
                            rd_[32*i +: 32] = (13'(i) < cnt_) ? unkey(e_[82:51], e_[0]) : 32'd0;
                        end
                        lq_d[t_] <= od_; lq_a[t_] <= ob_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 3'd1; n_ = n_ + 4'd1;
                        if (hr_q) begin lq_d[t_] <= rd_; lq_a[t_] <= rb_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 3'd1; n_ = n_ + 4'd1; end
                        line <= line + 9'd1; outn <= outn + cnt_; lp <= lp + 10'd1;
                        for (i = 0; i < 16; i = i + 1) lb[i] <= {EW{1'b0}};
                    end
                end
                lq_n <= n_; lq_t <= t_;
            end
   if(start_q)begin
    nout_q<=nout_pin;ob_q<=ob_pin;rb_q<=rb_pin;hr_q<=hr_pin;
    outn<=0;line<=0;lp<=0;
    for(i=0;i<16;i=i+1)lb[i]<=0;
   end
  end
 end
endmodule
