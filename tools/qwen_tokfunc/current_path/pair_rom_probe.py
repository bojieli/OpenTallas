#!/usr/bin/env python3
"""Exercise actual KV calendar and both QC code macros concurrently, with ROM faults.

Run through ot-run. This checks real native via-map loading at833ps, using
OT_QC_CODE_ROM_DIR, leaving the KV calendar and non-code ROMs unchanged. It is not a token pass.
"""
import argparse
import hashlib
import json
import subprocess
import struct
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--union', type=Path, required=True)
    parser.add_argument('--code-rank', type=Path, required=True)
    parser.add_argument('--macro-code', type=Path, required=True)
    parser.add_argument('--macro-kv', type=Path, required=True)
    parser.add_argument('--romleaf', type=Path, required=True)
    parser.add_argument('--logic', type=Path, required=True)
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
    source_expected = (args.code_rank / 'expected/qtile_t0_b0.hex').resolve(strict=True)
    expected_code = args.out / 'expected_bf16.hex'
    expanded = []
    for line in source_expected.read_text().splitlines():
        value = int(line, 16); output = 0
        for element in range(64):
            byte = (value >> (8*element)) & 255
            signed = byte if byte < 128 else byte-256
            bf16 = int.from_bytes(struct.pack('>f', float(signed))[:2], 'big')
            output |= bf16 << (16*element)
        expanded.append(f'{output:0256x}\n')
    expected_code.write_text(''.join(expanded))
    tb = f'''`timescale 1ps/1ps
module qtile_probe #(parameter integer ROM_TILE=-1)(input wire ck,rst_n,input wire [11:0] addr,output wire[1023:0] q);
generate for(genvar c=0;c<2;c=c+1) begin:g_code
 ot_qwen_tile_romleaf #(.ROM_TILE(ROM_TILE),.ROM_BANK(0),.ROM_COL(c)) u_leaf
 (.clk(ck),.rst_n(rst_n),.ce_d(1'b1),.any_d(1'b1),.ad_d(addr),.r_q(q[512*c+:512]));
end endgenerate
endmodule
module tb_qckvrom;
reg ck=0; always begin #416 ck=1; #417 ck=0; end
reg rst_n=0; reg [11:0] addr=0;
wire [31:0] kv; wire [1023:0] q; wire[265:0] foreign_zero;
ot_rom_64x32_m2 #(.VIAMAP({json.dumps(str(kv))}),.INSTANCE("kv_dcal")) u_kv (.clk(ck),.ce_in(1'b1),.addr_in(addr[5:0]),.rd_out(kv));
qtile_probe u_tile (.ck(ck),.rst_n(rst_n),.addr(addr),.q(q));
defparam u_tile.ROM_TILE=0;
// Existing unprogrammed non-code model stays untouched by the QC code namespace.
ot_rom_4096x266_m8 #(.INSTANCE("calendar_m0")) u_foreign (.clk(ck),.ce_in(1'b1),.addr_in(addr),.rd_out(foreign_zero));
reg [31:0] expected_kv[0:63]; reg [1023:0] expected_code[0:4095]; integer a;
initial begin
 $readmemh({json.dumps(str(expected_kv))},expected_kv);
 $readmemh({json.dumps(str(expected_code))},expected_code);
 #1;
 if ($test$plusargs("MUT_ROM")) u_tile.g_code[0].u_leaf.u_rom.arr[0][0]=~u_tile.g_code[0].u_leaf.u_rom.arr[0][0];
 if ($test$plusargs("MUT_KV")) u_kv.arr[0][0]=~u_kv.arr[0][0];
 repeat(3) @(negedge ck); rst_n=1;
 for(a=0;a<64;a=a+1) begin
  addr=12'(a); repeat(12) @(negedge ck);
  if(kv!==expected_kv[a] || q!==expected_code[a] || foreign_zero!==266'd0)
   $fatal(1,"ROM_LOAD_MISMATCH addr=%0d kv=%h expected=%h",a,kv,expected_kv[a]);
 end
 $display("CODE_KV_ROM_LOAD_PASS128codewords4096BF16values64KVwords"); $finish;
end
endmodule
'''
    top = args.out / 'tb_qckvrom.sv'; top.write_text(tb)
    command = [args.verilator, '--binary', '--timing', '-j', '2', '-Wno-fatal',
               '-Wno-TIMESCALEMOD', '--top-module', 'tb_qckvrom', '--Mdir', str(args.out/'obj'),
               str(top), str(args.macro_code), str(args.macro_kv), str(args.romleaf), str(args.logic)]
    with (args.out/'build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    results = {}
    for name, extra in [('nominal', []), ('code_mutant', ['+MUT_ROM']), ('kv_mutant', ['+MUT_KV']), ('namespace_missing', [])]:
        with (args.out/f'{name}.log').open('w') as log:
            namespace = [] if name == 'namespace_missing' else [f'+OT_QC_CODE_ROM_DIR={args.union}']
            run = subprocess.run([str(args.out/'obj/Vtb_qckvrom'), *namespace, *extra], stdout=log, stderr=subprocess.STDOUT)
        text = (args.out/f'{name}.log').read_text()
        if name == 'nominal':
            passed = run.returncode == 0 and 'CODE_KV_ROM_LOAD_PASS' in text
        elif name == 'namespace_missing':
            passed = run.returncode != 0 and 'bound ROMleaf requires' in text
        else:
            passed = run.returncode != 0 and 'ROM_LOAD_MISMATCH' in text
        results[name] = dict(returncode=run.returncode, passed=passed)
    receipt = dict(clock_period_ps=833, results=results, kv_sha256=sha(kv),
                   code_sha256=[sha(path) for path in columns], rank=record['rank'],
                   scope='Two actual generated-array QC ROMleafs and KV calendar,128codewords/4096BF16values64calendarwords; namespace isolation and missing-directory control; no token or programme qualification.')
    (args.out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, sort_keys=True))
    if not all(row['passed'] for row in results.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
