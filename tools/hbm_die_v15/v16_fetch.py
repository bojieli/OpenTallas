#!/usr/bin/env python3
"""Collect finished SYNTH views of v16 die cells (H-DIE-V16CASE 2026-10-16) into VIEWS_DIR/synth/<cell>/:
<wrapper>_synth_{tt,ff}.lib, etm_worst_*.rpt, meta.json = {std_area_um2 (yosys stat -liberty, top incl. submodules),
macros {module: [count, w, h]} (counts incl. submodules from the stat hierarchy; size from the macro LEF next to its
_bb.v), host, remote}.  Finds each cell on whichever fleet host built it.

    v16_fetch.py --views VIEWS_DIR [--remote-root DIR] [--commit SHA]
"""
import argparse, hashlib, json, re, shlex, subprocess
from pathlib import Path

HOSTS = ['ot-epyc4', 'ot-agidock128']   # ot-epyc1tb retired 10-16 (its reusable views were copied to ot-epyc4)
REMOTE_PY = r'''
import hashlib, json, re, sys, os, shlex, subprocess
root, src, cell, wrap = sys.argv[1:5]
direct = len(sys.argv) > 5 and sys.argv[5] == 'direct'
expected_src = sys.argv[6] if direct else src
d = f"{root}/syn/{cell}"
ys = open(f"{d}/{cell}.ys").read()
tops = re.findall(r'^hierarchy -check -top (\S+)\s*$', ys, re.M)
if tops != [wrap]:
    raise ValueError(f"Wrong synthesized top: {tops}; expected parameter wrapper {wrap}")
inputs = sorted({shlex.split(l)[-1] for l in ys.splitlines() if l.startswith('read_verilog ')})
# Source includes participate in the hardware just as read_verilog inputs do.
# Existing launchers have no -I options; refuse unknown search paths rather than
# claiming source closure using a guessed compiler resolution.
if any(tok.startswith('-I') for line in ys.splitlines() if line.startswith('read_verilog ')
       for tok in shlex.split(line)):
    raise ValueError('Include search options require explicit source-resolution proof')
pending, consumed = list(inputs), set()
while pending:
    path = pending.pop()
    if path in consumed:
        continue
    consumed.add(path)
    text = open(f'{src}/{path}').read()
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    for include in re.findall(r'^\s*`include\s+([^\n]+)', text, re.M):
        literal = re.fullmatch(r'"([^"\n]+)"\s*', include)
        if not literal:
            raise ValueError(f'Nonliteral include requires preprocessor proof: {path}: {include}')
        name = literal.group(1)
        candidates = {os.path.normpath(p) for p in (os.path.join(os.path.dirname(path), name), name)
                      if not os.path.isabs(p) and not os.path.normpath(p).startswith('../')
                      and os.path.isfile(os.path.join(src, p))}
        if len(candidates) != 1:
            raise ValueError(f'Missing/ambiguous include in {path}: {name}: {sorted(candidates)}')
        pending.extend(candidates)
inputs = sorted(consumed)
input_hashes = {p: hashlib.sha256(open(f'{src}/{p}', 'rb').read()).hexdigest() for p in inputs}
etm_scripts = {}
for corner in ('tt', 'ff'):
    script_path = f'{d}/etm_{corner}.tcl'
    if os.path.exists(script_path):
        script = open(script_path).read(); etm_scripts[corner] = hashlib.sha256(script.encode()).hexdigest()
        for path in re.findall(r'^read_(?:lef|liberty) /src/(\S+)\s*$', script, re.M):
            input_hashes[path] = hashlib.sha256(open(f'{src}/{path}', 'rb').read()).hexdigest()
st = open(f"{d}/{cell}.stat").read()
area = float(re.search(r"Chip area for top module '[^']*': ([\d.]+)", st).group(1))
fj = json.load(open(f"{d}/{cell}.files.json"))
resolution = None
if direct:
    resolution = json.loads(subprocess.check_output(['python3', f'{expected_src}/tools/hbm_die_v15/master_filelist.py',
                                                    cell, '--root', expected_src, '--json']))
    if resolution != fj or resolution.get('unresolved') or resolution.get('ambiguous') or resolution.get('blackboxes'):
        raise ValueError('Actual macro/module resolution differs from the frozen expected source graph')
    resolution_tool_sha256 = hashlib.sha256(open(f'{expected_src}/tools/hbm_die_v15/master_filelist.py','rb').read()).hexdigest()
    observed_synth_launcher_sha256 = hashlib.sha256(open(f'{src}/tools/hbm_die_v15/synth_master.sh','rb').read()).hexdigest()
mods = {m['module']: m['file'] for m in fj['macros']}
hier = st.split('=== design hierarchy ===', 1)[-1]
mac = {}
for m, f in mods.items():
    c = [int(x) for x in re.findall(r'^\s+(\d+)\s+\S+\s+' + re.escape(m) + r'\s*$', hier, re.M)]
    if not c:
        continue
    lef = f"{src}/{f[:-len('_bb.v')]}.lef" if f.endswith('_bb.v') else None
    w = h = 0.0
    if lef and os.path.exists(lef):
        s = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', open(lef).read())
        w, h = float(s.group(1)), float(s.group(2))
    mac[m] = [max(c), w, h]
out = dict(std_area_um2=area, macros=mac, actual_top=tops[0], source_file_sha256=input_hashes,
           synthesis_script_sha256=hashlib.sha256(ys.encode()).hexdigest(), etm_script_sha256=etm_scripts)
if direct:
    out.update(actual_elaboration_script=ys, expected_resolution=resolution,
               resolution_tool_sha256=resolution_tool_sha256, observed_synth_launcher_sha256=observed_synth_launcher_sha256)
print(json.dumps(out))
'''


