// Package functions inlined verbatim for native Yosys package parser.
`timescale 1ns/1ps
// Native 690-bit quarter instructions. ROM provider supplies four independently
// compiled words; no arithmetic rewriting occurs in this dispatcher. Immutable
// ROM requires validity/bounds but no ECC. Mutable command/state seats use SECDED.
module ot_qwen_r25_su_dispatch #(
 parameter integer ENABLE=0, CAPACITY=8224
)(
 input wire clk,rst_n,
 input wire launch_v,output wire launch_rdy,input wire [1:0] launch_checked,
 input wire [72:0] launch_owner,input wire [11:0] launch_pc,
 input wire [12:0] launch_count,input wire [19:0] launch_position,
 input wire [2:0] launch_queries,
 output wire rom_v,input wire rom_rdy,output wire [11:0] rom_pc,
 input wire rom_out_v,output wire rom_out_rdy,input wire [11:0] rom_out_pc,
 input wire [2759:0] rom_words,input wire [3:0] rom_quarters,
 input wire rom_valid,input wire rom_window,
 input wire [19:0] rom_row0,input wire [15:0] rom_rows,
 output wire [3:0] cmd_v,input wire [3:0] cmd_rdy,
 output wire [2759:0] cmd_words,output wire [72:0] cmd_owner,
 output wire [11:0] cmd_pc,output wire [1:0] cmd_query,
 output wire [19:0] cmd_position,output wire [20:0] cmd_valid_length,
 input wire [3:0] done_v,input wire [291:0] done_owner,
 input wire [47:0] done_pc,input wire [7:0] done_query,
 output wire finished_v,input wire finished_rdy,output wire fault
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

 generate if(!ENABLE)begin:disabled
  assign launch_rdy=0;assign rom_v=0;assign rom_pc=0;assign rom_out_rdy=0;
  assign cmd_v=0;assign cmd_words=0;assign cmd_owner=0;assign cmd_pc=0;
  assign cmd_query=0;assign cmd_position=0;assign cmd_valid_length=0;
  assign finished_v=0;assign fault=0;
 end else begin:enabled
  localparam IDLE=0,REQUEST=1,RECEIVE=2,EXEC=3,FINISH=4,FAILED=5;
  // state: phase3 issued4 returned4 active4 pc12 base12 remaining13 slot2 nq3.
  reg [71:0] state,owner_lo,context_seat;
  reg [71:0] words[0:43];
  wire [65:0] sd=decode64(state),od=decode64(owner_lo),xd=decode64(context_seat);
  wire [63:0] s=sd[63:0],x=xd[63:0];
  wire [2:0] phase=s[2:0];wire [3:0] issued=s[6:3],returned=s[10:7],active=s[14:11];
  wire [11:0] pc=s[26:15],base=s[38:27];wire [12:0] remaining=s[51:39];
  wire [1:0] slot=s[53:52];wire [2:0] nq=s[56:54];
  wire [12:0] original_count=x[41:29];
  wire [19:0] position=x[28:9];
  wire [65:0] wd[0:43];wire [43:0] wue;
  for(genvar k=0;k<44;k=k+1)begin:word_decode
   assign wd[k]=decode64(words[k]);assign wue[k]=wd[k][65];
  end
  wire bad=sd[65]||od[65]||xd[65]||(|wue);
  assign fault=bad||phase==FAILED;
  assign launch_rdy=phase==IDLE&&!fault;
  assign rom_v=phase==REQUEST&&!fault;assign rom_pc=pc;
  assign rom_out_rdy=phase==RECEIVE&&!fault;
  assign cmd_v=(phase==EXEC&&!fault)?active&~issued:4'd0;
  assign cmd_owner={x[8:0],od[63:0]};assign cmd_pc=pc;assign cmd_query=slot;
  assign cmd_position=position+slot;
  assign cmd_valid_length={1'b0,position}+slot+21'd1;
  assign finished_v=phase==FINISH&&!fault;
  for(genvar q=0;q<4;q=q+1)begin:quarter_words
   wire [703:0] payload;
   for(genvar j=0;j<11;j=j+1)begin:chunk
    assign payload[j*64+:64]=wd[q*11+j][63:0];
   end
   assign cmd_words[q*690+:690]=payload[689:0];
  end
  reg [63:0] next_s;reg [3:0] ni,nr;
  reg invalid;reg [15:0] rows;reg [20:0] available;
  reg [703:0] payload;integer q,j;
  always @* begin
   next_s=s;ni=issued;nr=returned;invalid=0;
   for(q=0;q<4;q=q+1)begin
    if(cmd_v[q]&&cmd_rdy[q])ni[q]=1;
    if(done_v[q])begin
     if(phase!=EXEC||!active[q]||!ni[q]||returned[q]||
        done_owner[q*73+:73]!=cmd_owner||done_pc[q*12+:12]!=pc||
        done_query[q*2+:2]!=slot)invalid=1;
     else nr[q]=1;
    end
   end
   case(phase)
    IDLE:if(launch_v&&launch_rdy)begin
     if(launch_checked!=3||!(launch_queries==1||launch_queries==4)||
        launch_count==0||({1'b0,launch_pc}+launch_count)>4096||
        ({1'b0,launch_position}+launch_queries)>CAPACITY)invalid=1;
     else begin
      next_s=0;next_s[2:0]=REQUEST;next_s[26:15]=launch_pc;
      next_s[38:27]=launch_pc;next_s[51:39]=launch_count;next_s[56:54]=launch_queries;
     end
    end
    REQUEST:if(rom_v&&rom_rdy)next_s[2:0]=RECEIVE;
    RECEIVE:if(rom_out_v)begin
     if(!rom_valid||rom_out_pc!=pc||rom_quarters==0||
        (rom_window&&(rom_rows==0||({1'b0,rom_row0}+rom_rows)>CAPACITY)))invalid=1;
     next_s[2:0]=EXEC;next_s[14:11]=rom_quarters;
     if(rom_window&&rom_row0>=cmd_valid_length)next_s[14:11]=0;
     next_s[10:3]=0;
    end
    EXEC:begin
     next_s[6:3]=ni;next_s[10:7]=nr;
     if((nr&active)==active)begin
      next_s[14:3]=0;
      if(remaining>1)begin
       next_s[26:15]=pc+1;next_s[51:39]=remaining-1;next_s[2:0]=REQUEST;
      end else if({1'b0,slot}+1<nq)begin
       next_s[53:52]=slot+1;next_s[26:15]=base;
       next_s[51:39]=original_count;next_s[2:0]=REQUEST;
      end else next_s[2:0]=FINISH;
     end
    end
    FINISH:if(finished_rdy)next_s=0;
    default:invalid=1;
   endcase
   if(invalid||bad)next_s[2:0]=FAILED;
  end
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin
    state<=encode64(0);owner_lo<=encode64(0);context_seat<=encode64(0);
    for(j=0;j<44;j=j+1)words[j]<=encode64(0);
   end else begin
    state<=encode64(next_s);
    if(launch_v&&launch_rdy&&!invalid)begin
     owner_lo<=encode64(launch_owner[63:0]);
     context_seat<=encode64({22'd0,launch_count,launch_position,launch_owner[72:64]});
    end
    if(rom_out_v&&rom_out_rdy&&!invalid)begin
     available=(cmd_valid_length>rom_row0)?cmd_valid_length-rom_row0:0;
     rows=(available<rom_rows)?available[15:0]:rom_rows;
     for(q=0;q<4;q=q+1)begin
      payload={14'd0,rom_words[q*690+:690]};
      // Native NIN field is bits31:16. Compiler must pre-zero partials for
      // an empty window; skipped quarters must not contribute stale results.
      if(rom_window)payload[31:16]=rows;
      for(j=0;j<11;j=j+1)words[q*11+j]<=encode64(payload[j*64+:64]);
     end
    end
   end
  end
 end endgenerate
 initial if(CAPACITY<8195)$fatal(1,"p4 dispatcher capacity too small");
endmodule
