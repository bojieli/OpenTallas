"""DIE-HBM-97/KSHARE-PC lockstep bench generator (cycle-shifted equivalence of the pin-cycle form).
   mk_bench.py OLD_RTL NEW_RTL VIEW OUTDIR
OLD = the vR kit RTL (face shell + wrapper + core, PCF absent), NEW = the PC form RTL.  Old modules are renamed *_O.
Both tops get the SAME pin stimulus; the old top's IN_STAGE buses are fed one hbm edge late (the new shell's
u_bimid0 relays).  hbm_clk and stream_clk carry ONE SDC clock on the die, so the bench runs them at the same period
(stream 1.7 ns phase offset); the fill_* face registers of the shell are hbm_clk flops, so every non-fill output must
match on every hbm edge, every fill_* output of the new top must equal the old top's one hbm edge earlier (the fill
stage is +1 stream edge = +1 hbm edge), fault on the same edge.  Stimulus: resets held 80 hbm edges, all pins 0 for
24 edges (the reset-held producer contract), then random group traffic in bursts, random WB requests and window
commands, and a controller model per lane (c_k_rdy 1, every read returns its len beats echoing the tag, offered only
while c_kr_rdy has been high 5 edges, one beat per 3 edges; one c_k_wr_done per write), driven from the new top's
c_k_* outputs (which must equal the old top's).  MODE 0 = the claimed mapping (must PASS), MODE 1 = fill
compared unshifted (must FAIL), MODE 2 = old top fed undelayed IN_STAGE buses (must FAIL), MODE 3 = no
delay, no shift (identity: run it with NEW = the vR RTL with only the core replaced, PCF default 0; must PASS)."""
import re, sys
from pathlib import Path
IN_STAGES = ["w_k_v", "w_k_addr", "w_k_wdata", "c_kr_v", "c_kr_tag", "c_kr_beat", "c_kr_data"]
MODEL = {"c_k_rdy", "c_kr_v", "c_kr_tag", "c_kr_beat", "c_kr_data", "c_k_wr_done"}
STREAM_IN = {"vm_v", "vm_bank", "vm_col", "vm_epoch", "vm_row", "wbw_v", "wbw_base", "wbw_total"}
FILL = {"fill_v", "fill_bank", "fill_slot", "fill_epoch", "fill_data"}
old, new, view, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
top = f"ot_hbm_svc_vm_kshare_splitstrap__{view}"
files = ["ot_hbm_face_reg.sv", "ot_hbm_svc_async_fifo.sv", "ot_hbm_svc_pc_ctrl_leaf.sv", "ot_hbm_svc_ring_h9b_ff.sv",
         "ot_reset_sync.sv", "ot_hbm_svc_vm_kshare_splitstrap.sv", f"{top}__wrap.sv", f"{top}__fshell.sv"]
txt = "\n".join((old / f).read_text() for f in files)
mods = sorted(set(re.findall(r"^\s*module\s+(\w+)", txt, re.M)), key=len, reverse=True)
for m in mods:
    txt = re.sub(r"\b%s\b" % m, m + "_O", txt)
(out / "old_all.sv").write_text(txt)
fs = (new / f"{top}__fshell.sv").read_text()
i0 = fs.index(f"module {top} ("); hdr = fs[i0:fs.index(");", i0)]
ports = re.findall(r"(input|output) wire (?:\[(\d+):0\] )?(\w+)", hdr)
P = [(d, int(h) + 1 if h else 1, n) for d, h, n in ports]
L = ["`timescale 1ns/1ps", "module tb;", " integer MODE, NCYC, seed, errs, cyc, scyc;",
     " reg hbm_clk=0, stream_clk=0, hbm_rst_n=0, stream_rst_n=0, go=0;",
     " always #5 hbm_clk=~hbm_clk;", " initial begin #1.7; forever #5 stream_clk = ~stream_clk; end   // one SDC clock on both ports: same period, 1.7 ns phase offset"]
for d, w, n in P:
    if n in ("hbm_clk", "stream_clk", "hbm_rst_n", "stream_rst_n"): continue
    if d == "input":
        L.append(f" reg [{w-1}:0] {n}=0;")
        if n in IN_STAGES: L.append(f" reg [{w-1}:0] {n}_d=0; always @(posedge hbm_clk) {n}_d <= {n};")
    else:
        L.append(f" wire [{w-1}:0] {n}_n, {n}_o;")
        if n in FILL: L.append(f" reg [{w-1}:0] {n}_op; always @(posedge hbm_clk) {n}_op <= {n}_o;   // fill face regs are hbm_clk (fshell u_bout_fill_*)")