def check_sources(meta, commit, views):
    """Verify remote source bytes against the declared Git snapshot and exact wrapper."""
    hashes = meta['source_file_sha256']
    paths = [p for p in hashes if not p.startswith('v16w/')]
    data = subprocess.run(['git', '-C', str(Path(__file__).resolve().parents[2]), 'cat-file', '--batch'],
                          input=''.join(f'{commit}:{p}\n' for p in paths).encode(), capture_output=True, check=True).stdout
    offset = 0
    for p in paths:
        end = data.index(b'\n', offset)
        header = data[offset:end].split()
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError(f'Source absent from {commit}: {p}')
        size = int(header[2]); blob = data[end + 1:end + 1 + size]; offset = end + 2 + size
        if hashlib.sha256(blob).hexdigest() != hashes[p]:
            raise ValueError(f'Source differs from {commit}: {p}')
    for p in hashes:
        if p.startswith('v16w/'):
            local = Path(views) / 'wrap' / Path(p).name
            if hashlib.sha256(local.read_bytes()).hexdigest() != hashes[p]:
                raise ValueError(f'Parameter wrapper mismatch: {p}')


def check_direct_master(entry, meta, expected_ports, actual_ports):
    """Only a genuinely unparameterized contract may bind its real, unrenamed master."""
    if entry['params'] != {} or entry.get('params_dropped_yosys') or entry.get('env') or entry.get('blackbox', '-') != '-':
        raise ValueError('Direct master requires params{}, no omitted parameters, default defines and no extra blackboxes')
    if meta['actual_top'] != entry['master'] or entry['cell'] != entry['master']:
        raise ValueError('Direct master name must remain the actual Liberty/master name')
    if actual_ports != expected_ports:
        raise ValueError('Direct master actual port names, widths or directions differ from the frozen contract')
    resolution = meta['expected_resolution']
    if resolution['top'] != entry['master'] or resolution.get('unresolved') or resolution.get('ambiguous') or resolution.get('blackboxes'):
        raise ValueError('Unresolved or ambiguous direct-master source graph')
    # Pin the exact elaboration, defines, hierarchy mode, mapping and macro resolution.
    cell = entry['cell']; top = entry['master']
    expected = [f"read_verilog -lib {m['file']}" for m in resolution['macros']]
    expected += [f"read_verilog -sv -DSYNTHESIS v16w/{entry['wrapper']}.sv"]
    expected += [f'read_verilog -sv -DSYNTHESIS {p}' for p in resolution['files']]
    expected += [f'hierarchy -check -top {top}', f'tee -o /out/{cell}.hier.stat stat', f'synth -top {top}',
                 'dfflibmap -liberty /tmp/lib/seq.lib', 'abc -liberty /tmp/lib/all.lib', 'opt_clean',
                 f'tee -o /out/{cell}.stat stat -liberty /tmp/lib/all.lib', f'write_verilog -noattr /out/{cell}.netlist.v']
    if meta['actual_elaboration_script'].splitlines() != expected:
        raise ValueError('Direct-master defines, parameter overrides or elaboration/mapping recipe differ')


