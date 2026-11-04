#!/usr/bin/env python3
"""DIE-HBM-63/REFORM 11-04: lock-step of a one-clock wrapper against its multi-clock reference (all clocks in phase).

    bench_oneclk.py KITRTL REFTOP [--ref-file OLD_WRAP --ref-from OLD_MODULE] NEWTOP OUT [--cycles N] [--sram MODEL] [--muts 0,1,2,3]

REF = multi-port module (kit RTL or the old kit wrapper renamed to REFTOP).  DUT = an adapter with REF's ports around the
kit's one-clock NEWTOP (`__fcore`), clock = the bench clock.  Compared on every output every edge after warmup.
MUT 0 must PASS.  MUT 1 inverts one bit of the last clock connection, 1:k of the k-th (--muts 1:0,1:1), MUT 2 inverts one
output bit, MUT 3 ties one input bit: must FAIL."""
import argparse, glob, json, os, re, subprocess, sys
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("kitrtl"); ap.add_argument("reftop"); ap.add_argument("newtop"); ap.add_argument("out")
ap.add_argument("--ref-file"); ap.add_argument("--ref-from"); ap.add_argument("--cycles", type=int, default=2000)
ap.add_argument("--sram", default=""); ap.add_argument("--muts", default="0,1,2,3"); a = ap.parse_args()
H = Path(__file__).resolve().parents[3] / "physical/die_plan/hbm/over_cap_split/reform_1103"
O = Path(a.out); O.mkdir(parents=True, exist_ok=True)
V = os.path.expanduser("~/.local/opentallas-tools/bin/verilator")
SKIP = ("__fshell.sv",)
kit = [f for f in sorted(glob.glob(a.kitrtl + "/*.sv")) if not f.endswith(SKIP)]
wrapf = [f for f in kit if f.endswith("__wrap.sv")][0]
base = [f for f in kit if f != wrapf] + ([a.sram] if a.sram else [])
ref_files = []
if a.ref_file:
    s = Path(a.ref_file).read_text(); s = re.sub(r"\bmodule\s+" + re.escape(a.ref_from) + r"\b", "module " + a.reftop, s)
    (O / "ref.sv").write_text(s); ref_files = [str(O / "ref.sv")]
CLK = r"(^|_)clk(_|$)"
out = subprocess.run([sys.executable, str(H / "facewrap.py"), "--top", a.reftop, "--clk-re", CLK, "--rst-re", r"(^|_)rst(_[a-z]+)?_n$",
                      "--out", str(O / "unused_fs.sv")] + base + ref_files, capture_output=True, text=True)
if out.returncode: raise SystemExit(out.stderr[-1500:])
P = json.loads(out.stdout.strip().splitlines()[-1]); ports = P["ports"]
clocks = sorted(n for n in ports if re.search(CLK, n))
wrap = Path(wrapf).read_text()
m = re.search(r"module\s+" + re.escape(a.newtop) + r"\s*\((.*?)\);", wrap, re.S)
newports = {x.group(1) for x in re.finditer(r"(?:input|output)\s+wire\s*(?:\[\d+:0\]\s*)?(\w+)", m[1])}
missing = (set(ports) - set(clocks)) ^ (newports - {"clk"})
if missing: raise SystemExit(f"port sets differ: {sorted(missing)[:10]}")
P["rst"] = [n for n in P["rst"] if ports[n][0] == "input"]   # a reset can also leave the core as a plain output
ins = [n for n, (d, w) in ports.items() if d == "input" and n not in clocks and n not in P["rst"]]
outs = [n for n, (d, w) in ports.items() if d == "output"]
wout = max(outs, key=lambda n: ports[n][1]); win = max(ins, key=lambda n: ports[n][1])
dec = lambda n: f"{ports[n][0]} wire {'[%d:0] ' % (ports[n][1]-1) if ports[n][1] > 1 else ''}{n}"
tb = a.reftop + "__ocdut"
conn = [".clk(%s)" % ("%s" % (clocks[0] if ports[clocks[0]][1] == 1 else clocks[0] + "[0]"))]
for n in ports:
    if n in clocks: continue
    e = n
    if n == win: e = f"(`OT_MUT == 3 ? ({n} & ~{ports[n][1]}'d1) : {n})"
    if n == wout: e = n + "__i"
    conn.append(f".{n}({e})")
ad = "`default_nettype none\nmodule " + tb + " (\n  " + ",\n  ".join(dec(n) for n in ports) + "\n);\n"
ad += f"  wire {'[%d:0] ' % (ports[wout][1]-1) if ports[wout][1] > 1 else ''}{wout}__i;\n"
ad += f"  assign {wout} = (`OT_MUT == 2) ? ({wout}__i ^ {ports[wout][1]}'d1) : {wout}__i;\n"
ad += f"  {a.newtop} u_dut (" + ", ".join(conn) + ");\nendmodule\n`default_nettype wire\n"
(O / "dut_adapter.sv").write_text(ad)
spec = dict(ref=a.reftop, dut=tb, ports=ports, clocks=clocks, resets=P["rst"], reset_cycles=10, warmup=150, cycles=a.cycles, stim={}, hold={}, shift={})
(O / "spec.json").write_text(json.dumps(spec, indent=1))
subprocess.check_call([sys.executable, str(H / "lockstep_gen.py"), str(O / "spec.json"), str(O / "tb.sv")])
def mutclk(s, k=-1):
    # invert exactly one clock connection bit in the wrapper
    hits = list(re.finditer(r"\.(\w+)\((\{(\d+)\{clk\}\}|clk)\)", s))
    h = hits[k]; w = int(h[3] or 1)
    new = f".{h[1]}(~clk)" if w == 1 else f".{h[1]}({{{{{w-1}{{clk}}}},~clk}})"
    return s[:h.start()] + new + s[h.end():]
rc = 0
for M in a.muts.split(","):
    M, _, kk = M.partition(":"); tag = M + ("_" + kk if kk else "")
    wf = O / f"wrap_m{tag}.sv"; wf.write_text(mutclk(wrap, int(kk or -1)) if M == "1" else wrap)
    d = O / f"obj_m{tag}"
    b = subprocess.run([V, "--binary", "-j", "16", "-Wno-fatal", "-Wno-lint", "-Wno-style", f"-DOT_MUT={M}", "--top-module", "tb", "-Mdir", str(d), "-o", "sim",
                        str(O / "tb.sv"), str(wf), str(O / "dut_adapter.sv")] + base + ref_files, capture_output=True, text=True)
    (O / f"build_m{tag}.log").write_text(b.stdout + b.stderr)
    if b.returncode: print(f"MUT {tag}: BUILD FAIL", (b.stdout + b.stderr)[-600:]); rc = 2; continue
    r = subprocess.run([str(d / "sim")], capture_output=True, text=True); (O / f"sim_m{tag}.log").write_text(r.stdout + r.stderr)
    print(f"MUT {tag}:", next((l[:220] for l in r.stdout.splitlines() if "LOCKSTEP" in l), "no LOCKSTEP line rc=%d" % r.returncode), flush=True)
    subprocess.run(["rm", "-rf", str(d)])
sys.exit(rc)
