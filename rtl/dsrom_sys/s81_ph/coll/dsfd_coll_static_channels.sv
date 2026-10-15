`timescale 1ns/1ps
// Compiler calendar channel adapter. Lane c is physical lane 3+c; physical
// lanes 0..2 belong to TP4. payload552 enters the real595/FMT1 transport.
// kind: 0 raw VM row, 1 WFC, 2 host, 3 illegal. A slot is consumed on its
// named edge even on fault: there is no ready, grant, retry, FIFO or credit.
// Raw VM rows still require compiler allocated mutable storage in composition.
// Exact one-cycle registered latency in either direction. rst_n synchronous.
module dsfd_coll_static_channels #(parameter integer MUT=0)(
 input wire clk, rst_n,
 input wire [4:0] tx_slot, rx_slot,
 input wire [9:0] tx_kind, rx_kind,
 input wire vm_tx_last, input wire vm_tx_valid, input wire [2:0] vm_tx_channel,
 input wire [551:0] vm_tx_payload,
 input wire [513:0] wfc_tx,
 input wire host_tx_valid, input wire [10:0] host_status,
 input wire [64:0] host_completion,
 output reg [4:0] lane_tx_last, output reg [4:0] lane_tx_valid,
 output reg [2759:0] lane_tx_payload,
 input wire [4:0] lane_rx_last, input wire [4:0] lane_rx_valid,
 input wire [2759:0] lane_rx_payload,
 output reg vm_rx_last, output reg vm_rx_valid, output reg [2:0] vm_rx_channel,
 output reg [551:0] vm_rx_payload,
 output reg [513:0] wfc_rx,
 output reg [515:0] host_rx,
 output reg fault
);
 integer c;
 integer tv,tw,th,rv,rw,rh;
 reg bad;
 reg [4:0] ntv,ntl; reg nvl;
 reg [2759:0] ntd;
 reg nvv; reg [2:0] nvc; reg [551:0] nvd;
 reg [513:0] nwd; reg [515:0] nhd;
 reg [551:0] payload;
 always @* begin
   tv=0;tw=0;th=0;rv=0;rw=0;rh=0;bad=0;
   ntv=0;ntl=0;nvl=0;ntd=0;nvv=0;nvc=0;nvd=0;nwd=0;nhd=0;payload=0;
   for(c=0;c<5;c=c+1) begin
     if(tx_slot[c]) begin
       case(tx_kind[c*2 +: 2])
         0: begin tv=tv+1; bad=bad|!vm_tx_valid|(vm_tx_channel!=c[2:0]);
            ntl[c]=vm_tx_last; ntv[c]=vm_tx_valid; ntd[c*552 +: 552]=vm_tx_payload; end
         1: begin tw=tw+1; bad=bad|!wfc_tx[0];
            ntl[c]=wfc_tx[513]; ntv[c]=wfc_tx[0]; ntd[c*552 +: 552]={wfc_tx[513],39'b0,wfc_tx[512:1]}; end
         2: begin th=th+1; bad=bad|!host_tx_valid;
            ntl[c]=1; ntv[c]=host_tx_valid;
            ntd[c*552 +: 552]={1'b1,470'b0,host_status,5'b0,host_completion}; end
         default: bad=1;
       endcase
     end
     // Unexpected and missing arrivals both fault on the original calendar edge.
     bad=bad|(lane_rx_valid[c]!=rx_slot[c]);
     if(rx_slot[c]) begin
       payload=lane_rx_payload[c*552 +: 552];
       case(rx_kind[c*2 +: 2])
         0: begin rv=rv+1; nvl=lane_rx_last[c];nvv=lane_rx_valid[c];nvc=c[2:0];nvd=payload;end
         1: begin rw=rw+1;nwd={lane_rx_last[c],payload[511:0],lane_rx_valid[c]};end
         2: begin rh=rh+1;nhd={payload[514:0],lane_rx_valid[c]};end
         default: bad=1;
       endcase
     end
   end
   bad=bad|(tv>1)|(tw>1)|(th>1)|(rv>1)|(rw>1)|(rh>1);
   bad=bad|(vm_tx_valid!=(tv!=0))|(wfc_tx[0]!=(tw!=0))|(host_tx_valid!=(th!=0));
   // Negative control changes actual transmitted data, not the checker.
   if(MUT==1) ntd[0]=~ntd[0];
 end
 always @(posedge clk) begin
   if(!rst_n) begin
     lane_tx_last<=0;vm_rx_last<=0;lane_tx_valid<=0;lane_tx_payload<=0;vm_rx_valid<=0;vm_rx_channel<=0;
     vm_rx_payload<=0;wfc_rx<=0;host_rx<=0;fault<=0;
   end else begin
     lane_tx_last<=ntl;vm_rx_last<=nvl;lane_tx_valid<=ntv;lane_tx_payload<=ntd;vm_rx_valid<=nvv;vm_rx_channel<=nvc;
     vm_rx_payload<=nvd;wfc_rx<=nwd;host_rx<=nhd;fault<=fault|bad;
   end
 end
endmodule
