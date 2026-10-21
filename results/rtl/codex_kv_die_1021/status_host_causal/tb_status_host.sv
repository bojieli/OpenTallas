`timescale 1ns/1ps
module tb_status_host;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,sv=0;reg[15:0]ep=0;reg[207:0]ext=0;
 reg av=0,wv=0,arv=0;reg[12:0]aa=0,ra=0;reg[31:0]wd=0;
 wire awr,wr,bv,arr,rv;wire[31:0]rd;wire[1:0]br,rr;
 wire da,dw,dar;wire[12:0]daddr,daraddr;wire[31:0]ddata;reg drv=0,dbv=0;
 integer writes=0;
 always @(posedge ck)begin drv<=dar;dbv<=da&&dw;if(da&&dw)writes<=writes+1;end
 qkd_host_status_obs #(.MUT(MUT))d(.clk(ck),.rst_n(rst_n),.status_obs_v(sv),.status_obs_epoch16(ep),.status_obs_payload(ext),
 .u_awvalid(av),.u_awready(awr),.u_awaddr(aa),.u_wvalid(wv),.u_wready(wr),.u_wdata(wd),.u_wstrb(4'hf),
 .u_bvalid(bv),.u_bready(1'b1),.u_bresp(br),.u_arvalid(arv),.u_arready(arr),.u_araddr(ra),
 .u_rvalid(rv),.u_rready(1'b1),.u_rdata(rd),.u_rresp(rr),
 .d_awvalid(da),.d_awready(1'b1),.d_awaddr(daddr),.d_wvalid(dw),.d_wready(1'b1),.d_wdata(ddata),.d_wstrb(),
 .d_bvalid(dbv),.d_bready(),.d_bresp(2'b00),.d_arvalid(dar),.d_arready(1'b1),.d_araddr(daraddr),
 .d_rvalid(drv),.d_rready(),.d_rdata(32'hcafebabe),.d_rresp(2'b00));
 task tick(input integer n);repeat(n)begin @(posedge ck);#1;end endtask
 task reset;@(negedge ck);rst_n=0;sv=0;av=0;wv=0;arv=0;tick(8);@(negedge ck);rst_n=1;tick(8);endtask
 task send(input[15:0]e,input[31:0]cnt,input[58:0]tag);
 @(negedge ck);ep=e;ext=0;ext[207:204]=1;ext[94]=cnt!=0;ext[92:61]=cnt;ext[60:2]=tag;sv=1;
 tick(1);@(negedge ck);sv=0;tick(3);endtask
 task write(input[12:0]a,input[31:0]v);
 @(negedge ck);aa=a;wd=v;av=1;wv=1;#1;if(!awr||!wr)$fatal(1,"AXI_WRITE_NOT_READY");tick(1);
 @(negedge ck);av=0;wv=0;tick(2);endtask
 task read(input[12:0]a,output[31:0]v,output[1:0]rsp);
 integer n;
 @(negedge ck);ra=a;arv=1;#1;if(!arr)$fatal(1,"AXI_READ_NOT_READY");tick(1);n=1;
 @(negedge ck);arv=0;
 while(!rv)begin tick(1);n=n+1;if(n>6)$fatal(1,"AXI_READ_TIMEOUT");end
 v=rd;rsp=rr;
 if(a>=13'h1800&&a<13'h1a00&&n!=3)$fatal(1,"CSR_FIXED_LATENCY %d",n);
 tick(1);
 endtask
 reg[319:0]snap;integer i;reg[31:0]v;reg[1:0]rsp;reg[207:0]saved;
 task snapshot;
 write(13'h1800,1);for(i=0;i<10;i=i+1)begin read(13'(13'h1900+4*i),v,rsp);if(rsp!=0)$fatal(1,"SNAPSHOT_RRESP");snap[32*i+:32]=v;end
 endtask
 initial begin
 reset();read(13'h1900,v,rsp);if(rsp!==2||v!==0)$fatal(1,"UNCAPTURED_READ_NOT_REJECTED");
 send(16'd64,32'd5,{16'd66,6'd1,18'd20,13'd100,6'd0});saved=ext;snapshot();
 if(snap[207:0]!==saved||snap[223:208]!==64||snap[255:224]!==1||snap[287:256]!==5||snap[291:288]!==0||!snap[292])$fatal(1,"FIRST_RECORD_OR_DELTA_LOST %h",snap);
 send(16'd64,32'd8,{16'd69,6'd1,18'd21,13'd101,6'd0});
 read(13'h1900,v,rsp);if(v!==saved[31:0])$fatal(1,"SNAPSHOT_NOT_ATOMIC");
 saved=ext;snapshot();if(snap[207:0]!==saved||snap[255:224]!==2||snap[287:256]!==3)$fatal(1,"COMPLETION_DELTA_NOT_COUNT");
 send(16'd64,32'd7,{16'd70,6'd1,18'd22,13'd102,6'd0});snapshot();if(!snap[288]||snap[287:256]!==0)$fatal(1,"SAME_EPOCH_REGRESSION_NOT_REPORTED");
 reset();send(16'd64,32'd5,{16'd66,6'd1,18'd20,13'd100,6'd0});send(16'd68,32'd1,{16'd71,6'd1,18'd30,13'd103,6'd0});snapshot();
 if(snap[223:208]!==68||snap[287:256]!==1||snap[291:288]!==0)$fatal(1,"EPOCH_FENCE_DELTA_BAD");
 saved=ext;@(negedge ck);ext[207:204]=2;sv=1;tick(1);@(negedge ck);sv=0;tick(3);snapshot();
 if(!snap[291]||snap[207:0]!==saved||snap[255:224]!==2)$fatal(1,"BAD_RECORD_NOT_QUARANTINED");
 read(13'h1004,v,rsp);if(v!==32'hcafebabe||rsp!==0)$fatal(1,"CSR_PASS_THROUGH_BROKEN");
 write(13'h1000,32'h12345678);if(writes==0)$fatal(1,"CSR_WRITE_DROPPED");
 $display("STATUS_HOST_PASS atomic208+epoch+seq delta_count regression fence identity readonly pass_through latency3");$finish;
 end
endmodule
