`timescale 1ns/1ps
module tb_source_abi #(parameter integer F=3,PWT=545);
 localparam NSM=8,NPT=8,FW=512;
reg clk_sm;
reg rst_sm_n;
reg pclk;
reg prst_n;
wire sm_clk;
wire sm_rst_n;
wire endpoint_clk;
wire endpoint_rst_n;
wire endpoint_pclk;
wire endpoint_prst_n;
reg [NSM-1:0] start;
reg [NSM-1:0] release_in;
reg [NSM-1:0] d_valid;
reg [NSM*13-1:0] op_rows;
reg [NSM*13-1:0] input;
reg [NSM*8-1:0] op_g;
reg [NSM*8-1:0] input;
reg [NSM*2-1:0] op_fmt;
reg [NSM*2-1:0] input;
reg [NSM*32-1:0] d_base;
reg [NSM*32-1:0] input;
wire [NSM-1:0] sm_start;
wire [NSM-1:0] sm_release_in;
wire [NSM-1:0] sm_d_valid;
wire [NSM*13-1:0] sm_op_rows;
wire [NSM*13-1:0] output;
wire [NSM*8-1:0] sm_op_g;
wire [NSM*8-1:0] output;
wire [NSM*2-1:0] sm_op_fmt;
wire [NSM*2-1:0] output;
wire [NSM*32-1:0] sm_d_base;
wire [NSM*32-1:0] output;
reg [NSM-1:0] sm_start_ready;
reg [NSM-1:0] sm_busy;
reg [NSM-1:0] sm_arrive;
reg [NSM-1:0] sm_released;
reg [NSM-1:0] sm_d_ready;
wire [NSM-1:0] start_ready;
wire [NSM-1:0] busy;
wire [NSM-1:0] arrive;
wire [NSM-1:0] released;
wire [NSM-1:0] d_ready;
reg [NPT-1:0] endpoint_tx_v;
reg [NPT-1:0] input;
wire [NPT-1:0] ph_tx_v;
wire [NPT-1:0] output;
reg [NPT-1:0] ph_rx_v;
reg [NPT-1:0] input;
wire [NPT-1:0] endpoint_rx_v;
wire [NPT-1:0] output;
reg [NPT-1:0] sw_cr_ret;
reg [NPT-1:0] output;
reg [NPT-1:0] endpoint_rx_credit;
reg [NPT-1:0] output;
 ot_hbm_station_source_abi #(.ENABLE(1),.FUNCTION(F),.PWT(PWT)) dut(.*);
 reg [7:0] rv,fault;reg [95:0] rrow;reg [2047:0] rdata;
 wire [2159:0] die_wire,gather_internal;
 ot_hbm_sm_result_codec codec(.*);
 reg [31:0] rng=32'h1062026;
 function automatic [31:0] step(input [31:0] v);reg [31:0] t;begin t=v^(v<<13);t=t^(t>>17);step=t^(t<<5);end endfunction
 initial begin
 clk_sm=0;
 rst_sm_n=0;
 pclk=0;
 prst_n=0;
 start=0;
 release_in=0;
 d_valid=0;
 op_rows=0;
 input=0;
 op_g=0;
 input=0;
 op_fmt=0;
 input=0;
 d_base=0;
 input=0;
 sm_start_ready=0;
 sm_busy=0;
 sm_arrive=0;
 sm_released=0;
 sm_d_ready=0;
 endpoint_tx_v=0;
 input=0;
 ph_rx_v=0;
 input=0;
 sw_cr_ret=0;
 output=0;
 endpoint_rx_credit=0;
 output=0;
 rv=0;fault=0;rrow=0;rdata=0;
 for(integer trial=0;trial<64;trial=trial+1)begin
 rng=step(rng);clk_sm=rng[0];
 rng=step(rng);rst_sm_n=rng[0];
 rng=step(rng);pclk=rng[0];
 rng=step(rng);prst_n=rng[0];
 for(integer b=0;b<$bits(start);b=b+1)begin rng=step(rng);start[b]=rng[0];end
 for(integer b=0;b<$bits(release_in);b=b+1)begin rng=step(rng);release_in[b]=rng[0];end
 for(integer b=0;b<$bits(d_valid);b=b+1)begin rng=step(rng);d_valid[b]=rng[0];end
 for(integer b=0;b<$bits(op_rows);b=b+1)begin rng=step(rng);op_rows[b]=rng[0];end
 for(integer b=0;b<$bits(input);b=b+1)begin rng=step(rng);input[b]=rng[0];end
 for(integer b=0;b<$bits(op_g);b=b+1)begin rng=step(rng);op_g[b]=rng[0];end
 for(integer b=0;b<$bits(input);b=b+1)begin rng=step(rng);input[b]=rng[0];end
 for(integer b=0;b<$bits(op_fmt);b=b+1)begin rng=step(rng);op_fmt[b]=rng[0];end
 for(integer b=0;b<$bits(input);b=b+1)begin rng=step(rng);input[b]=rng[0];end
 for(integer b=0;b<$bits(d_base);b=b+1)begin rng=step(rng);d_base[b]=rng[0];end
 for(integer b=0;b<$bits(input);b=b+1)begin rng=step(rng);input[b]=rng[0];end
 for(integer b=0;b<$bits(sm_start_ready);b=b+1)begin rng=step(rng);sm_start_ready[b]=rng[0];end
 for(integer b=0;b<$bits(sm_busy);b=b+1)begin rng=step(rng);sm_busy[b]=rng[0];end
 for(integer b=0;b<$bits(sm_arrive);b=b+1)begin rng=step(rng);sm_arrive[b]=rng[0];end
 for(integer b=0;b<$bits(sm_released);b=b+1)begin rng=step(rng);sm_released[b]=rng[0];end
 for(integer b=0;b<$bits(sm_d_ready);b=b+1)begin rng=step(rng);sm_d_ready[b]=rng[0];end
 for(integer b=0;b<$bits(endpoint_tx_v);b=b+1)begin rng=step(rng);endpoint_tx_v[b]=rng[0];end
 for(integer b=0;b<$bits(input);b=b+1)begin rng=step(rng);input[b]=rng[0];end
 for(integer b=0;b<$bits(ph_rx_v);b=b+1)begin rng=step(rng);ph_rx_v[b]=rng[0];end
 for(integer b=0;b<$bits(input);b=b+1)begin rng=step(rng);input[b]=rng[0];end
 for(integer b=0;b<$bits(sw_cr_ret);b=b+1)begin rng=step(rng);sw_cr_ret[b]=rng[0];end
 for(integer b=0;b<$bits(output);b=b+1)begin rng=step(rng);output[b]=rng[0];end
 for(integer b=0;b<$bits(endpoint_rx_credit);b=b+1)begin rng=step(rng);endpoint_rx_credit[b]=rng[0];end
 for(integer b=0;b<$bits(output);b=b+1)begin rng=step(rng);output[b]=rng[0];end
 for(integer b=0;b<$bits(rv);b=b+1)begin rng=step(rng);rv[b]=rng[0];end
 for(integer b=0;b<$bits(fault);b=b+1)begin rng=step(rng);fault[b]=rng[0];end
 for(integer b=0;b<$bits(rrow);b=b+1)begin rng=step(rng);rrow[b]=rng[0];end
 for(integer b=0;b<$bits(rdata);b=b+1)begin rng=step(rng);rdata[b]=rng[0];end
 #1;
 if(sm_start !== ((F==3)?start:0))$fatal(1,"control named pin sm_start");
 if(sm_release_in !== ((F==3)?release_in:0))$fatal(1,"control named pin sm_release_in");
 if(sm_d_valid !== ((F==3)?d_valid:0))$fatal(1,"control named pin sm_d_valid");
 if(sm_op_rows !== ((F==3)?op_rows:0))$fatal(1,"control named pin sm_op_rows");
 if(sm_op_c !== ((F==3)?op_c:0))$fatal(1,"control named pin sm_op_c");
 if(sm_op_g !== ((F==3)?op_g:0))$fatal(1,"control named pin sm_op_g");
 if(sm_op_gs !== ((F==3)?op_gs:0))$fatal(1,"control named pin sm_op_gs");
 if(sm_op_fmt !== ((F==3)?op_fmt:0))$fatal(1,"control named pin sm_op_fmt");
 if(sm_op_xb !== ((F==3)?op_xb:0))$fatal(1,"control named pin sm_op_xb");
 if(sm_d_base !== ((F==3)?d_base:0))$fatal(1,"control named pin sm_d_base");
 if(sm_d_lines !== ((F==3)?d_lines:0))$fatal(1,"control named pin sm_d_lines");
 if(start_ready !== ((F==3)?sm_start_ready:0))$fatal(1,"control named pin start_ready");
 if(busy !== ((F==3)?sm_busy:0))$fatal(1,"control named pin busy");
 if(arrive !== ((F==3)?sm_arrive:0))$fatal(1,"control named pin arrive");
 if(released !== ((F==3)?sm_released:0))$fatal(1,"control named pin released");
 if(d_ready !== ((F==3)?sm_d_ready:0))$fatal(1,"control named pin d_ready");
 if(sm_clk !== ((F==3)?clk_sm:0))$fatal(1,"control named pin sm_clk");
 if(sm_rst_n !== ((F==3)?rst_sm_n:0))$fatal(1,"control named pin sm_rst_n");
 if(ph_tx_v !== ((F==4)?endpoint_tx_v:0))$fatal(1,"duplex domain/direction ph_tx_v");
 if(ph_tx_flit !== ((F==4)?endpoint_tx_flit:0))$fatal(1,"duplex domain/direction ph_tx_flit");
 if(endpoint_rx_v !== ((F==4)?ph_rx_v:0))$fatal(1,"duplex domain/direction endpoint_rx_v");
 if(endpoint_rx_flit !== ((F==4)?ph_rx_flit:0))$fatal(1,"duplex domain/direction endpoint_rx_flit");
 if(endpoint_cr_ret !== ((F==4)?sw_cr_ret:0))$fatal(1,"duplex domain/direction endpoint_cr_ret");
 if(rx_credit !== ((F==4)?endpoint_rx_credit:0))$fatal(1,"duplex domain/direction rx_credit");
 if(endpoint_clk !== ((F==4)?clk_sm:0))$fatal(1,"duplex domain/direction endpoint_clk");
 if(endpoint_rst_n !== ((F==4)?rst_sm_n:0))$fatal(1,"duplex domain/direction endpoint_rst_n");
 if(endpoint_pclk !== ((F==4)?pclk:0))$fatal(1,"duplex domain/direction endpoint_pclk");
 if(endpoint_prst_n !== ((F==4)?prst_n:0))$fatal(1,"duplex domain/direction endpoint_prst_n");
 for(integer k=0;k<8;k=k+1)begin
  if(die_wire[k*270]!==rv[k]||die_wire[k*270+1+:12]!==rrow[k*12+:12]||die_wire[k*270+13+:256]!==rdata[k*256+:256]||die_wire[k*270+269]!==fault[k])$fatal(1,"actual bit0-first result ABI");
  if(gather_internal[k*270+:270]!=={fault[k],rv[k],rrow[k*12+:12],rdata[k*256+:256]})$fatal(1,"explicit canonical gather codec");
 end
 end
 $display("PASS actual named source ABI FUNCTION%0d NSM8/NPT8/PWT%0d seed1062026:64 full-port vectors + SM wire codec; zero storage/cycles; no parent qualification",F,PWT);
 $finish;
 end
endmodule
