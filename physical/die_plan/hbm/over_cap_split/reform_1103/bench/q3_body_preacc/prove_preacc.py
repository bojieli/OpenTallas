#!/usr/bin/env python3
"""DIE-HBM-88-Q3C proof of OT_Q3CTL_PREACC.  Usage: prove_preacc.py <patched.sv> <old.sv> <workdir> <yosys>
 1. text: the patched file without its `ifdef OT_Q3CTL_PREACC ... (`else) / `endif lines is byte-identical to the old file.
 2. formal (yosys sat, -set-init-undef, -prove-skip 1, seq 8): gold = 256-bit no-reset copy register of u.data_q and the two
    reductions of the copy (old assigns); gate = the same copy register + the two pre-registered reductions (new block and
    new assigns, taken verbatim from the patched file).  Outputs hz/ms equal on every cycle after the first edge for any
    input sequence; both are 1-deep feed-forward registers of the input, so depth 8 is complete.
 3. mutants of the new block must FAIL the same proof."""
import hashlib, os, re, subprocess, sys
pat, old, wd, ys = sys.argv[1:5]
os.makedirs(wd, exist_ok=True)
S = open(pat).read().split("\n")
out, i, blocks = [], 0, []
while i < len(S):
    if S[i] == "`ifdef OT_Q3CTL_PREACC":
        a = i; e = None; z = a + 1
        while S[z] != "`endif":
            if S[z] == "`else": e = z
            z += 1
        blocks.append((a, e, z))
        if e is not None: out += S[e + 1:z]
        i = z + 1; continue
    out.append(S[i]); i += 1
recon = "\n".join(out)
ho, hr = hashlib.sha256(open(old, "rb").read()).hexdigest(), hashlib.sha256(recon.encode()).hexdigest()
print("TEXT blocks", len(blocks), "old sha256", ho, "patched-minus-ifdef sha256", hr, "IDENTICAL" if ho == hr else "DIFFERENT")
ok = ho == hr and len(blocks) == 5
newlines, oldlines = [], []
for a, e, z in blocks:
    if e is None: newlines += S[a + 1:z]
    else: newlines += S[a + 1:e]; oldlines += S[e + 1:z]
def clean(t):
    t = re.sub(r"\\u_body\.g_q3\.n_u_fj\.u_fj\.u\.u_program\.data_q\[(\d+)\] ", r"dq[\1]", t)
    t = re.sub(r"\\u_body\.g_q3\.n_u_fj\.u_fj\.u\.data_q\[(\d+)\] ", r"ud[\1]", t)
    return t
COPY = "  reg [255:0] dq;\n  always @(posedge clk_program) dq <= ud;\n"
HDR = "(input clk_program, input [255:0] ud, output hz1, output hz2, output ms1, output ms2);\n  wire _027460_, _027468_, _027461_, _027469_;\n"
TAIL = "  assign hz1 = _027460_; assign hz2 = _027468_; assign ms1 = _027461_; assign ms2 = _027469_;\nendmodule\n"
OLD = "module blk_gold" + HDR + COPY + clean("\n".join(oldlines)) + "\n" + TAIL
NEWT = "module blk_gate" + HDR + COPY + clean("\n".join(newlines)) + "\n" + TAIL
MUT = {
 "M1_no_register": ("ot_q3_pre_hz <= | {", "ot_q3_pre_hz <= ot_q3_pre_hz | 1'b0 & | {"),
 "M2_range_drops_bit64": (", ud[64] };", " };"),
 "M3_ms_bit56": ("ud[57] };", "ud[57] , ud[56] };"),
 "M4_swap_hz_ms": ("assign _027460_ = ot_q3_pre_hz;", "assign _027460_ = ot_q3_pre_ms;"),
 "M5_reads_copy_not_source": ("ot_q3_pre_ms <= | { ud[63]", "ot_q3_pre_ms <= | { dq[63]"),
}
def run(name, gate):
    open(f"{wd}/{name}.v", "w").write(OLD + gate)
    scr = (f"read_verilog {wd}/{name}.v; proc; opt_clean; miter -equiv -flatten -make_outputs blk_gold blk_gate miter; "
           f"hierarchy -top miter; flatten; opt; sat -verify -seq 8 -prove-skip 1 -set-init-undef -prove trigger 0 miter")
    r = subprocess.run([ys, "-q", "-p", scr], capture_output=True, text=True)
    open(f"{wd}/{name}.log", "w").write(r.stdout + r.stderr)
    return r.returncode == 0
p = run("M0_new_form", NEWT)
print("FORMAL M0 new form vs old:", "PASS" if p else "FAIL"); ok &= p
for k, (x, y) in MUT.items():
    assert x in NEWT, k
    q = run(k, NEWT.replace(x, y, 1))
    print(f"MUTANT {k}:", "caught (proof FAILS)" if not q else "NOT CAUGHT"); ok &= not q
print("RESULT", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
