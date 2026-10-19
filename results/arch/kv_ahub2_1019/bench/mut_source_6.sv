`timescale 1ns/1ps
// PRIVATE FUNCTIONAL ONLY; no native/production binding. Source successor143642.
// ENABLE defaults OFF. Indexed4slot READ_OLD, accepted edge n -> landing n+4.
module qkd_ahub_grouped_root_private #(parameter integer MUT=0)(
 input wire clk,raw_rst_n,output wire group_rst_n);
 (* keep="true",dont_touch="true" *) reg a0,a1;
 always @(posedge clk or negedge raw_rst_n)
   if(!raw_rst_n) begin a0<=1'b0;a1<=1'b0;end
   else begin a0<=1'b1;a1<=a0;end
 assign group_rst_n=(MUT==1)?a1:(raw_rst_n & ((MUT==2)?a0:a1));
endmodule
module qkd_ahub_grouped_leaf_private #(parameter integer MUT=0)(
 input wire clk,rst_n_in,output wire ready,qualified);
 (* keep="true",dont_touch="true" *) reg s0,s1,q0,q1;
 always @(posedge clk or negedge rst_n_in)
   if(!rst_n_in) begin s0<=1'b0;s1<=1'b0;end
   else begin s0<=1'b1;s1<=s0;end
 always @(posedge clk) begin q0<=s1;q1<=q0;end
 assign ready=(MUT==3)?q0:q1;
 assign qualified=s1;
endmodule
module qkd_ahub_grouped_transport_private #(
 parameter integer W=268,BANK_BITS=8,GROUP_BANKS=8,MUT=0
)(input wire clk,tx_rst_n,rx_rst_n,in_valid,input wire[W-1:0]d,
 output wire[W-1:0]q,output wire out_valid,accept);
 localparam integer BANKS=(W+BANK_BITS-1)/BANK_BITS;
 localparam integer GROUPS=(BANKS+GROUP_BANKS-1)/GROUP_BANKS;
 wire[GROUPS-1:0] ga,gv,rx_authority;
 // Reduction trees are binary equations with one consumer per intermediate.
 wire[GROUPS:0] accept_tree,output_tree;
 assign accept_tree[0]=1'b1;assign output_tree[0]=1'b1;
 assign accept=accept_tree[GROUPS];assign out_valid=output_tree[GROUPS];
 genvar g,b,s,k;
 generate for(g=0;g<GROUPS;g=g+1) begin:g_group
   localparam integer NB=((BANKS-g*GROUP_BANKS)<GROUP_BANKS)?BANKS-g*GROUP_BANKS:GROUP_BANKS;
   wire tx_gr,rx_gr;
   qkd_ahub_grouped_root_private #(.MUT(MUT)) u_tx_root(clk,tx_rst_n,tx_gr);
   qkd_ahub_grouped_root_private #(.MUT(MUT)) u_rx_root(clk,rx_rst_n,rx_gr);
   wire[NB:0] ready_tree,valid_tree;
   assign ready_tree[0]=1'b1;assign valid_tree[0]=1'b1;
   (* keep="true",dont_touch="true" *) reg ingress_valid;
   wire admission=in_valid & tx_gr & rx_gr & ready_tree[NB];
   always @(posedge clk) ingress_valid<=admission;
   assign ga[g]=admission;assign gv[g]=valid_tree[NB];assign rx_authority[g]=rx_gr;
   assign accept_tree[g+1]=accept_tree[g] & ga[g];
   assign output_tree[g+1]=output_tree[g] & (gv[g] & rx_authority[g]);
   for(b=0;b<NB;b=b+1) begin:g_bank
     localparam integer BI=g*GROUP_BANKS+b;
     localparam integer BW=((W-BI*BANK_BITS)<BANK_BITS)?W-BI*BANK_BITS:BANK_BITS;
     wire tr,tq,rr,rq;
     qkd_ahub_grouped_leaf_private #(.MUT(MUT)) u_tx_reset(clk,tx_gr,tr,tq);
     qkd_ahub_grouped_leaf_private #(.MUT(MUT)) u_rx_reset(clk,rx_gr,rr,rq);
     wire bank_ready=tr & tq & rr & rq;
     wire active=rr & rq;
     assign ready_tree[b+1]=ready_tree[b] & bank_ready;
     (* keep="true",dont_touch="true" *) reg[BW-1:0] ingress,ring_q,landing;
     // This is genuine indexed storage. Native macro binding remains HOLD.
     (* keep="true",dont_touch="true" *) reg[BW-1:0] payload[0:3];
     (* keep="true",dont_touch="true" *) reg[1:0] phase;
     (* keep="true",dont_touch="true" *) reg[3:0] slot_valid;
     (* keep="true",dont_touch="true" *) reg ring_valid,landing_valid;
     wire[3:0] dec,we;
     wire[3:0] read_dec;
     wire[3:0] valid_terms;
     wire[BW-1:0] read_terms[0:3];
     for(s=0;s<4;s=s+1) begin:g_slot
       assign dec[s]=(phase==s);
       assign we[s]=active & dec[s];
       // rotation by2 gives READ_OLD: source slot n becomes read n+2.
       assign read_dec[s]=dec[(s+2+((MUT==5 && BI==0)?1:0))%4];
       always @(posedge clk) if(we[s]) payload[s]<=ingress;
       always @(posedge clk)
         if(!active) slot_valid[s]<=1'b0;
         else if(we[s]) slot_valid[s]<=(MUT==4)?1'b1:ingress_valid;
       assign read_terms[s]=payload[s] & {BW{read_dec[s]}};
       assign valid_terms[s]=slot_valid[s] & read_dec[s];
     end
     wire[BW-1:0] read_word=(read_terms[0]|read_terms[1])|(read_terms[2]|read_terms[3]);
     wire read_valid=(valid_terms[0]|valid_terms[1])|(valid_terms[2]|valid_terms[3]);
     always @(posedge clk) begin
       ingress<=d[BI*BANK_BITS+:BW];
       if(!active) begin phase<=2'b0;ring_valid<=1'b0;end
       else begin phase<=phase+2'd1;ring_q<=read_word;ring_valid<=read_valid;end
       landing<=ring_q;
     end
     always @(posedge clk or negedge rq)
       if(!rq) landing_valid<=1'b0;
       else if(!rr) landing_valid<=1'b0;
       else landing_valid<=ring_valid;
     assign q[BI*BANK_BITS+:BW]=landing;
     assign valid_tree[b+1]=valid_tree[b] & landing_valid;
   end
 end endgenerate
`ifndef SYNTHESIS
 initial if(W<1 || BANK_BITS<1 || BANK_BITS>8 || GROUP_BANKS<1 || GROUP_BANKS>8)
   $fatal(1,"private grouped transport bounds");
