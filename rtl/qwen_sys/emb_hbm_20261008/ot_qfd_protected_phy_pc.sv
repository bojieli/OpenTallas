`timescale 1ns/1ps
// Functional physical-API fallback. Native JEDEC adapter and allocator exclusion OPEN.
// All writes sharing a sidecar word MUST serialize through this sole PC owner.
module ot_qfd_protected_phy_pc #(parameter integer ENABLE=0, PC=0, ROW0=24427)(
 input wire clk,rst_n,
 input wire q_v, output wire q_rdy, input wire q_we,q_emb,
 input wire [18:0] q_row, input wire [4:0] q_bank,q_col,
 input wire [16:0] q_sec, input wire [7:0] q_lrow, input wire [63:0] q_id,
 input wire [287:0] q_code,
 output reg o_v, input wire o_rdy, output reg o_we,o_emb,
 output reg [16:0] o_sec, output reg [7:0] o_lrow, output reg [63:0] o_id,
 output reg [18:0] o_row, output reg [4:0] o_bank,o_col,
 output reg [287:0] o_code, output reg fault,
 output wire p_v, input wire p_rdy, output wire p_we,
 output wire [30:0] p_addr, output wire [4:0] p_len,
 output wire [15:0] p_tag, output wire [255:0] p_data,
 input wire r_v, output wire r_rdy, input wire [4:0] r_pc,
 input wire [15:0] r_tag, input wire [3:0] r_beat,input wire [255:0] r_data
);
 localparam IDLE=0, DR=1,DWAIT=2,ER=3,EWAIT=4,DW=5,EW=6,FD=7,FDWAIT=8,FE=9,FEWAIT=10,OUT=11,DEAD=12;
 reg [3:0] st;
 reg wr,emb; reg [18:0] row_q; reg [4:0] bank_q,col_q;
 reg [16:0] sec_q; reg [7:0] lr_q; reg [63:0] id_q;
 reg [287:0] code_q;
 reg [255:0] data_q,ecc_q;
 reg [30:0] da,ea; reg [2:0] lane;
 reg [15:0] serial,expected;
 function automatic [30:0] address(input [15:0] row,input [4:0] bank,col);
 reg [2:0] hi; reg [4:0] pcraw; begin
 hi=bank[4:2]^row[4:2]; pcraw=5'(PC)^col^{row[1:0],hi};
 address={row,hi,col,pcraw,(bank[1:0]^row[1:0])}; end endfunction
 function automatic [255:0] payload(input [287:0] c);
 integer w,p,j; begin payload=0; for(w=0;w<4;w=w+1)begin j=0;
 for(p=1;p<=71;p=p+1) if((p&(p-1))!=0)begin payload[w*64+j]=c[w*72+p-1];j=j+1;end end end endfunction
 function automatic [31:0] checks(input [287:0] c);
 integer w,k; begin for(w=0;w<4;w=w+1)begin
 for(k=0;k<7;k=k+1) checks[w*8+k]=c[w*72+(1<<k)-1];
 checks[w*8+7]=c[w*72+71]; end end endfunction
 function automatic [287:0] join_code(input [255:0] d,input [31:0] e);
 integer w,p,j,k;begin join_code=0;for(w=0;w<4;w=w+1)begin j=0;
 for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin join_code[w*72+p-1]=d[w*64+j];j=j+1;end
 for(k=0;k<7;k=k+1)join_code[w*72+(1<<k)-1]=e[w*8+k];
 join_code[w*72+71]=e[w*8+7];end end endfunction
 wire requesting=st==DR||st==ER||st==DW||st==EW||st==FD||st==FE;
 wire waiting=st==DWAIT||st==EWAIT||st==FDWAIT||st==FEWAIT;
 assign q_rdy=ENABLE!=0 && st==IDLE && !fault;
 assign p_v=ENABLE!=0 && requesting && !fault;
 assign p_we=st==DW||st==EW;
 assign p_addr=(st==ER||st==EW||st==FE)?ea:da;
 assign p_len=5'd1; assign p_tag=serial;
 assign p_data=st==EW?ecc_q:payload(code_q);
 assign r_rdy=ENABLE!=0 && waiting && !fault;
 always @(posedge clk or negedge rst_n) begin : seq
 reg [9:0] j,ej; reg [18:0] erow; reg [30:0] nd,ne; reg [255:0] ec;
 if(!rst_n)begin st<=IDLE;fault<=0;o_v<=0;serial<=1;expected<=0;
 wr<=0;emb<=0;row_q<=0;bank_q<=0;col_q<=0;sec_q<=0;lr_q<=0;id_q<=0;da<=0;ea<=0;lane<=0;code_q<=0;ecc_q<=0;data_q<=0;
 o_we<=0;o_emb<=0;o_sec<=0;o_lrow<=0;o_id<=0;o_row<=0;o_bank<=0;o_col<=0;o_code<=0;
 end else if(ENABLE!=0)begin
 if(r_v && (!waiting || r_pc!=5'(PC)||r_tag!=expected||r_beat!=0))begin fault<=1;st<=DEAD;o_v<=0;end
 else case(st)
 IDLE:if(q_v&&q_rdy)begin
 if((q_emb && (q_row<ROW0||q_row>=ROW0+149))||(!q_emb&&q_row>=36))begin fault<=1;st<=DEAD;end
 else begin
 j={q_bank[4:2],q_col,q_bank[1:0]};
 if(q_emb)begin erow=19'(ROW0+149)+((q_row-19'(ROW0))>>3);ej={3'(q_row-19'(ROW0)),j[9:3]};end
 else begin erow=19'd64+q_row;ej={3'b0,j[9:3]};end
 nd=address(q_row[15:0],q_bank,q_col);ne=address(erow[15:0],{ej[9:7],ej[1:0]},ej[6:2]);
 wr<=q_we;emb<=q_emb;row_q<=q_row;bank_q<=q_bank;col_q<=q_col;sec_q<=q_sec;lr_q<=q_lrow;id_q<=q_id;code_q<=q_code;
 da<=nd;ea<=ne;lane<=j[2:0];
 st<=q_we?ER:DR;end end
 DR,ER,FD,FE:if(p_v&&p_rdy)begin
 if(serial==16'hffff)begin fault<=1;st<=DEAD;end else begin expected<=serial;serial<=serial+1'b1;
 case(st)DR:st<=DWAIT;ER:st<=EWAIT;FD:st<=FDWAIT;FE:st<=FEWAIT;default:st<=DEAD;endcase end end
 DWAIT:if(r_v&&r_rdy)begin data_q<=r_data;st<=ER;end
 EWAIT:if(r_v&&r_rdy)begin
 if(wr)begin ec=r_data;ec[lane*32+:32]=checks(code_q);ecc_q<=ec;st<=DW;end
 else begin o_code<=join_code(data_q,r_data[lane*32+:32]);st<=OUT;end end
 DW:if(p_v&&p_rdy)st<=EW;
 EW:if(p_v&&p_rdy)st<=FD;
 FDWAIT:if(r_v&&r_rdy)begin if(r_data!=payload(code_q))begin fault<=1;st<=DEAD;end else st<=FE;end
 FEWAIT:if(r_v&&r_rdy)begin if(r_data[lane*32+:32]!=checks(code_q))begin fault<=1;st<=DEAD;end else begin o_code<=code_q;st<=OUT;end end
 OUT:begin if(!o_v)begin o_v<=1;o_we<=wr;o_emb<=emb;o_sec<=sec_q;o_lrow<=lr_q;o_id<=id_q;o_row<=row_q;o_bank<=bank_q;o_col<=col_q;end
 else if(o_rdy)begin o_v<=0;st<=IDLE;end end
 DEAD:begin o_v<=0;end
 default:begin fault<=1;st<=DEAD;end
 endcase
 end
 end
endmodule
