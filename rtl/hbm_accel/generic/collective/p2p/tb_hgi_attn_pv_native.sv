`timescale 1ns/1ps
`default_nettype none
module tb_hgi_attn_pv_native;
 import ot_hgi_attn_pv_pkg::*;
 import "DPI-C" function int unsigned f32add(input int unsigned a,input int unsigned b);
 localparam integer NC=1100;
 parameter integer MUT_CARRY=0;
 integer mutant=0;
 bit continuous=0;
 string program_dir="",program_path;
 ring_cmd_t hexprog[0:NC-1];
 reg[255:0] boundary_prog[0:3][0:NC-1];
 reg[31:0] program_cycles[0:1];
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 ring_cmd_t prog[0:3][0:NC-1],cmd[0:3];
 local_cmd_t lp[0:NC-1],lc;
 reg [255:0] boundary[0:3];
 reg [1:0] dest;
 reg [3:0] land[0:NC-1],landing;
 reg singles[0:NC-1],single_v;reg [255:0] single_data;
 wire out_v,local_fault,scratch_fault;wire[255:0] out_data;
 wire[3:0] ring_fault,rr;
 ot_hgi_attn_pv_native #(.MUT_CARRY(MUT_CARRY)) dut(.clk(clk),.rst_n(rst_n),.cmd(cmd),.boundary_data(boundary),
  .dest_q(dest),.landing_slot(landing),.local_cmd(lc),.single_v(single_v),.single_data(single_data),
  .out_v(out_v),.out_data(out_data),.ring_fault(ring_fault),.local_fault(local_fault),
  .scratch_fault(scratch_fault),.ring_rr_v(rr));
    function automatic integer nextq(input integer q);case(q)0:nextq=1;1:nextq=3;3:nextq=2;default:nextq=0;endcase endfunction
    function automatic integer prevq(input integer q);case(q)0:prevq=2;1:prevq=0;3:prevq=1;default:prevq=3;endcase endfunction
    function automatic integer pos(input integer q);case(q)0:pos=0;1:pos=1;3:pos=2;default:pos=3;endcase endfunction

 function automatic [31:0] term(input integer k,input integer lane,input integer blocks,input integer seed);
  if(k>=blocks)return 0;
  case(k%8)
   0:return 32'h60ad78ec+32'(seed*31+lane);
   1:return 32'h3f400000+32'(seed*13+lane*53+k*17);
   2:return 32'he0ad78ec+32'(seed*31+lane);
   3:return 32'hbf200000+32'(seed*19+lane*29+k*311);
   4:return 32'h3f800000+32'(seed*7+lane*31);
   5:return 32'h40000000+32'(seed*5+lane*37);
   6:return 32'hbf000000+32'(seed*3+lane*41);
   default:return 32'h3e800000+32'(seed*11+lane*43);
  endcase
 endfunction
 // Declared boundary block: 128 rows, 16 chunks of 8 sequential FP32
 // terms, followed by the exact pairwise chunk tree. Expected data only.
 function automatic [31:0] partial(input integer k,input integer lane,input integer blocks,input integer seed);
  reg[31:0] chunk[0:15];integer n;
  if(k>=blocks)return 0;
  for(integer j=0;j<16;j++)begin
   chunk[j]=0;
   for(integer t=0;t<8;t++)chunk[j]=f32add(chunk[j],term(k,lane,blocks,seed+j*8+t));
  end
  n=16;
  while(n>1)begin
   for(integer j=0;j<n/2;j++)chunk[j]=f32add(chunk[j*2],chunk[j*2+1]);
   n=n/2;
  end
  return chunk[0];
 endfunction
 function automatic [255:0] golden(input integer blocks,input integer seed);
  reg[31:0] vals[0:63];reg[255:0] answer;integer n;
  for(integer l=0;l<8;l++)begin
   for(integer k=0;k<64;k++)vals[k]=partial(k,l,blocks,seed);
   n=blocks==1?1:blocks==5?8:64;
   while(n>1)begin
    for(integer k=0;k<n/2;k++)vals[k]=f32add(vals[2*k],vals[2*k+1]);
    n=n/2;
   end
   answer[l*32+:32]=vals[0];
  end
  return answer;
 endfunction
    task automatic send(input integer source,input integer dest,input integer cyc,input integer tag,
                        input bit result,input bit acc,input integer round);
        integer d,q,t,hops;
        d=result?0:(((pos(dest)-pos(source)+4)%4)==3?1:0);
        if(prog[source][cyc].inject[d] || prog[source][cyc].fwd[d])$fatal(1,"compiler injection collision");
        if(|prog[source][cyc].inject && (prog[source][cyc].tx_tag!=3'(tag) ||
           prog[source][cyc].dst!=2'(dest) || prog[source][cyc].result!=result ||
           prog[source][cyc].acc!=acc))$fatal(1,"compiler shared injection payload collision");
        prog[source][cyc].inject[d]=1;prog[source][cyc].tx_tag=3'(tag);prog[source][cyc].dst=2'(dest);
        prog[source][cyc].result=result;prog[source][cyc].acc=acc;
        if(prog[source][cyc-1].read_tx)$fatal(1,"compiler TX state read collision");
        prog[source][cyc-1].read_tx=1;prog[source][cyc-1].read_tx_tag=3'(tag);prog[source][cyc-1].read_tx_acc=acc;
        q=source;t=cyc;hops=result?3:((d==0)?(pos(dest)-pos(source)+4)%4:(pos(source)-pos(dest)+4)%4);
        if(hops==0)$fatal(1,"compiler zero route");
        for(integer h=1;h<=hops;h=h+1)begin
            q=d?prevq(q):nextq(q);t=t+2;
            if(prog[q][t].rx[d])$fatal(1,"compiler receive collision");
            prog[q][t].rx[d]=1;prog[q][t].kind[d*2+:2]=result?2:1;
            prog[q][t].src[d*2+:2]=2'(source);prog[q][t].tag[d*3+:3]=3'(tag);
            if(h<hops)begin
                if(prog[q][t].inject[d] || prog[q][t].fwd[d])$fatal(1,"compiler forwarding collision");
                prog[q][t].fwd[d]=1;
            end
            
        end
        if(result)begin
            prog[source][cyc].rr=1;prog[source][cyc].rr_tag=3'(tag);
            prog[source][cyc-1].read_rr=1;prog[source][cyc-1].read_rr_tag=3'(tag);
        end
    endtask
    task automatic add(input integer q,input integer cyc,input integer tag,input integer source,input bit rhsacc);
        if(prog[q][cyc].add_v)$fatal(1,"compiler adder collision");
        if(prog[q][cyc-1].read_add)$fatal(1,"compiler ADD state read collision");
        prog[q][cyc-1].read_add=1;prog[q][cyc-1].read_add_tag=3'(tag);prog[q][cyc-1].read_add_src=2'(source);prog[q][cyc-1].read_rhs_acc=rhsacc;
        prog[q][cyc].add_v=1;prog[q][cyc].add_tag=3'(tag);prog[q][cyc].add_src=2'(source);prog[q][cyc].rhs_acc=rhsacc;
    endtask

 integer checked=0,mismatches=0;
 initial begin
  if($value$plusargs("mutant=%d",mutant))begin end
  if($value$plusargs("PROGRAM_DIR=%s",program_dir))begin end
  continuous=$test$plusargs("NO_RESET");
  if(continuous&&program_dir=="")$fatal(1,"NO_RESET requires external clear calendar");
  for(integer shape=0;shape<3;shape++)begin
   for(integer batch=0;batch<(shape==0?128:64);batch++)begin
    integer head,blocks,quartets,c,last,seed,final_cycle;reg[255:0] expected;
    head=(batch/16)%4;
    blocks=shape==0?64:shape==1?5:1;quartets=(blocks+3)/4;seed=batch+shape*128;
    if(!continuous||(shape==0&&batch==0))rst_n=0;
    dest=2'(head);lc='0;single_v=0;landing=0;
    for(integer q=0;q<4;q++)begin cmd[q]='0;boundary[q]=0;end
    for(integer t=0;t<NC;t++)begin
     lp[t]='0;land[t]=0;singles[t]=0;
     for(integer q=0;q<4;q++)prog[q][t]='0;
    end
    if(blocks==1)begin
     singles[0]=1;
     for(integer l=0;l<8;l++)single_data[l*32+:32]=partial(0,l,blocks,seed);
     c=4;
    end else begin
     for(integer g=0;g<quartets;g++)begin
      integer b;b=g*40;
      for(integer q=0;q<4;q++)begin
       prog[q][b].lp_we=1;
       for(integer l=0;l<8;l++)prog[q][b].lp_data[l*32+:32]=partial((mutant==1&&blocks==64)?(4*((g*4+q)%16)+(g*4+q)/16):g*4+q,l,blocks,seed);
      end
      send(0,1,b+2,0,0,0,0);send(2,3,b+2,0,0,0,0);
      add(1,b+6,0,0,0);add(3,b+6,0,2,0);
      send(1,3,b+16,0,0,1,0);add(3,b+20,0,1,1);
      send(3,3,b+30,0,1,1,0);
      for(integer t=b+30;t<b+39;t++)land[t]=4'(g);
     end
     c=quartets*40;
    end
    // Compact pairwise local tree. scratch reads are actual registered RTL.
    for(integer width=quartets;width>1;width=width/2)begin
     for(integer k=0;k<width;k+=2)begin
      lp[c-1].scratch_read_v=1;lp[c-1].scratch_read=4'(k);
      lp[c].load_v=1;
      lp[c+1].scratch_read_v=1;lp[c+1].scratch_read=4'(k+1);
      lp[c+2].add_read=1;lp[c+3].add_issue=1;
      lp[c+12].pub_read=1;lp[c+13].pub_issue=1;
      lp[c+14].capture=1;lp[c+14].capture_slot=4'(k/2);
      c+=16;
     end
    end
    // Final publication also covers the single-node / two-quartet cases.
    lp[c-1].scratch_read_v=1;lp[c-1].scratch_read=0;lp[c].load_v=1;
    lp[c+2].pub_read=1;lp[c+3].pub_issue=1;last=c+4;
    if(mutant==2&&blocks>1)lp[c-1].pub_read=1;
    expected=golden(blocks,seed);final_cycle=c+3;
    for(integer q=0;q<4;q++)for(integer t=0;t<NC;t++)boundary_prog[q][t]=prog[q][t].lp_data;
    if(program_dir!="")begin
     program_path=$sformatf("%s/shape%0d/dst%0d",program_dir,blocks,head);
     $readmemh({program_path,"/cycles.hex"},program_cycles);
     final_cycle=program_cycles[0];last=program_cycles[1];
     for(integer q=0;q<4;q++)begin
      $readmemh($sformatf("%s/ring%0d.hex",program_path,q),hexprog);
      for(integer t=0;t<NC;t++)prog[q][t]=hexprog[t];
     end
     $readmemh({program_path,"/local.hex"},lp);
     $readmemh({program_path,"/landing.hex"},land);
     $readmemh({program_path,"/single.hex"},singles);
    end
    if(!continuous||(shape==0&&batch==0))begin repeat(4)@(negedge clk);rst_n=1;end
    for(integer t=0;t<=last;t++)begin
     for(integer q=0;q<4;q++)begin cmd[q]=prog[q][t];boundary[q]=boundary_prog[q][t];end
     lc=lp[t];landing=land[t];single_v=singles[t];
     @(posedge clk);#0.01;
     if(mutant==2&&((|ring_fault)||local_fault||scratch_fault))begin $display("ATTN_NATIVE EARLYPUB REJECTED");$finish;end
     if((|ring_fault)||local_fault||scratch_fault)$fatal(1,"ATTN_NATIVE fault shape%0d h%0d cycle%0d ring%h local%0d scratch%0d cause%h",blocks,head,t,ring_fault,local_fault,scratch_fault,dut.fault_cause);
     if(t==final_cycle)begin
      if(!out_v)$fatal(1,"ATTN_NATIVE missing final output");
      if(out_data!==expected)begin
       mismatches++;
       if(mutant==0&&MUT_CARRY==0)$fatal(1,"ATTN_NATIVE mismatch blocks%0d h%0d got%h expected%h",blocks,head,out_data,expected);
      end
      checked+=8;
     end
     @(negedge clk);
    end
    if(batch==0)$display("ATTN_NATIVE shape blocks=%0d cycles=%0d lanes=8 batches=%0d",blocks,last+1,shape==0?128:64);
   end
  end
  if(mutant==1||MUT_CARRY!=0)begin
   if(mismatches==0)$fatal(1,"ATTN_NATIVE mutant survived");
   $display("ATTN_NATIVE MUTANT REJECTED mutant=%0d carry=%0d mismatches=%0d",mutant,MUT_CARRY,mismatches);
  end else if(mutant==2)$fatal(1,"ATTN_NATIVE earlypub survived");
  else $display("ATTN_NATIVE PASS checked=%0d batches=256",checked);
  $finish;
 end
endmodule
