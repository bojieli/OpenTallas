module tb;
 reg [4:0]opcode;reg [1:0]dtype,a_type,b_type,c_type;reg a_scalar,b_scalar,c_scalar;
 reg [3:0]lane_mask;reg [255:0]a_data,b_data,c_data;
 wire [255:0]result,off_result;wire [1:0]result_type,off_type;wire[3:0]lane_fault,off_fault;wire supported,off_supported;
 ot_hbm_accel_native_bits #(.ENABLE(1))dut(.*);
 ot_hbm_accel_native_bits #(.ENABLE(0))off(.opcode(opcode),.dtype(dtype),.a_type(a_type),.b_type(b_type),.c_type(c_type),
 .a_scalar(a_scalar),.b_scalar(b_scalar),.c_scalar(c_scalar),.lane_mask(lane_mask),.a_data(a_data),.b_data(b_data),.c_data(c_data),
 .result(off_result),.result_type(off_type),.lane_fault(off_fault),.supported(off_supported));
 integer fd,r,k,n=0,errors=0,op,dt,at,bt,ct,sc,mask,typ,err;
 reg[255:0]expected;reg[2047:0]file;
 initial begin
 if(!$value$plusargs("VECTORS=%s",file))$fatal(1,"vectors required");fd=$fopen(file,"r");
 while(!$feof(fd))begin
 r=$fscanf(fd,"%d %d %d %d %d %d %d %h %h %h %h %d %d\n",op,dt,at,bt,ct,sc,mask,a_data,b_data,c_data,expected,typ,err);
 if(r==13)begin
 opcode=op;dtype=dt;a_type=at;b_type=bt;c_type=ct;{c_scalar,b_scalar,a_scalar}=sc;lane_mask=mask;#1;
 if(!supported||result_type!==typ[1:0]||lane_fault!==err[3:0])begin errors=errors+1;$display("METAFAIL case%0d op%0d type%0d/%0d err%0h/%0h",n,op,result_type,typ,lane_fault,err);end
 for(k=0;k<4;k=k+1)if(!err[k]&&result[k*64+:64]!==expected[k*64+:64])begin errors=errors+1;$display("DATAFAIL case%0d op%0d lane%0d got%h exp%h",n,op,k,result[k*64+:64],expected[k*64+:64]);end
 if(off_supported!==0||off_result!==0||off_fault!==0)begin errors=errors+1;$display("DEFAULTFAIL");end
 n=n+1;
 end end
 $display("DONE cases=%0d errors=%0d",n,errors);if(errors)$fatal(1,"numerical mismatch");$finish;
 end endmodule