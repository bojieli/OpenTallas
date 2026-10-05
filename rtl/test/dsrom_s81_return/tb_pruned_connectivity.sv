`timescale 1ns/1ps
// Compare new connectivity against the complete padded original tree on every
// output-valid cycle, identity, arithmetic result, error and sticky fault.
module tb_pruned_connectivity;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 reg[9:0]lv=0,le=0;reg[319:0]lt=0,ld=0;
 wire[15:0]fullv={2'b0,lv[9:4],4'b0,lv[3:0]};
 wire[15:0]fulle={2'b0,le[9:4],4'b0,le[3:0]};
 wire[511:0]fullt={64'd0,lt[319:128],128'd0,lt[127:0]};
 wire[511:0]fulld={64'd0,ld[319:128],128'd0,ld[127:0]};
 wire[1:0]rv,re,fv,fe;wire[31:0]row,bf,frow,fbf;wire[5:0]pos,fpos;wire[63:0]fp,ffp;wire fault,ffault;
 ot_v41_return_rd64_pruned5 dut(.clk(clk),.rst_n(rst_n),.lv(lv),.le(le),.lt(lt),.ld(ld),
 .rv(rv),.re(re),.rrow(row),.rbf16(bf),.rpos(pos),.rfp32(fp),.fault(fault));
 ot_v41_return_rd64_reference8 ref_dut(.clk(clk),.rst_n(rst_n),.lv(fullv),.le(fulle),.lt(fullt),.ld(fulld),
 .rv(fv),.re(fe),.rrow(frow),.rbf16(fbf),.rpos(fpos),.rfp32(ffp),.fault(ffault));
 integer sent[0:9];integer k,seg,nseg,r,iter,c=0,got=0,mode=0,faultcycles=0;
 function integer segment(input integer leaf);
 case(leaf)0:segment=0;1:segment=2;2:segment=-1;3:segment=1;
 4:segment=4;5:segment=0;6:segment=3;7:segment=1;8:segment=2;default:segment=-1;endcase
 endfunction
 function[31:0]value(input integer iteration,input integer s);
 case(s)0:value=(iteration%2)?32'h4b800000:32'h3f800001;
 1:value=(iteration%2)?32'hcb800000:32'hbf800000;
 2:value=32'h3f800000;3:value=32'h3f800000;default:value=32'h33800000;endcase
 endfunction
 always @(posedge clk)if(rst_n)begin
 c=c+1;
 for(k=0;k<10;k=k+1)if(lv[k])sent[k]=sent[k]+1;
 end
 always @(negedge clk)if(rst_n)begin
 if(rv!==fv || fault!==ffault)$fatal(1,"cycle/fault mismatch at%0d",c);
 for(r=0;r<2;r=r+1)if(rv[r])begin
 if({re[r],row[16*r+:16],pos[3*r+:3],fp[32*r+:32],bf[16*r+:16]} !==
    {fe[r],frow[16*r+:16],fpos[3*r+:3],ffp[32*r+:32],fbf[16*r+:16]})$fatal(1,"identity/arithmetic/error mismatch");
 if(mode==0)got=got+1;
 end
 if(fault)faultcycles=faultcycles+1;
 if(mode==0 && got==64)begin mode=1;$display("FUNCTIONAL rows=%0d cycle=%0d",got,c);end
 if(mode==1 && c>800)begin
  if(faultcycles==0)$fatal(1,"overflow witness not exercised");
  $display("PASS_PRUNED_CONNECTIVITY rows=%0d cycles=%0d identical_fault_cycles=%0d",got,c,faultcycles);$finish;
 end
 lv=0;le=0;
 for(k=0;k<10;k=k+1)begin
 if(mode==0)begin
  seg=segment(k);nseg=k<4?3:5;iter=sent[k];
  lv[k]=seg>=0 && iter<32 && c%(k%3+2)!=0;
  lt[32*k+:32]={3'(iter%6),16'(iter),5'(seg),3'd0,5'(nseg)};
  ld[32*k+:32]=value(iter,seg);
  le[k]=(iter%7)==0 && seg==0;
 end else begin
  // Excess unmatched traffic exercises the retained sticky overflow path;
  // no READY is invented and both trees see exactly the same valid offers.
  lv[k]=k<2;lt[32*k+:32]={3'd0,16'(1000+2*c+k),5'd0,3'd0,5'd2};
  ld[32*k+:32]=32'h3f800000;
 end
 end
 end
 initial begin for(k=0;k<10;k=k+1)sent[k]=0;#22;rst_n=1;end
 initial begin repeat(2048)@(posedge clk);$fatal(1,"new connectivity workload incomplete");end
endmodule
