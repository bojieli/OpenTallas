`timescale 1ns/1ps
`default_nettype none
// Publication mechanism vehicle: actual frontend command metadata, actual XS,
// BF16 column arithmetic, actual PV merge/stack/fold and scalar publication.
// BF16 row inputs are the declared seed boundary. Converter/HBM/top-SM
// integration and physical timing are outside this vehicle's scope.
module tb_hbm_sm_folded_leaf;
 import "DPI-C" function int unsigned f32add(input int unsigned a,input int unsigned b);
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg[191:0] calendar_words[0:499],command;
 reg[817:0] seed_row;
 reg seed_v=0;
 reg[2:0] column;reg[1:0] row;
 wire[3271:0] rl,rr;wire[4137:0] bl,br;wire[42:0] request;
 wire rv,frontfault,schedulefault;wire[11:0] rrow;wire[255:0] rdata;
 wire gv,gf;wire[31:0] gy;wire[15:0] gt;
 ot_hbm_sm_attn_front_static front(.clk(clk),.rst_n(rst_n),.command(command),.kv_desc(64'd0),.packet(1099'd0),
 .xw_en(1'b0),.xw_addr(7'd0),.xw_grp(7'd0),.xw_data(2048'd0),.request(request),.rl(rl),.rr(rr),
 .bl(bl),.br(br),.ql(184'd0),.qr(184'd0),.rv(rv),.rrow(rrow),.rdata(rdata),.fault(frontfault),.schedule_fault(schedulefault));
 ot_hbm_sm_attn_leafh leaf(.clk(clk),.rst_n(rst_n),.attn_column(column),.attn_row(row),
 .xs_a1(9'd0),.xs_g1(5'd0),.xs_a2(7'd0),.xs_g2(5'd0),
 .rl1(seed_v?seed_row:rl[0+:818]),.bk1(2069'd0),.ohl1(13'd0),.gv(gv),.gf(gf),.gy(gy),.gt(gt));
 function automatic [15:0] weight(input integer slot,input integer lane);
  return 16'h3f80+16'(slot*16+lane);
 endfunction
 function automatic [31:0] node(input integer slot,input integer lane);
  reg[31:0] y;y=0;
  for(integer t=0;t<8;t++)y=f32add(y,{weight(slot,lane),16'd0});
  return y;
 endfunction
 function automatic[31:0] golden(input integer parity,input integer lane);
  return f32add(f32add(node(parity,lane),node(parity+2,lane)),f32add(node(parity+4,lane),node(parity+6,lane)));
 endfunction
 integer checked=0,first_reference=-1,mutant=0;
 string file;
 initial begin:run_gate
  if(!$value$plusargs("CMD=%s",file))$fatal(1,"need compiler CMD");
  if($value$plusargs("mutant=%d",mutant))begin end
  $readmemh(file,calendar_words);
  for(integer col=0;col<8;col++)for(integer lr=0;lr<4;lr++)begin
   integer seen,first_seen,prev_cycle;reg[531:0] meta;reg[255:0] weights;reg[21:0] control;
   rst_n=0;seed_v=0;seed_row=0;command=0;column=3'(col);row=2'(lr);seen=0;first_seen=-1;prev_cycle=-1;
   repeat(6)@(negedge clk);rst_n=1;
   for(integer c=0;c<500;c++)begin
    command=calendar_words[c] | (192'ha2<<184) | (192'd6<<181) | (192'd1<<180);
    if(mutant==1)command[124]=0;
    if(mutant==2&&command[131])command[130:128]=command[127:125];
    seed_v=c>=20&&c<84;
    if(seed_v)begin
     integer slot,t;slot=(c-20)%8;t=(c-20)/8;
     meta=0;meta[130:128]=6;meta[131]=1;meta[132]=1;meta[133]=1;meta[137]=1;
     for(integer cc=0;cc<8;cc++)meta[cc*16+:16]=16'h3f80;
     for(integer l=0;l<16;l++)weights[l*16+:16]=weight(slot,l);
     control={1'b0,1'b1,(t==0),(t==7),1'b1,1'b1,12'd0,1'b0,3'(slot)};
     seed_row={control,weights,meta,1'b0,7'd0};
    end
    @(posedge clk);#0.01;
    if(frontfault||schedulefault||gf)begin
     if(mutant!=0)begin $display("FOLDED_LEAF MUTANT REJECTED mutant=%0d fault=1 cycle=%0d",mutant,c);$finish;disable run_gate;end
     $fatal(1,"FOLDED_LEAF fault col%0d row%0d cyc%0d front%0d sched%0d leaf%0d",col,lr,c,frontfault,schedulefault,gf);
    end
    if(gv)begin
     if(gy!==golden(col%2,seen)||gt!==16'((((col%2)*64+lr*16+seen)<<4)|8))begin
      if(mutant!=0)begin $display("FOLDED_LEAF MUTANT REJECTED mutant=%0d fault=0",mutant);$finish;disable run_gate;end
      $fatal(1,"FOLDED_LEAF mismatch col%0d row%0d cyc%0d word%0d data%h want%h tag%h",col,lr,c,seen,gy,golden(col%2,seen),gt);
     end
     if(seen==0)first_seen=c;
     else if(c!=prev_cycle+1)$fatal(1,"FOLDED_LEAF publication bubble");
     prev_cycle=c;seen++;checked++;
    end
    @(negedge clk);
   end
   if(seen!=16)$fatal(1,"FOLDED_LEAF expected16 words got%0d col%0d row%0d",seen,col,lr);
   if(first_reference<0)begin
    first_reference=first_seen;
    if(first_reference!=291)$fatal(1,"FOLDED_LEAF command-to-publication must be11edges");
   end
   if(first_seen!=first_reference+16*lr)$fatal(1,"FOLDED_LEAF stagger mismatch");
  end
  if(mutant!=0)$fatal(1,"FOLDED_LEAF mutant survived");
  $display("FOLDED_LEAF PASS words=%0d columns=8 rows=4 first=%0d row_stagger=16",checked,first_reference);$finish;
 end
endmodule
`default_nettype wire
