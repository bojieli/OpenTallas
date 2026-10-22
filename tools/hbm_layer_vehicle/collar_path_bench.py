#!/usr/bin/env python3
"""HBMc/TOKEN2 (10-22): directed GEN-die bench for the host->collar->programme-store paths and the client fault returns.

Proves on a GEN die netlist (gen_die_func.py output; relays and landing stations inside the cut) that
  (a) each collar's programme-row writes (pw_we/pw_addr/pw_data) reach the consumer pins:
      col_su  -> su_prog.cfg_we/cfg_data,  col_idx -> hb_idx__ctl / hb_idx__qctl_<q> program_we/program_data;
      self-check: exactly N write strobes arrive at every consumer and each carries the frame's data word;
  (b) each client fault reaches its collar: su_prog.fault -> col_su.c_fault, sfucore_<q>.fault -> col_sfu_<q>.c_fault
      (the collar fault output must rise after the client fault is driven, and must be 0 before).
The consumers stay OUTSIDE the cut: the bench samples the exact consumer pin expressions of the die netlist.
Collar cfg inputs are forced at the collar (the host ingress is not under test here).

  collar_path_bench.py --die die_func.v --contract C.json --out DIR    -> DIR/{slice/,tb_collar.sv,expect.json}
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

T = Path(__file__).resolve().parent
CONS = [('su_prog', 'cfg_we', 'cfg_data', 'col_su', 'clk')] + \
       [('hb_idx__ctl', 'program_we', 'program_data', 'col_idx', 'clk')] + \
       [(f'hb_idx__qctl_{q}', 'program_we', 'program_data', 'col_idx', 'clk_program') for q in ('SW', 'SE', 'NW', 'NE')]
FAULTS = [('su_prog', 'col_su')] + [(f'sfucore_{q}', f'col_sfu_{q}') for q in ('SW', 'SE', 'NW', 'NE')]
NFRAMES = 4


def conn(text, inst, port):
    m = re.search(r"\n  \w+(?: #\(.*?\))? " + re.escape(inst) + r" \(\n(.*?)\n  \);", text, re.S)
    if not m:
        sys.exit(f'collar_path_bench: instance {inst} not in die')
    for ln in m.group(1).split('\n'):
        c = re.match(r"\s*\." + re.escape(port) + r"\((.*)\),?\s*$", ln)
        if c:
            return c.group(1)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', required=True); ap.add_argument('--contract', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    text = Path(a.die).read_text()
    c = json.load(open(a.contract)); I = c['instances']
    tgt = {s['inst']: s['value'] for s in c['straps'] if s['port'] == 'tgt'}
    collars = ['col_su', 'col_idx'] + [f'col_sfu_{q}' for q in ('SW', 'SE', 'NW', 'NE')]
    r = subprocess.run([sys.executable, str(T / 'cut_slice.py'), '--die', a.die, '--contract', a.contract,
                        '--include', '^(' + '|'.join(collars) + '|hb_ckgen)$', '--with-relays', r'^(l12p_|rf\d+_)',
                        '--relays-out', '--out', str(out / 'slice')], capture_output=True, text=True)
    (out / 'cut.log').write_text(r.stdout + r.stderr)
    if r.returncode:
        sys.exit(f'collar_path_bench: cut failed: {r.stderr[-400:]}')
    b = json.load(open(out / 'slice' / 'boundary.json'))
    inputs = {x['name']: x['width'] for x in b['inputs']}
    S = set(b['instances'])
    # constants like 1'd0 keep their form; nets become hierarchical refs into the slice
    def hier(e):
        e = re.sub(r"(\d+)'([bdh])([0-9a-fA-F_]+)", lambda m: f"{m.group(1)}'{m.group(2)}{m.group(3)}".replace("'", "\x00"), e)
        e = re.sub(r"\b([A-Za-z_]\w*)\b", lambda m: f'u.{m.group(1)}', e)
        return e.replace('\x00', "'")
    expect = dict(frames=NFRAMES, consumers=[], faults=[])
    L = ['`timescale 1ns/1ps', 'module tb_collar;', '  reg refclk = 1\'b0, por_n = 1\'b0;', '  always #5 refclk = ~refclk;']
    for n, w in inputs.items():
        if n not in ('hb_ckgen__refclk', 'hb_ckgen__por_n'):
            L.append(f'  reg [{w - 1}:0] {n} = 0;')
    L.append(f"  {b['slice_top']} u (" + ', '.join(
        f'.{n}({"refclk" if n == "hb_ckgen__refclk" else "por_n" if n == "hb_ckgen__por_n" else n})' for n in inputs) + ');')
    L.append('  reg [255:0] D [0:%d];' % (NFRAMES - 1))
    L.append('  integer errors = 0;'); L.append('  reg arm = 0;  // count consumer strobes only once reset has settled')
    for k, (inst, we, data, col, ck) in enumerate(CONS):
        ew, ed, ec = conn(text, inst, we), conn(text, inst, data), conn(text, inst, ck)
        ok = ew is not None and ed is not None and ec is not None
        expect['consumers'].append(dict(consumer=inst, clock=ec, we=ew, data=(ed or '')[:200], collar=col, sampled=ok))
        if not ok:
            L.append(f'  initial begin #1; $display("COLLAR_CHECK FAIL {inst}.{we} not connected on the die"); errors = errors + 1; end')
            continue
        L += [f'  integer n{k} = 0, bad{k} = 0;',
              f'  wire w{k} = {hier(ew)};', f'  wire [255:0] d{k} = {hier(ed)};',
              f'  wire c{k} = {hier(ec or "")};',
              f'  always @(posedge c{k}) if (arm && w{k}) begin if (n{k} < {NFRAMES} && d{k} !== D[n{k}]) bad{k} = bad{k} + 1; n{k} = n{k} + 1; end']
    for k, (src, col) in enumerate(FAULTS):
        port = f'{src}__fault'
        expect['faults'].append(dict(source=src, collar=col, boundary_input=port if port in inputs else None))
    # cfg drive: force collar inputs on their clk_in (ingress landing clock)
    seq = []
    for col, label in (('col_su', 'su'), ('col_idx', 'idx')):
        seq += [f'    // {col}: {NFRAMES} sequential programme rows (L = 0..{NFRAMES - 1}) to target {tgt[col]}']
        for f in range(NFRAMES):
            seq += [f'    @(negedge u.{col}.clk_in); force u.{col}.cfg_v = 1\'b1; force u.{col}.cfg_target = 8\'d{tgt[col]}; '
                    f'force u.{col}.cfg_addr = 12\'d{f}; force u.{col}.cfg_data = D[{f}];',
                    f'    @(negedge u.{col}.clk_in); force u.{col}.cfg_v = 1\'b0;',
                    f'    repeat (3) @(negedge u.{col}.clk_in);']
        seq += [f'    release u.{col}.cfg_v; force u.{col}.cfg_v = 1\'b0;']
    L += ['  initial begin : RUN', '    integer f;',
          f'    for (f = 0; f < {NFRAMES}; f = f + 1) D[f] = {{8{{$urandom}}}};',
          '    force u.col_su.cfg_v = 0; force u.col_idx.cfg_v = 0;',
          '    #100 por_n = 1\'b1;', '    #20000; arm = 1;'] + seq + ['    #20000;']
    # fault phase: collar fault must be 0 now, then rise after the client fault input is driven
    for k, fe in enumerate(expect['faults']):
        col = fe['collar']
        if fe['boundary_input'] is None:
            L.append(f'    $display("COLLAR_CHECK FAIL fault {fe["source"]}.fault -> {col}.c_fault not connected on the die"); errors = errors + 1;')
            continue
        L += [f'    if (u.{col}.fault !== 1\'b0) begin $display("COLLAR_CHECK FAIL {col}.fault high before client fault"); errors = errors + 1; end',
              f'    {fe["boundary_input"]} = 1\'b1; #2000;',
              f'    if (u.{col}.fault !== 1\'b1) begin $display("COLLAR_CHECK FAIL {fe["source"]}.fault did not reach {col}.c_fault"); errors = errors + 1; end',
              f'    else $display("COLLAR_CHECK PASS fault {fe["source"]} -> {col}");']
    for k, ce in enumerate(expect['consumers']):
        if not ce['sampled']:
            continue
        L += [f'    if (n{k} != {NFRAMES} || bad{k} != 0) begin $display("COLLAR_CHECK FAIL {ce["consumer"]} write strobes %0d (want {NFRAMES}) data mismatches %0d", n{k}, bad{k}); errors = errors + 1; end',
              f'    else $display("COLLAR_CHECK PASS {ce["consumer"]} {NFRAMES} writes, data exact");']
    L += ['    if (errors == 0) $display("COLLAR_BENCH PASS"); else $display("COLLAR_BENCH FAIL errors=%0d", errors);',
          '    $finish;', '  end', 'endmodule']
    (out / 'tb_collar.sv').write_text('\n'.join(L) + '\n')
    (out / 'expect.json').write_text(json.dumps(expect, indent=1) + '\n')
    print(f"COLLAR_BENCH_GEN slice={len(S)} inst consumers={sum(x['sampled'] for x in expect['consumers'])}/{len(CONS)} "
          f"faults_connected={sum(x['boundary_input'] is not None for x in expect['faults'])}/{len(FAULTS)} -> {out}")


if __name__ == '__main__':
    main()
