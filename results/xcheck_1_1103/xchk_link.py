"""XCHECK-1 cross-die link probe (report only): registered-face form around a modelled PHY.
  TX : face flop (ASAP7 DFFHQNx1 RVT) -> wire L -> PHY input pin (lib setup/hold vs PHY clock pin)
  RX : PHY output pin (lib clk->q) -> wire L -> face flop D
The off-die part (PMA / bumps / CDR / async FIFO) lives inside the PHY model and is not timed here (12.x / 2.8).
usage: python3 -I xchk_link.py OUTDIR NAME TT.lib FF.lib [--L 30] [--Lmin 3]
writes OUTDIR/NAME/{top.v,sta_tt.tcl,sta_ff.tcl}; run sta in the ORFS image."""
import os, re, sys

out, name, tt, ff = sys.argv[1:5]
L = float(sys.argv[sys.argv.index('--L') + 1]) if '--L' in sys.argv else 30.0
LMIN = float(sys.argv[sys.argv.index('--Lmin') + 1]) if '--Lmin' in sys.argv else 3.0
CAP_FF_PER_UM = 0.2      # ASAP7 M4/M5 ~0.2 fF/um (die model basis)
KMAX = 64                # pins per class probed


def groups(s, i0, i1):
    """top-level 'kw(name) { ... }' groups between i0 and i1."""
    r = []
    rx = re.compile(r'(\w+)\s*\(\s*"?([^")]*)"?\s*\)\s*\{')
    i = i0
    while True:
        m = rx.search(s, i, i1)
        if not m:
            return r
        d, j = 1, m.end()
        while d and j < i1:
            c = s[j]
            d += (c == '{') - (c == '}')
            j += 1
        r.append((m.group(1), m.group(2), m.end(), j - 1))
        i = j


s = open(tt, errors='ignore').read()
cm = re.search(r'cell\s*\(\s*"?(\w+)"?\s*\)\s*\{', s)
cell = cm.group(1)
widths = {}
lib_top0 = groups(s, 0, len(s))
cb0 = [g for g in lib_top0 if g[0] == 'library'][0]
for kw, n, a, b in groups(s, cb0[2], cb0[3]):
    if kw == 'type':
        w = re.search(r'bit_width\s*:\s*(\d+)', s[a:b]); widths[n] = int(w.group(1)) if w else 1
lib_top = groups(s, 0, len(s))
cb = [g for g in lib_top if g[0] == 'library'][0]
cg = [g for g in groups(s, cb[2], cb[3]) if g[0] == 'cell'][0]
ports = []   # (name, dir, width, is_clock, has_setup, has_clkq)
for kw, n, a, b in groups(s, cg[2], cg[3]):
    if kw not in ('pin', 'bus'):
        continue
    body = s[a:b]
    d = re.search(r'direction\s*:\s*(\w+)', body); d = d.group(1) if d else 'input'
    w = 1
    if kw == 'bus':
        bt = re.search(r'bus_type\s*:\s*"?(\w+)"?', body); w = widths.get(bt.group(1), 1) if bt else 1
    ports.append((n, d, w, kw == 'bus', bool(re.search(r'clock\s*:\s*true', body)),
                  'setup_rising' in body, 'rising_edge' in body))
clk = [p for p in ports if p[4]]
clkpin = clk[0][0] if clk else None
os.makedirs(os.path.join(out, name), exist_ok=True)
V = ['module top(input clk);']
conn = []
tx = rx = 0
for n, d, w, isbus, isclk, su, cq in ports:
    if isclk and n == clkpin:
        conn.append(f'.{n}(clk)'); continue
    if isbus:
        V.append(f'  wire [{w - 1}:0] w_{n};'); conn.append(f'.{n}(w_{n})'); bit = f'w_{n}[0]'
    else:
        V.append(f'  wire w_{n};'); conn.append(f'.{n}(w_{n})'); bit = f'w_{n}'
    if d == 'input' and su and tx < KMAX:
        V.append(f'  DFFHQNx1_ASAP7_75t_R l_{n} (.CLK(clk), .D(1\'b0), .QN({bit}));'); tx += 1
    elif d == 'output' and cq and rx < KMAX:
        V.append(f'  DFFHQNx1_ASAP7_75t_R c_{n} (.CLK(clk), .D({bit}), .QN());'); rx += 1
V.append(f'  {cell} u_phy ({", ".join(conn)});')
V.append('endmodule')
open(os.path.join(out, name, 'top.v'), 'w').write('\n'.join(V) + '\n')
LIB = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'
for corner, ml, Lw in (('tt', tt, L), ('ff', ff, LMIN)):
    C = corner.upper()
    T = f"""read_liberty {LIB}/asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib
read_liberty {ml}
read_verilog top.v
link_design top
create_clock -name clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks clk]
set_clock_uncertainty -hold 25 [get_clocks clk]
set_timing_derate -late -data -cell_delay 1.10
set_timing_derate -late -data -net_delay 1.05
foreach n [get_nets w_*] {{ set_load {Lw * CAP_FF_PER_UM:.3f} $n }}
set_input_transition 30 [all_inputs]
puts "XCHK {name} {corner} L={Lw} tx={tx} rx={rx} clkpin={clkpin}"
foreach dl {{max min}} {{
  foreach grp {{to_phy from_phy}} {{
    if {{$grp == "to_phy"}} {{ set ps [sta::find_timing_paths -path_delay $dl -to [get_pins u_phy/*] -group_path_count 1 -endpoint_path_count 1] }} else {{ set ps [sta::find_timing_paths -path_delay $dl -from [get_pins u_phy/*] -group_path_count 1 -endpoint_path_count 1] }}
    foreach p $ps {{ puts "XCHK {name} {corner} $dl $grp slack=[format %.1f [expr {{[$p slack]*1e12}}]] end=[get_full_name [$p pin]]" }}
  }}
}}
report_check_types -min_period -violators
"""
    open(os.path.join(out, name, f'sta_{corner}.tcl'), 'w').write(T)
print(name, cell, 'clk', clkpin, 'tx', tx, 'rx', rx)