`endif
endmodule
module qkd_ahub_grouped_zh_transport_private #(
 parameter integer ENABLE=0,MUT_CMD=0,MUT_RETURN=0
)(input wire clk,core_rst_n,child_rst_n,command_valid,return_valid,
 input wire[267:0]command_word,input wire[67:0]return_word,
 output wire[267:0]child_command,output wire[67:0]core_return,
 output wire command_out_valid,return_out_valid,command_accept,return_accept);
 generate if(ENABLE) begin:g_private
   qkd_ahub_grouped_transport_private #(.W(268),.MUT(MUT_CMD)) u_command
     (clk,core_rst_n,child_rst_n,command_valid,command_word,child_command,command_out_valid,command_accept);
   wire[67:0]owned_return;
   if(1) begin:g_wrong_owner
     reg[3:0]previous_fault;
     always @(posedge clk) previous_fault<=return_word[67:64];
     assign owned_return={previous_fault,return_word[63:0]};
   end else begin:g_owned
     assign owned_return=return_word;
   end
   qkd_ahub_grouped_transport_private #(.W(68),.MUT(MUT_RETURN)) u_return
     (clk,child_rst_n,core_rst_n,return_valid,owned_return,core_return,return_out_valid,return_accept);
 end else begin:g_default_off
   assign child_command=command_word;assign core_return=return_word;
   assign command_out_valid=command_valid;assign return_out_valid=return_valid;
   assign command_accept=command_valid;assign return_accept=return_valid;
 end endgenerate
endmodule
