`timescale 1ps/1ps
module tb_native_slice;
    localparam W=2160;
    reg clk=0;
    always #416 clk=~clk;
    reg [3:0] rst_n=0;
    reg iv=0;
    reg [W-1:0] id=0;
    wire oc,ov; wire [W-1:0] od;
    ot_hbm_native_register_slice #(.W(W),.ENABLE(1)) dut
      (.fclk_i(clk),.rst_n(rst_n),.i_v(iv),.i_d(id),.fclk_o(oc),.o_v(ov),.o_d(od));
    reg [W-1:0] refd [0:3]; reg [3:0] refv=0;
    integer checks=0;
    reg [31:0] rng=32'h1062026;
    function automatic [31:0] next(input [31:0] n);
      reg [31:0] r;
      begin r=n^(n<<13);r=r^(r>>17);next=r^(r<<5);end
    endfunction
    always @(negedge clk) begin
      refv[0]<=rst_n[0]&&iv; refd[0]<=id;
      refv[2]<=rst_n[2]&&refv[1];refd[2]<=refd[1];
    end
    always @(posedge clk) begin
      refv[1]<=rst_n[1]&&refv[0];refd[1]<=refd[0];
      refv[3]<=rst_n[3]&&refv[2];refd[3]<=refd[2];
      #5;
      if (checks>=12 && (ov!==refv[3] || (ov && od!==refd[3])))
        $fatal(1,"native slice exact mismatch check=%0d",checks);
      if(oc!==clk) $fatal(1,"four actual clock inversions not preserved");
      checks=checks+1;
    end
    initial begin
      for(integer cycle=0;cycle<1200;cycle=cycle+1) begin
        #200;
        rst_n=(cycle<8 || (cycle>=401&&cycle<411))?0:4'b1111;
        rng=next(rng);iv=rng[0];
        for(integer bitidx=0;bitidx<W;bitidx=bitidx+32) begin
          rng=next(rng);
          for(integer k=0;k<32&&bitidx+k<W;k=k+1) id[bitidx+k]=rng[k];
        end
        #632;
      end
      $display("PASS native W2160 stages4 seed1062026 checks=%0d",checks);
      $finish;
    end
endmodule