def conn(sfx):
    c = []
    for d, w, n in P:
        if d == "input":
            src = n
            if sfx == "o" and n in IN_STAGES: src = f"(MODE>=2 ? {n} : {n}_d)"
            c.append(f".{n}({src})")
        else:
            c.append(f".{n}({n}_{sfx})")
    return ", ".join(c)
L.append(f" {top} u_new({conn('n')});")
L.append(f" {top}_O u_old({conn('o')});")
def rnd(w):
    return "{" + ",".join(["$random(seed)"] * ((w + 31) // 32)) + "}"
L.append(" always @(negedge hbm_clk) if (go) begin")
for d, w, n in P:
    if d != "input" or n in STREAM_IN or n in ("hbm_clk", "stream_clk", "hbm_rst_n", "stream_rst_n", "sm_hbm", "sm_stream"): continue
    if n in MODEL: continue
    if n == "g_kr_rdy":
        L.append(f"  {n} <= ~({rnd(w)} & {rnd(w)} & {rnd(w)});")   # group response ready p=7/8
        continue
    if n == "g_k_v":
        L.append(f"  {n} <= ((cyc % 2048) < 400) ? ({rnd(w)} & {rnd(w)}) : 0;")   # group traffic in bursts (lets windows drain)
    elif re.search(r"_v$|_rdy$|_wr_done$|_we$", n):
        L.append(f"  {n} <= {rnd(w)} & {rnd(w)};")   # control bits: 1 with p=1/4
    else:
        L.append(f"  {n} <= {rnd(w)};")
L.append(" end")
# controller model (one per lane, driven from the NEW design's c_k_* outputs; the old design sees the same inputs,
# delayed on the IN_STAGE faces): c_k_rdy = 1, every read request returns len beats echoing its tag (KRL1: a beat is
# offered only while c_kr_rdy was high the last 5 hbm edges, at most one per 3 edges), every write gets one c_k_wr_done.
L.append(" reg [16:0] rq_tag [0:1023]; reg [3:0] rq_len [0:1023]; reg [7:0] rq_wp [0:3]; reg [7:0] rq_rp [0:3]; reg [4:0] bcur [0:3]; reg [9:0] wpend [0:3]; reg [3:0] rh0 = 0, rh1 = 0, rh2 = 0, rh3 = 0, rh4 = 0; reg [1:0] gap [0:3]; integer ml;")
L.append(" initial for (ml = 0; ml < 4; ml = ml + 1) begin rq_wp[ml] = 0; rq_rp[ml] = 0; bcur[ml] = 0; wpend[ml] = 0; gap[ml] = 0; end")
L.append(" always @(posedge hbm_clk) if (go) for (ml = 0; ml < 4; ml = ml + 1) if (c_k_v_n[ml] && c_k_rdy[ml]) begin")
L.append("  if (c_k_we_n[ml]) wpend[ml] = wpend[ml] + 1;")
L.append("  else if (c_k_len_n[4*ml+:4] != 0) begin rq_tag[ml*256+rq_wp[ml]] = c_k_tag_n[17*ml+:17]; rq_len[ml*256+rq_wp[ml]] = c_k_len_n[4*ml+:4]; rq_wp[ml] = rq_wp[ml] + 1; end")
L.append(" end")
L.append(" always @(negedge hbm_clk) if (go) begin rh4 = rh3; rh3 = rh2; rh2 = rh1; rh1 = rh0; rh0 = c_kr_rdy_n;")
L.append("  for (ml = 0; ml < 4; ml = ml + 1) begin")
L.append("   c_k_rdy[ml] = 1'b1; c_k_wr_done[ml] = 1'b0; if (gap[ml] != 0) gap[ml] = gap[ml] - 1;")
L.append("   if (wpend[ml] != 0 && ($random(seed) & 1)) begin c_k_wr_done[ml] = 1'b1; wpend[ml] = wpend[ml] - 1; end")
L.append("   c_kr_v[ml] = 1'b0; c_kr_data[256*ml+:256] = {8{$random(seed)}}; c_kr_tag[17*ml+:17] = $random(seed); c_kr_beat[4*ml+:4] = $random(seed);")
L.append("   if (rq_wp[ml] != rq_rp[ml] && rh0[ml] && rh1[ml] && rh2[ml] && rh3[ml] && rh4[ml] && gap[ml] == 0) begin gap[ml] = 2;")
L.append("    c_kr_v[ml] = 1'b1; c_kr_tag[17*ml+:17] = rq_tag[ml*256+rq_rp[ml]]; c_kr_beat[4*ml+:4] = bcur[ml][3:0];")
L.append("    if (bcur[ml] + 5'd1 == {1'b0, rq_len[ml*256+rq_rp[ml]]}) begin bcur[ml] = 0; rq_rp[ml] = rq_rp[ml] + 1; end else bcur[ml] = bcur[ml] + 1;")
L.append("   end")
L.append("  end")
L.append(" end")
L.append(" always @(negedge stream_clk) if (go) begin")
for d, w, n in P:
    if d == "input" and n in STREAM_IN:
        if n == "vm_v": L.append(f"  {n} <= ($random(seed) & 511) == 0;")
        elif n.endswith("_v"): L.append(f"  {n} <= ($random(seed) & 1023) == 0;")
        elif n == "wbw_total": L.append(f"  {n} <= $random(seed) % 300;")
        else: L.append(f"  {n} <= {rnd(w)};")
L.append(" end")
L.append(" always @(negedge hbm_clk) if (cyc > 140) begin")
for d, w, n in P:
    if d == "output" and n not in FILL and n != "fault":
        L.append(f"  if ({n}_n !== {n}_o) begin errs = errs + 1; if (errs < 20) $display(\"MISMATCH hbm cyc %0d {n}\", cyc); end")
L.append(" end")
L.append(" always @(negedge hbm_clk) if (scyc > 110) begin")
for d, w, n in P:
    if d == "output" and n in FILL:
        L.append(f"  if ({n}_n !== ((MODE==1 || MODE==3) ? {n}_o : {n}_op)) begin errs = errs + 1; if (errs < 20) $display(\"MISMATCH stream cyc %0d {n}\", scyc); end")
L.append(f"  if (fault_n !== fault_o) begin errs = errs + 1; if (errs < 20) $display(\"MISMATCH stream cyc %0d fault\", scyc); end")
L.append(" end")
L.append(" reg [31:0] nfill_n=0, nfill_o=0, nck=0, ngkr=0, nwd=0, nwin=0;")
L.append(" always @(posedge stream_clk) if (go) begin nfill_n <= nfill_n + (fill_v_n != 0); nfill_o <= nfill_o + (fill_v_o != 0); end")
L.append(" always @(posedge hbm_clk) if (go) begin nck <= nck + (c_k_v_n != 0); ngkr <= ngkr + (g_kr_v_n != 0); nwd <= nwd + (w_k_wr_done_n != 0); nwin <= nwin + (u_new.u_fcore.u_core.lane[0].st != 0); end")
L.append(" always @(posedge hbm_clk) cyc = cyc + 1;  always @(posedge stream_clk) scyc = scyc + 1;")
L.append(" initial begin")
L.append("  if (!$value$plusargs(\"MODE=%d\", MODE)) MODE = 0; if (!$value$plusargs(\"N=%d\", NCYC)) NCYC = 20000;")
L.append("  if (!$value$plusargs(\"SEED=%d\", seed)) seed = 1; errs = 0; cyc = 0; scyc = 0; sm_hbm = 3'd5; sm_stream = 3'd5;")
L.append("  repeat (80) @(posedge hbm_clk); hbm_rst_n = 1; stream_rst_n = 1;")
L.append("  repeat (24) @(posedge hbm_clk); go = 1;")
L.append("  repeat (NCYC) @(posedge hbm_clk);")
L.append(f"  $display(\"BENCH {view} MODE %0d seed %0d cycles %0d errs %0d fill_v_new %0d fill_v_old %0d c_k_v %0d g_kr_v %0d w_k_wr_done %0d lane0_notNORM %0d g_k_rdy %b fault %b %s\", MODE, seed, NCYC, errs, nfill_n, nfill_o, nck, ngkr, nwd, nwin, g_k_rdy_n, fault_n, errs ? \"FAIL\" : \"PASS\");")
L.append("  $finish; end")
L.append("endmodule")
(out / f"tb_{view}.sv").write_text("\n".join(L) + "\n")
(out / "files_new.f").write_text("\n".join(str(new / f) for f in files) + "\n")
print("bench", out)
