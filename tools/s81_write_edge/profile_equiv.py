#!/usr/bin/env python3
"""Profile binding bench (claude S81 VM F1, 2026-10-15): the hardened profile top (face-split wrapper) is cycle-equivalent
to the production leaf instance it replaces (same parameters), under random stimulus incl. reset, for N edges.

    profile_equiv.py OUT PROFILE [--mutant]     PROFILE = dsfd_vm_static_wdispatch128_B{0,8,16,24} | dsfd_vm_static_wstage128_{E,W}
--mutant swaps one face-bus half in the comparison (self-test: must FAIL).
"""
import random, subprocess, sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
V = R / 'rtl/dsrom_sys/s81_ph/vm'
IN = [('i_v', 1), ('i_row', 14), ('i_mask', 4), ('i_data', 128), ('i_tag', 8), ('i_capture_lane', 2), ('i_storage_slot', 2)]
OUT = [('o_v', 3), ('o_slot', 6), ('o_row', 42), ('o_mask', 12), ('o_data', 384), ('o_tag', 24)]


def main():
    out, prof = Path(sys.argv[1]), sys.argv[2]
    mut = '--mutant' in sys.argv
    out.mkdir(parents=True, exist_ok=True)
    N = 3000
    if prof.startswith('dsfd_vm_static_wdispatch128_B'):
        base = int(prof.rsplit('B', 1)[1])
        srcs = [V / 'dsfd_vm_static_wdispatch128.sv', V / 'dsfd_vm_static_wdispatch128_profiles.sv']
        decl, pc, rc, drive, cmp = [], [], [], [], []
        for n, v in IN:
            decl.append(f'reg [{53*v-1}:0] {n};')
            pc.append(f'.{n}_n({n}[{27*v-1}:0]), .{n}_s({n}[{53*v-1}:{27*v}])')
            rc.append(f'.{n}({n})')
            drive.append(f'{n} = {{' + ','.join(['$random'] * ((53 * v + 31) // 32)) + '};')
        for n, v in OUT:
            decl.append(f'wire [{8*v-1}:0] r_{n}; wire [{4*v-1}:0] p_{n}_e, p_{n}_w;')
            pc.append(f'.{n}_e(p_{n}_e), .{n}_w(p_{n}_w)')
            rc.append(f'.{n}(r_{n})')
            cat = f'{{p_{n}_e, p_{n}_w}}' if mut and n == 'o_data' else f'{{p_{n}_w, p_{n}_e}}'
            cmp.append(f'if (r_{n} !== {cat}) bad = bad + 1;')
        decl.append('wire r_fault, p_fault;')
        pc.append('.fault(p_fault)'); rc.append('.fault(r_fault)'); cmp.append('if (r_fault !== p_fault) bad = bad + 1;')
        # bias rows / lanes so records hit this quarter's banks without lane faults most of the time
        bias = ['for (k = 0; k < 53; k = k + 1) begin i_capture_lane[2*k +: 2] = $urandom % 3; i_storage_slot[2*k +: 2] = $urandom % 3; '
                f'i_row[14*k +: 5] = {base} + ($urandom % 8); i_row[14*k+5 +: 3] = 0; i_v[k] = ($urandom % 4) == 0; end']
        inst = (f'{prof} p (.ck(ck), .rst_n(rst_n), ' + ', '.join(pc) + ');\n'
                f'dsfd_vm_static_wdispatch128 #(.NSRC(53), .NBANK(8), .BANK_BASE({base})) r (.ck(ck), .rst_n(rst_n), ' + ', '.join(rc) + ');')
    elif prof in ('dsfd_vm_static_wstage128_E', 'dsfd_vm_static_wstage128_W'):
        srcs = [V / 'dsfd_vm_static_wstage128.sv', V / 'dsfd_vm_static_wstage128_profiles.sv']
        ins = [('capture_v', 3), ('capture_slot', 6), ('capture_row', 42), ('capture_mask', 12), ('capture_data', 384), ('capture_tag', 24),
               ('drain_v', 1), ('drain_slot', 2)]
        outs = [('o_v', 1), ('o_row', 14), ('o_mask', 4), ('o_data', 128), ('o_tag', 8), ('fault', 1)]
        decl = [f'reg [{v-1}:0] {n};' for n, v in ins] + [f'wire [{v-1}:0] r_{n}, p_{n};' for n, v in outs]
        drive = [f'{n} = {{' + ','.join(['$random'] * ((v + 31) // 32)) + '};' for n, v in ins]
        bias = []
        cmp = [f'if (r_{n} !== ' + (f'~p_{n}' if mut and n == 'o_data' else f'p_{n}') + ') bad = bad + 1;' for n, v in outs]
        conn = lambda pre: ', '.join([f'.{n}({n})' for n, v in ins] + [f'.{n}({pre}{n})' for n, v in outs])
        inst = f'{prof} p (.ck(ck), .rst_n(rst_n), {conn("p_")});\ndsfd_vm_static_wstage128 #(.DEPTH(3)) r (.ck(ck), .rst_n(rst_n), {conn("r_")});'
    else:
        sys.exit(f'unknown profile {prof}')
    tb = f'''`timescale 1ns/1ps
module tb_profile_equiv;
reg ck = 0, rst_n = 0; integer cy = 0, bad = 0, k;
{chr(10).join(decl)}
{inst}
always #0.5 ck = ~ck;
initial begin
 {' '.join(drive)} {' '.join(bias)}
 repeat (3) @(posedge ck); rst_n = 1;
 while (cy < {N}) begin
  @(negedge ck); {' '.join(cmp)}
  {' '.join(drive)} {' '.join(bias)}
  if (cy == {N // 2}) rst_n = 0; if (cy == {N // 2 + 3}) rst_n = 1;
  cy = cy + 1;
 end
 if (bad == 0) $display("PROFILE_EQUIV PASS {prof} cycles %0d", cy); else $display("PROFILE_EQUIV FAIL {prof} cycles %0d bad %0d", cy, bad);
 $finish;
end
endmodule
'''
    (out / 'tb.sv').write_text(tb)
    subprocess.run(['iverilog', '-g2012', '-o', str(out / 'tb'), str(out / 'tb.sv')] + [str(s) for s in srcs], check=True)
    r = subprocess.run(['vvp', str(out / 'tb')], capture_output=True, text=True)
    print(r.stdout[-2000:])
    sys.exit(0 if 'PROFILE_EQUIV PASS' in r.stdout else 1)


if __name__ == '__main__':
    main()
