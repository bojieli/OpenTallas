"""HBM load-path bandwidth audit at the target context (Qwen3-8B 8K, DeepSeek-V4.1 1M): summary.

Reads the part records in results/rtl/hbm_path_bandwidth_audit_20261004/ (each from its own measured bench or
from committed records) and writes summary.json: one row per HBM load path of the three designs with
bytes/token/die, peak, achieved TB/s, first access, limiter, >=90% and owner, the DS HBM per-token change, and
the list of paths still below 90% with owners.

    python3 tools/hbm_path_bandwidth_audit.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / 'results/rtl/hbm_path_bandwidth_audit_20261004'


def load(n):
    return json.loads((D / n).read_text())


def main():
    ef = load('dshbm_expert_fetch_la.json')
    ss = load('dshbm_static_stream.json')
    base = json.loads((ROOT / 'results/rtl/dshbm_baseline_measured_20261004/measured.json').read_text())
    sel = ef['stats']['sel_notice']
    r5a = json.loads((ROOT / 'results/rtl/hbm_accel_ha4_20261004/expert_first_access.json').read_text())
    sel_cases = [c for c in ef['cases'] if c['case'] == 'sel_notice']
    n_fetch = 40
    static_us = ss['selected']['static_stream_us']
    routed_b = ss['bytes_per_die']['routed']
    routed_stream_tbs_die = 4 * sel['stream_tbs']['mean']
    routed_us = routed_b / (routed_stream_tbs_die * 1e12) * 1e6
    tot_b = ss['bytes_per_die']['total']
    active_us = static_us + routed_us
    fa_mean, fa_max = sel['first_access_ns']['mean'], sel['first_access_ns']['max']
    model_fetch_us = base['published']['parts_us_1p2GHz']['fetch']
    sm_us = base['published']['parts_us_1p2GHz']['sm']
    token_us = base['headline']['measured_total_us']
    fetch_meas_mean = n_fetch * fa_mean / 1e3
    fetch_meas_max = n_fetch * fa_max / 1e3
    dshbm = dict(
        record='results/rtl/dshbm_baseline_measured_20261004/measured.json (main 7fb0d0174)',
        bytes_per_die=dict(total=tot_b, static_stream=ss['bytes_per_die']['static'], routed=routed_b),
        before=dict(achieved_tbs_over_sm_busy=base['hbm']['achieved_tbs_over_sm_busy'],
                    fraction=base['hbm']['fraction_of_peak_over_sm_busy'],
                    note='SM-schedule DEMAND with a behavioural LAT/JIT bulk copy, not a DRAM measurement'),
        after=dict(static_stream_tbs_die=ss['selected']['tbs_per_die'], static_fraction=ss['selected']['fraction_of_peak'],
                   static_stream_us=static_us, routed_stream_tbs_die=round(routed_stream_tbs_die, 4),
                   routed_us=round(routed_us, 3), hbm_active_us=round(active_us, 3),
                   achieved_tbs_over_hbm_active=round(tot_b / (active_us * 1e-6) / 1e12, 4),
                   fraction_over_hbm_active=round(tot_b / (active_us * 1e-6) / 1e12 / 4.0, 4),
                   sm_busy_us=sm_us,
                   note='the stream runs ahead of the SMs (prefetch window) and finishes in hbm_active_us < sm_busy_us, '
                        'so the SMs never wait on the static bytes; HBM utilisation over SM-busy stays the SMs\' demand'),
        per_token=dict(model_fetch_us=model_fetch_us, measured_fetch_us_mean=round(fetch_meas_mean, 3),
                       measured_fetch_us_worst=round(fetch_meas_max, 3),
                       delta_us_mean=round(fetch_meas_mean - model_fetch_us, 3),
                       delta_us_worst=round(fetch_meas_max - model_fetch_us, 3),
                       static_delta_us=0.0, token_us=token_us,
                       delta_pct_of_token_worst=round((fetch_meas_max - model_fetch_us) / token_us * 100, 3),
                       note='routed: 40 fetches x first access (w13 at every SM, refresh live, notice); the rest of '
                            'each burst streams at 4x the measured stack rate, faster than the SMs consume it'))
    rows = [
        # ---- Qwen3-8B at 8K ----
        dict(design='Qwen3-8B ROM', path='KV stream (REAL_MEM HBM_STREAM, near-HBM attention)', bytes_per_token_per_die=150994944,
             peak_tbs=4.0, achieved_tbs=0.900, fraction=0.225, first_access_ns=24.6, ge90=False,
             limiter='one of four stacks mapped; positions >= 2048 fault (8K unsupported)',
             status='before only; fix owned by the Qwen 8K load-path agent (no committed after-record yet)',
             owner='Claude, Qwen 8K full-bandwidth load-path agent', source='qwen_paths.json'),
        dict(design='Qwen3-8B HBM accel', path='weight + KV prefetch stream (HA8)', bytes_per_token_per_die=None,
             peak_tbs=4.0, achieved_tbs=3.85, fraction=0.962, first_access_ns=None, ge90=True,
             limiter='HBM column bus', status='measured at P1023 only; unmeasured at P8191',
             owner='Claude, HBM-accelerator closure', source='qwen_paths.json'),
        # ---- DeepSeek-V4.1 ROM at 1M ----
        dict(design='DS-V4.1 ROM', path='index-key scan ratio 1 (L20)', bytes_per_token_per_die=17.8e6, peak_tbs=4.0,
             achieved_tbs=3.676, fraction=0.919, first_access_ns=97, ge90=True, limiter='HBM', owner='Claude dsrom-1m-measured',
             source='dsrom_paths.json'),
        dict(design='DS-V4.1 ROM', path='index-key scan ratio 2 (L2/L8/L14)', bytes_per_token_per_die=8.9e6, peak_tbs=4.0,
             achieved_tbs=3.774, fraction=0.944, first_access_ns=97, ge90=True, limiter='HBM', owner='Claude dsrom-1m-measured',
             source='dsrom_paths.json'),
        dict(design='DS-V4.1 ROM', path='packed WINDOW KV load (128 x 544 B)', bytes_per_token_per_die=69632, peak_tbs=1.0,
             achieved_tbs=0.0006, fraction=0.0006, after_fraction_sustained=0.939, after_us_median=0.127, first_access_ns=55,
             ge90=False, limiter='as built one row at a time, one sector a request; refactor ot_dsrom_window_stream_la: 93.9% sustained',
             status='refactor built and exact; S81 binding pending', owner='Codex/Noether WINDOW source (binding)',
             source='dsrom_window_load.json'),
        dict(design='DS-V4.1 ROM', path='re-index candidate read (L24/28/32/36)', bytes_per_token_per_die=17.8e6, peak_tbs=4.0,
             achieved_tbs=3.676, fraction=0.919, ge90=True,
             limiter='reads 63x the needed bytes; ot_dsrom_hbm_list_gather_la reads only candidates: 4.85 -> 0.75 us/layer '
                     '(scatter-bound, 9-12% of peak; time is the measure)',
             owner='Claude dsrom-1m-measured (adopt) / DS ROM index owner (address generator)', source='dsrom_reindex_candidate_gather.json'),
        dict(design='DS-V4.1 ROM', path='selected compressed-KV gather', bytes_per_token_per_die=41e3, peak_tbs=4.0,
             achieved_tbs=None, fraction=0.023, ge90=False, limiter='all-gather links, not HBM (port sweep measured)',
             owner='Codex S81 CKV service', source='dsrom_paths.json'),
        dict(design='DS-V4.1 ROM', path='Engram tables', bytes_per_token_per_die=0, ge90=None, limiter='in ROM, no HBM',
             owner='n/a', source='dsrom_paths.json'),
        # ---- DeepSeek-V4.1 HBM accelerator / baseline at 1M ----
        dict(design='DS-V4.1 HBM', path='static stream (all non-routed weights, index keys, window/CKV rows) in consumption order',
             bytes_per_token_per_die=ss['bytes_per_die']['static'], peak_tbs=4.0, achieved_tbs=ss['selected']['tbs_per_die'],
             fraction=ss['selected']['fraction_of_peak'], ge90=ss['selected']['fraction_of_peak'] >= 0.9,
             limiter='HBM column bus (REFpb on schedule)', owner='Claude (HBM accelerator)', source='dshbm_static_stream.json'),
        dict(design='DS-V4.1 HBM', path='routed-expert fetch (R5a-LA), per stack burst of 6 experts',
             bytes_per_token_per_die=routed_b, peak_tbs=4.0, achieved_tbs=round(routed_stream_tbs_die, 4),
             fraction=sel['stream_tbs']['mean'], fraction_min=sel['stream_tbs']['min'], fraction_max=sel['stream_tbs']['max'],
             e2e_fraction_mean=sel['e2e_tbs']['mean'], first_access_ns=fa_max, ge90=sel['stream_tbs']['mean'] >= 0.9,
             before=dict(r5a_tbs_per_stack=0.395, r5a_first_access_worst_ns=r5a['measured_first_access_worst_ns']),
             limiter='300-KB bursts: per-PC 96% but REFpb tRREFD ACT blocking and the refresh round tail skew the 32 PCs; '
                     'same-set expert pairs (set feasibility) cost tRC',
             owner='Claude (HBM accelerator)', source='dshbm_expert_fetch_la.json'),
        dict(design='DS-V4.1 HBM', path='index-key scan L20-type (stand-alone R5a PC, refactor)', bytes_per_token_per_die=3713820,
             peak_tbs=4.0, achieved_tbs=3.76, fraction=0.94, ge90=True, limiter='HBM; subsumed by the static stream',
             owner='Claude (HBM accelerator)', source='dshbm_kv_paths.json'),
        dict(design='DS-V4.1 HBM', path='index-key scan L2-type (stand-alone, refactor)', bytes_per_token_per_die=1114248,
             peak_tbs=4.0, achieved_tbs=3.552, fraction=0.888, ge90=False,
             limiter='10 ns exposed first access on a 371-KB layer; subsumed by the static stream (no per-layer first access)',
             owner='Claude (HBM accelerator)', source='dshbm_kv_paths.json'),
        dict(design='DS-V4.1 HBM', path='KV write-back', bytes_per_token_per_die=23968, ge90=None,
             limiter='no 1M-addressable DS write path RTL (kv_lifecycle keys position[12:0])',
             owner='Claude (HBM accelerator, HA6 successor)', source='dshbm_kv_paths.json'),
    ]
    remaining = [
        dict(item='Qwen ROM KV stream at 8K, four stacks', owner='Claude Qwen 8K load-path agent', status='22.5% before; after pending'),
        dict(item='Qwen HBM accel stream at P8191', owner='Claude HBM-accelerator closure', status='unmeasured at target (96% at P1023)'),
        dict(item='DS ROM WINDOW load in the S81 die', owner='Codex/Noether (bind ot_dsrom_window_stream_la)', status='component 93.9% sustained; as built 0.06%'),
        dict(item='DS ROM selected-CKV gather', owner='Codex S81 CKV service', status='link-bound, not HBM-bound'),
        dict(item='DS HBM routed-expert burst', owner='Claude (HBM accelerator)',
             status=f"R5a 0.395 -> LA {sel['stream_tbs']['mean']:.3f} mean ({sel['stream_tbs']['min']:.3f} min) of the stack; "
                    'not >=90% per burst; next: in-stream REFpb slot steering around ACT groups, PC-skew-aware notice'),
        dict(item='DS HBM KV write-back at 1M', owner='Claude (HBM accelerator, HA6 successor)', status='no RTL path'),
    ]
    git = lambda *c: subprocess.run(['git', *c], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    out = dict(schema='opentallas.hbm_path_audit.summary.v1', source_commit=git('rev-parse', 'HEAD'),
               target=dict(qwen3_8b='position 8,191', deepseek_v41='position 1,048,575'),
               rule='owner: every HBM load at >= 90% of the die\'s stack peak (4 x 1.0 TB/s)',
               rows=rows, dshbm_token=dshbm, remaining_below_90=remaining,
               parts=sorted(p.name for p in D.glob('*.json') if p.name != 'summary.json'))
    (D / 'summary.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(dict(dshbm=dshbm, remaining=remaining), indent=2))


if __name__ == '__main__':
    main()
