#!/usr/bin/env python3
"""sys-takeover 2026-10-09: the committed plain pc-mux bench (tb_s81_native_pc_mux_plain) on the registered-input
wrapper ot_s81_native_pc_mux_plain_rb.sv.  Every input crosses one pin flop, so the response / completion checks compare
against the previous cycle's driven rv / wd / data / tag / beat (+1 cycle, the priced boundary cost); every value,
order, credit and drain check is unchanged.
    python3 physical/sys_takeover/pcmux_rb_bench.py pos|neg WORKDIR      (neg: Codex's wrong-source mutant in the core)"""
import os, pathlib, subprocess, sys
mode, w = sys.argv[1], pathlib.Path(sys.argv[2]); w.mkdir(parents=True, exist_ok=True)
t = pathlib.Path("rtl/test/s81_native_ingest/tb_s81_native_pc_mux_plain.sv").read_text()
R = [("if(i!=active_tag[16:15]||!(wd||(rv&&beat==0)))", "if(i!=active_tag[16:15]||!(p_wd||(p_rv&&p_beat==0)))"),
     ("if(sw[i])begin if(!wd||", "if(sw[i])begin if(!p_wd||"),
     ("if(!rv||i!=active_tag[16:15]||st[i*17+:17]!=tag||sb[i*4+:4]!=beat||sd[i*256+:256]!=data)",
      "if(!p_rv||i!=active_tag[16:15]||st[i*17+:17]!=p_tag||sb[i*4+:4]!=p_beat||sd[i*256+:256]!=p_data)"),
     ("returns=returns+1;if(beat==0)", "returns=returns+1;if(p_beat==0)"),
     ("   @(negedge ck);\n  end\n  for(i=0;i<4;i=i+1)if(sent[i]",
      "   p_rv=rv;p_wd=wd;p_data=data;p_tag=tag;p_beat=beat;\n   @(negedge ck);\n  end\n  repeat(4)@(posedge ck);\n  for(i=0;i<4;i=i+1)if(sent[i]"),
     (" reg active_we;", " reg p_rv=0,p_wd=0;reg[255:0] p_data=0;reg[16:0] p_tag=0;reg[3:0] p_beat=0;\n reg active_we;")]
for a, b in R:
    assert t.count(a) == 1, a
    t = t.replace(a, b)
(w / "tb.sv").write_text(t)
rb = pathlib.Path("physical/sys_takeover/ot_s81_native_pc_mux_plain_rb.sv").read_text()
PICK = os.environ.get("PCMUX_PICK") == "1"     # sys-takeover: the PICK=1 pipelined arbitration
PRE = os.environ.get("PCMUX_PRE") == "1"       # sys-takeover: PRE=1 head pre-read (with PICK)
if mode == "negpre":                          # PRE mutant: the head register misses the pop's advance (stale head)
    pass
elif mode == "neg":
    a = "if(PICK)next_owner=sel;" if PICK else "next_owner=chosen[1:0]"
    assert rb.count(a) == 1, a
    rb = rb.replace(a, "if(PICK)next_owner=0;" if PICK else "next_owner=0")
(w / "dut.sv").write_text(rb)
b = subprocess.run(["iverilog", "-g2012", *(["-DPCMUX_PICK"] if PICK else []), *(["-DPCMUX_PRE"] if PRE else []),
                    *(["-DPCMUX_MUT_STALEHEAD"] if mode == "negpre" else []), "-s", "tb_s81_native_pc_mux", "-o", str(w / "sim"), str(w / "dut.sv"), str(w / "tb.sv")],
                   capture_output=True, text=True)
if b.returncode: print(b.stdout + b.stderr); print("PCMUX_RB_BENCH_ERROR build"); sys.exit(2)
r = subprocess.run(["vvp", "-n", str(w / "sim")], capture_output=True, text=True)
out = r.stdout + r.stderr; (w / "run.log").write_text(out); print(out[-600:])
if mode == "pos":
    ok = "S81_NATIVE_PC PASS" in out and "FATAL" not in out
    print("PCMUX_RB_PASS" if ok else "PCMUX_RB_FAIL"); sys.exit(0 if ok else 1)
caught = "wrong or premature source retirement" in out or "wrongread" in out or "issue reordered" in out
print("PCMUX_RB_NEG_DETECTED" if caught else "PCMUX_RB_NEG_MISSED"); sys.exit(1 if caught else 0)
