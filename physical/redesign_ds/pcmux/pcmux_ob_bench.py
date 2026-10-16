#!/usr/bin/env python3
"""redesign-ds 2026-10-09: exactness gate of the OREG pc mux (physical/redesign_ds/pcmux/ot_s81_native_pc_mux_plain_ob.sv).
The committed closed-loop bench (tb_s81_native_pc_mux_plain at sys-takeover 0eb22908a, copied here, with the +1-input
patches of physical/sys_takeover/pcmux_rb_bench.py) drives the REFERENCE (sys-takeover's input-registered mux, here
ot_s81_native_pc_mux_plain_ib) and must PASS; a second instance, the OREG mux, sees the same inputs every cycle and
every one of its outputs must equal the reference's outputs one edge earlier (lockstep, all 1,483 output bits, every
cycle after reset).  Negative: PCMUX_OB_MUT (one rq bit bypasses its pin register) must be caught.
    pcmux_ob_bench.py pos|neg WORKDIR [PICK PRE]   (default PICK=1 PRE=1, the pcmux_pre_* configuration)"""
import pathlib, subprocess, sys
mode, w = sys.argv[1], pathlib.Path(sys.argv[2]); w.mkdir(parents=True, exist_ok=True)
pick = sys.argv[3] if len(sys.argv) > 3 else "1"; pre = sys.argv[4] if len(sys.argv) > 4 else "1"
t = pathlib.Path("physical/redesign_ds/pcmux/tb_s81_native_pc_mux_plain_0eb22908a.sv").read_text()
R = [("if(i!=active_tag[16:15]||!(wd||(rv&&beat==0)))", "if(i!=active_tag[16:15]||!(p_wd||(p_rv&&p_beat==0)))"),
     ("if(sw[i])begin if(!wd||", "if(sw[i])begin if(!p_wd||"),
     ("if(!rv||i!=active_tag[16:15]||st[i*17+:17]!=tag||sb[i*4+:4]!=beat||sd[i*256+:256]!=data)",
      "if(!p_rv||i!=active_tag[16:15]||st[i*17+:17]!=p_tag||sb[i*4+:4]!=p_beat||sd[i*256+:256]!=p_data)"),
     ("returns=returns+1;if(beat==0)", "returns=returns+1;if(p_beat==0)"),
     ("   @(negedge ck);\n  end\n  for(i=0;i<4;i=i+1)if(sent[i]",
      "   p_rv=rv;p_wd=wd;p_data=data;p_tag=tag;p_beat=beat;\n   @(negedge ck);\n  end\n  repeat(4)@(posedge ck);\n  for(i=0;i<4;i=i+1)if(sent[i]"),
     (" reg active_we;", " reg p_rv=0,p_wd=0;reg[255:0] p_data=0;reg[16:0] p_tag=0;reg[3:0] p_beat=0;\n reg active_we;"),
     # the reference is the input-registered mux; the OREG mux is a second instance
     (" ot_s81_native_pc_mux_plain #(", " ot_s81_native_pc_mux_plain_ib #(")]
for a, b in R:
    assert t.count(a) == 1, a
    t = t.replace(a, b)
EQ = """
 // ---- redesign-ds: lockstep equivalence of the OREG mux = reference outputs delayed one edge
 wire[3:0] cr2,sw2,srv2,sdone2;wire[340:0] rq2;wire[1023:0] sd2;wire[67:0] st2;wire[15:0] sb2;wire pending2,ce2,fault2;
 ot_s81_native_pc_mux_plain #(.ENABLE(1),.PICK(`ifdef PCMUX_PICK 1 `else 0 `endif),.PRE(`ifdef PCMUX_PRE 1 `else 0 `endif),.OREG(1)) dut2(ck,rst_n,live,inq,cr2,rq2,rk,wd,rv,data,tag,beat,sw2,srv2,sdone2,sd2,st2,sb2,pending2,ce2,fault2);
 wire[1482:0] ref_now={cr,rq,sw,srv,sdone,sd,st,sb,pending,ce,fault};
 wire[1482:0] new_now={cr2,rq2,sw2,srv2,sdone2,sd2,st2,sb2,pending2,ce2,fault2};
 reg[1482:0] ref_d;integer eq_n=0,eq_bad=0,eq_live=0;
 always @(posedge ck)begin
  #0.05;
  if(rst_n)begin
   eq_live=eq_live+1;
   if(eq_live>2)begin eq_n=eq_n+1;if(new_now!==ref_d)begin eq_bad=eq_bad+1;if(eq_bad<5)$display("PCMUX_OB_MISMATCH cycle %0d",eq_n);end end
  end
  ref_d=ref_now;
 end
 final $display("PCMUX_OB_EQUIV cycles=%0d mismatches=%0d",eq_n,eq_bad);
endmodule"""
i = t.rindex("endmodule")
t = t[:i] + EQ.lstrip("\n") + t[i + len("endmodule"):]
(w / "tb.sv").write_text(t)
d = ["-DPCMUX_PICK"] if pick == "1" else []
d += ["-DPCMUX_PRE"] if pre == "1" else []
d += ["-DPCMUX_OB_MUT"] if mode == "neg" else []
b = subprocess.run(["iverilog", "-g2012", *d, "-s", "tb_s81_native_pc_mux", "-o", str(w / "sim"),
                    "physical/redesign_ds/pcmux/ot_s81_native_pc_mux_plain_ob.sv", str(w / "tb.sv")], capture_output=True, text=True)
if b.returncode:
    print(b.stdout + b.stderr); print("PCMUX_OB_BENCH_ERROR build"); sys.exit(2)
r = subprocess.run(["vvp", "-n", str(w / "sim")], capture_output=True, text=True)
out = r.stdout + r.stderr; (w / f"run_{mode}.log").write_text(out); print(out[-700:])
import re
m = re.search(r"PCMUX_OB_EQUIV cycles=(\d+) mismatches=(\d+)", out)
n, bad = (int(m[1]), int(m[2])) if m else (0, -1)
tb_ok = "S81_NATIVE_PC PASS" in out and "FATAL" not in out
if mode == "pos":
    ok = tb_ok and bad == 0 and n > 3000
    print("PCMUX_OB_PASS" if ok else "PCMUX_OB_FAIL"); sys.exit(0 if ok else 1)
caught = bad > 0
print("PCMUX_OB_NEG_DETECTED" if caught else "PCMUX_OB_NEG_MISSED"); sys.exit(1 if caught else 0)
