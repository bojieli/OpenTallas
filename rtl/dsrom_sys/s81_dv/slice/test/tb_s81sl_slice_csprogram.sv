`timescale 1ns/1ps
// Directed standard-slice LF_CS forwarding proof: real ring RD/CTL packets,
// SW quantization in leaf2, HLOAD/POST/HSTORE/RDOUT in leaf0. Every public
// output and POST producer completion compared cycle for cycle against the
// pre-R3 default slice. This does not qualify the generated cap5r clone.
module tb_s81sl_slice_csprogram;
    parameter integer HB = 0;
    parameter integer MUT = 0;
    parameter integer CYC = 4000;
    parameter integer SEED = 1;
    localparam [19:0] N1 = 20'h11111, N2 = 20'h22222, N4 = 20'h44444;
    reg clk = 1'b0; always #0.5 clk = ~clk;
    reg rst_n = 1'b0;
    reg [1103:0] ri_w, ri_e, bi; reg [275:0] vi; reg [559:0] rt;
    wire [1103:0] ro_e_a, ro_w_a, ro_e_b, ro_w_b; wire [512:0] bo_a, bo_b; wire [275:0] vo_a, vo_b; wire [4415:0] xc_a, xc_b;
    wire [15:0] cl_a, cl_b, cx_a, cx_b; wire [1:0] cv_a, cv_b; wire [7:0] cr_a, cr_b; wire f_a, f_b;
    O_ot_s81sl_slice #(.HB(HB)) u_a (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e_a),
        .ro_w(ro_w_a), .vi(vi), .vo(vo_a), .bi(bi), .bo(bo_a), .xc(xc_a), .rt(rt), .ck_line(cl_a), .ck_v(cv_a), .ck_xc(cx_a),
        .ck_rt(cr_a), .fault(f_a));
    generate if (MUT == 0) begin : g_m0
        ot_s81sl_slice #(.HB(HB)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e_b),
            .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b), .ck_v(cv_b),
            .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end else if (MUT == 1) begin : g_m1
        ot_s81sl_slice #(.HB(HB), .LF_CS_U_D(20'h00100)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e),
            .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b),
            .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end else if (MUT == 2) begin : g_m2
        ot_s81sl_slice #(.HB(HB), .LF_CS_HI_D(20'h00002)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3), .ri_w(ri_w), .ri_e(ri_e),
            .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt), .ck_line(cl_b),
            .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end else begin : g_m3
        ot_s81sl_slice #(.HB(HB), .LF_CS_HI_D(N2), .LF_CS_HO_D(N2), .LF_CS_H_G(N4), .LF_CS_PVS_D(N1), .LF_CS_SWR_D(N1),
            .LF_CS_U_D(N1), .LF_CS_VNI_D(N1), .LF_CS_VSP_D(N1), .LF_CS_Y_D(N1)) u_b (.clk(clk), .rst_n(rst_n), .sid(4'd3),
            .ri_w(ri_w), .ri_e(ri_e), .ro_e(ro_e_b), .ro_w(ro_w_b), .vi(vi), .vo(vo_b), .bi(bi), .bo(bo_b), .xc(xc_b), .rt(rt),
            .ck_line(cl_b), .ck_v(cv_b), .ck_xc(cx_b), .ck_rt(cr_b), .fault(f_b));
    end endgenerate
    wire [11041:0] oa = {ro_e_a, ro_w_a, bo_a, vo_a, xc_a, f_a};
    wire [11041:0] ob = {ro_e_b, ro_w_b, bo_b, vo_b, xc_b, f_b};
    wire [41:0] ka = {cl_a, cx_a, cv_a, cr_a}, kb = {cl_b, cx_b, cv_b, cr_b};
    // Full public interface is checked at every edge, including idle and fault.
    // POST h-write is the declared producer completion used to price CS_HI_D;
    // comparing it prevents a late RDOUT from hiding an incorrect stage count.
    integer cycle=0, bad=0, public_bad=0, post_bad=0, ubeats=0, postbeats=0, xbeats=0, phase=0;
    reg [255:0] image [0:511]; reg [159:0] swcmd [0:0]; string fixture;
    always @(posedge clk) begin
        cycle <= cycle+1;
        if (rst_n && cycle>50) begin
            if (oa !== ob || ka !== kb) begin
                bad=bad+1; public_bad=public_bad+1;
                if (public_bad<5) $display("CSP_PUBLIC_MISMATCH cycle=%0d phase=%0d ro_e=%0d ro_w=%0d bo=%0d vo=%0d xc=%0d fault=%0d clock=%0d",
                    cycle,phase,ro_e_a!==ro_e_b,ro_w_a!==ro_w_b,bo_a!==bo_b,vo_a!==vo_b,xc_a!==xc_b,f_a!==f_b,ka!==kb);
            end
            if (u_a.lf[2].u_lf.u_v) ubeats=ubeats+1;
            if (u_a.lf[2].u_lf.xf_v) xbeats=xbeats+1;
            if (phase==3) begin
                if (u_a.lf[0].u_lf.hw_v) postbeats=postbeats+1;
                if (post_a !== post_b) begin bad=bad+1; post_bad=post_bad+1; end
            end
        end
    end
    wire [260:0] post_a={u_a.lf[0].u_lf.hw_v,u_a.lf[0].u_lf.hw_j,u_a.lf[0].u_lf.hw_hf,u_a.lf[0].u_lf.hw_d};
    wire [260:0] post_b;
    generate
    if (MUT==0) begin assign post_b={g_m0.u_b.lf[0].u_lf.hw_v,g_m0.u_b.lf[0].u_lf.hw_j,g_m0.u_b.lf[0].u_lf.hw_hf,g_m0.u_b.lf[0].u_lf.hw_d}; end
    else if (MUT==1) begin assign post_b={g_m1.u_b.lf[0].u_lf.hw_v,g_m1.u_b.lf[0].u_lf.hw_j,g_m1.u_b.lf[0].u_lf.hw_hf,g_m1.u_b.lf[0].u_lf.hw_d}; end
    else if (MUT==2) begin assign post_b={g_m2.u_b.lf[0].u_lf.hw_v,g_m2.u_b.lf[0].u_lf.hw_j,g_m2.u_b.lf[0].u_lf.hw_hf,g_m2.u_b.lf[0].u_lf.hw_d}; end
    else if (MUT==3) begin assign post_b={g_m3.u_b.lf[0].u_lf.hw_v,g_m3.u_b.lf[0].u_lf.hw_j,g_m3.u_b.lf[0].u_lf.hw_hf,g_m3.u_b.lf[0].u_lf.hw_d}; end
    endgenerate
    function automatic [1103:0] ctl(input [4:0] mask,input [159:0] body);
        reg [1103:0] x; begin x=0;x[0]=1;x[8:4]=1;x[12:9]=2;x[21+:16]=16'h8;
            x[37+:5]=0;x[42+:5]=mask;x[47+:160]=body;ctl=x;end
    endfunction
    task automatic idle(input integer n); repeat(n) @(negedge clk); endtask
    task automatic send(input [1103:0] x); begin @(negedge clk);ri_w=x;@(negedge clk);ri_w=0;end endtask
    task automatic cmd(input [4:0] mask,input [3:0] op,input [9:0] a0,input [9:0] a1,input [7:0] n);
        send(ctl(mask,{128'd0,n,a1,a0,op})); endtask
    reg [1103:0] packet; integer b,j,k;
    initial begin
        ri_w=0;ri_e=0;bi=0;vi=0;rt=0;
        if (!$value$plusargs("fixture=%s",fixture)) $fatal(1,"fixture required");
        $readmemh({fixture,"/pairs.mem"},image);$readmemh({fixture,"/swcmd.mem"},swcmd);
        idle(8);rst_n=1;idle(60);phase=1;
        // Real ring RD packets, addressed to sid3 leaf0/2: four consecutive row pairs per packet.
        for(k=0;k<2;k=k+1) for(b=0;b<128;b=b+1) begin
            packet=0;packet[0]=1;packet[3:1]=4;packet[8:4]=1;packet[12:9]=2;packet[21+:16]=16'h8;
            packet[37+:3]=(k==0)?0:2;packet[40+:10]=8*b;packet[50+:2]=3;
            for(j=0;j<4;j=j+1) packet[52+256*j+:256]=image[4*b+j];
            send(packet);idle(2);
        end
        idle(100);phase=2;
        // The fixture's actual SW quantizing command, so u/um and XQ must toggle.
        send(ctl(5'b00100,swcmd[0]));idle(1000);
        phase=3;cmd(1,3,0,0,0);idle(80);cmd(1,2,0,32,0);idle(140);
        phase=4;cmd(1,4,900,0,0);idle(80);cmd(1,6,900,0,16);idle(200);
        $display("CSP COUNTS MUT=%0d public_bad=%0d post_transport_bad=%0d ubeats=%0d postbeats=%0d xbeats=%0d fault=%0d",MUT,public_bad,post_bad,ubeats,postbeats,xbeats,f_a);
        if(ubeats==0 || postbeats==0 || xbeats==0 || f_a) $display("CSP INVALID inactive_or_faulted_reference");
        else if(bad==0) $display("CSP PASS MUT=%0d",MUT);
        else $display("CSP FAIL MUT=%0d mismatches=%0d",MUT,bad);
        $finish;
    end
endmodule
