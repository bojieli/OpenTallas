`timescale 1ns/1ps
module tb_hnx_union_compiled;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cfg_we=0,union_v=0;
 reg [13:0] cfg_addr=0;reg [80:0] cfg_data=0;reg [9:0] union_count=0;
 wire busy,fault,done,selected_v,launch_v;wire [9:0] selected_u;wire [13:0] selected_base;
 wire [15:0] launch_mask;wire [31:0] launch_record;
 reg [4:0] shift=0;
 ot_hnx_union_calendar #(.MUT(MUT)) dut(.*,.n_rows(5'd6),.topk(4'd6),.bank_base(14'd0),.bank_shift(shift));
 reg [80:0] image[0:16383];integer fd,rc,words,stride,u,n,age,i,j,total=0;
 integer times[0:1023],masks[0:1023],ids[0:1023],terminal;
 initial begin
  $readmemh("calendar.mem",image);
  fd=$fopen("cases.txt","r");rc=$fscanf(fd,"%d %d\n",words,stride);
  shift=5'($clog2(stride));
  repeat(4) @(negedge clk);rst_n=1;
  for(i=0;i<words;i=i+1)begin @(negedge clk);cfg_we=1;cfg_addr=14'(i);cfg_data=image[i];end
  @(negedge clk);cfg_we=0;
  for(u=6;u<=36;u=u+1)begin
   rc=$fscanf(fd,"%d %d\n",n,terminal);
   for(i=0;i<n;i=i+1)rc=$fscanf(fd,"%d %d %d\n",times[i],masks[i],ids[i]);
   @(negedge clk);union_v=1;union_count=10'(u);
   @(negedge clk);union_v=0;
   if(!selected_v || selected_u!=u || selected_base!=(u-6)*stride)
    $fatal(1,"COMPILED_WRONG_VARIANT U%0d selected%0d",u,selected_u);
   j=0;
   for(age=1;age<=terminal;age=age+1)begin
    @(negedge clk);
    if(fault)$fatal(1,"COMPILED calendar fault U%0d age%0d",u,age);
    if(launch_v)begin
     if(j>=n || age!=times[j] || launch_mask!=masks[j] || launch_record!=ids[j])
      $fatal(1,"COMPILED event U%0d age%0d expected%0d token%0d",u,age,times[j],launch_record);
     j=j+1;total=total+1;
    end else if(j<n && age==times[j])$fatal(1,"COMPILED missing launch");
    if(done && age!=terminal)$fatal(1,"COMPILED early done");
   end
   if(j!=n || !done || busy)$fatal(1,"COMPILED incomplete");
  end
  $fclose(fd);$display("UNION_COMPILED PASS L2_N6_P3 variants31 launches%0d static_no_ready",total);$finish;
 end
endmodule
