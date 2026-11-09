#!/usr/bin/env python3
"""QC-TYPES-9/REACH bench: realise the plan_qc53v4w cw_n stations on a v4s bound hc module with the same code the native
bind runs (native_istations.source_entries + kit_istations --apply), then prove new == old delayed by N (data whenever
the delayed epoch is set, epoch always) on the exact bound lines, with mutants that must fail.
usage: bench_reach.py TOOLS_DIE_PLAN PLAN_V4W BOUND_SV TYPE OUTDIR"""
import copy, json, re, shutil, subprocess, sys
from pathlib import Path

tools, plan, bsv, tn, out = sys.argv[1:6]
sys.path.insert(0, tools)
import native_istations, kit_istations  # noqa: E402

out = Path(out).resolve(); kd = out / 'kit'; kd.mkdir(parents=True, exist_ok=True)
raw = json.loads(Path(plan).read_text())
typ = copy.deepcopy(raw['partition_types'][tn])
typ['internal_stations'] = native_istations.source_entries(typ)
(kd / 'plan.json').write_text(json.dumps({'partition_types': {tn: typ}}))
local = kd / Path(bsv).name
shutil.copyfile(bsv, local)
(kd / 'kit_rtl.json').write_text(json.dumps({'bound_module': local.stem, 'files': [str(local)]}))
kit_istations.main([str(kd / 'plan.json'), tn, str(kd), '--apply'])
old_t, new_t = Path(bsv).read_text(), local.read_text()
k = re.search(r'_hc(\d)__', tn).group(1)
bus = f'cw_n{k}'
old_line = re.search(rf'^\s*ot_dp_st #\(\.W\((\d+)\)\) u_bout_{bus} .*$', old_t, re.M)
W = int(old_line.group(1))
new_lines = [l for l in new_t.splitlines() if re.search(rf'\bu_ist_{bus}_\d+\b|\bu_bout_{bus}\b', l) and 'ot_dp_st' in l]
decls = [l for l in new_t.splitlines() if re.search(rf'wire .*\b{bus}_is\d+_e?q\b', l)]
N = len([l for l in new_lines if 'u_ist_' in l])
d_in = re.search(r'\.d\(([^)]*)\)', old_line.group(0)).group(1)
src = re.match(r'(\w+)\[', d_in).group(1)
hdr = f'(input wire clk, input wire rst_n, input wire [{W-1}:0] {src}, output wire [{W}:0] {bus})'
ref = f'module old_adapter{hdr};\n{old_line.group(0)}\nendmodule\n'
cand = f'module new_adapter{hdr};\n' + '\n'.join(decls + new_lines) + '\nendmodule\n'
(out / 'adapters.sv').write_text(ref + cand)
# mutants: m1 inverted data into station 0; m2 one station short (last station bypassed); m3 epoch not carried
m1 = cand.replace(f'u_ist_{bus}_0 (.clk(clk), .rst_n(rst_n), .d(', f'u_ist_{bus}_0 (.clk(clk), .rst_n(rst_n), .d(~', 1)
last = N - 1
m2 = re.sub(rf'\.d\({bus}_is{last}_q\), \.ea\({bus}_is{last}_eq\)', f'.d({bus}_is{last-1}_q), .ea({bus}_is{last-1}_eq)', cand) \
    if N > 1 else cand
m3 = re.sub(rf'(u_bout_{bus} \(.*?\.ea\()[^)]*\)', r"\g<1>1'b1)", cand)
for nm, txt in (('m1', m1), ('m2', m2), ('m3', m3)):
    assert txt != cand, nm
    (out / f'{nm}.sv').write_text(ref + txt)
cells = Path(tools).parents[1] / 'rtl'
tb = f'''`timescale 1ns/1ps
module tb; reg clk=0; always #5 clk=~clk; reg rst_n=0; integer errors=0, cycle=0, seen=0, k;
reg [{W-1}:0] {src}=0; wire [{W}:0] o, n; reg [{W}:0] h [0:{N+1}];
old_adapter od(.clk(clk), .rst_n(rst_n), .{src}({src}), .{bus}(o));
new_adapter nd(.clk(clk), .rst_n(rst_n), .{src}({src}), .{bus}(n));
always @(posedge clk) begin h[0] <= o; for (k=1; k<={N+1}; k=k+1) h[k] <= h[k-1]; end
// reset at cycle 60..63 flushes the in-flight stages: epoch unchecked 60..{N+61}, data unchecked 60..{N+64}
always @(negedge clk) begin cycle=cycle+1; if (cycle > {N+4}) begin
  if (!(cycle >= 60 && cycle <= {N+61}) && n[{W}] !== h[{N-1}][{W}]) errors=errors+1;
  if (!(cycle >= 60 && cycle <= {N+64})) begin
    if (h[{N-1}][{W}] && n[{W-1}:0] !== h[{N-1}][{W-1}:0]) errors=errors+1; else if (h[{N-1}][{W}]) seen=seen+1; end end
  {src} <= {{{', '.join(['$random'] * ((W + 31) // 32))}}};
  if (cycle == 60) rst_n = 0; if (cycle == 63) rst_n = 1;
end
initial begin #13 rst_n=1; #4000; if (errors || !seen) begin $display("REACH_FAIL errors=%0d seen=%0d", errors, seen); $fatal(1); end
  else $display("REACH_PASS cycles=%0d checks=%0d N={N} W={W}", cycle, seen); $finish; end
endmodule
'''
(out / 'tb.sv').write_text(tb)
print(json.dumps(dict(type=tn, bus=bus, W=W, stations=N, src=src)))
