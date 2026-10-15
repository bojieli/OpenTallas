`timescale 1ns/1ps
`default_nettype none
// One local 4-word island in one physical SRAM bank. Sixteen entries retain
// expected payload/owner independently of the live SRAM row. Nine copies per
// physical bank; no whole-row expected or release register root.
module vm_service_wordbank #(parameter integer OWNER_BANK=0)(
 input wire clk,rst_n,
 input wire expect_v,input wire [3:0] expect_slot,input wire [255:0] expect_data,
 output wire [287:0] encoded,
 input wire capture_v,check_v,check_write,input wire [3:0] check_slot,
 input wire [287:0] returned,
 output wire valid,error,output wire [255:0] repaired_data);
 function automatic [71:0] encode64(input [63:0] data);
  reg [71:0] c;integer j,k,p;
  begin
   c=0;k=0;
   for(j=1;j<=71;j=j+1)
    if(j!=1&&j!=2&&j!=4&&j!=8&&j!=16&&j!=32&&j!=64)begin c[j-1]=data[k];k=k+1;end
   for(p=0;p<7;p=p+1)for(j=1;j<=71;j=j+1)if((j&(1<<p))!=0)c[(1<<p)-1]=c[(1<<p)-1]^c[j-1];
   c[71]=^c[70:0];encode64=c;
  end
 endfunction
 function automatic [63:0] payload(input [71:0] code);
  integer j,k;
  begin
   payload=0;k=0;
   for(j=1;j<=71;j=j+1)
    if(j!=1&&j!=2&&j!=4&&j!=8&&j!=16&&j!=32&&j!=64)begin payload[k]=code[j-1];k=k+1;end
  end
 endfunction
 reg[287:0] expected[0:15];wire[287:0] fixed_code;
 for(genvar w=0;w<4;w=w+1)begin:words
  assign encoded[w*72+:72]=encode64(expect_data[w*64+:64]);
  assign repaired_data[w*64+:64]=payload(fixed_code[w*72+:72]);
 end
 // Registered, kept local halfword enables bound each data enable to36 sinks.
 (* keep = "true" *) reg [127:0] insert_en;
 reg [287:0] insert_code;
 always @(posedge clk)insert_code<=encoded;
 for(genvar e=0;e<16;e=e+1)begin:expected_entries
  for(genvar h=0;h<8;h=h+1)begin:halves
   always @(posedge clk or negedge rst_n)
    if(!rst_n)insert_en[e*8+h]<=0;
    else insert_en[e*8+h]<=expect_v&&(expect_slot==4'(e));
   always @(posedge clk)if(insert_en[e*8+h])expected[e][h*36+:36]<=insert_code[h*36+:36];
  end
 end
 // OWNER_BANK has 15 low data bits, 192 owner bits, then 49 reserved zeros.
 localparam [255:0] OWNER_MASK=OWNER_BANK ? (256'hffffffffffffffffffffffffffffffffffffffffffffffff<<15) : 256'b0;
 localparam [255:0] PAD_MASK=OWNER_BANK ? (256'hffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff<<207) : 256'b0;
 vm_ck4 u_check(.ck(clk),.rst_n(rst_n),.capture_i(capture_v),.check_i(check_v),
  .write_i(check_write),.capture_regions_i(8'b0),.check_regions_i(8'b0),
  .sample_i(returned),.expected_i(expected[check_slot]),
  .owner_mask_i(OWNER_MASK),.padding_mask_i(PAD_MASK),
  .error_o(error),.valid_o(valid),.repaired_o(fixed_code));
endmodule
`default_nettype wire
