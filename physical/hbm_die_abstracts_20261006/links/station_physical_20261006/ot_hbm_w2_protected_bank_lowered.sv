`timescale 1ns/1ps
// Exact package expansion; keep/dont_touch attributes preserved.

// One physical W6 representation. Normal extraction contains no correction
// mux. All permissions use normal. CE has a five-edge held repair sequence;
// controller/snapshot/mask corruption fails closed without changing ownership.
module ot_hbm_w2_protected_bank #(parameter integer WORDS=1)(
 input wire clk,por_n,load,load_encoded,fatal,
 input wire [WORDS*64-1:0] d,
 input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,
 output wire [WORDS*72-1:0] encoded_q,
 output wire normal,fault,repairing
);

  function automatic logic [71:0] encode64(input logic [63:0] data);
    logic [71:0] c; integer p, k, j;
    begin
      c='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin c[p-1]=data[j]; j=j+1; end
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0 && p!=(1<<k)) c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
      c[71]=^c[70:0]; encode64=c;
    end
  endfunction
  // {uncorrectable, corrected, data64}; overall parity is bit71.
  function automatic logic [65:0] decode64(input logic [71:0] code);
    logic [71:0] c; logic [6:0] syndrome; logic overall, ue, corrected;
    logic [63:0] data; integer p,k,j;
    begin
      c=code; syndrome='0; overall=^code; ue=0; corrected=0;
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0) syndrome[k]=syndrome[k]^code[p-1];
      if (syndrome!=0) begin
        if (overall && syndrome<=71) begin c[syndrome-1]=~c[syndrome-1]; corrected=1; end
        else ue=1;
      end else if (overall) begin c[71]=~c[71]; corrected=1; end
      data='0; j=0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin data[j]=c[p-1]; j=j+1; end
      decode64={ue,corrected,data};
    end
  endfunction
  function automatic logic [143:0] encode_row(input logic [70:0] raw);
    encode_row={encode64({57'b0,raw[70:64]}),encode64(raw[63:0])};
  endfunction


 function automatic [63:0] raw64(input [71:0] c);
  integer p,j;begin j=0;raw64=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin raw64[j]=c[p-1];j=j+1;end
  end
 endfunction
 function automatic [7:0] check72(input [71:0] c);
  integer p,k;begin check72=0;check72[7]=^c;
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)
    if((p&(1<<k))!=0)check72[k]=check72[k]^c[p-1];
  end
 endfunction

 reg [71:0] code[0:WORDS+4];
 (* keep=1, dont_touch=1 *) reg failed,failed_n;
 wire [WORDS-1:0] ce,ue;
 wire [63:0] ctl=raw64(code[WORDS]);
 wire [2:0] phase=ctl[2:0];wire [15:0] index=ctl[18:3];
 wire [7:0] syn=ctl[26:19];
 wire [63:0] snapshot_hi=raw64(code[WORDS+2]);
 wire [71:0] snapshot={snapshot_hi[7:0],raw64(code[WORDS+1])};
 wire [63:0] mask_hi=raw64(code[WORDS+4]);
 wire [71:0] mask={mask_hi[7:0],raw64(code[WORDS+3])};
 wire [71:0] next_mask=72'b1<<(syn[6:0]==0?7'd71:syn[6:0]-1'b1);
 wire [4:0] control_bad;
 for(genvar g=0;g<WORDS;g=g+1)begin:word
  wire [7:0] s=check72(code[g]);
  assign ce[g]=s[7]&&s[6:0]<=71;
  assign ue[g]=s[6:0]!=0&&(!s[7]||s[6:0]>71);
  assign q[g*64+:64]=raw64(code[g]);assign encoded_q[g*72+:72]=code[g];
 end
 for(genvar g=0;g<5;g=g+1)begin:control
  assign control_bad[g]=check72(code[WORDS+g])!=0;
 end
 assign fault=failed||failed==failed_n||(|ue)||(|control_bad)||phase>4;
 assign normal=!fault&&phase==0&&!(|ce);
 assign repairing=!fault&&((|ce)||phase!=0);
 integer first,i;
 always @*begin first=0;for(integer k=WORDS-1;k>=0;k=k-1)if(ce[k])first=k;end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   failed<=0;failed_n<=1;
   for(i=0;i<WORDS+5;i=i+1)code[i]<=encode64(0);
  end else if(fault||fatal)begin failed<=1;failed_n<=0;end
  else case(phase)
   0:if(|ce)begin
    code[WORDS+1]<=encode64(code[first][63:0]);
    code[WORDS+2]<=encode64({56'b0,code[first][71:64]});
    code[WORDS]<=encode64({37'b0,check72(code[first]),16'(first),3'd1});
   end else if(load)begin
    for(i=0;i<WORDS;i=i+1)
     code[i]<=load_encoded?encoded_d[i*72+:72]:encode64(d[i*64+:64]);
   end
   1:begin
    code[WORDS+3]<=encode64(next_mask[63:0]);
    code[WORDS+4]<=encode64({56'b0,next_mask[71:64]});
    code[WORDS]<=encode64({ctl[63:3],3'd2});
   end
   2:if(index>=WORDS||code[index]!==snapshot)begin failed<=1;failed_n<=0;end
     else begin code[index]<=snapshot^mask;code[WORDS]<=encode64({ctl[63:3],3'd3});end
   3:if(check72(code[index])!=0)begin failed<=1;failed_n<=0;end
     else code[WORDS]<=encode64({ctl[63:3],3'd4});
   4:begin
    for(i=0;i<5;i=i+1)code[WORDS+i]<=encode64(0);
   end
   default:begin failed<=1;failed_n<=0;end
  endcase
 end
endmodule

module ot_hbm_w2_protected_cut #(parameter integer W=337)(
 input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault
);
 localparam integer N=(W+1+63)/64;
 wire [N*64-1:0] q;wire normal,repairing;
 wire valid=q[W];
 assign in_r=normal&&(!valid||out_r);
 assign out_v=normal&&valid;assign out_d=q[W-1:0];
 assign empty=normal&&!valid;
 ot_hbm_w2_protected_bank #(.WORDS(N)) u_state(
  .clk(clk),.por_n(por_n),.load(in_r),.load_encoded(1'b0),.fatal(1'b0),
  .d({{(N*64-W-1){1'b0}},in_v,(in_v?in_d:{W{1'b0}})}),.encoded_d({N*72{1'b0}}),
  .q(q),.encoded_q(),.normal(normal),.fault(fault),.repairing(repairing));
endmodule
