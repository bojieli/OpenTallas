#!/usr/bin/env python3
"""TOK-DS/ENTRY (2026-10-25): actual S81 entry-port mechanism gate -> entry_mechanism.py inputs.

Fleet-only (Verilator 5.050 + the in-tree tools/verilator_nba_guard.py; run through ot-run).  One slice cut: ot_s81sl_rstopt entry pin -> ot_s81sl_xrt1
-> production leaf glue (ot_s81sl_rly W594/W667, 4 edges) -> ot_s81sl_vp leaf store (tb_entry_vp.sv).  The stimulus is the
real entry image of one (sid, leaf): entry_inputs.compile_inputs(die, fixtures) target-5 rows, the leaf's own HLOAD /
GAIN readers and its delayed-pre row, encoded with the compiler's own ctl_payload / ctl_line_beat / vp_cmd.

  --cut w   port ri_w            -> result key measured_local_contract, checks positive / negative_payload
  --cut ev  ports ri_e and vi    -> result key by_input_port {ri_e, vi}, checks <port> / negative_<port>

Each positive must PASS (every commit's data exact, every row read back exactly through HLOAD / GAIN / RDOUT, no fault,
no stray write); each payload mutant (one row-data bit flipped at the entry pin) must FAIL.  Ages are parsed from the run
logs, never supplied.  Every hashed source is repo-relative to ROOT (= the tree this file sits in), so entry_boot.py run
from the same ROOT can verify them.  A new --out per attempt; nothing is overwritten.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent.relative_to(ROOT)
sys.path[:0] = [str(ROOT / 'tools/s81_dv'), str(ROOT / 'tools/s81_dv/layer_prog')]
import dv_layer_compile as D              # noqa: E402
from entry_inputs import compile_inputs    # noqa: E402

RTL = ['rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_f12.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_delay.sv',
       'rtl/hdc/v41x/ot_dsrom_su_add6.sv', 'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv',
       'rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv', 'rtl/lib/ot_rst_relay.sv',
       'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv',
       'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv',
       'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
BENCH = [str(HERE / 'tb_entry_vp.sv'), str(HERE / 'gate.py')]
PORT_NUM = dict(ri_w=0, ri_e=1, vi=2)
CLOCK = 'common bench clock phase0 only; die phase/route outside this pin remain unqualified'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--cut', choices=('w', 'ev'), required=True)
    ap.add_argument('--tree', type=Path, required=True, help='die tree (results/arch/s81_dv_1016/bind9/die.v.gz)')
    ap.add_argument('--fixtures', type=Path, required=True, help='layer fixture dir (files.json, io/, weights/)')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--sid-w', type=int, default=11)
    ap.add_argument('--sid-e', type=int, default=5)
    ap.add_argument('--sid-v', type=int, default=9)
    ap.add_argument('--leaf', type=int, default=0)
    ap.add_argument('--muti', type=int, default=13, help='write index whose payload the mutant corrupts')
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    src = RTL + BENCH
    pins = {s: sha(ROOT / s) for s in src}

    die = D.Die(a.tree)
    entry = compile_inputs(die, a.fixtures)
    (a.out / 'entry_image.json').write_text(json.dumps(entry, indent=1) + '\n')
    slices = die.slices()
    by_sid = {v['sid']: k for k, v in slices.items()}
    ports = ['ri_w'] if a.cut == 'w' else ['ri_e', 'vi']
    sids = dict(ri_w=a.sid_w, ri_e=a.sid_e, vi=a.sid_v)
    plan = {}
    for port in ports:
        sid, leaf = sids[port], a.leaf
        sl = by_sid[sid]
        cp = D.ctl_path(die, sl)
        if cp['entry_port'] != port:
            raise SystemExit(f'{sl} (sid {sid}) enters on {cp["entry_port"]}, not {port}')
        writes = [w for w in entry['writes'] if w['sid'] == sid and w['leaf'] == leaf]
        rd = [r for r in entry['readers'] if r['slice'] == sl and r['leaf'] == leaf]
        assert len(rd) == 1 and 0 < len(writes) <= 64 and a.muti < len(writes)
        rd = rd[0]
        src_sid = 8 | (sid & 1)                          # line beats come from the column-4 slice of the tier
        hops = 0 if port == 'vi' else 1                  # terminal stop on the line; V beats as seq_host injects them
        width = 276 if port == 'vi' else 1104

        def beat(payload):
            b = D.ctl_line_beat(payload, src=4 if port == 'vi' else src_sid, hops=hops)
            assert b < 1 << width
            return f'{b:0276x}'
        cmds = [D.ctl_payload(1 << sid, 0, 1 << leaf, D.vp_cmd(D.VP['HLOAD'], a0=rd['hload_a0'])),
                D.ctl_payload(1 << sid, 0, 1 << leaf, D.vp_cmd(D.VP['GAIN'], a0=rd['gain_a0'])),
                D.ctl_payload(1 << sid, 0, 1 << leaf, D.vp_cmd(D.VP['RDOUT'], a0=rd['normr_a0'], n=1))]
        pd = a.out / ('vec_' + port)
        pd.mkdir()
        (pd / 'writes.memh').write_text(''.join(beat(int(w['ctl_payload186'], 16)) + '\n' for w in writes))
        (pd / 'expect.memh').write_text(''.join(f'{w["row"]:04x}{w["data128"]}\n' for w in writes))
        (pd / 'cmds.memh').write_text(''.join(beat(c) + '\n' for c in cmds))
        (pd / 'cargs.memh').write_text(''.join(f'{v:04x}\n' for v in (rd['hload_a0'], rd['gain_a0'], rd['normr_a0'])))
        plan[port] = dict(slice=sl, sid=sid, leaf=leaf, master=slices[sl]['master'], nw=len(writes),
                          regions=sorted({w['region'] for w in writes}), rows=[w['row'] for w in writes],
                          die_ctl_path_edges=cp['edges'],
                          vectors={p.name: sha(p) for p in sorted(pd.iterdir())})

    obj = a.out / 'obj'
    v = str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator')
    cmd = [v, '--binary', '--timing', '-O1', '-fno-dfg', '--unroll-count', '4', '-Wno-fatal', '-Wno-WIDTH',
           '--top-module', 'tb_entry_vp', '-Mdir', str(obj), '-j', str(a.jobs),
           *[str(ROOT / s) for s in RTL + BENCH[:1]], '-CFLAGS', '-O1']
    result = dict(schema='opentallas.s81.entry_vp_gate.v1', cut=a.cut, status='RUNNING', full_token=False,
                  full_layer=False, source_root=str(ROOT), source_sha256=pins, argv=cmd, defines=[],
                  die_sha256=die.die_sha, entry_image_sha256=sha(a.out / 'entry_image.json'),
                  fixture_meta_sha256=entry['fixture_meta_sha256'], relay_module_sha256=pins[RTL[11]],
                  plan=plan,
                  scope=('one slice, one leaf: rstopt entry pin -> xrt1 -> production leaf glue 4 edges '
                         '(c1x_k8_cap5r_lp: DLK 1 + landed crossing +3 on leaves 0/1/3/4, DLK 4 on leaf 2) -> VP store; '
                         'real entry image rows at the entry_boot two-edge cadence'),
                  open=['die route phases / regional clocks (common bench clock)', 'xgt_xo ring stop variant '
                        '(rstopt, ring +0)', 'vn / vq / vs consumers of hw / wl (VP outputs observed)',
                        'cut replay of the native jobs (run_entry_replay.py) is the runtime proof'])

    def save():
        (a.out / 'result.json').write_text(json.dumps(result, indent=1) + '\n')
    save()
    t0 = time.time()
    b = subprocess.run(['/usr/bin/time', '-v', *cmd], capture_output=True, text=True)
    (a.out / 'build.log').write_text(b.stdout + b.stderr)
    m = re.search(r'Maximum resident set size \(kbytes\): (\d+)', b.stderr)
    result['build'] = dict(seconds=round(time.time() - t0), max_rss_gb=round(int(m.group(1)) / 2**20, 2) if m else None)
    if b.returncode:
        result.update(status='FAIL', reason='build', exit_code=b.returncode)
        save()
        sys.exit(1)
    # in-tree NBA guard (hashed with the sources; the installed share/ot_nba_guard copy is absent on the fleet hosts)
    sys.path.insert(0, str(ROOT / 'tools'))
    import verilator_nba_guard as G
    guard = G.scan(str(obj))
    (a.out / 'nba_guard.json').write_text(json.dumps(guard, indent=2) + '\n')
    result['nba_guard_sha256'] = sha(ROOT / 'tools/verilator_nba_guard.py')
    if guard['findings']:
        result.update(status='FAIL', reason='NBA guard')
        save()
        sys.exit(86)

    checks, contracts = {}, {}
    for port in ports:
        p = plan[port]
        for name, mut in ((port, 0), ('negative_' + port, 1)):
            rd = a.out / ('run_' + name)
            rd.mkdir()
            for f in (a.out / ('vec_' + port)).iterdir():
                (rd / f.name).write_bytes(f.read_bytes())
            argv = [str(obj / 'Vtb_entry_vp'), f'+PORT={PORT_NUM[port]}', f'+SID={p["sid"]}', f'+LEAF={p["leaf"]}',
                    f'+NW={p["nw"]}', f'+MUT={mut}', f'+MUTI={a.muti}']
            r = subprocess.run(argv, cwd=rd, capture_output=True, text=True)
            log = r.stdout + r.stderr
            (a.out / (name + '.log')).write_text(log)
            good = (r.returncode != 0 and 'ENTRY_VP FAIL' in log) if mut else \
                (r.returncode == 0 and 'ENTRY_VP PASS' in log)
            checks[name] = dict(passed=good, exit_code=r.returncode, argv=argv[1:])
            if not mut:
                t5 = [int(x) for x in re.findall(r'^AGE T5 .* age=(\d+)$', log, re.M)]
                hl = [int(x) for x in re.findall(r'^AGE HLOAD .* age=(\d+)$', log, re.M)]
                gn = [int(x) for x in re.findall(r'^AGE GAIN .* age=(\d+)$', log, re.M)]
                rdout = [int(x) for x in re.findall(r'^AGE RDOUT .* age=(\d+)$', log, re.M)]
                contracts[port] = dict(target5_pin_to_store_commit_edges=t5, hload_pin_to_hw_edges=hl,
                                       gain_pin_to_wl_edges=gn, rdout_pin_to_lo_edges=rdout,
                                       sid=p['sid'], leaf=p['leaf'], slice=p['slice'],
                                       source_pin='ot_s81sl_rstopt.' + port, clock_scope=CLOCK,
                                       target5_rows=len(t5), target5_cadence_edges=2)
    if {s: sha(ROOT / s) for s in src} != pins:
        result.update(status='FAIL', reason='sources changed during the run')
        save()
        sys.exit(1)
    ok = all(c['passed'] for c in checks.values()) and all(
        len(c['target5_pin_to_store_commit_edges']) == plan[k]['nw'] and len(c['hload_pin_to_hw_edges']) == 1
        and len(c['gain_pin_to_wl_edges']) == 1 for k, c in contracts.items())
    result.update(status='PASS' if ok else 'FAIL', checks=checks)
    if a.cut == 'w':
        result['measured_local_contract'] = contracts.get('ri_w')
        result['checks'] = dict(positive=checks['ri_w'], negative_payload=checks['negative_ri_w'])
    else:
        result['by_input_port'] = contracts
    save()
    for port, c in contracts.items():
        print('ENTRY_VP_GATE', port, 'T5 max', max(c['target5_pin_to_store_commit_edges'] or [-1]),
              'HLOAD', c['hload_pin_to_hw_edges'], 'GAIN', c['gain_pin_to_wl_edges'])
    print('ENTRY_VP_GATE', a.cut, result['status'], {k: v['passed'] for k, v in checks.items()})
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