def check_etm_signature(path, top, expected_ports):
    from die_case import ports_of_lib
    cells = re.findall(r'\bcell\s*\(\s*"?([^"\s)]+)"?\s*\)', Path(path).read_text())
    if cells != [top]:
        raise ValueError(f'Wrong actual ETM cell in {path}: {cells}, expected {top}')
    if ports_of_lib(path) != expected_ports:
        raise ValueError(f'Actual ETM ports differ from frozen contract: {path}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--views', required=True)
    ap.add_argument('--remote-root', default='/srv/opentallas-scratch/claude/hdie-v16case')
    ap.add_argument('--commit', default='8c3c2a340')
    ap.add_argument('--build-commit', help='actual source snapshot used by a preserved build; all RTL/macro bytes must also match --commit')
    ap.add_argument('--allow-direct-master', action='store_true', help='strictly prove params{} real-master ETMs without changing their Liberty names')
    ap.add_argument('cells', nargs='*', help='only these cells (a same-named older build with other ports/params/source must not be fetched)')
    a = ap.parse_args()
    V = json.loads((Path(a.views) / 'views.json').read_text())
    build_commit = a.build_commit or a.commit
    src = f'{a.remote_root}/src_{build_commit}'
    expected_src = f'{a.remote_root}/src_{a.commit}'
    contract = json.loads(subprocess.check_output(['git', '-C', str(Path(__file__).resolve().parents[2]),
                                                  'show', f'{a.commit}:results/arch/hbm_die_v16/contract.json']))
    found = {}
    for h in HOSTS:
        out = subprocess.run(['ssh', h, f'cd {a.remote_root}/syn 2>/dev/null && ls -d */ | tr -d /'], capture_output=True,
                             text=True).stdout.split()
        for c in out:
            w = V.get(c, {}).get('wrapper')
            if not w or (a.cells and c not in a.cells):
                continue
            ok = subprocess.run(['ssh', h, f'test -s {a.remote_root}/syn/{c}/{w}_synth_ff.lib && '
                                f'grep -qx OT_ETM_DONE_ff {a.remote_root}/syn/{c}/etm.log && echo y'],
                                capture_output=True, text=True).stdout.strip()
            if ok == 'y':
                found[c] = (h, w, False)
            elif a.allow_direct_master and V[c]['params'] == {}:
                top = V[c]['master']
                ok = subprocess.run(['ssh', h, f'test -s {a.remote_root}/syn/{c}/{top}_synth_ff.lib && '
                                     f'grep -qx OT_ETM_DONE_ff {a.remote_root}/syn/{c}/etm.log && echo y'],
                                     capture_output=True, text=True).stdout.strip()
                if ok == 'y':
                    found[c] = (h, top, True)
    for c, (h, w, direct) in sorted(found.items()):
        meta = subprocess.run(['ssh', h, 'python3', '-', a.remote_root, src, c, w,
                               'direct' if direct else 'wrapper', expected_src], input=REMOTE_PY,
                              capture_output=True, text=True)
        if meta.returncode:
            raise ValueError(f'Cannot admit {c}: {meta.stderr[-1000:]}')
        m = json.loads(meta.stdout)
        check_sources(m, build_commit, a.views)
        if build_commit != a.commit:
            check_sources(m, a.commit, a.views)
        dst = Path(a.views) / 'synth' / c
        dst.mkdir(parents=True, exist_ok=True)
        files = (f'{w}_synth_tt.lib', f'{w}_synth_ff.lib', 'etm_worst_tt.rpt', 'etm_worst_ff.rpt')
        # Large Liberty tables compress well. Copy a cell in one checked transfer;
        # a failed transfer must not publish a receipt for incomplete views.
        subprocess.run(['rsync', '-az', *[f'{h}:{a.remote_root}/syn/{c}/{f}' for f in files], str(dst) + '/'],
                       check=True)
        rep = contract['instances'][V[c]['representative']]
        expected_ports = {p: (d['direction'], d['bits']) for p, d in rep['ports'].items()}
        for corner in ('tt', 'ff'):
            check_etm_signature(dst / f'{w}_synth_{corner}.lib', w, expected_ports)
        if direct:
            from die_case import ports_of_lib
            rep = contract['instances'][V[c]['representative']]
            if rep['params'] != {} or rep['master'] != c:
                raise ValueError('Frozen contract does not name this exact unparameterized master')
            expected_ports = {p: (d['direction'], d['bits']) for p, d in rep['ports'].items()}
            for corner in ('tt', 'ff'):
                check_direct_master(V[c], m, expected_ports, ports_of_lib(dst / f'{w}_synth_{corner}.lib'))
            root = Path(__file__).resolve().parents[2]
            for key, commit, path in [('resolution_tool_sha256', a.commit, 'tools/hbm_die_v15/master_filelist.py')]:
                wanted = hashlib.sha256(subprocess.check_output(['git', '-C', str(root), 'show', f'{commit}:{path}'])).hexdigest()
                if m[key] != wanted:
                    raise ValueError(f'Direct master tool source differs: {key}')
            V[c]['synth_top'] = w
            V[c]['parameter_binding'] = 'EXACT_DIRECT_MASTER_PARAMS_EMPTY_NO_RENAME'
        m.update(host=h, remote=f'{a.remote_root}/syn/{c}', declared_source_snapshot=build_commit,
                 compatible_source_snapshot=a.commit, parameter_binding=V[c].get('parameter_binding', 'EXACT_WRAPPER'),
                 consumed_file_sha256={f: hashlib.sha256((dst / f).read_bytes()).hexdigest() for f in files})
        (dst / 'meta.json').write_text(json.dumps(m, indent=1))
        print(c, h, m.get('std_area_um2'), len(m.get('macros', {})))
    print('FETCHED', len(found))
    if any(direct for _, _, direct in found.values()):
        (Path(a.views) / 'views.json').write_text(json.dumps(V, indent=1) + '\n')


if __name__ == '__main__':
    main()
