#!/usr/bin/env python3
"""QC-TYPES-10/FWS bench: the START/reset cone of every sle_fw_v3 FSTART face, cut from the actual strict-bind RTL,
new (v4x_fws) vs old (v4w), with iverilog on the real cells.

Contract checked, cycle by cycle, under random rst_root_n and random START (cland_rstart_in):
  * cws0_o, x_st_a_fe_o: new face == old (W=0) face fed with START delayed 3 edges (writer K +3, 0 payload cycles)
  * the other 14 faces:   new face == old face (the same-depth local reset leaf moves no edge)
Mutants that must be caught: S stage bypass, S stage reset one phase too shallow, S stage reset one phase too deep,
S face leaf one depth short, W/N face leaf one depth deep."""
import argparse, random, re, subprocess
from pathlib import Path

CELL = re.compile(r'\b(ot_dp_landing_relay|ot_dp_rrelay|ot_dp_rgate)\s+(\w+)\s*\((.*?)\);', re.S)
S = ('cws0_o', 'x_st_a_fe_o')


def cone(text, name):
    drivers, alias = {}, dict(re.findall(r'\bassign\s+(\w+)\s*=\s*(\w+)\s*;', text))
    for m in CELL.finditer(text):
        pins = dict(re.findall(r'\.(\w+)\(\s*(\w+)\s*\)', m.group(3)))
        if pins['q'] in drivers:
            raise SystemExit(f'{name}: two drivers of {pins["q"]}')
        drivers[pins['q']] = (m.group(1), m.group(2), pins)
    faces = sorted(n for n in set(re.findall(r'\bcland_fstart_out_(\w+)\b', text))
                   if f'q(cland_fstart_out_{n})' in text.replace(' ', ''))
    keep, todo, wires, assigns = {}, [f'cland_fstart_out_{b}' for b in faces], set(), {}
    while todo:
        n = todo.pop()
        if n in ('rst_root_n', 'cland_rstart_in', 'clk') or n in wires:
            continue
        wires.add(n)
        if n in drivers:
            kind, inst, pins = drivers[n]
            if kind == 'ot_dp_rgate':
                raise SystemExit(f'{name}: gated relay {inst} in a START cone')
            keep[inst] = (kind, pins)
            todo += [v for k, v in pins.items() if k not in ('q', 'clk')]
        elif n in alias:
            assigns[n] = alias[n]; todo.append(alias[n])
        else:
            raise SystemExit(f'{name}: {n} has no driver in the bound module')
    body = [f'module {name}(input clk, input rst_root_n, input cland_rstart_in, output [{len(faces)-1}:0] f);']
    body += [f'  wire {w};' for w in sorted(wires)]
    body += [f'  assign {a} = {b};' for a, b in sorted(assigns.items())]
    for inst, (kind, pins) in sorted(keep.items()):
        body.append(f'  {kind} {inst} (' + ', '.join(f'.{k}({v})' for k, v in pins.items()) + ');')
    body += [f'  assign f[{i}] = cland_fstart_out_{b};' for i, b in enumerate(faces)]
    body.append('endmodule')
    return '\n'.join(body) + '\n', faces, keep


def tb(faces, cycles, seed):
    sidx = [faces.index(b) for b in S]
    oth = [i for i in range(len(faces)) if i not in sidx]
    n = len(faces)
    return f'''module tb;
 reg clk=0; always #5 clk=~clk;
 reg r=0, s=0, s1=0, s2=0, s3=0; integer cyc=0, chk=0, seed={seed};
 wire [{n-1}:0] fn, fo0, fo3;
 cone_new dn(clk, r, s, fn);
 cone_old do0(clk, r, s, fo0);
 cone_old do3(clk, r, s3, fo3);
 always @(posedge clk) begin s1<=s; s2<=s1; s3<=s2; end
 always @(negedge clk) begin
  cyc=cyc+1;
  if (cyc < 40) begin r = 0; s = 0; end
  else begin r = ({{$random(seed)}} % 100) > (cyc % 997 < 500 ? 3 : 25); s = ({{$random(seed)}} % 100) > 45; end
  if (cyc > 60) begin
   {''.join(f'if (fn[{i}] !== fo3[{i}]) $fatal(1, "S face {faces[i]} mismatch cycle %0d new %b old+3 %b", cyc, fn[{i}], fo3[{i}]); ' for i in sidx)}
   {''.join(f'if (fn[{i}] !== fo0[{i}]) $fatal(1, "face {faces[i]} mismatch cycle %0d", cyc); ' for i in oth)}
   chk = chk + 1;
  end
  if (cyc == {cycles}) begin $display("PASS %0d cycles, %0d faces", chk, {n}); $finish; end
 end
endmodule
'''


def run(work, tag, files, expect):
    exe = work / tag
    p = subprocess.run(['iverilog', '-g2012', '-s', 'tb', '-o', str(exe), *map(str, files)], capture_output=True, text=True)
    if p.returncode:
        raise SystemExit(f'{tag}: compile\n{p.stderr[-3000:]}')
    p = subprocess.run(['vvp', '-n', str(exe)], capture_output=True, text=True)
    ok = p.returncode == 0 and 'PASS' in p.stdout and 'FATAL' not in p.stdout + p.stderr
    line = [l for l in (p.stdout + p.stderr).splitlines() if 'PASS' in l or 'mismatch' in l][:1]
    print(f'{tag}: {"PASS" if ok else "MUTANT CAUGHT" if not expect else "FAIL"} {line[0].strip() if line else ""}')
    if ok != expect:
        raise SystemExit(f'{tag}: unexpected result')


