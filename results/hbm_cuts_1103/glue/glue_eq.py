"""DIE-HBM-61/CUTS glue EQ: shell(in_stages '.*'=1) == shell(RF1, as built) with every signal input delayed 1 edge
(rst_n not delayed), lockstep on every output every edge, random inputs, periodic reset; mutants must FAIL."""
import importlib.util, json, re, subprocess, sys
from pathlib import Path
fsp, kit, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location('fs', fsp); fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
J = json.loads((kit / 'face_shell.json').read_text())
args = (J['module'], J['core'], J['params'], J['widths'], J['dirs'], J['keep'], set(J['passthrough']), J['clock'])
kw = dict(scalars=set(J['scalars']), stages=J.get('out_extra_stages') or {},
          lockup=set((J.get('out_lockup') or {}).get('buses', [])), rst_relay=(J.get('reset_relay') or {}).get('resets', {}))
gold = (kit / 'rtl' / f"{J['module']}__fshell.sv").read_text()
assert fs.emit_shell(*args, mutant=None, **kw) == gold
sig_in = [n for n in J['widths'] if J['dirs'][n] == 'input' and n not in J['passthrough'] and J['keep'][n] > 0]
ist = {n: 1 for n in sig_in}
(out / 'gold.sv').write_text(gold.replace(f"module {J['module']} (", f"module gold_{J['module']} ("))
cases = {'cut': None, 'm1_cw_in_short': {'kind': 'in_short', 'bus': 'cw_in', 'bit': 5},
         'm2_b3_eg_short': {'kind': 'in_short', 'bus': 'b3_eg', 'bit': 0},
         'm3_b5_pr_short': {'kind': 'in_short', 'bus': 'b5_pr', 'bit': 7},
         'm4_ccw_in_bypass': {'kind': 'in_bypass', 'bus': 'ccw_in', 'bit': 100}}
for c, m in cases.items():
    (out / f'{c}.sv').write_text(fs.emit_shell(*args, mutant=m, **kw, in_stages=ist))
W, D = J['widths'], J['dirs']
outs = [n for n in W if D[n] == 'output']
rst = [n for n in J['passthrough'] if n != 'clk' and D[n] == 'input']
lines = ['`timescale 1ns/1ps', 'module tb;', ' parameter integer CYC=6000;', ' reg clk=0; always #0.5 clk=~clk;']
for n in sig_in + rst:
    lines.append(f' reg [{W[n]-1}:0] {n}=0; reg [{W[n]-1}:0] {n}__d=0;')
for n in outs:
    lines.append(f' wire [{W[n]-1}:0] g_{n}, d_{n};')
lines.append(' always @(posedge clk) begin ' + ' '.join(f'{n}__d<={n};' for n in sig_in) + ' end')
def inst(mod, pre, dl):
    cs = ['.clk(clk)'] + [f'.{n}({n})' for n in rst] + [f'.{n}({n}{"__d" if dl else ""})' for n in sig_in] + [f'.{n}({pre}_{n})' for n in outs]
    return f' {mod} u_{pre}(' + ', '.join(cs) + ');'
lines.append(inst(f"gold_{J['module']}", 'g', True)); lines.append(inst(J['module'], 'd', False))
rnd = lambda n: '{' + ','.join(['$urandom'] * ((W[n] + 31) // 32)) + '}'
lines += [' integer cyc, bad=0, nc=0, act=0;', ' initial begin', '  for(cyc=0;cyc<CYC;cyc=cyc+1) begin', '   @(negedge clk);']
for n in rst:
    lines.append(f'   {n} = (cyc%2000)>=12;')
for n in sig_in:
    rate = 2 if W[n] > 4 else 3
    lines.append(f'   {n} = (($urandom%{rate})==0) ? {rnd(n)} : {n};')
cmp = ' || '.join(f'g_{n}!==d_{n}' for n in outs)
lines += ['   if(cyc>30 && (cyc%2000)>=40) begin nc=nc+1;',
          '    act = act + (' + ' + '.join(f'(g_{n}!=0)' for n in outs) + ');',
          f'    if({cmp}) begin bad=bad+1; if(bad<=3) $display("MISMATCH cyc=%0d", cyc); end', '   end', '  end',
          '  if(bad==0) $display("GLUE_EQ PASS compared=%0d nonzero_out_samples=%0d", nc, act); else $display("GLUE_EQ FAIL mismatches=%0d of %0d", bad, nc);',
          '  $finish;', ' end', 'endmodule']
(out / 'tb.sv').write_text('\n'.join(lines) + '\n')
cfg = (kit / 'config.mk').read_text()
files = [str(kit / 'rtl' / Path(f).name) for f in re.search(r'VERILOG_FILES = (.*)', cfg).group(1).split() if not f.endswith('__fshell.sv')]
res = {}
for c in cases:
    exe = out / f'{c}.vvp'
    r = subprocess.run(['iverilog', '-g2012', '-DSYNTHESIS', '-o', str(exe), str(out / 'tb.sv'), str(out / 'gold.sv'), str(out / f'{c}.sv'), *files], capture_output=True, text=True)
    if r.returncode:
        print(c, 'COMPILE', r.stderr[-2000:]); res[c] = 'COMPILE_FAIL'; continue
    o = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True).stdout
    res[c] = [l for l in o.splitlines() if 'GLUE_EQ' in l][-1] if 'GLUE_EQ' in o else o[-500:]
    print(c, res[c], flush=True)
(out / 'glue_eq.json').write_text(json.dumps(dict(kit=str(kit), in_stages=ist, in_extra_stage_flops=sum(J['keep'][n] for n in ist), results=res), indent=1) + '\n')
