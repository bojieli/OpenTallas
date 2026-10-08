module tb_sm_serial_owner;
reg clk,rst_n;
reg run_valid;
wire run_ready;
reg [31:0] program_base;
reg [32:0] program_limit;
reg [15:0] record_count;
wire mem_req_valid;
reg mem_req_ready;
wire [31:0] mem_req_addr;
reg mem_rsp_valid;
wire mem_rsp_ready;
reg [31:0] mem_rsp_addr,mem_rsp_data;
reg mem_rsp_error;
wire alloc_valid;
reg alloc_ready;
wire [15:0] alloc_record;
wire [23:0] alloc_lines;
reg alloc_rsp_valid;
wire alloc_rsp_ready;
reg [15:0] alloc_rsp_record;
reg [31:0] alloc_rsp_base;
reg alloc_rsp_error;
wire x_req_valid;
reg x_req_ready;
wire [15:0] x_req_record;
wire [6:0] x_req_base;
wire [7:0] x_req_extent;
reg x_valid;
wire x_ready;
reg [15:0] x_record;
reg [6:0] x_ordinal;
reg [3:0] x_group;
reg [2047:0] x_data;
reg x_error;
wire xw_en;
wire [6:0] xw_addr,xw_grp;
wire [2047:0] xw_data;
wire d_valid;
reg d_ready;
wire [31:0] d_base;
wire [23:0] d_lines;
wire start;
reg start_ready;
wire [12:0] op_rows;
wire [15:0] op_c;
wire [7:0] op_g;
wire op_gs;
wire [1:0] op_fmt;
wire [6:0] op_xb;
reg arrive;
reg sm_fault;
reg publication_valid;
wire publication_ready;
reg [15:0] publication_record;
wire done;
reg done_ready;
wire fault;
 ot_hbm_sm_serial_owner #(.ENABLE(1)) dut(.*);
 always #5 clk=~clk;
 reg[31:0] words[0:129];
 integer cyc=0,ops=0,captures=0,total_captures=0,xi=0,xg=0,xrec=0,expected_captures=0;
 integer delay_retire=0,delay_publish=0,j;
 integer state_cycles[0:13];
 reg x_active=0; reg[2047:0] expected_data;
 reg[1023:0] fixture;
 function automatic[2047:0] pattern(input integer rec,ord,grp);
  integer b;begin for(b=0;b<64;b=b+1)pattern[b*32+:32]=(rec*65536+ord*256+grp*64+b)^32'hac13579b;end
 endfunction
 always @(negedge clk) if(rst_n)begin
  mem_req_ready=(cyc%4!=0);alloc_ready=(cyc%5!=0);d_ready=(cyc%7!=0);x_req_ready=(cyc%3!=0);start_ready=(cyc%4!=0);
  x_valid=x_active && cyc%5!=0;x_record=xrec;x_ordinal=xi;x_group=xg;x_data=pattern(xrec,xi,xg);
 end
 always @(posedge clk)begin
  cyc<=cyc+1;
  if(rst_n)state_cycles[dut.state]=state_cycles[dut.state]+1;
  if(cyc>50000)$fatal(1,"bounded 13-record owner stalled");
  mem_rsp_valid<=mem_req_valid && mem_req_ready;
  if(mem_req_valid && mem_req_ready)begin
   if(mem_req_addr<32'h1000 || mem_req_addr>=32'h1208)$fatal(1,"program bounds");
   mem_rsp_addr<=mem_req_addr;mem_rsp_data<=words[(mem_req_addr-32'h1000)/4];
  end
  alloc_rsp_valid<=alloc_valid && alloc_ready;
  if(alloc_valid && alloc_ready)begin
   if(alloc_record!=ops || alloc_lines!=words[ops*10+4])$fatal(1,"allocation identity/length");
   alloc_rsp_record<=alloc_record;alloc_rsp_base<=32'h80000000+alloc_record*4096;
  end
  if(d_valid && d_ready)begin
   if(d_base!=32'h80000000+ops*4096 || d_lines!=words[ops*10+4])$fatal(1,"real allocated base lost");
   captures=0;
  end
  if(x_req_valid && x_req_ready)begin
   if(x_req_record!=ops || x_req_base!=words[ops*10+9] || x_req_extent!=words[ops*10+7])$fatal(1,"X context");
   x_active<=1;xi=0;xg=0;xrec=ops;
  end
  if(x_valid && x_ready)begin
   if(xg==12)begin xg=0;if(xi+1==words[ops*10+7])x_active<=0;else xi=xi+1;end
   else xg=xg+1;
  end
  if(xw_en)begin
   expected_data=pattern(ops,captures/13,captures%13);
   if(captures%13==12)expected_data[2047:640]=0;
   if(xw_addr!=7'((words[ops*10+9]+captures/13)%128) || xw_grp!=captures%13 || xw_data!==expected_data)
    $fatal(1,"full-shape X capture mismatch op=%0d beat=%0d",ops,captures);
   captures=captures+1;total_captures=total_captures+1;
  end
  if(start && start_ready)begin
   if(op_rows!=words[ops*10] || op_c!=words[ops*10+1] || op_g!=words[ops*10+2] ||
      op_fmt!=words[ops*10+3] || op_gs!=words[ops*10+5] || op_xb!=words[ops*10+9])$fatal(1,"native record mismatch");
   if(captures!=(words[ops*10+6]?words[ops*10+7]*13:0))$fatal(1,"start precedes actual X publication");
   delay_retire=7;delay_publish=13;
  end
  if(delay_retire>0)begin delay_retire=delay_retire-1;if(delay_retire==0)arrive<=~arrive;end
  if(delay_publish>0)begin delay_publish=delay_publish-1;if(delay_publish==0)begin publication_valid<=1;publication_record<=ops;end end
  if(publication_valid && publication_ready)begin publication_valid<=0;ops=ops+1;end
  if(fault)$fatal(1,"owner fault op=%0d state=%0d",ops,dut.state);
  if(done)begin
   if(ops!=13 || total_captures!=expected_captures)$fatal(1,"missing records or X captures");
   $display("PASS native stress records=%0d full_shape_X_captures=%0d cycles=%0d",ops,total_captures,cyc);
   for(j=0;j<14;j=j+1)$display("STATE %0d CYCLES %0d",j,state_cycles[j]);
   $finish;
  end
 end
 initial begin
  for(j=0;j<14;j=j+1)state_cycles[j]=0;
  clk=0;rst_n=0;run_valid=0;program_base=32'h1000;program_limit=33'h1208;record_count=13;
  mem_req_ready=0;mem_rsp_valid=0;mem_rsp_addr=0;mem_rsp_data=0;mem_rsp_error=0;
  alloc_ready=0;alloc_rsp_valid=0;alloc_rsp_record=0;alloc_rsp_base=0;alloc_rsp_error=0;
  x_req_ready=0;x_valid=0;x_record=0;x_ordinal=0;x_group=0;x_data=0;x_error=0;
  d_ready=0;start_ready=0;arrive=0;sm_fault=0;publication_valid=0;publication_record=0;done_ready=0;
  if(!$value$plusargs("SEQ=%s",fixture))$fatal(1,"SEQ fixture required");
  $readmemh(fixture,words);
  for(j=0;j<13;j=j+1)if(words[j*10+6])expected_captures=expected_captures+13*words[j*10+7];
  repeat(3)@(negedge clk);rst_n=1;run_valid=1;
  @(negedge clk);run_valid=0;
 end
endmodule
