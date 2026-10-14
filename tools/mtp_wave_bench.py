#!/usr/bin/env python3
"""DS-ROM MTP 'wave' class throughput bench (el1011-ds-mtp [wave], 2026-10-11).

Runs rtl/dsrom_sys/mtp/tb/tb_mtp_wave.sv -- the integrated DS-ROM MTP draft / WFC verify / accept loop as bound on the
S81 dies, every MTP / WFC element as its closed RTL (see the bench header) -- and writes the opentallas.mtp-wave-bench.v1
record: per charge of results/arch/mtp_step_20261009/ds_rom_step.json the price, the cycles the RTL spends between the
same events (measured), ratio = measured / price, the elements it covers; exactness (bit-exact ends, mutants that must
FAIL); per element the qualification verdict (QUALIFIED ratio <= qualify_ratio, else UNQUALIFIED; elements with no
charge: QUALIFIED_BY_BOUND when 10x their measured cycles move the step by < 1 %, else UNQUALIFIED_NO_BENCH).

    python3 tools/mtp_wave_bench.py run --out DIR [--case NAME ...] [-j N] [--sim iverilog|verilator]   (fleet host)
    python3 tools/mtp_wave_bench.py record --out DIR --record results/rtl/dsrom_mtp_wave_bench_20261011/record.json
Cases: wave (production shape, PASS required), mut_* (one mutant define each, FAIL required), smoke (short busy times).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = 'rtl/dsrom_sys/mtp'
D = 'rtl/experimental/mtp_p2_ordered_20261009'
C = 'rtl/dsrom_sys/s81_ph/coll'
TB = [f'{M}/tb/tb_mtp_wave.sv', f'{M}/tb/tb_mtp_wave_dies.sv', f'{M}/tb/tb_mtp_wave_parts.sv']
SRC = [
    # WFC kit + S0 / stage die masters
    f'{M}/ot_dsrom_mtp_skid.sv', f'{M}/ot_dsrom_mtp_link_pair.sv', f'{M}/ot_dsrom_mtp_link_rtt.sv', f'{M}/ot_dsrom_mtp_seq.sv',
    f'{M}/ot_dsrom_wfc_tok.sv', f'{M}/ot_dsrom_wfc_lnk.sv', f'{M}/ot_dsrom_wfc_vmx.sv', f'{M}/ot_dsrom_drf_fan.sv',
    f'{M}/dsfd_mtp_tops.sv', 'rtl/common/ot_ratio_cdc_fifo.sv', 'rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv',
    'rtl/link/ot_fifo_sram_fwft.sv', f'{M}/ot_dsrom_wfc_tok_r3.sv', 'rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc_tokpipe.sv',
    f'{M}/ot_dsrom_wfc_tokpipe_src.sv', f'{M}/ot_dsrom_wfc_tokpipe_stg.sv', f'{M}/dsfd_wfc_kit.sv',
    f'{M}/dsfd_wfc_crp.sv', 'rtl/lib/ot_rst_relay.sv', 'rtl/common/ot_link_credit.sv',
    f'{M}/dsfd_vm_wfc_ep.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv', f'{M}/dsfd_stage_seq.sv',
    # head die: sequencer + partner ends; MTP lanes
    f'{M}/dsfd_mtp_seq_rtt.sv', f'{M}/dsfd_mtp_partner_ep.sv', f'{C}/dsfd_coll_mtp_lane.sv', f'{M}/dsfd_coll_mtp_ep.sv',
    'rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv', f'{C}/ot_s81ph_skid2.sv',
    # primary die
    f'{M}/ot_dsrom_mtp_seed_launch.sv', f'{M}/ot_dsrom_mtp_hrow.sv', f'{M}/ot_dsrom_mtp_hrow_bank.sv',   # hrow_rx's hardened bank (el1013)
    # draft die A: P2
    f'{C}/dsfd_coll_p2_lane.sv', f'{D}/ot_mtp_p2_ordered_rows.sv', f'{D}/ot_mtp_p2_prefix.sv', f'{D}/ot_mtp_p2_prefix_native.sv',
    f'{D}/ot_mtp_p2_prefix_path.sv', f'{D}/ot_mtp_p2_tiles.sv', f'{D}/dsfd_p2_lnk.sv', f'{D}/dsfd_p2_rtt.sv', 'rtl/v41rom/ot_v41_fadd.sv',
    'rtl/common/ot_prefix.sv', 'rtl/common/ot_secded.sv', 'rtl/common/ot_sc_pfifo.sv',
    # draft head Markov join
    'rtl/v41rom/ot_v41_bmul2.sv', 'rtl/v41rom/ot_dsrom_bmul3.sv', 'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv',
    # accept
    'rtl/mtp/rollback/ot_mtp_commit.sv', 'rtl/mtp/rollback/ot_mtp_hist_ring.sv', 'rtl/mtp/rollback/ot_mtp_hist_ring_p.sv',
    # SRAM macro models
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
    'physical/s81_ph_views/mtp/macros/ot_sram_1r1w_512x64_m4_r2c2/ot_sram_1r1w_512x64_m4_r2c2.v',
    'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
]
MARKOV = 'results/rtl/dsrom_markov_row_20261008'
SMOKE = dict(T_BUSY=300, T_BUSY0=300, T_LM=400, T_BLK=200, T_HX=60, T_SC=300, NSTEPMAX=13)
CASES = {
    'wave': dict(params={}, defines=[], expect='pass'),
    'smoke': dict(params=SMOKE, defines=[], expect='pass'),
    # negatives (must FAIL): a stage done before its core finished / the hrow issue epoch never advances (stale rows) /
    # P2 lane segmentation corrupts the second beat.  (Not discriminated by this single-user, stall-free traffic and so
    # not listed: OT_HROW_MUT_NOEPOCH, OT_VMWFC_MUT_EARLY_START, OT_FIXLAT_MUT_NOGATE -- their own gates cover them.)
    'mut_sseq_earlydone': dict(params=SMOKE, defines=['OT_SSEQ_MUT_EARLY_DONE'], expect='fail'),
    'mut_hep_stale': dict(params=SMOKE, defines=['OT_WFCHEP_MUT_STALE'], expect='fail'),
    'mut_p2l_seg': dict(params=SMOKE, defines=['OT_P2L_MUT_SEG'], expect='fail'),
}


def prepare(d: Path):
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run(['python3', str(ROOT / 'tools/mtp_p2_prefix_fixture.py')], cwd=d, check=True, capture_output=True)
    for a, b in (('w', 'mk_w'), ('x', 'mk_x'), ('head', 'mk_head'), ('gold', 'mk_gold')):
        shutil.copy2(ROOT / MARKOV / f'{a}.hex', d / f'{b}.hex')


def classify_run(log: str, returncode: int) -> str:
    # A missing PASS line is not evidence that a mutation was observed. Runtime
    # crashes, missing memory files and simulator aborts are harness failures.
    if returncode != 0 or re.search(r'(?im)^(?:FATAL:|ERROR:|Traceback|Segmentation fault)', log):
        return 'runtime_error'
    if re.search(r'^WAVE FAIL', log, re.M):
        return 'fail'
    if re.search(r'^WAVE PASS ', log, re.M):
        return 'pass'
    return 'no_observation'


def run_case(name: str, out: Path, sim: str):
    c = CASES[name]
    d = out / name
    prepare(d)
    top = 'tb_mtp_wave'
    inc = ['-I' + str(ROOT / M / 'tb'), '-I' + str(ROOT / 'rtl/common')]
    srcs = [str(ROOT / s) for s in SRC + TB]
    if sim == 'verilator':
        cmd = ['verilator', '--binary', '-j', '8', '--timing', '-Wno-fatal', '-Wno-WIDTH', '-Wno-UNUSED', '-Wno-PINCONNECTEMPTY',
               '-Wno-MULTIDRIVEN', '-Wno-UNOPTFLAT', '-Wno-PINMISSING', '-Wno-CASEINCOMPLETE', '-Wno-INITIALDLY',
               '--top-module', top, '--Mdir', str(d / 'obj'), '-o', 'sim'] + inc + \
              [f'+define+{x}' for x in c['defines']] + [f'-G{k}={v}' for k, v in c['params'].items()] + srcs
        run = [str(d / 'obj' / 'sim')]
    else:
        cmd = ['iverilog', '-g2012', '-s', top, '-o', str(d / 'sim.vvp')] + inc + [f'-D{x}' for x in c['defines']] + \
              [f'-P{top}.{k}={v}' for k, v in c['params'].items()] + srcs
        run = ['vvp', '-n', str(d / 'sim.vvp')]
    b = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    (d / 'build.log').write_text(b.stdout + b.stderr)
    if b.returncode:
        return dict(case=name, expect=c['expect'], got='build_error', ok=False, tail=(b.stdout + b.stderr).splitlines()[-12:])
    with open(d / 'run.log', 'w') as fo:
        result = subprocess.run(run, cwd=d, stdout=fo, stderr=subprocess.STDOUT)
    log = (d / 'run.log').read_text(errors='replace')
    got = classify_run(log, result.returncode)
    lines = [l for l in log.splitlines() if l.startswith(('WAVE ', 'WAVE_CHARGE', 'WAVE_EVENT', 'WAVE FAIL'))]
    return dict(case=name, expect=c['expect'], got=got, ok=got == c['expect'], params=c['params'], defines=c['defines'],
                lines=lines[:80], first_fail=next((l for l in lines if l.startswith('WAVE FAIL')), None))


def main_run(a):
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    names = list(a.case or CASES)
    # Mutants use SMOKE parameters; their exact matched control must pass too.
    if any(CASES[n]['expect'] == 'fail' for n in names) and 'smoke' not in names:
        names.append('smoke')
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda n: run_case(n, out, a.sim), names))
    src = sorted(set(SRC + TB + [f'{M}/tb/tb_mtp_wave_fn.svh', f'{M}/tb/tb_mtp_wave_meas.svh', 'tools/mtp_wave_bench.py']))
    pins = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in src}
    commit = subprocess.run(['git', 'rev-parse', '--short=9', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    (out / 'summary.json').write_text(json.dumps(dict(sim=a.sim, source_commit=commit, cases=res, source_sha256=pins), indent=1) + '\n')
    for r in res:
        print(f"{'OK ' if r['ok'] else 'BAD'} {r['case']:22s} expect={r['expect']} got={r['got']} {r.get('first_fail') or ''}")
    print('MTP_WAVE_BENCH', 'PASS' if all(r['ok'] for r in res) else 'FAIL')
    return 0 if all(r['ok'] for r in res) else 1


# ---------------------------------------------------------------------------------------------------------------- record
# charge -> elements whose cycles it measures (registry element names)
CHARGE_ELEMENTS = {
    'wfc_kit.ar_pass': ['ot_dsrom_wfc_tokpipe_stg', 'dsfd_wfc_lnk', 'dsfd_wfc_vmx', 'dsfd_wfc_crp', 'dsfd_vm_wfc_ep'],
    'wfc_kit.intervals': ['ot_dsrom_wfc_tokpipe_stg', 'ot_dsrom_wfc_tokpipe_src', 'dsfd_wfc_lnk', 'dsfd_wfc_vmx', 'dsfd_wfc_crp',
                          'dsfd_vm_wfc_ep'],
    'mtp_seq.draft_chain': ['dsfd_mtp_seq_rtt', 'ot_dsrom_mtp_lrx_rtt'],
    'mtp_seq.seed_release': ['dsfd_mtp_seq_rtt', 'ot_dsrom_mtp_lrx_rtt'],
    'wfc_tok.edges': ['dsfd_wfc_tok_hard'],
    'mtp_commit': ['ot_mtp_commit'],
    'p2.link_ends': ['dsfd_p2_lnk', 'dsfd_coll_p2_ep', 'dsfd_vm_p2_ep'],
    'p2.core_transaction': ['ot_mtp_p2_prefix_path'],
    'mtp_lane.adapters': ['dsfd_coll_mtp_lane'],
    'p2.lane_adapters': ['dsfd_coll_p2_lane_pa', 'dsfd_coll_p2_lane_ba'],
    'markov.floor': ['ot_dsrom_markov_row_K256'],
    'draft_head.pipe_regs.vm_mtp_ep': ['dsfd_vm_mtp_ep', 'dsfd_cap_mtp_ep'],
    'seedl.launch': ['dsfd_mtp_seed_launch'],
    'hrow.transport': ['dsfd_mtp_hrow'],
}
PRICE_SRC = {  # the ds_rom_step.json charge each bench charge is priced by (formula of record)
    'p2.core_transaction': 'p2.selected_path (per rank prefix 5,467: physical/mtp_p2_transport/route.sh gate)',
    'draft_head.pipe_regs.vm_mtp_ep': 'draft_head.pipe_regs (the vm_mtp_ep OUTPUT_PIPE half: 5 x 1)',
    'seedl.launch': 'seedl.launch (34 + 3 + (rows - 1) x 35 at this bench\'s committed rows; tau 4.159 -> 147.6)',
}
NOT_BENCHED = {
    'dsfd_mtp_seq': 'legacy receivers (overflow behind the head631 stations, mtp_seq_rtt_link_gate); the bound head631ep '
                    'carries dsfd_mtp_seq_rtt (same core ot_dsrom_mtp_seq), which this bench runs',
    'ot_dsrom_mtp_seed_ctl': 'seed projection controller drives the native q-element over the released main_proj tensor; its '
                             'cycles are the composition seed term (bench stub at T_SC), not a wave charge',
    'ot_dsrom_markov_head_driver': 'needs the head weight ROM image (viamap); HBRELAY half of draft_head.pipe_regs not measured',
    'ot_dsrom_markov_embed_localcapture_pair': 'embedding lookup feeding the Markov join: not on a wave charge in this bench',
    'dsrom_mtp_head_full340_A': 'whole-vocab head wrapper (needs redesign, not built)',
    'ot_dsrom_markov_row_K256_PINREG2': 'PINREG 2 variant (the charge is priced on PINREG 1)',
}
BOUND_ONLY = {  # exercised exact in the loop, no wave charge: (measured cycles per step, what)
    'ot_mtp_hist_ring': 'Engram history read (read -> last token), off the token-path charges',
    'ot_mtp_hist_ring_p': 'Engram history read (read -> last token), off the token-path charges',
}


def parse(lines):
    ch, ev = {}, {}
    for l in lines:
        m = re.match(r'WAVE_CHARGE id=(\S+) price=([\d.]+) measured=(-?[\d.]+) n=(\d+) unit=(.*)', l)
        if m:
            ch[m.group(1)] = dict(price=float(m.group(2)), measured=float(m.group(3)), n=int(m.group(4)), unit=m.group(5))
        m = re.match(r'WAVE_EVENT (.*)', l)
        if m:
            for k, v in re.findall(r'(\w+)=(-?[\d.]+)', m.group(1)):
                ev[k] = float(v)
    return ch, ev


def main_record(a):
    s = json.loads((a.out / 'summary.json').read_text())
    drift = [k for k, v in s['source_sha256'].items() if (ROOT / k).exists() and hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != v]
    if drift:
        print('WARNING: sources differ from the run:', drift)
    if not s.get('source_commit'):
        s['source_commit'] = subprocess.run(['git', 'rev-parse', '--short=9', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip() + ' (record-time HEAD; run sources pinned by sha256)'
    cases = {c['case']: c for c in s['cases']}
    wave = cases.get('wave') or cases.get('smoke')
    ch, ev = parse(wave['lines'])
    step = json.loads((ROOT / 'results/arch/mtp_step_20261009/ds_rom_step.json').read_text())
    budget = ROOT / 'results/arch/throughput_budget_20261010/budget.json'
    qual = json.loads(budget.read_text()).get('qualify_ratio', 1.10) if budget.exists() else 1.10
    step_cyc = step['totals']['charged_step_cycles']
    charges = []
    for cid, c in ch.items():
        r = c['measured'] / c['price'] if c['price'] else None
        charges.append(dict(id=cid, price=c['price'], measured=round(c['measured'], 2), ratio=round(r, 4) if r is not None else None,
                            n=c['n'], unit=c['unit'], elements=CHARGE_ELEMENTS.get(cid, []),
                            price_source=PRICE_SRC.get(cid, f'ds_rom_step.json charges[{cid}]'),
                            status=('QUALIFIED' if r is not None and r <= qual and c['n'] > 0 else 'UNQUALIFIED')))
    el = {}
    for c in charges:
        for e in c['elements']:
            cur = el.get(e)
            if cur is None or (c['ratio'] or 9e9) > (cur['ratio'] or 9e9):
                el[e] = dict(status=c['status'], ratio=c['ratio'], charge=c['id'])
    for e, why in NOT_BENCHED.items():
        if why and e not in el:
            el[e] = dict(status='UNQUALIFIED_NO_BENCH', ratio=None, charge=None, why=why)
    for e, k in (('ot_mtp_hist_ring', 'hist_ring_read_to_last'), ('ot_mtp_hist_ring_p', 'hist_ring_p_read_to_last')):
        per = ev.get(k)
        c_step = 2 * 6 * per if per else None      # Engram layers L1 / L14 x 6 verified positions a step
        ok = c_step is not None and 9 * c_step / step_cyc < 0.01
        el[e] = dict(status='QUALIFIED_BY_BOUND' if ok else 'UNQUALIFIED_NO_BENCH', ratio=None, charge=None,
                     bound=dict(read_to_last_token_cycles=per, cycles_per_step=c_step, step_cycles=step_cyc,
                                rule='bound rule of budget.json: 9 x cycles / step < 1 %'),
                     why='exact in the loop (rollback reads checked); no token-path charge: ' + BOUND_ONLY[e])
    muts = [dict(case=k, defines=v['defines'], expect=v['expect'], got=v['got'], ok=v['ok'], first_fail=v.get('first_fail'))
            for k, v in cases.items() if k.startswith('mut_')]
    rec = dict(schema='opentallas.mtp-wave-bench.v1', owner='Claude:el1011-ds-mtp [wave]',
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               bench='rtl/dsrom_sys/mtp/tb/tb_mtp_wave.sv (+ _dies, _parts, _fn.svh, _meas.svh); runner tools/mtp_wave_bench.py',
               sim=s['sim'], source_commit=s['source_commit'], source_sha256=s['source_sha256'], host=a.host,
               prices='results/arch/mtp_step_20261009/ds_rom_step.json charges (not re-priced)', qualify_ratio=qual,
               shape=dict(users=1, gamma=5, accept_pattern_committed_rows=[4, 6, 3, 5, 1, 6, 4, 5, 2, 6, 4, 4], tau=round(50 / 12, 3),
                          p2_transactions_per_draft=3, hidden_row_beats=80, hidden_row_bf16=5120, stage_dies=4,
                          params=wave['params'], stations=dict(die_wfc_collective=10, head631_result='6/7', head631_mtp_lane='9/9',
                                                               head631_vm='11/11', vm_hub='13/13', primary_desc='9/9', primary_hrow='9/9',
                                                               primary_vm='6/6', seed_join=4, draftA_vm='12/14', draftA_coll='8/9', lane=17)),
               exactness=dict(wave=dict(got=wave['got'], summary=next((l for l in wave['lines'] if l.startswith('WAVE ')), None),
                                        checks=['committed tokens = greedy truth (every position)',
                                                'every HIDDEN payload word at every die hop and at the head = golden',
                                                'P2 result rows (metadata + numeric) = fixture gold, 3 transactions a draft',
                                                'Markov joins = released-vector gold (results/rtl/dsrom_markov_row_20261008)',
                                                'every seed beat = the committed position\'s main-hidden row (versioned row store)',
                                                'program starts = the sequencer descriptors; sequencer accept = prefix accept',
                                                'commit n / q_next / squash; history ring reads (both rings)']),
                              mutants=muts, all_ok=all(c['ok'] for c in cases.values())),
               charges=charges, events=ev, elements=el,
               notes=['wfc_kit.ar_pass measured = stage core done -> next stage core command, minus the ideal hop (header + 46 TXW words '
                      'serialised + 2 x 10 die hub stations + the collective stub cycle); price 160.53 a hop, x 120 hops',
                      'wfc_kit.intervals measured = same-pass start-to-start at the last stage - stage busy - the composed handoff 46',
                      'POSTED VM (the priced configuration): the stage kits run HEP 1 and count the START doorbell write '
                      '(fix cfe25038d); their t_hep feeds the layer 37/38/39 row senders',
                      'coll.engine_endpoint (dsfd_coll_job) is not a wave-class element and is not in this bench'])
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(rec, indent=1) + '\n')
    for c in charges:
        print(f"{c['id']:34s} price {c['price']:9.2f} measured {c['measured']:9.2f} ratio {c['ratio']} {c['status']}")
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['run', 'record'])
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--case', action='append')
    ap.add_argument('-j', '--jobs', type=int, default=6)
    ap.add_argument('--sim', choices=['iverilog', 'verilator'], default='iverilog')
    ap.add_argument('--record', type=Path)
    ap.add_argument('--host', default=None)
    a = ap.parse_args()
    sys.exit(main_run(a) if a.mode == 'run' else main_record(a))
