#!/usr/bin/env python3
"""Pinned Yosys resolver + async-flop dfflibmap repro (TOKc-YOSYS 2026-10-22).

Why: /usr/bin/yosys 0.52 (every fleet host in 10-2026) dfflibmap maps the only ASAP7 async flop,
DFFASRHQNx1 (liberty `ff (IQN,IQNN)`, next_state "!D", clear "!SETN", preset "!RESETN", QN = IQN), with
SET and CLEAR swapped: every async-reset flop resets to the INVERTED value.  HBMc k5 native lockstep failed
5/48 with it and passes 48/48 with Yosys 0.68 (finding HBMc 11:34, commit a83752122).  The ORFS docker image
(openroad/orfs:asap7lock == :latest) synthesises with /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
(0.68+post) and is not affected; `--repro` below shows which binaries swap.

Use from Python:   from yosys_pin import pinned_yosys;  Y = pinned_yosys()   (raises YosysPinError)
Use from a shell:  Y=$(python3 tools/yosys_pin.py) || exit 2      or  source tools/yosys_pin.sh
Override:          OT_YOSYS=<binary> (or YOSYS=<binary>); the override must itself be >= 0.68 or the call fails.
Repro:             python3 tools/yosys_pin.py --repro /usr/bin/yosys [--liberty <ASAP7 SEQ RVT TT lib>]
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MIN_VERSION = (0, 68)
PINNED = Path(os.environ.get('OPENTALLAS_TOOLS_ROOT', Path.home() / '.local/opentallas-tools')) / 'yosys-0.68/bin/yosys'
ENV_KEYS = ('OT_YOSYS', 'YOSYS')
SEQ_LIB = 'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib'
LIB_CANDIDATES = (Path.home() / '.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM' / SEQ_LIB,
                  Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM') / SEQ_LIB)
WHY = ('Yosys < 0.68 dfflibmap maps ASAP7 DFFASRHQNx1 with set/clear swapped (async-reset flops reset to the '
       'inverted value; HBMc k5 native lockstep 5/48). Use %s (every fleet host has it) or the ORFS docker yosys.' % PINNED)


class YosysPinError(RuntimeError):
    pass


def parse_version(text):
    m = re.search(r'Yosys (\d+)\.(\d+)', text or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def version(binary):
    try:
        out = subprocess.run([str(binary), '-V'], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise YosysPinError('cannot run %s -V: %s' % (binary, exc))
    v = parse_version(out)
    if v is None:
        raise YosysPinError('cannot parse the version of %s: %r' % (binary, out.strip()))
    return v


def check(binary):
    """Fail closed unless `binary` runs and is >= MIN_VERSION. Returns str(binary)."""
    if not binary or not (Path(binary).exists() or shutil.which(str(binary))):
        raise YosysPinError('yosys %r not found. %s' % (binary, WHY))
    v = version(binary)
    if v < MIN_VERSION:
        raise YosysPinError('%s is Yosys %d.%d, need >= %d.%d. %s' % ((binary,) + v + MIN_VERSION + (WHY,)))
    return str(binary)


def pinned_yosys(env=os.environ):
    """The Yosys every dfflibmap / native-netlist / lockstep helper must use (override must also pass)."""
    for key in ENV_KEYS:
        if env.get(key):
            return check(env[key])
    return check(PINNED)


# ---------------------------------------------------------------------------------------------- repro
REPRO_RTL = r'''
module ot_async_flop_repro(input clk, input rst_n, input d, output reg q0, output reg q1);
  always @(posedge clk or negedge rst_n) if (!rst_n) q0 <= 1'b0; else q0 <= d;  // async reset to 0
  always @(posedge clk or negedge rst_n) if (!rst_n) q1 <= 1'b1; else q1 <= d;  // async reset to 1
endmodule
'''
# Behaviour written straight from the liberty ff group (checked in liberty_ff_ok): IQN cleared by !SETN,
# preset by !RESETN, next_state !D, QN = IQN; clear_preset_var1 L (both asserted -> IQN 0).
CELL_MODEL = r'''
module DFFASRHQNx1_ASAP7_75t_R(output reg QN, input CLK, input D, input RESETN, input SETN);
  always @(posedge CLK or negedge RESETN or negedge SETN)
    if (!SETN) QN <= 1'b0; else if (!RESETN) QN <= 1'b1; else QN <= ~D;
endmodule
'''
BENCH = r'''
module tb;
  reg clk = 0, rst_n = 1, d = 0; wire q0, q1;
  ot_async_flop_repro dut(.clk(clk), .rst_n(rst_n), .d(d), .q0(q0), .q1(q1));
  initial begin
    #1 d = 1; #1 clk = 1; #1 clk = 0;           // load 1 into both
    #1 rst_n = 0; #1;                           // async reset, no clock edge
    $display("RESET q0=%b q1=%b", q0, q1);
    #1 d = 0; #1 clk = 1; #1 clk = 0; #1;       // clock while held in reset
    $display("HELD q0=%b q1=%b", q0, q1);
    #1 rst_n = 1; d = 1; #1 clk = 1; #1 clk = 0; #1;
    $display("RUN q0=%b q1=%b", q0, q1);
    $finish;
  end
endmodule
'''
EXPECT = {'RESET': '01', 'HELD': '01', 'RUN': '11'}


def find_liberty():
    for p in LIB_CANDIDATES:
        if p.exists():
            return p
    raise YosysPinError('ASAP7 %s not found (pass --liberty)' % SEQ_LIB)


def liberty_ff_ok(liberty):
    text = Path(liberty).read_text(errors='replace')
    i = text.find('cell (DFFASRHQNx1_ASAP7_75t_R)')
    j = text.find('cell (', i + 10)
    cell = re.sub(r'\s+', ' ', text[i:j if j > 0 else None])
    return i >= 0 and all(s in cell for s in ('ff (IQN,IQNN)', 'clear : "!SETN"', 'preset : "!RESETN"',
                                              'next_state : "!D"', 'function : "IQN"'))


def map_ys(rtl, liberty, mapped):
    return ('read_verilog %s; synth -top ot_async_flop_repro -noabc; dfflibmap -liberty %s; opt_clean; '
            'write_verilog -noattr %s' % (rtl, liberty, mapped))


def simulate(mapped_text, iverilog='iverilog', vvp='vvp'):
    """Simulate a mapped REPRO_RTL netlist against the liberty-derived DFFASRHQNx1 model."""
    with tempfile.TemporaryDirectory(prefix='yosys_pin_sim_') as tmp:
        w = Path(tmp)
        (w / 'mapped.v').write_text(mapped_text)
        (w / 'cell.v').write_text(CELL_MODEL)
        (w / 'tb.v').write_text(BENCH)
        try:
            r = subprocess.run([iverilog, '-o', str(w / 'sim'), str(w / 'tb.v'), str(w / 'mapped.v'), str(w / 'cell.v')],
                               capture_output=True, text=True)
            if r.returncode:
                raise YosysPinError('iverilog failed: %s' % r.stderr[-800:])
            out = subprocess.run([vvp, '-n', str(w / 'sim')], capture_output=True, text=True).stdout
        except OSError as exc:
            raise YosysPinError('cannot simulate (iverilog/vvp): %s' % exc)
    got = {m.group(1): m.group(2) + m.group(3) for m in re.finditer(r'(\w+) q0=(\S) q1=(\S)', out)}
    return {'async_cells': len(re.findall(r'\bDFFASRHQNx1_ASAP7_75t_R\b', mapped_text)), 'got': got, 'expect': EXPECT,
            'ok': got == EXPECT, 'swapped': got.get('RESET') == '10' and got.get('HELD') == '10'}


def repro(yosys, liberty=None, iverilog='iverilog', vvp='vvp'):
    """Map REPRO_RTL with `yosys` dfflibmap on the ASAP7 SEQ lib and simulate it. Returns a dict;
    ok=True means both async reset values are correct, swapped=True means the <0.68 bug."""
    liberty = Path(liberty or find_liberty())
    if not liberty_ff_ok(liberty):
        raise YosysPinError('%s: DFFASRHQNx1 ff group differs from the model this repro assumes' % liberty)
    with tempfile.TemporaryDirectory(prefix='yosys_pin_') as tmp:
        w = Path(tmp)
        (w / 'rtl.v').write_text(REPRO_RTL)
        r = subprocess.run([str(yosys), '-q', '-p', map_ys(w / 'rtl.v', liberty, w / 'mapped.v')],
                           capture_output=True, text=True, timeout=600)
        if r.returncode:
            raise YosysPinError('%s synth failed: %s' % (yosys, (r.stderr or r.stdout)[-800:]))
        res = simulate((w / 'mapped.v').read_text(), iverilog, vvp)
    res.update(yosys=str(yosys), version='%d.%d' % version(yosys))
    return res


def report(r):
    return '%-60s %-5s cells=%d got=%s -> %s' % (r.get('yosys', '?'), r.get('version', '?'), r['async_cells'], r['got'],
                                                  'OK' if r['ok'] else 'SWAPPED set/clear' if r['swapped'] else 'WRONG')


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', metavar='BIN', help='fail (rc 2) unless BIN is >= 0.68')
    ap.add_argument('--repro', metavar='BIN', nargs='+', help='run the async-flop dfflibmap repro on each BIN')
    ap.add_argument('--liberty')
    ap.add_argument('--emit', metavar='DIR', help='write rtl.v + map.ys (yosys -s DIR/map.ys -> DIR/mapped.v) for a host without iverilog')
    ap.add_argument('--mapped', metavar='V', nargs='+', help='simulate netlists produced from --emit')
    a = ap.parse_args(argv)
    try:
        if a.emit:
            d = Path(a.emit); d.mkdir(parents=True, exist_ok=True); (d / 'rtl.v').write_text(REPRO_RTL)
            (d / 'map.ys').write_text(map_ys(d / 'rtl.v', a.liberty or find_liberty(), d / 'mapped.v').replace('; ', '\n') + '\n')
            return 0
        if a.repro or a.mapped:
            rs = [repro(b, a.liberty) for b in a.repro or []]
            rs += [dict(simulate(Path(m).read_text()), yosys=m, version='?') for m in a.mapped or []]
            for r in rs:
                print(report(r))
            return 1 if any(not r['ok'] for r in rs) else 0
        print(check(a.check) if a.check else pinned_yosys())
        return 0
    except YosysPinError as exc:
        print('yosys_pin: %s' % exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
