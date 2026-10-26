#!/usr/bin/env python3
"""Receipt of the A2-F / hop-1 VM parent gate (S-VM-RTL 2026-10-16).

  python3 tools/s81_vm/a2f_parent_receipt.py PKG_DIR REV HOST:REMOTE_DIR
PKG_DIR holds manifest.txt (repo path + sha256 of every staged source), gate.sh and the fetched out/*.log + gate.log.
Writes results/rtl/s81_vm_a2f_parent_0200/{record.json, gate.log, logs/*.log} (logs = the run markers only).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/rtl/s81_vm_a2f_parent_0200'

PORT_MAP = {
    'write_sources': {
        '0..15': 'SU f_su_wqv/wq/wqm/wqd slot c (tag c)',
        '16..23': 'HC f_hc_wq* slot c-16 (tag c)',
        '24..27': 'static landing dsfd_vm_static_landing o_v/o_row/o_d lanes 0..3 = scan a0, scan a1, selector, collector '
                  '(mask ffff, tag c; LARM groups 0 / 5 / 6 from engine 12)',
        '28..31': 'Engram MIX4 f_mx_wq* lane c-28 (tag c)',
        '32..43': 'capture lanes 0..11 (dsfd_vm_static_cap w_*; tag c)',
        '44..47': 'collective landing rows (dsfd_vm_static_xio cl_*; tag = compiler cl_t)',
        '48..51': 'capture lanes 12..15 (tag c)',
        '52': 'WFC kit writes (dsfd_vm_static_wfc wf_*; mask ffff, tag 52)',
    },
    'front_inputs': 'dsfd_vm_a2f_core p_src (the legacy wiring, unchanged) -> s81_a2f_controlled_split4m i_v[c], i_row[14c+:14], '
                    'i_tag[8c+:8], i_mask[16c+:16] (slice x = bits 4x..4x+3), i_data[512c+:512] (slice x = bits 128x..); '
                    'the W0 header / 4 payload leaves are the source pin registers (edge P), control4 x4 samples i_row[7:0] '
                    'directly at P for the bank lane',
    'front_to_storage': 'bank-linear o_slice_v[32x+k], o_slice_row[14(32x+k)], o_slice_tag[8(32x+k)], o_mask[16k+4x], '
                        'o_data[512k+128x] -> dsfd_vm_static_scatter_b8_out PIPE 1 (slice x, group k/8) -> relay128_b8 (x, k/8) '
                        'write -> bank128 (x, k) [HOP1: no b4]; the legacy logical packet J = 8 (k mod 4) + k/4 and the 128 '
                        'write_capture128 leaves are gone',
    'read': 'rsched (dsfd_vm_a2f_rsched_p REL 8) n_v/n_row/n_slot/n_group, a_v/a_row -> per slice dsfd_vm_static_suhc_fsr_split '
            '(unchanged) -> b8 read request -> bank128 -> b8 response -> dsfd_vm_static_return32_native_lanes (release / '
            'prepare at E0+8 / E0+7) -> dsfd_vm_static_suhc_return_map -> native_v/data, group_v/data -> read router '
            '(unchanged): SU / HC / PQ / aux / MIX outputs',
    'commit': 'bank128 o_commit/o_ca/o_cm/o_ct -> b8 response -> commit_v[32x+k], commit_addr[9(32x+k)], commit_mask[4(32x+k)], '
              'commit_tag[8(32x+k)] -> dsfd_vm_seq_tile o_cv/o_ca/o_cm (engine-12 CHECK), the legacy layout',
    'faults': 'm_flt[40] legacy layout ([10x+:4] FSR, [10x+4] = OR of the 4 scatter faults, [10x+5+:4] return lanes, [10x+9] '
              'native map); w_flt = OR of the 16 registered A2-F quarter faults (fault_join4), re-registered in the seq tile',
    'clock_reset_ports': {
        'unchanged': 'every functional port; ck/rss core, rsched, seq, landing, mem_fsr 16, mem_return 16/4, mem_bank 128, '
                     'mem_wscatter 16 (now PIPE-1 scatter), read_data 64, read_valid 8, all serial-side cap / wfc / xio / x34 '
                     '/ x43 roots',
        'reused_new_master': 'ck/rss_write_header_t 1 -> s81_a2_w0_header; ck/rss_write_payload_t 4 -> s81_a2_w0_payload x4',
        'width_changed': 'ck/rss_write_control_t 1 -> 4 (s81_a2f_control4_resetlocal per slice); ck_mem_relay_req_t / rsp_t and '
                         'rss_mem_relay_t 48 -> 16 (b8 only, bit 4*slice+group; the 32-entry b4 tail is pruned)',
        'new': 'ck/rss_write_meta_t 28 (7 metadata field4 leaves per slice), ck/rss_write_data_t 128 (32 data field4 leaves '
               'per slice: 32*slice + 4*field + nibble), ck/rss_write_fault_t 4 (fault_join4 per slice)',
        'retired': 'ck/rss_write_dispatch_t 16, ck/rss_write_stage_t 128, ck/rss_mem_wcapture_t 128 (no sink exists)',
        'census': 'tools/s81_vm/die_clock_abi.py --a2f -> results/arch/s81_vm_die_abi_a2f_0200/contract.json: clock bits '
                  '693 -> 520, reset bits 617 -> 476',
    },
}


def main():
    pkg, rev, remote = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    manifest = {}
    for line in (pkg / 'manifest.txt').read_text().split('\n'):
        if line.strip():
            p, h = line.split()
            manifest[p] = h
            assert hashlib.sha256((pkg / 'src' / Path(p).name).read_bytes()).hexdigest() == h, p
    gate = (pkg / 'gate.log').read_text()
    runs = {}
    for m in re.finditer(r'^(PASS|FAIL) (\S+)$', gate, re.M):
        runs[m.group(2)] = m.group(1)
    lat = sorted(set(re.findall(r'^\s*\d+ (TB_A2F_DIFF LAT .*)$', gate, re.M)))
    res = sorted(set(re.findall(r'^\s*\d+ (TB_A2F_DIFF RESULT .*|TB_SPVM RESULT .*)$', gate, re.M)))
    logs = {}
    for f in sorted((pkg / 'out').glob('*.log')):
        if f.name.startswith('build_'):
            continue
        keep = [l for l in f.read_text(errors='replace').split('\n') if l.startswith(('TB_', 'LATENCY', 'UNEXPECTED', 'REF ', 'DUT ',
                                                                                     'SOURCE', 'BENCH', 'ENGINE'))][:40]
        logs[f.stem] = keep
    verdict = 'PASS' if re.search(r'^A2F_GATE PASS$', gate, re.M) else 'FAIL'
    rec = {
        'schema': 'opentallas.s81.vm-a2f-parent-gate.v1',
        'verdict': verdict,
        'scope': 'RTL function + fixed-cycle calendar of the A2-F / hop-1 VM parent dsfd_sp_vm_a2f (READ_PIPE 4, CAP_PIPE 2, '
                 'HOP1 1) against the legacy dsfd_sp_vm path; 128 real SRAM models per VM; Verilator 5.050. No physical, '
                 'timing or die-level qualification is claimed.',
        'source_revision': rev,
        'remote_package': remote,
        'source_sha256': manifest,
        'gate': 'tools/s81_vm/a2f_parent_gate.sh (staged copy gate.sh in the package)',
        'runs': runs,
        'latency_lines': lat,
        'result_lines': res,
        'calendar': {
            'legacy_w1 (profile s81_vm_r4_c2_w1)': {'write_raw': 'P+10+lane', 'write_commit': 'P+12+lane', 'read_raw': 'Q+7', 'read_return': 'Q+16'},
            'legacy_w0 (profile s81_vm_r4_c2_w0, dsfd_sp_vm default WSCATTER_PIPE 0)': {'write_raw': 'P+9+lane', 'write_commit': 'P+11+lane', 'read_raw': 'Q+7', 'read_return': 'Q+16'},
            'a2f_hop2 (HOP1 0)': {'write_raw': 'P+12+lane', 'write_commit': 'P+14+lane', 'read_raw': 'Q+7', 'read_return': 'Q+16'},
            'a2f_hop1 (HOP1 1, production)': {'write_raw': 'P+11+lane', 'write_commit': 'P+12+lane', 'read_raw': 'Q+6', 'read_return': 'Q+14'},
            'deltas_vs_w1': 'A2 +2 write / +2 commit; hop-1 -1 write / -2 commit / -1 raw read / -2 read return; net +1 / 0 / -1 / -2',
            'dependent_read_rule_hop1': 'raw read must be strictly after raw write: Q+6 > P+11+lane, i.e. Q >= P+6+lane (w1: Q >= P+4+lane)',
            'source': 'calibrated in tb_dsfd_vm_a2f_diff (isolated write / read), then held exact for every record of the run; '
                      'see latency_lines',
        },
        'mutants_must_fail': {
            'mut_lane': 'DSFD_VM_A2F_MUT_LANE (slice 0: record of bank k on the data lane of bank k^1)',
            'mut_commit': 'DSFD_VM_A2F_MUT_COMMIT (slice 0 bank 5 commit observation dropped)',
            'mut_rel': 'DSFD_VM_A2F_MUT_HOP1_REL (hop-1 storage with the legacy release edge E0+10: the missing hop-1 edge)',
            'par_capword / par_wfcpair / par_x43phase': 'the S-FUNC master mutants on the A2-F parent',
        },
        'port_map': PORT_MAP,
        'logs': logs,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'record.json').write_text(json.dumps(rec, indent=1) + '\n')
    (OUT / 'gate.log').write_text(gate)
    print(verdict, OUT / 'record.json')


if __name__ == '__main__':
    main()
