#!/usr/bin/env python3
"""Exercise actual KV calendar and both QC code macros concurrently, with ROM faults.

Run through ot-run. This checks real native via-map loading at833ps, without
setting global OT_ROM_DIR or changing the KV calendar. It is not a token pass.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--union', type=Path, required=True)
    parser.add_argument('--code-rank', type=Path, required=True)
    parser.add_argument('--macro-code', type=Path, required=True)
    parser.add_argument('--macro-kv', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--verilator', default='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    record = json.loads((args.union / 'union.json').read_text())
    kv = (args.union / 'kv_dcal.viamap.hex').resolve(strict=True)
    columns = [(args.union / f'qtile_t0_b0_c{c}.viamap.hex').resolve(strict=True) for c in range(2)]
    rows = [int(line, 16) for line in kv.read_text().splitlines()]
    if len(rows) != 32:
        raise ValueError('selected actual64x32 calendar must have32 physical rows')
    expected_kv = args.out / 'kv_words.hex'
    expected_kv.write_text(''.join(f'{sum(((rows[a//2] >> (2*b+a%2)) & 1) << b for b in range(32)):08x}\n' for a in range(64)))
    expected_code = (args.code_rank / 'expected/qtile_t0_b0.hex').resolve(strict=True)
    tb = f'''`timescale 1ps/1ps
module tb_qckvrom;
reg ck=0; always begin #416 ck=1; #417 ck=0; end
reg [11:0] addr=0;
wire [31:0] kv; wire [265:0] c0,c1;
ot_rom_64x32_m2 #(.VIAMAP({json.dumps(str(kv))}),.INSTANCE("kv_dcal")) u_kv (.clk(ck),.ce_in(1'b1),.addr_in(addr[5:0]),.rd_out(kv));
ot_rom_4096x266_m8 #(.VIAMAP({json.dumps(str(columns[0]))})) u_c0 (.clk(ck),.ce_in(1'b1),.addr_in(addr),.rd_out(c0));
ot_rom_4096x266_m8 #(.VIAMAP({json.dumps(str(columns[1]))})) u_c1 (.clk(ck),.ce_in(1'b1),.addr_in(addr),.rd_out(c1));
reg [31:0] expected_kv[0:63]; reg [511:0] expected_code[0:4095]; integer a;
initial begin
 $readmemh({json.dumps(str(expected_kv))},expected_kv);
 $readmemh({json.dumps(str(expected_code))},expected_code);
 #1;
 if ($test$plusargs("MUT_ROM")) u_c0.arr[0][0]=~u_c0.arr[0][0];
 if ($test$plusargs("MUT_KV")) u_kv.arr[0][0]=~u_kv.arr[0][0];
 for(a=0;a<64;a=a+1) begin
  addr=12'(a); repeat(4) @(negedge ck);
  if(kv!==expected_kv[a] || {{c1[255:0],c0[255:0]}}!==expected_code[a] || c0[265:256]!==10'd0 || c1[265:256]!==10'd0)
   $fatal(1,"ROM_LOAD_MISMATCH addr=%0d kv=%h expected=%h",a,kv,expected_kv[a]);
 end
 $display("CODE_KV_ROM_LOAD_PASS128codewords64KVwords"); $finish;
end
endmodule
'''
    top = args.out / 'tb_qckvrom.sv'; top.write_text(tb)
    command = [args.verilator, '--binary', '--timing', '-j', '2', '-Wno-fatal',
               '-Wno-TIMESCALEMOD', '--top-module', 'tb_qckvrom', '--Mdir', str(args.out/'obj'),
               str(top), str(args.macro_code), str(args.macro_kv)]
    with (args.out/'build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = {}
    for name, extra in [('nominal', []), ('code_mutant', ['+MUT_ROM']), ('kv_mutant', ['+MUT_KV'])]:
        with (args.out/f'{name}.log').open('w') as log:
            run = subprocess.run([str(args.out/'obj/Vtb_qckvrom'), *extra], stdout=log, stderr=subprocess.STDOUT)
        text = (args.out/f'{name}.log').read_text()
        passed = run.returncode == 0 and 'CODE_KV_ROM_LOAD_PASS' in text if name == 'nominal' else run.returncode != 0 and 'ROM_LOAD_MISMATCH' in text
        results[name] = dict(returncode=run.returncode, passed=passed)
    receipt = dict(clock_period_ps=833, results=results, kv_sha256=sha(kv),
                   code_sha256=[sha(path) for path in columns], rank=record['rank'],
                   scope='Three actual native ROM macros, direct VIAMAPs,128codewords64calendarwords; no token or programme qualification.')
    (args.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, sort_keys=True))
    if not all(row['passed'] for row in results.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
