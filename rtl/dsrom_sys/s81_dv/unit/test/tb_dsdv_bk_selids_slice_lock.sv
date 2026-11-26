// S81-BKSEL-RTL lockstep: dsdv_bk_selids_old (portfix178 as on main) vs dsdv_bk_selids (per-slice copies), random + directed jobs.
module tb_ids_lock;
  parameter integer MUT = 0;
  localparam V = 276;
  reg ck = 0, rst = 0;
  reg [V-1:0] vo = '0;
  wire [V-1:0] oa, ob; wire fa, fb;
  dsdv_bk_selids_old #(.V(V), .MUT(MUT)) a (.ck(ck), .rst(rst), .vo(vo), .o(oa), .fault(fa));
  dsdv_bk_selids     #(.V(V), .MUT(MUT)) b (.ck(ck), .rst(rst), .vo(vo), .o(ob), .fault(fb));
  integer cyc = 0, bad = 0, nbeat = 0, njob = 0, seed;
  reg [31:0] r;
  reg [3:0] tg;
  reg [7:0] cur_ot = 8'd7;
  reg [V-1:0] x;
  integer k;
  always #5 ck = ~ck;
  always @(negedge ck) begin
    cyc <= cyc + 1;
    if (oa !== ob || fa !== fb) begin bad = bad + 1; if (bad < 5) $display("MISMATCH cyc %0d oa^ob=%h fa=%b fb=%b", cyc, oa ^ ob, fa, fb); end
    if (oa[0]) nbeat = nbeat + 1;
  end
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    r = $urandom(seed);
    #23 rst = 1;
    repeat (200000) begin
      @(posedge ck); #1;
      x = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
      tg = $urandom % 12;
      if (tg == 0) vo = '0;
      else if (tg == 1 || tg == 2) begin         // JOB ctl: kind 0, UID 5C, p[10:8]==3, K, OT, mask
        vo = x; vo[0] = 1; vo[3:1] = 0; vo[28:21] = 8'h5C; vo[31:29] = 3'd3;
        vo[61:52] = ($urandom % 8 == 0) ? 10'd0 : 10'($urandom % 40 + 1);
        cur_ot = ($urandom % 4 == 0) ? 8'($urandom) : cur_ot; vo[89:82] = cur_ot;
        njob = njob + 1;
      end else if (tg >= 3 && tg <= 8) begin      // egress part 0 / part 1 pair-ish, kind 5
        vo = x; vo[0] = 1; vo[3:1] = 3'd5; vo[6] = ($urandom % 2);
        vo[275:272] = ($urandom % 8 == 0) ? 4'($urandom) : 4'd3;
        vo[271:264] = ($urandom % 8 == 0) ? 8'($urandom) : cur_ot;
        case ($urandom % 4)                        // lv: prefix, empty, full, or arbitrary
          0: vo[99:84] = 16'((16'd1 << ($urandom % 17)) - 1);
          1: vo[99:84] = 16'h0000;
          2: vo[99:84] = 16'hFFFF;
          default: ;
        endcase
      end else vo = x;
    end
    $display("LOCKSTEP MUT=%0d seed=%0d cycles=%0d beats=%0d jobs=%0d mismatches=%0d %s", MUT, seed, cyc, nbeat, njob, bad, bad == 0 ? "PASS" : "FAIL");
    $finish;
  end
endmodule
