#!/usr/bin/env python3
"""HBM-BIND-4: lockstep proof of stock Yosys memory_map on the 8 actual SU g_inj.slot arrays.

For each actual module the island holds exactly its original $memwr_v2/$memrd cells and memory
record with their actual connections (repeated nets stay one input, constants stay literal).
Reference = memory_collect only (array semantics); DUT = memory_collect+memory_map; mutant =
DUT built from the island with the write-address bits swapped. iverilog random lockstep with
warm-up writes compares every known reference bit each cycle; the mutant must be CAUGHT.
"""
import json, sys, subprocess, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools' / 'die_plan'))
import bind_elab as E

def island(mod, swap_addr=False):
    cells = {n: c for n, c in mod['cells'].items() if c['type'] in ('$memwr_v2', '$memrd')}
    wr = next(c for c in cells.values() if c['type'] == '$memwr_v2')
    rd = next(c for c in cells.values() if c['type'] == '$memrd')
    clk = wr['connections']['CLK']
    assert len(clk) == 1 and not isinstance(clk[0], str)
    ins, seen = [], set()
    for c in (wr, rd):
        for p, bits in sorted(c['connections'].items()):
            if c['port_directions'][p] != 'input' or p == 'CLK' and c is wr:
                continue
            for b in bits:
                if not isinstance(b, str) and b not in seen and b != clk[0]:
                    seen.add(b); ins.append(b)
    out = rd['connections']['DATA']
    assert not (set(out) & seen)
    cells = json.loads(json.dumps(cells))
    if swap_addr:
        w = next(c for c in cells.values() if c['type'] == '$memwr_v2')
        w['connections']['ADDR'] = list(reversed(w['connections']['ADDR']))
    m = {'attributes': {}, 'ports': {'clk': {'direction': 'input', 'bits': clk},
                                     'x': {'direction': 'input', 'bits': ins},
                                     'y': {'direction': 'output', 'bits': out}},
         'cells': cells, 'memories': mod['memories'], 'netnames': {}}
    roles = {'wa': [ins.index(b) for b in wr['connections']['ADDR'] if b in seen],
             'en': sorted({ins.index(b) for b in wr['connections']['EN'] if b in seen}),
             'ra': [ins.index(b) for b in rd['connections']['ADDR'] if b in seen]}
    return m, len(ins), len(out), roles

TB = r'''
module tb;
  reg clk = 0; reg [{NI}-1:0] x; wire [{NO}-1:0] yr, yd;
  ref_m r(.clk(clk), .x(x), .y(yr)); dut_m d(.clk(clk), .x(x), .y(yd));
  integer cyc, k, bad, known, checks; reg [31:0] s;
  initial begin
    bad = 0; known = 0; checks = 0; s = {SEED};
    for (cyc = 0; cyc < {N}; cyc = cyc + 1) begin
      for (k = 0; k < {NI}; k = k + 1) begin s = s * 1103515245 + 12345; x[k] = s[16]; end
      if (cyc < 8) begin {WARM} end
      #1;
      for (k = 0; k < {NO}; k = k + 1) if (yr[k] === 1'b0 || yr[k] === 1'b1) begin
        known = known + 1; if (yd[k] !== yr[k]) bad = bad + 1; end
      checks = checks + 1;
      #4 clk = 1; #1;
      for (k = 0; k < {NO}; k = k + 1) if (yr[k] === 1'b0 || yr[k] === 1'b1) begin
        known = known + 1; if (yd[k] !== yr[k]) bad = bad + 1; end
      #4 clk = 0;
    end
    $display("RESULT checks=%0d known_bits=%0d mismatches=%0d", checks, known, bad);
    $finish;
  end
endmodule
'''

def yosys(ys, log):
    E.run_yosys(ys, log, [ys.parent], mem_gb=4)

def main():
    src, outd = Path(sys.argv[1]), Path(sys.argv[2])
    outd.mkdir(parents=True, exist_ok=True)
    d = json.loads(src.read_text())
    mods = sorted(mn for mn, m in d['modules'].items()
                  if any(c['type'] == '$memwr_v2' for c in m.get('cells', {}).values()))
    assert len(mods) == 8, mods
    res = []
    for i, mn in enumerate(mods):
        rows = {}
        for tag, swap in (('ref', False), ('dut', False), ('mut', True)):
            m, ni, no, roles = island(d['modules'][mn], swap)
            j = outd / f'm{i}_{tag}.json'
            j.write_text(json.dumps({'modules': {f'{tag}_m': m}}))
            mm = '' if tag == 'ref' else 'memory_map\n'
            ys = outd / f'm{i}_{tag}.ys'
            ys.write_text(f'read_json "{j}"\nmemory_collect\n{mm}write_verilog -noattr "{outd}/m{i}_{tag}.v"\n')
            yosys(ys, outd / f'm{i}_{tag}.log')
        warm = ' '.join([f'x[{e}] = 1;' for e in roles['en']] +
                        [f'x[{b}] = (cyc >> {k}) & 1;' for k, b in enumerate(roles['wa'])])
        for tag in ('dut', 'mut'):
            tb = outd / f'm{i}_tb_{tag}.v'
            tb.write_text(TB.replace('{NI}', str(ni)).replace('{NO}', str(no)).replace('{N}', '4000')
                          .replace('{SEED}', str(1000 + i)).replace('{WARM}', warm))
            dutv = (outd / f'm{i}_{tag}.v').read_text().replace(f'module {tag}_m', 'module dut_m')
            (outd / f'm{i}_{tag}_as_dut.v').write_text(dutv)
            exe = outd / f'm{i}_{tag}.vvp'
            subprocess.run(['iverilog', '-g2012', '-o', str(exe), str(tb), str(outd / f'm{i}_ref.v'),
                            str(outd / f'm{i}_{tag}_as_dut.v')], check=True)
            r = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True, check=True).stdout
            line = [l for l in r.splitlines() if l.startswith('RESULT')][0]
            kv = dict(t.split('=') for t in line.split()[1:])
            rows[tag] = {k: int(v) for k, v in kv.items()}
        ok = rows['dut']['mismatches'] == 0 and rows['dut']['known_bits'] > 0 and rows['mut']['mismatches'] > 0
        res.append(dict(module=mn, inputs=ni, outputs=no, en_unique=len(roles['en']), lockstep=rows['dut'],
                        mutant_swapped_write_addr=rows['mut'], verdict='PASS' if ok else 'FAIL'))
        print(mn[-60:], res[-1]['verdict'], rows)
    v = 'PASS' if all(r['verdict'] == 'PASS' for r in res) else 'FAIL'
    rec = dict(schema='hbm.bind4.memory_map_lockstep.v1', verdict=v, source=str(src), cycles_per_module=4000,
               reference='memory_collect (array)', dut='memory_collect+memory_map (stock Yosys)',
               mutant='write ADDR bits swapped before memory_map, must be CAUGHT', modules=res)
    (outd / 'receipt.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('VERDICT', v)
    sys.exit(0 if v == 'PASS' else 1)

if __name__ == '__main__':
    main()
