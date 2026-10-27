"""QC-CORES-1: formal reset-release equivalence of every grouped SU lane tap vs the type's five-leaf leaf tap.
Extracts the generated wavefront relay tree from each bound type frame, builds a miter (leaf tap == lane tap for
every bound group) and proves it with yosys sat -tempinduct from an arbitrary state after DEPTH cycles.
MUTANT: re-drive one lane tap from depth-3 (one relay short) -> must FAIL."""
import json, re, subprocess, sys, pathlib
D = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
rep = json.load(open(D/'bind_reset.json')) if (D/'bind_reset.json').exists() else None
CELLS = """module ot_dp_rrelay (input wire clk, input wire d, output reg q); always @(posedge clk) q <= d; endmodule
module ot_dp_rgate (input wire clk, input wire d, input wire run, output reg q); always @(posedge clk) q <= d & run; endmodule
"""
res = {}
for g in sorted((D/'rtl').glob('*.bound_groups.json')):
    tn = g.name[:-len('.bound_groups.json')]
    groups = json.load(open(g))['groups']
    src = (D/'rtl'/(tn+'.sv')).read_text()
    rel = [l for l in src.splitlines() if re.match(r'\s*ot_dp_r(relay|gate) u_(rrl|srl|rst_in|run_in)', l)]
    m = re.search(r'wire rst_n = (rst_n_t\d+);', src); leaf = m[1]
    lanes = [x['reset_net'] for x in groups]
    # every instance of a lane group in the frame must be driven by its recorded net
    for x in groups:
        assert re.search(rf'\b{x["module"]} {x["inst"]} \(\.clk\(clk\), \.rst_n\({x["reset_net"]}\)', src), (tn, x)
    nets = sorted({w for l in rel for w in re.findall(r'\.q\((\w+)\)', l)})
    def miter(mut):
        body = list(rel)
        if mut:   # lane tap 0 one relay short: its gate takes the depth-1 root pins instead of its depth-3 parents
            t = lanes[0]
            body = [re.sub(r'\.d\(\w+\), \.run\(\w+\)', '.d(rst_root_n), .run(run_root)', l) if f'.q({t})' in l else l for l in body]
        eqs = ' & '.join(f'({leaf} == {t})' for t in lanes)
        return (CELLS + 'module miter(input wire clk, input wire arst_n, input wire start_i, output wire eq);\n' +
                ''.join(f'    wire {n};\n' for n in nets) + '\n'.join(body) + f'\n    assign eq = {eqs};\nendmodule\n')
    r = {}
    for mut in (0, 1):
        f = out/f'{tn}.m{mut}.v'; f.write_text(miter(mut))
        ys = f'read_verilog {f}; hierarchy -top miter; proc; flatten; opt_clean; sat -tempinduct -prove eq 1 -seq 5 -maxsteps 40 -verify-no-timeout'
        p = subprocess.run(['yosys', '-q', '-p', ys], capture_output=True, text=True)
        r['proof' if not mut else 'mutant'] = 'PASS' if p.returncode == 0 else 'FAIL'
    r.update(leaf=leaf, lanes=lanes, relays=len(rel))
    res[tn] = r
    print(tn, r, flush=True)
json.dump(res, open(out/'rst_eq.json', 'w'), indent=1)
ok = all(v['proof'] == 'PASS' and v['mutant'] == 'FAIL' for v in res.values())
print('RST_EQ', 'PASS' if ok else 'FAIL', len(res), 'types', sum(len(v['lanes']) for v in res.values()), 'lane taps')
