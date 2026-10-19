#!/usr/bin/env python3
"""tb_pr.sv: original qkd_kvs_attn_safe_control vs pin-registered qkd_kvs_attn_safe_pr (actual Liberty models), lockstep.
Every edge: all public outputs AND every original flop's QN net (same net name in both; a removed flop's QN net is driven
by the retimed / split replacement) must be equal.  RX payload words are biased (zero / one-hot / sparse / dense) so the
zero-test cones see both values; reset pulses between trials.  Usage: build_eq_bench.py <orig.v> <pr.v> <out_dir>"""
import re, sys, pathlib
orig, pr, od = sys.argv[1:4]
od = pathlib.Path(od); od.mkdir(parents=True, exist_ok=True)
src = open(orig).read()
hdr = src[:src.index(';', src.index('module '))]
ports = re.findall(r'^\s*(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+);', src, re.M)
ff_qn = re.findall(r'^\s*\(\*[^*]*\*\)\s*DFF\w+\s+c\d+\s*\(.*?\.QN\((n\d+)\)', src, re.M)
prsrc = open(pr).read()
prnets = set(re.findall(r'\.(?:QN|Y|H|L)\((n\d+)\)', prsrc))
dropped = [q for q in ff_qn if q not in prnets]      # QN nets of old output-chain flops deleted by outclone (load-less)
ff_qn = [q for q in ff_qn if q in prnets]
ins = [(n, int(h) - int(l) + 1 if h else 1) for d, h, l, n in ports if d == 'input' and n not in ('ck',)]
outs = [(n, int(h) - int(l) + 1 if h else 1) for d, h, l, n in ports if d == 'output']
s = ['`timescale 1ns/1ps', 'module tb_pr;', 'reg ck=0; always #0.416667 ck=~ck;']
s += [f'reg [{w-1}:0] {n}=0;' for n, w in ins]
s += [f'wire [{w-1}:0] o_{n}, p_{n};' for n, w in outs]
for typ, pre in (('qkd_kvs_attn_safe_control', 'o'), ('qkd_kvs_attn_safe_pr', 'p')):
    s.append(f'{typ} {pre}dut(.ck(ck),' + ','.join(f'.{n}({n})' for n, _ in ins) + ',' + ','.join(f'.{n}({pre}_{n})' for n, _ in outs) + ');')
s += ["reg [63:0] rng=64'h9e3779b97f4a7c15; integer checks=0, ffchecks=0, mode;",
      'function automatic [31:0] draw; rng=rng^(rng<<13); rng=rng^(rng>>7); rng=rng^(rng<<17); return rng[31:0]; endfunction',
      'task automatic chk(input integer trial, input integer cycle);']
for n, _ in outs:
    s.append(f' if (o_{n} !== p_{n}) begin $display("PR_EQ_MISMATCH out {n} trial=%0d cycle=%0d", trial, cycle); $fatal(1); end')
for q in ff_qn:
    s.append(f' if (odut.{q} !== pdut.{q}) begin $display("PR_EQ_MISMATCH ff {q} trial=%0d cycle=%0d", trial, cycle); $fatal(1); end')
s += [f' checks++; ffchecks += {len(ff_qn)};', 'endtask', 'initial begin',
      ' for (int trial=0; trial<48; trial++) begin',
      '  @(negedge ck); rst_n=0; repeat(12) begin @(negedge ck); #0.1; chk(trial,-1); end',
      '  rst_n=1;',
      '  for (int cycle=0; cycle<160; cycle++) begin', '   @(negedge ck);']
for n, w in ins:
    if n == 'rst_n':
        continue
    if n == 'd2d__rx_payload':
        s += ['   mode = draw() % 4;',
              f'   for (int k=0;k<{w};k+=32) d2d__rx_payload[k+:32] = (mode==0) ? 0 : (mode==1) ? 0 : (mode==2) ? ((draw()%8==0) ? (32\'h1 << (draw()%32)) : 0) : draw();',
              '   if (mode==1) d2d__rx_payload[draw()%548] = 1\'b1;']
    elif n.startswith('uf'):
        s.append(f'   {n} = (draw()%16==0);')        # sparse unit faults: the root runs between faults
    else:
        s += [f'   for (int k=0;k<{w};k+=32) {n}[k+:32] = draw();'] if w > 1 else [f'   {n} = draw()%2;']
s += ['   #0.1; chk(trial,cycle);', '  end', ' end',
      ' $display("PR_EQ PASS checks=%0d ff_net_checks=%0d outputs=%0d ff_nets=%0d", checks, ffchecks, ' + str(len(outs)) + ', ' + str(len(ff_qn)) + ');',
      ' $finish;', 'end', 'endmodule']
(od / 'tb_pr.sv').write_text('\n'.join(s) + '\n')
print('tb_pr.sv', len(outs), 'outputs', len(ff_qn), 'ff nets compared', len(dropped), 'dropped (deleted load-less output-chain flops)', dropped)
