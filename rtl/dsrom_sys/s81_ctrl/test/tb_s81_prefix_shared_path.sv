`timescale 1ns/1ps
module tb_s81_prefix_shared_path #(parameter integer INJECT=0);
 reg clk=0,serial_clk=0;always #0.416667 clk=~clk;always #0.555555 serial_clk=~serial_clk;
 reg rst_n=0,start_v=0;wire start_r,pdone,pfault,pce;
 reg[73:0] id={3'd0,2'd3,2'd2,4'd13,21'd1048575,10'd513,32'hdead0000};
 reg[1:0] iv=0;wire[1:0] ir;reg[147:0] itag=0;reg[17:0] ie=0;
 reg[13:0] iw=0;reg[1:0] ilast=0;reg[1023:0] data=0;
 wire pv,pr,pl;wire[511:0] pd;wire[73:0] pt;wire[6:0] pw;
 reg scmd=0,siv=0;wire scr,sir,sv,sr,sl,sce,sbusy,sfault;
 reg[511:0] sidata=0;reg[6:0] siword=0;
 wire[511:0] sd;wire[73:0] st;wire[6:0] sw;
 wire ov,ol,cd,busy,fault;reg ordy=0;wire[511:0] out;
 wire[73:0] ot;wire[6:0] ow;
 reg[31:0] inputs[0:3839],shared[0:1279],gold[0:1279];
 integer w,l,received=0,cycles=0,sumcycles=0,first=0,ptail=0,stail=0,corrected_count=0;
 reg[511:0] held;reg stalled=0;
`ifdef BINDING_DUT
 ot_s81_prefix_shared_binding #(.ENABLE(1)) binding(.stream_clk(clk),.serial_clk(serial_clk),
 .rst_n(rst_n),.start_valid(start_v),.start_ready(start_r),.start_identity(id),
 .start_ids({9'd127,9'd65,9'd3}),.expert_valid(iv),.expert_ready(ir),
 .expert_identity(itag),.expert_id(ie),.expert_last(ilast),.expert_word(iw),.expert_data(data),
 .shared_valid(siv),.shared_ready(sir),.shared_data(sidata),.shared_identity(id),
 .shared_word(siword),.shared_last(siword==79),.shared_fmt_fp32(1'b0),.shared_error(1'b0),
 .out_valid(ov),.out_ready(ordy),.out_data(out),.out_identity(ot),.out_word(ow),.out_last(ol),
 .done(cd),.busy(busy),.fault(fault));
 assign scr=start_r;assign pfault=0;assign sfault=0;assign sbusy=0;
 assign pv=binding.enabled.prefix_v;assign pr=binding.enabled.prefix_r;
 assign pl=binding.enabled.prefix_last;
 assign sv=binding.enabled.sv;assign sr=binding.enabled.sr;assign sl=binding.enabled.sl;
 assign sce=0;
 always @(posedge clk)if(rst_n&&busy&&start_r)$fatal(1,"BINDING released owned command early");
`else
 ot_mtp_p2_prefix_path #(.ENABLE(1)) prefix(.clk(clk),.rst_n(rst_n),
 .start_v(start_v),.start_r(start_r),.start_identity(id),.start_ids({9'd127,9'd65,9'd3}),
 .in_v(iv),.in_r(ir),.in_identity(itag),.in_expert(ie),.in_shared(2'b00),
 .in_last(ilast),.in_word(iw),.in_data(data),.out_v(pv),.out_r(pr),
 .out_data(pd),.out_identity(pt),.out_word(pw),.out_last(pl),
 .abort(1'b0),.done(pdone),.fault(pfault),.corrected(pce));
 ot_s81_shared_publisher_plain #(.ENABLE(1),.READ_INJECT(INJECT)) publisher(.clk(clk),.rst_n(rst_n),
 .cmd_valid(scmd),.cmd_ready(scr),.cmd_context(id),.in_valid(siv),.in_ready(sir),
 .in_data(sidata),.in_context(id),.in_word(siword),.in_last(siword==79),
 .in_fmt_fp32(1'b0),.in_error(1'b0),.out_valid(sv),.out_ready(sr),
 .out_data(sd),.out_context(st),.out_word(sw),.out_last(sl),
 .out_corrected(sce),.busy(sbusy),.fault(sfault));
 ot_s81_primary_shared_receive #(.ENABLE(1)) primary(.stream_clk(clk),.serial_clk(serial_clk),
 .rst_n(rst_n),.p_valid(pv),.p_ready(pr),.p_data(pd),.p_tag(pt),.p_word(pw),.p_last(pl),
 .s_valid(sv),.s_ready(sr),.s_data(sd),.s_tag(st),.s_word(sw),.s_last(sl),
 .out_valid(ov),.out_ready(ordy),.out_data(out),.out_tag(ot),.out_word(ow),
 .out_last(ol),.context_done(cd),.busy(busy),.fault(fault));
`endif
 always @(posedge clk)if(rst_n)begin
 cycles=cycles+1;
 if(INJECT==3&&sfault)begin
 if(received!=0||sv)$fatal(1,"COMPOSE UE published payload");
 $display("COMPOSE shared SRAM UE blocks publication PASS cycle%0d",cycles);$finish;
 end
 if(pfault||sfault||fault)$fatal(1,"COMPOSE component fault");
 if(sv&&sr&&sce)corrected_count=corrected_count+1;
 if(pv&&pr&&pl)ptail=cycles;
 if(sv&&sr&&sl)stail=cycles;
 end
 always @(negedge serial_clk)ordy=rst_n&&(sumcycles%11>2);
 always @(posedge serial_clk)if(rst_n)begin
 sumcycles=sumcycles+1;
 if(ov&&!ordy)begin
 if(stalled&&out!==held)$fatal(1,"COMPOSE stall changed");held=out;stalled=1;
 end else stalled=0;
 if(ov&&ordy)begin
 if(!first)first=cycles;
 if(ot!==id||ow!==received||ol!==(received==79))$fatal(1,"COMPOSE metadata");
 for(l=0;l<16;l=l+1)if(out[32*l+:32]!==gold[received*16+l])
 $fatal(1,"COMPOSE numerical word%0d lane%0d got%h exp%h",received,l,out[32*l+:32],gold[received*16+l]);
 received=received+1;
 end
 end
 function automatic[511:0] flit(input integer e,w);
 integer j;begin for(j=0;j<16;j=j+1)flit[32*j+:32]=inputs[e*1280+w*16+j];end
 endfunction
 task automatic sendpair(input integer w);
 begin @(negedge clk);iv=3;itag={id,id};ie={9'd3,9'd127};
 iw={7'(w),7'(w)};ilast={2{w==79}};data={flit(0,w),flit(2,w)};
 @(posedge clk);if(ir!==3)$fatal(1,"COMPOSE prefix readiness");@(negedge clk);iv=0;end
 endtask
 initial begin
 $readmemh("inputs.hex",inputs);$readmemh("shared.hex",shared);$readmemh("final.hex",gold);
 repeat(4)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
 start_v=1;scmd=1;@(posedge clk);if(!start_r||!scr)$fatal(1,"COMPOSE start");
 @(negedge clk);start_v=0;scmd=0;
 fork
 begin
 for(integer a=0;a<80;a=a+1)sendpair(a);
 for(integer a=0;a<80;a=a+1)begin
 @(negedge clk);iv=1;itag={id,id};ie={9'd0,9'd65};iw={7'd0,7'(a)};
 ilast={1'b0,a==79};data={512'd0,flit(1,a)};
 @(posedge clk);if(!ir[0])$fatal(1,"COMPOSE second readiness");@(negedge clk);iv=0;
 end
 end
 begin
 for(integer a=0;a<80;a=a+1)begin
 @(negedge clk);while(!sir)@(negedge clk);
 if(a%7==0)repeat(3)@(negedge clk);
 for(integer j=0;j<16;j=j+1)sidata[32*j+:32]=shared[a*16+j];
 siword=a;siv=1;@(posedge clk);if(!sir)$fatal(1,"COMPOSE shared input readiness");
 @(negedge clk);siv=0;
 end
 end
 join
 wait(cd);repeat(6)@(negedge serial_clk);
 if(received!=80||busy||sbusy||!start_r)$fatal(1,"COMPOSE final retirement");
 if(INJECT==1&&corrected_count!=80)$fatal(1,"COMPOSE missing SRAM correction");
 if(INJECT==1)$display("COMPOSE shared SRAM CE80 corrected PASS");
 $display("COMPOSE PASS actual12prefixSRAM+3sharedSRAM native594CDC16LAT3 sharedLAST1280values frames80 streamcycles%0d serialcycles%0d first%0d prefixlast%0d sharedlast%0d",cycles,sumcycles,first,ptail,stail);$finish;
 end
 initial begin #1000000;$fatal(1,"COMPOSE deadlock");end
endmodule
