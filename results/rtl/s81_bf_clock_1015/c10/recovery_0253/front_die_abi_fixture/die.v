// tools/dsrom_s81_fulldie.py: die-level nets only (k = 1)
module bf_root_abi_fixture (n_clock, x2, xa, xb, qy0, qy1, x0, x1, go, cfg, rs, f_prog, c0, c1, st);
  input [535:0] x2;
  input [282:0] xa;
  input [265:0] xb;
  input qy0;
  input qy1;
  input [282:0] x0;
  input [265:0] x1;
  input go;
  input [53:0] cfg;
  input rs;
  input [37:0] f_prog;
  output [775:0] c0;
  output [775:0] c1;
  output [1:0] st;
  input [0:0] n_clock;
  dsfd_bf_front_roots e0 (.ck(n_clock), .io_n(n_clock), .io_w(n_clock), .io_e(n_clock), .io_clk(n_clock), .c0(c0), .c1(c1), .qy0(qy0), .qy1(qy1), .x0(x0), .x1(x1), .go(go), .cfg(cfg), .st(st), .rs(rs), .f_prog(f_prog), .xb_meta({x2[43:0]}), .xb_data({xb[265:0], xa[265:0], x2[535:44]}));
endmodule
