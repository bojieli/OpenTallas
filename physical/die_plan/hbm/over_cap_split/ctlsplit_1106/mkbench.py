import json, sys
d = json.load(open(sys.argv[1])); m = d['modules']['ot_hgi_sfu_split3_ctl_core']
gate_mod = sys.argv[2]; ncyc = int(sys.argv[3])
P = [(n, p['direction'], len(p['bits'])) for n, p in m['ports'].items()]
CLK = {'clk', 'clk_lg', 'clk_pw', 'clk_pe'}; RST = {'rst_n', 'rst_lg_n'}
L = ['`timescale 1ns/1ps', 'module tb;', ' reg clk=0; integer cyc=0, errs=0, seed=12345;']
for n, d_, w in P:
    if d_ == 'input' and n not in CLK: L.append(f' reg [{w-1}:0] {n};')
    if d_ == 'output': L.append(f' wire [{w-1}:0] g_{n}, s_{n};')
def conns(pfx):
    c = []
    for n, d_, w in P:
        if n in CLK: c.append(f'.{n}({{{w}{{clk}}}})')
        elif d_ == 'input': c.append(f'.{n}({n})')
        else: c.append(f'.{n}({pfx}_{n})')
    return ', '.join(c)
L.append(f' ot_hgi_sfu_split3_ctl_core gold({conns("g")});')
L.append(f' {gate_mod} gate({conns("s")});')
L.append(' task rnd; begin')
for n, d_, w in P:
    if d_ == 'input' and n not in CLK and n not in RST:
        k = (w + 31) // 32
        L.append(f'  {n} = {{' + ', '.join(['$random(seed)'] * k) + '};')
L.append(' end endtask')
L.append(' always #1 clk = ~clk;')
L.append(' initial begin')
L.append('  rst_n = 0; rst_lg_n = 0; rnd;')
L.append(f'  repeat (5) @(negedge clk) rnd;')
L.append('  rst_n = 1; rst_lg_n = 4\'hf;')
L.append(f'  for (cyc = 0; cyc < {ncyc}; cyc = cyc + 1) begin')
L.append('   @(negedge clk); rnd;')
L.append('   if (cyc == 300) begin rst_lg_n = 4\'h5; end')
L.append('   if (cyc == 303) begin rst_lg_n = 4\'hf; end')
L.append('   if (cyc == 500) begin rst_n = 0; end')
L.append('   if (cyc == 502) begin rst_n = 1; end')
L.append('   #0.5;')
for n, d_, w in P:
    if d_ == 'output':
        L.append(f'   if (g_{n} !== s_{n}) begin errs = errs + 1; if (errs < 10) $display("MISMATCH cyc %0d {n}", cyc); end')
L.append('  end')
L.append('  $display("BENCH_DONE cycles %0d errors %0d", cyc, errs); $finish;')
L.append(' end')
L.append('endmodule')
print('\n'.join(L))
