`timescale 1ns/1ps
// Own-flop output leaf. Every related input is captured at its actual boundary.
// One pending cell stage is included in empty; lp counts completed lines, not admission.
module ot_hgi_coll_tkm_packer #(parameter integer FW=512, MUT=0, ACK_SEAM=0)(
 input wire clk,rst_n,start,
 input wire [12:0] cfg_nout,input wire [39:0] cfg_obase,cfg_rbase,input wire cfg_has_r,
 input wire cell_v,input wire [339:0] cell_t,input wire [1:0] cell_slot,input wire cell_last,
 input wire w_rdy,input wire w_ack,output reg w_seq,
 output reg w_v,output reg[39:0] w_addr,output reg[15:0] w_mask,output reg[FW-1:0] w_data,
 output wire[3:0] queued,output wire[9:0] lines_pushed,output wire empty
);
 localparam integer EW=85;
 wire[0:0] rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 wire rn=rr[0];
 reg start_q,cell_v_q,last_q; reg[1:0]slot_q; reg[339:0]cell_q;
 reg[12:0] nout_pin,nout_q,outn;reg[39:0]ob_pin,rb_pin,ob_q,rb_q,ob_next,rb_next;reg hr_pin,hr_q;
 reg[EW-1:0]lb[0:15];reg[9:0]lp;reg[8:0]line;
 reg[FW-1:0]lq_d[0:7];reg[39:0]lq_a[0:7];reg[15:0]lq_m[0:7];reg[3:0]lq_n;reg[2:0]lq_h,lq_t;
 reg ack_pin;always @(posedge clk)ack_pin<=w_ack;
 wire accepted=ACK_SEAM?(w_v&&(ack_pin==w_seq)):(w_v&&w_rdy);
 wire lq_pop=(lq_n!=0)&&(!w_v||accepted);
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
 // Payload enables come only from local captured control, never the reset relay.
 always @(posedge clk)begin:p_dat
  reg[EW-1:0]lx[0:15],e_;reg[12:0]cnt_;reg[15:0]m_;reg[FW-1:0]od_,rd_;
  if(cell_v_q)begin
   for(integer i_=0;i_<16;i_=i_+1)lx[i_]=lb[i_];
   for(integer s_=0;s_<4;s_=s_+1)begin
    lx[4*slot_q+s_]=tinv(cell_q[EW*s_+:EW]);lb[4*slot_q+s_]<=tinv(cell_q[EW*s_+:EW]);
   end
   if(slot_q==3||last_q)begin
    cnt_=((nout_q-outn)>=16)?13'd16:(nout_q-outn);m_=(cnt_==16)?16'hffff:16'((17'd1<<cnt_[4:0])-1);
    for(integer i_=0;i_<16;i_=i_+1)begin
     e_=lx[i_];od_[32*i_+:32]=(13'(i_)<cnt_)?((MUT==1)?e_[50:19]:~e_[50:19]):32'd0;
     rd_[32*i_+:32]=(13'(i_)<cnt_)?unkey(e_[82:51],e_[0]):32'd0;
    end
    lq_d[lq_t]<=od_;lq_a[lq_t]<=ob_next;lq_m[lq_t]<=m_;
    if(hr_q)begin lq_d[3'(lq_t+3'd1)]<=rd_;lq_a[3'(lq_t+3'd1)]<=rb_next;lq_m[3'(lq_t+3'd1)]<=m_;end
    for(integer i_=0;i_<16;i_=i_+1)lb[i_]<=0;
   end
  end
  if(start_q)for(integer i_=0;i_<16;i_=i_+1)lb[i_]<=0;
 end
 // Independent local pointer feedback retains each physical mux selector copy.
 for(genvar chunk=0;chunk<(FW+31)/32;chunk=chunk+1)begin:g_rd_chunk
  (* keep *)reg[2:0]h_local;
  always @(posedge clk or negedge rn)
   if(!rn)h_local<=0;else if(lq_pop)h_local<=h_local+1'b1;
  always @(posedge clk)if(lq_pop)w_data[32*chunk+:32]<=lq_d[h_local][32*chunk+:32];
 end
 always @(posedge clk)if(lq_pop)begin w_addr<=lq_a[lq_h];w_mask<=lq_m[lq_h];end
 always @(posedge clk or negedge rn)begin
  if(!rn)begin
   w_seq<=0;w_v<=0;
   nout_q<=1;ob_q<=0;rb_q<=0;ob_next<=0;rb_next<=0;hr_q<=0;
   outn<=0;line<=0;lp<=0;lq_n<=0;lq_h<=0;lq_t<=0;
  end else begin
            begin:pk
             reg[3:0]n_;reg[2:0]t_;reg[12:0]cnt_;
             n_=lq_n;t_=lq_t;
             if(lq_pop)begin w_seq<=!w_seq;w_v<=1;lq_h<=lq_h+1'b1;n_=n_-1'b1;end
             else if(accepted)w_v<=0;
             if(cell_v_q&&(slot_q==3||last_q))begin
              cnt_=((nout_q-outn)>=16)?13'd16:(nout_q-outn);
              t_=t_+1'b1;n_=n_+1'b1;
              if(hr_q)begin t_=t_+1'b1;n_=n_+1'b1;end
              ob_next<=ob_next+40'd16;rb_next<=rb_next+40'd16;line<=line+1'b1;outn<=outn+cnt_;lp<=lp+1'b1;
             end
             lq_n<=n_;lq_t<=t_;
            end
   if(start_q)begin
    nout_q<=nout_pin;ob_q<=ob_pin;rb_q<=rb_pin;ob_next<=ob_pin;rb_next<=rb_pin;hr_q<=hr_pin;
    outn<=0;line<=0;lp<=0;
   end
  end
 end
endmodule