def mutate(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f'mutant anchor {old!r} found {text.count(old)}x')
    return text.replace(old, new)


def main():
    a = argparse.ArgumentParser(description=__doc__)
    for k in ('old', 'new', 'cells', 'landing', 'out'):
        a.add_argument('--' + k, type=Path, required=True)
    a.add_argument('--cycles', type=int, default=40000)
    x = a.parse_args()
    x.out.mkdir(parents=True, exist_ok=True)
    cells = x.cells.read_text()
    lib = '\n'.join(m.group(0) for m in re.finditer(r'module (ot_dp_rrelay|ot_dp_rgate)\b.*?endmodule', cells, re.S))
    land = x.landing.read_text()
    m = re.search(r'module ot_dp_landing_relay\b.*?endmodule', land, re.S)
    lib += '\n' + m.group(0) + '\n'
    (x.out / 'cells.sv').write_text(lib)
    old, fo, ko = cone(x.old.read_text(), 'cone_old')
    new, fn, kn = cone(x.new.read_text(), 'cone_new')
    if fo != fn or not set(S) <= set(fn):
        raise SystemExit(f'face sets differ {fo} {fn}')
    (x.out / 'cone_old.sv').write_text(old); (x.out / 'cone_new.sv').write_text(new)
    print(f'cones: old {len(ko)} cells, new {len(kn)} cells, {len(fn)} faces')
    for b in S:
        st = [kn[f'u_cland_writer_start_{b}_{i}'][1] for i in range(3)]
        print(f'  {b}: stage resets {[p["rst_raw_n"] for p in st]}, face reset '
              f'{kn["u_cland_fstart_" + b][1]["rst_raw_n"]}')
    (x.out / 'tb.sv').write_text(tb(fn, x.cycles, 20261108))
    base = [x.out / 'cells.sv', x.out / 'cone_old.sv', x.out / 'tb.sv']
    run(x.out, 'equiv', base + [x.out / 'cone_new.sv'], True)
    st = {b: [kn[f'u_cland_writer_start_{b}_{i}'][1] for i in range(3)] for b in S}
    muts = {
        'bypass_cws0_o_s1': mutate(new, f'.d(cland_writer_start_cws0_o_1), .q(cland_writer_start_cws0_o_2)',
                                   f'.d(cland_writer_start_cws0_o_0), .q(cland_writer_start_cws0_o_2)'),
        'shallow_phase_cws0_o_s2': mutate(new, f'.rst_raw_n({st["cws0_o"][2]["rst_raw_n"]}), .d(cland_writer_start_cws0_o_1)',
                                          f'.rst_raw_n({st["cws0_o"][1]["rst_raw_n"]}), .d(cland_writer_start_cws0_o_1)'),
        'deep_phase_x_st_a_fe_o_s0': mutate(new, f'.rst_raw_n({st["x_st_a_fe_o"][0]["rst_raw_n"]}), .d(cland_start_d), .q(cland_writer_start_x_st_a_fe_o_0)',
                                            f'.rst_raw_n({st["x_st_a_fe_o"][1]["rst_raw_n"]}), .d(cland_start_d), .q(cland_writer_start_x_st_a_fe_o_0)'),
    }
    # S face: a leaf one depth short is observable (the stage resets do not cover r(t-4) there).
    leaf = kn['u_cland_lrst_fstart_cws0_o'][1]
    par = kn[next(i for i, (k, p) in kn.items() if p['q'] == leaf['d'])][1]['d']
    muts['leaf_short_cws0_o'] = mutate(new, f'.d({leaf["d"]}), .q(cland_lrst_fstart_cws0_o)', f'.d({par}), .q(cland_lrst_fstart_cws0_o)')
    # W face: phase-1 stages already AND r(t-2..t-4), so a leaf one depth SHORT is logically equivalent there (not a
    # mutant); one depth DEEP (an extra relay in front of the leaf) moves the release edge and must be caught.
    for b in ('ag_eo', 'x_ctl_o'):
        leaf = kn[f'u_cland_lrst_fstart_{b}'][1]
        muts[f'leaf_deep_{b}'] = mutate(new, f'.d({leaf["d"]}), .q(cland_lrst_fstart_{b})', f'.d(mut_x_{b}), .q(cland_lrst_fstart_{b})').replace(
            'endmodule', f'  wire mut_x_{b};\n  ot_dp_rrelay u_mut_x_{b} (.clk(clk), .d({leaf["d"]}), .q(mut_x_{b}));\nendmodule')
    for tag, text in muts.items():
        f = x.out / f'cone_new_{tag}.sv'
        f.write_text(text.replace('module cone_new', 'module cone_new'))
        run(x.out, tag, base + [f], False)


if __name__ == '__main__':
    main()
