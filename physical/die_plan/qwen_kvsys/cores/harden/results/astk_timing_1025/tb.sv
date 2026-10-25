module tb;
reg ck=0; always #5 ck=~ck;
reg rst_n=0; reg [31:0] cal=0; reg [1:0] st=0; reg [539:0] aq=0; reg [35:0] am=0; reg [266:0] xi=0; reg [137:0] zi=0; reg fz=0;
reg [14:0] tc=0; reg [137:0] zzi=0;
wire [20:0] lt0,lt1; wire [42:0] ap0,ap1; wire af0,af1; wire [571:0] qo0,qo1,qf0,qf1; wire [59:0] tf0,tf1;
qkd_astk_ctl_s_o #(.Z_STRIDE(4),.PORT_REGS(1)) c0(.cal(cal),.ck(ck),.rst_n(rst_n),.st(st),.aq(aq),.lt(lt0),.am(am),.ap(ap0),.af(af0),.qo(qo0),.tc_faces(tf0),.qo_face(qf0),.xi(xi),.zi(zi),.fz(fz));
qkd_astk_ctl_s   #(.Z_STRIDE(4),.PORT_REGS(1)) c1(.cal(cal),.ck(ck),.rst_n(rst_n),.st(st),.aq(aq),.lt(lt1),.am(am),.ap(ap1),.af(af1),.qo(qo1),.tc_faces(tf1),.qo_face(qf1),.xi(xi),.zi(zi),.fz(fz));
wire [137:0] za,zb,ha,hb; wire fa,fb,hfa,hfb;
qkd_astk_zn_o z0(.ck(ck),.rst_n(rst_n),.zc(4'd5),.tc(tc),.zi(zzi),.zo(za),.fi(1'b0),.fo(fa));
qkd_astk_zn   z1(.ck(ck),.rst_n(rst_n),.zc(4'd5),.tc(tc),.zi(zzi),.zo(zb),.fi(1'b0),.fo(fb));
qkd_astk_zn_head_p_o #(.ZC(4'd0)) h0(.ck(ck),.rst_n(rst_n),.tc(tc),.zi(zzi),.zo(ha),.fo(hfa));
qkd_astk_zn_head_p   #(.ZC(4'd0)) h1(.ck(ck),.rst_n(rst_n),.tc(tc),.zi(zzi),.zo(hb),.fo(hfb));
integer n, mis=0, apv=0, zv=0, lsl=0, zsl=0; reg [15:0] lm, zs;
initial begin
  for (n=0; n<60000; n=n+1) begin
    @(negedge ck);
    rst_n = !(n<4 || (n>30000 && n<30003));
    if (n%600==10) begin lm = 1 + $urandom%24; zs = lm + 4 + $urandom%40; cal = {zs, lm}; end
    aq = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
    aq[0] = (n%600==12); aq[14:1] = $urandom%4096; st = $urandom; am = {$urandom,$urandom}; am[0] = ($urandom%8==0);
    xi = {$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}; xi[0] = 0;
    zi = {$urandom,$urandom,$urandom,$urandom,$urandom}; zi[0] = ($urandom%3==0); fz = 0;
    tc = {$urandom%16384, (n%600==12)};
    zzi = {$urandom,$urandom,$urandom,$urandom,$urandom}; zzi[0] = ($urandom%2==0);
    @(posedge ck); #1;
    if (n>=6) begin
      if (lt0!==lt1 || ap0!==ap1 || af0!==af1 || qo0!==qo1 || tf0!==tf1 || qf0!==qf1) begin mis=mis+1; if (mis<4) $display("CTL MISMATCH n=%0d ap %h %h", n, ap0, ap1); end
      if (za!==zb || fa!==fb || ha!==hb || hfa!==hfb) begin mis=mis+1; if (mis<8) $display("ZN MISMATCH n=%0d", n); end
      if (ap0[0]) apv=apv+1; if (ap0[0] && ap0[2:1]==0) lsl=lsl+1; if (ap0[0] && ap0[2:1]==1) zsl=zsl+1; if (za[0]) zv=zv+1;
    end
  end
  $display("MITER %s mismatches=%0d ap_valid=%0d lmax_msgs=%0d z_msgs=%0d zn_valid=%0d", mis==0?"PASS":"FAIL", mis, apv, lsl, zsl, zv);
  $finish;
end
endmodule
