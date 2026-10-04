// Small connected native path, not the full parent or a timing qualification.
module embedding_vm (
 input wire clk,rst_n,start,
 input wire [16:0] token,input wire [46:0] identity,input wire [18:0] vm_base,
 output wire req_v,input wire req_ready,
 output wire [13:0] req_macro,output wire [11:0] req_row,output wire [46:0] req_identity,
 input wire rsp_v,output wire rsp_ready,input wire [255:0] rsp_data,
 input wire [13:0] rsp_macro,input wire [11:0] rsp_row,input wire [46:0] rsp_identity,
 input wire commit_ready,
 output wire vm_v,output wire [18:0] vm_address,output wire [511:0] vm_data,
 output wire [46:0] vm_identity,
 output wire busy,done,output wire fault,
 input wire [14:0] probe_address,output wire [31:0] probe_data,
 output reg [31:0] committed_words
);
 wire vm_ready=commit_ready && vm_identity==identity && vm_address<=32752;
 reg [31:0] vm [0:32767];
 assign probe_data=vm[probe_address];
 ot_dsrom_s81_embedding reader(
   .clk(clk),.rst_n(rst_n),.start(start),.token(token),.identity(identity),.vm_base(vm_base),
   .req_v(req_v),.req_ready(req_ready),.req_macro(req_macro),.req_row(req_row),.req_identity(req_identity),
   .rsp_v(rsp_v),.rsp_ready(rsp_ready),.rsp_data(rsp_data),.rsp_macro(rsp_macro),.rsp_row(rsp_row),
   .rsp_identity(rsp_identity),.vm_v(vm_v),.vm_ready(vm_ready),.vm_address(vm_address),
   .vm_data(vm_data),.vm_identity(vm_identity),.busy(busy),.done(done),.fault(fault));
 always @(posedge clk) begin
   if(!rst_n) committed_words<=0;
   else if(vm_v && vm_ready) begin
     for(integer lane=0;lane<16;lane=lane+1) vm[vm_address+lane]<=vm_data[lane*32 +:32];
     committed_words<=committed_words+16;
   end
 end
endmodule
