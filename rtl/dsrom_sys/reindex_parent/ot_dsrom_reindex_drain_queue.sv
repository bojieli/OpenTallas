// Actual four-entry production drain header and its in-flight reservation.
// The key store uses these same write/read addresses; no synthetic credits.
module ot_dsrom_reindex_drain_queue(
 input wire clk,rst_n,reserve,in_valid,input wire [70:0] in_data,
 output wire [1:0] write_address,read_address,
 output wire ready,out_valid,input wire out_ready,
 output wire [70:0] out_data,output reg fault
);
 reg [78:0] mem[0:3];
 reg [1:0] wp,rp,wp_n,rp_n;
 reg [2:0] count,count_n,reserved,reserved_n;
 reg ready_q;
 function automatic [78:0] encode(input [70:0] d);
  reg [78:0] w;reg par;integer p,k,j;
  begin w=0;j=0;for(p=1;p<=78;p=p+1)if((p&(p-1))!=0)begin w[p-1]=d[j];j=j+1;end
   for(k=0;k<7;k=k+1)begin par=0;for(p=1;p<=78;p=p+1)if((p&(1<<k))!=0)par=par^w[p-1];w[(1<<k)-1]=par;end
   w[78]=^w[77:0];encode=w;end
 endfunction
 wire [78:0] word=mem[rp];
 reg [6:0] syndrome;reg [70:0] payload;integer p,k,j;
 always @*begin
  syndrome=0;payload=0;j=0;
  for(p=1;p<=78;p=p+1)begin
   if((p&(p-1))!=0)begin payload[j]=word[p-1];j=j+1;end
   for(k=0;k<7;k=k+1)if((p&(1<<k))!=0)syndrome[k]=syndrome[k]^word[p-1];
  end
 end
 wire state_ok=(wp==~wp_n)&&(rp==~rp_n)&&(count==~count_n)&&
               (reserved==~reserved_n)&&(count<=reserved)&&(reserved<=4);
 wire clean=(syndrome==0)&&!(^word);
 assign out_valid=(count!=0)&&state_ok&&clean&&!fault;
 assign out_data=payload;
 assign ready=ready_q&&state_ok&&!fault;
 assign write_address=wp;assign read_address=rp;
 wire pop=out_valid&&out_ready;
 wire [3:0] nr={1'b0,reserved}+(reserve?4'd1:4'd0)-(pop?4'd1:4'd0);
 wire [3:0] nc={1'b0,count}+(in_valid?4'd1:4'd0)-(pop?4'd1:4'd0);
 always @(posedge clk)begin
  if(!rst_n)begin
   wp<=0;rp<=0;wp_n<=3;rp_n<=3;count<=0;count_n<=7;reserved<=0;reserved_n<=7;ready_q<=1;fault<=0;
  end else begin
   if(!state_ok||(count!=0&&!clean)||nr>4||nc>nr||(in_valid&&count==4&&!pop))fault<=1;
   else if(!fault)begin
    reserved<=nr[2:0];reserved_n<=~nr[2:0];ready_q<=(nr<4);
    count<=nc[2:0];count_n<=~nc[2:0];
    if(in_valid)begin mem[wp]<=encode(in_data);wp<=wp+2'd1;wp_n<=~(wp+2'd1);end
    if(pop)begin rp<=rp+2'd1;rp_n<=~(rp+2'd1);end
   end
  end
 end
endmodule
