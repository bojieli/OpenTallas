`timescale 1ns/1ps
module tb_hgi_coll_decode;
 parameter integer MUT_GROUP=0,MUT_ROW_BLOCK=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cmd_v=0,br=0,er=0;
 reg [7:0] g=96,die=0;
 reg [127:0] hdr=0;reg [31:0] count=0;reg count_valid=0;
 wire cr,bv,ev;wire [5:0] op;wire [3:0] gsz;
 wire [7:0] bg,rank,group_id,subgroup,block_size,dest;
 wire [20:0] rows;
 ot_hgi_coll_decode #(.ENABLE(1),.MUT_GROUP(MUT_GROUP),.MUT_ROW_BLOCK(MUT_ROW_BLOCK)) d
 (.clk(clk),.rst_n(rst_n),.coll_group_size(g),.die_id(die),.cmd_v(cmd_v),.cmd_r(cr),
 .hdr(hdr),.selected_count(count),.selected_count_valid(count_valid),.backend_v(bv),.backend_r(br),.backend_op(op),
 .backend_gsz(gsz),.backend_group_size(bg),.backend_rank(rank),.backend_group(group_id),
 .backend_subgroup(subgroup),.backend_owner_block(block_size),.backend_destinations(dest),
 .backend_row_count(rows),.error_v(ev),.error_r(er));
 integer cases=0,gg,r,o,k,j;reg [7:0] groups[0:7];
 reg [103:0] held;
 task issue;
  input integer group_size,dieid,operation,p,ia,ib,ct,expect_error;
  begin
   @(negedge clk);g=group_size;die=dieid;count=ct;count_valid=(ct!=0);
   hdr=0;hdr[127:124]=6;hdr[123:118]=operation;
   hdr[99:93]=(operation==5)?7'h51:7'h11;
   hdr[88:64]=p;hdr[63:32]=ia;hdr[31:0]=ib;cmd_v=1;
   if(!cr)$fatal(1,"notready");
   @(negedge clk);cmd_v=0;
   @(negedge clk);
   if(expect_error)begin
    if(!ev || bv)$fatal(1,"invalid command leaked to backend g=%0d op=%0d",group_size,operation);
    er=1;@(negedge clk);er=0;
   end else begin
    if(!bv || ev || op!=operation || bg!=group_size)$fatal(1,"dispatch mismatch");
    if(rank!=(dieid%group_size)||group_id!=(dieid/group_size))$fatal(1,"group isolation rank=%0d expected=%0d",rank,dieid%group_size);
    if(gsz!=((group_size==96)?15:((group_size==8)?3:((group_size==4)?2:((group_size==2)?1:0)))))$fatal(1,"group encode");
    if(subgroup!=((operation==4)?p:0))$fatal(1,"subgroup mismatch");
    if(block_size!=((operation==5)?p:0))$fatal(1,"owner block mismatch");
    if(dest!=((operation==5)?ib:group_size))$fatal(1,"destination mismatch");
    if(rows!=((operation==5)?((ct!=0)?ct:ia):0))$fatal(1,"rowcount mismatch");
    held={op,gsz,bg,rank,group_id,subgroup,block_size,dest,rows};
    repeat(3)begin
     @(negedge clk);hdr=~hdr;count=~count;die=~die;
     if(!bv || ev || cr || {op,gsz,bg,rank,group_id,subgroup,block_size,dest,rows}!==held)$fatal(1,"stall changed command");
    end
    br=1;@(negedge clk);br=0;
   end
   cases=cases+1;
  end
 endtask
 initial begin
  groups[0]=1;groups[1]=2;groups[2]=4;groups[3]=8;groups[4]=96;
  groups[5]=16;groups[6]=32;groups[7]=64;
  repeat(2)@(negedge clk);rst_n=1;
  if(gsz!=15 || bg!=96)$fatal(1,"DS reset changed");
  for(gg=0;gg<5;gg=gg+1)begin
   for(r=0;r<256;r=r+1)begin
    for(o=0;o<4;o=o+1) issue(groups[gg],r,o,0,0,0,0,0);
    for(k=2;k<=8;k=k*2)issue(groups[gg],r,4,k,0,0,0,k>groups[gg]);
    // k=7/512/2048 CF-COLL selected rows, every owner/destination rank;
    for(j=0;j<3;j=j+1)begin
     k=(j==0)?7:((j==1)?512:2048);
     issue(groups[gg],r,5,8,k,groups[gg],0,0);
     issue(groups[gg],r,5,8,999,groups[gg],k,0);
    end
   end
  end
  for(gg=5;gg<8;gg=gg+1)issue(groups[gg],0,0,0,0,0,0,1);
  issue(0,0,0,0,0,0,0,1);issue(96,0,63,0,0,0,0,1);
  issue(96,0,4,3,0,0,0,1);issue(96,0,5,0,7,8,0,1);
  issue(96,0,5,8,7,0,0,1);issue(96,0,5,8,7,97,0,1);
  issue(96,0,5,8,0,8,0,1);issue(96,0,5,8,1048576,8,0,0);issue(96,0,5,8,1048577,8,0,1);
  issue(96,0,5,8,7,8,1048576,0);issue(96,0,5,8,7,8,1048577,1);
  $display("PASS HGI-COLL decode cases=%0d DSreset96 allgroups/allranks k7/512/2048 hold/isolation/reserved",cases);$finish;
 end
endmodule
