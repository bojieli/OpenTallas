`timescale 1ns/1ps
module tb_hgi_dma_wide_convert_tile #(parameter integer TEST_MUT=0, LIVE_BANKS=1);
 localparam integer MUT=0;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0;
 reg[3:0]raw_v=0;wire[3:0]raw_r;reg[71:0]raw_sec=0;reg[1023:0]raw_data=0;reg[7:0]raw_fmt=0;reg[15:0]raw_piece_mask=0;
 wire[3:0]bank_v;wire[3:0]bank_r;reg[3:0]sink_allow=0;wire[71:0]bank_sec;wire[1023:0]bank_data;wire[31:0]bank_word_mask;wire fault;
 ot_hgi_dma_wide_convert_tile #(.ENABLE(1),.MUT(TEST_MUT))dut(.*);
 wire[3:0]off_ready,off_valid;wire off_fault;
 ot_hgi_dma_wide_convert_tile off(.clk(clk),.rst_n(rst_n),.raw_v(raw_v),.raw_r(off_ready),.raw_sec(raw_sec),.raw_data(raw_data),.raw_fmt(raw_fmt),.raw_piece_mask(raw_piece_mask),.bank_v(off_valid),.bank_r(bank_r),.fault(off_fault));
 wire[7:0]physical_ready,physical_done,physical_fault;
 wire[159:0]physical_tag;
 integer bankcommits=0;
 genvar pb;
 generate for(pb=0;pb<8;pb=pb+1)begin:physical
  localparam integer B=pb/2,P=pb%2;
  ot_hgi_vm_wide_bank #(.ENABLE(LIVE_BANKS)) u_bank(.clk(clk),.rst_n(rst_n),
   .w_v(bank_v[B]&&sink_allow[B]&&(bank_sec[B*18+9]==P)),.w_rdy(physical_ready[pb]),
   .w_addr(bank_sec[B*18+10+:8]),.w_data(bank_data[B*256+:256]),.w_mask(bank_word_mask[B*8+:8]),
   .w_tag({2'b0,bank_sec[B*18+:18]}),.w_done(physical_done[pb]),.w_done_tag(physical_tag[pb*20+:20]),
   .r_v(1'b0),.r_addr(8'd0),.r_tag(20'd0),.fault(physical_fault[pb]),.inj_v(1'b0),.inj_word(3'd0),.inj_mask(39'd0));
 end
 for(pb=0;pb<4;pb=pb+1)begin:ready
  assign bank_r[pb]=sink_allow[pb]&&((LIVE_BANKS==0)?1'b1:physical_ready[pb*2+int'(bank_sec[pb*18+9])]);
 end endgenerate
 integer bank_due[0:7][0:4095];reg[19:0]bank_expected_tag[0:7][0:4095];integer bankin[0:7],bankout[0:7];
 initial for(integer p=0;p<8;p=p+1)begin bankin[p]=0;bankout[p]=0;end
    function automatic [31:0] i8_f(input [7:0] c);
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    function automatic [255:0] conv(input [255:0] s, input [2:0] f, input [1:0] j);
        reg [255:0] o; integer w; reg [7:0] b; reg [15:0] h;
        begin
            o = 256'd0;
            for (w = 0; w < 8; w = w + 1) begin
                case (f)
                    3'd1: begin h = s[({3'd0, j} * 8 + w) * 16 +: 16]; if (MUT == 1) h = s[({3'd0, j} * 8 + (7 - w)) * 16 +: 16];
                                o[w*32 +: 32] = {h, 16'd0}; end
                    3'd2: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = e4m3_f(b); end
                    3'd4: begin b = s[({3'd0, j} * 8 + w) * 8 +: 8]; o[w*32 +: 32] = i8_f(b); end
                    default: o[w*32 +: 32] = s[w*32 +: 32];
                endcase
            end
            conv = o;
        end
    endfunction

 reg[17:0]expected_sec[0:4095];reg[255:0]expected_data[0:4095];reg pending[0:4095];
 integer source_cycle[0:4095];integer min_elapsed=99999,max_elapsed=0;
 integer want=0,got=0,cycle=0,max_out=0,nout,last_input=-1;reg[3:0]prev_hold=0;reg[71:0]prev_sec;reg[1023:0]prev_data;reg[31:0]prev_mask;
 integer i,j,k,found,count;reg[18:0]dst;reg valid_in;reg[3:0]accepted;
 integer reject_mode=0;
 always @(posedge clk)if(rst_n)begin
  cycle=cycle+1;accepted=raw_v&raw_r;nout=0;
  for(integer p=0;p<8;p=p+1)if(LIVE_BANKS&&bank_v[p/2]&&bank_r[p/2]&&bank_sec[(p/2)*18+9]==p%2)begin
   bank_due[p][bankin[p]]=cycle+4;bank_expected_tag[p][bankin[p]]={2'b0,bank_sec[(p/2)*18+:18]};bankin[p]=bankin[p]+1;
  end
  for(i=0;i<4;i=i+1)begin
   if(prev_hold[i]&&(!bank_v[i]||bank_sec[i*18+:18]!==prev_sec[i*18+:18]||bank_data[i*256+:256]!==prev_data[i*256+:256]||bank_word_mask[i*8+:8]!==prev_mask[i*8+:8]))$fatal(1,"OUTPUT_HOLD");
   if(accepted[i]&&!reject_mode)begin
    count=raw_fmt[i*2+:2]==0?1:raw_fmt[i*2+:2]==1?2:4;
    for(j=0;j<count;j=j+1)if(raw_piece_mask[i*4+j])begin
     dst={1'b0,raw_sec[i*18+:18]}+19'(j);
     if(dst[18]||dst%512/4!=0)$fatal(1,"TEST_INVALID_PACKET");
     expected_sec[want]=dst[17:0];expected_data[want]=conv(raw_data[i*256+:256],{1'b0,raw_fmt[i*2+:2]},2'(j));pending[want]=1;source_cycle[want]=cycle;want=want+1;
    end
    last_input=cycle;
   end
   if(bank_v[i]&&bank_r[i])begin
    found=-1;
    for(k=0;k<want;k=k+1)if(found<0&&pending[k]&&expected_sec[k]==bank_sec[i*18+:18]&&expected_data[k]===bank_data[i*256+:256])found=k;
    if(found<0)$fatal(1,"CONVERT_EXACT_OR_DUP bank%0d sec%0d",i,bank_sec[i*18+:18]);
    if(bank_word_mask[i*8+:8]!==8'hff||bank_sec[i*18+:18]%512!=i)$fatal(1,"BANK_ID_OR_MASK");
    if(cycle-source_cycle[found]<2)$fatal(1,"CONVERT_CAUSAL_LATENCY");
    if(cycle-source_cycle[found]<min_elapsed)min_elapsed=cycle-source_cycle[found];
    if(cycle-source_cycle[found]>max_elapsed)max_elapsed=cycle-source_cycle[found];
    pending[found]=0;got=got+1;nout=nout+1;
   end
  end
  if(nout>max_out)max_out=nout;
  prev_hold=bank_v&~bank_r;prev_sec=bank_sec;prev_data=bank_data;prev_mask=bank_word_mask;
  #0.05;
  for(integer p=0;p<8;p=p+1)begin
   if(physical_fault[p])$fatal(1,"ACTUAL_BANK_FAULT");
   if(physical_done[p])begin
    if(bankout[p]>=bankin[p]||bank_due[p][bankout[p]]!=cycle||physical_tag[p*20+:20]!==bank_expected_tag[p][bankout[p]])$fatal(1,"ACTUAL_BANK_COMMIT_ID_OR_TIME");
    bankout[p]=bankout[p]+1;bankcommits=bankcommits+1;
   end
  end
  if({off_ready,off_valid,off_fault}!==9'd0)$fatal(1,"DEFAULT_OFF");
  if(^({raw_r,bank_v,bank_sec,bank_data,bank_word_mask,fault})===1'bx)$fatal(1,"OUTPUT_X");
 end
 function automatic[255:0]rawpattern(input integer row);
  integer b;begin for(b=0;b<32;b=b+1)rawpattern[b*8+:8]=8'(row*32+b);end
 endfunction
 task drain;
 begin
  sink_allow=4'hf;repeat(20)@(negedge clk);
  if(want!=got)$fatal(1,"CONVERT_DROP %0d/%0d",got,want);
  if(fault)$fatal(1,"UNEXPECTED_FAULT");
  if(LIVE_BANKS&&bankcommits!=got)$fatal(1,"ACTUAL_BANK_COMMIT_DROP");
 end endtask
 task send(input integer slot,input[17:0]sec,input[1:0]fmt,input[3:0]mask,input[255:0]data);
 begin
  @(negedge clk);raw_sec[slot*18+:18]=sec;raw_fmt[slot*2+:2]=fmt;raw_piece_mask[slot*4+:4]=mask;raw_data[slot*256+:256]=data;raw_v[slot]=1;
  #0.01;while(!raw_r[slot])@(negedge clk);
  @(negedge clk);raw_v[slot]=0;
 end endtask
 integer row,f;
 initial begin
  repeat(4)@(negedge clk);rst_n=1;sink_allow=4'hf;
  // Allformats, all256E4M3encodings and BF16bitpatterns, everypiece number, masks.
  for(f=0;f<3;f=f+1)for(row=0;row<16;row=row+1)begin
   send(row%4,18'(row*512),2'(f),f==0?4'b0001:f==1?4'b0011:4'b1111,rawpattern(row));
  end
  drain;
  // Wrap acrosslogicalbank511: only pieces1..3 belongtile0.
  send(0,18'd511,2'd2,4'b1110,rawpattern(7));drain;
  send(1,18'd1023,2'd2,4'b1010,rawpattern(13));drain;
  // Four-way conflict+independent heldbank ports. Fill outputbank0 and thenstall it.
  sink_allow=0;send(0,18'd2048,2'd0,1,rawpattern(1));
  fork
   send(0,18'd2560,2'd2,15,rawpattern(2));
   send(1,18'd3072,2'd2,15,rawpattern(3));
   send(2,18'd3584,2'd2,15,rawpattern(4));
   send(3,18'd4096,2'd2,15,rawpattern(5));
  join
  sink_allow=4'b1110;repeat(16)@(negedge clk);drain;
  // Fourpieces/cycle roof onone source and no stalls.
  send(0,18'd5120,2'd2,15,rawpattern(6));drain;
  if(max_out!=4)$fatal(1,"CONVERTER_NOT_FOUR_WIDE");
  $display("CONVERT_DATA_PASS pieces%0d max4/cycle exactformats FP32/BF16/E4M3 masks wrap stalls RR4 actualquad8banks16SRAMmacros min_elapsed%0d max_elapsed_stalls%0d",got,min_elapsed,max_elapsed);
  // Invalid masks,format,bounds and tileownership are all failclosed; reset between cases.
  reject_mode=1;
  for(row=0;row<4;row=row+1)begin
   @(negedge clk);rst_n=0;raw_v=0;prev_hold=0;repeat(3)@(negedge clk);rst_n=1;
   case(row)
    0:send(0,0,3,1,0);
    1:send(0,0,0,2,0);
    2:send(0,18'h3ffff,2,2,0);
    3:send(0,4,0,1,0);
   endcase
   repeat(8)@(negedge clk);
   if(!fault||raw_r!=0||bank_v!=0)$fatal(1,"INVALID_NOT_CLOSED case%0d",row);
  end
  // Immutable rawcontrol rail fault while downstream blocked.
  @(negedge clk);rst_n=0;raw_v=0;prev_hold=0;repeat(3)@(negedge clk);rst_n=1;
  sink_allow=0;send(0,0,2,15,rawpattern(7));
  dut.sec_n[0]=dut.sec_n[0]^18'd1;
  repeat(6)@(negedge clk);
  if(!fault||bank_v!=0||raw_r!=0)$fatal(1,"CONTROL_NOT_CLOSED");
  $display("CONVERT_PASS malformed4 controlfault defaultoffarchitecture noX");$finish;
 end
endmodule
