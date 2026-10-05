import sys, json, math
sys.path.insert(0, '/tmp/claude-dshbm-wt/tools')
import uarch_model as U
out = {}
rec = json.load(open('/tmp/claude-dshbm-wt/results/uarch/hbm_gpu.json'))
# default identity check
rows = U.v41_hbm_rows()
out['default_rows_identical'] = all(r == rr for r, rr in zip(rows, rec['rows'][7:]))
spec = U.hbm_speculation_rows() if hasattr(U, 'hbm_speculation_rows') else None
clock = U.hbm_gpu_design('v41')['clock_hz']
def ar_mtp(service):
    T, parts, nb = U.v41_hbm_chain(True, 1, None, service)
    Tv, pv, _ = U.v41_hbm_chain(True, U.V41_POSITIONS, None, service)
    Td = U.V41_DRAFT_FRACTION * T
    return dict(T_us=round(T, 3), tokens_s=round(1e6 / T, 1), boundaries=nb,
                boundary_service_us=round(parts.get('boundary_service', 0), 3), routed_fetch_us=round(parts.get('routed_fetch', 0), 3),
                mtp_verify_us=round(Tv, 2), mtp_draft_us=round(Td, 2), mtp_tokens_s=round(U.V41_TAU * 1e6 / (Tv + Td), 1))
res = {}
for lvl in ('off', 'low', 'central', 'high'):
    res[lvl] = ar_mtp(lvl)
    sv = U.V41_HBM_SERVICE[lvl]
    res[lvl + '_boundary_only'] = ar_mtp(dict(boundary_cycles=sv['boundary_cycles'], routed_fetch_ns=0.0))
    res[lvl + '_fetch_only'] = ar_mtp(dict(boundary_cycles=0, routed_fetch_ns=sv['routed_fetch_ns']))
for k, v in res.items():
    v['delta_rate_pct'] = round(100 * (v['tokens_s'] / res['off']['tokens_s'] - 1), 2)
    v['delta_mtp_pct'] = round(100 * (v['mtp_tokens_s'] / res['off']['mtp_tokens_s'] - 1), 2)
out['v41'] = res
# sensitivities
sens = {}
for name, cyc in (('membar_round_trip_62', 62), ('hopper_cluster_barrier_181', 181 - 62), ('hopper_cluster_barrier_213', 213 - 62)):
    T, p, nb = U.v41_hbm_chain(True, 1, None, dict(boundary_cycles=cyc, routed_fetch_ns=0.0))
    sens[name] = dict(extra_cycles_per_boundary=cyc, T_us=round(T, 2), tokens_s=round(1e6 / T, 1))
T, p, nb = U.v41_hbm_chain(True, 1)
sens['csa_gather_at_HBM_LOADED_LAT_NS_500'] = dict(extra_us=round(8 * (0.5 - 0.2548), 3), tokens_s=round(1e6 / (T + 8 * (0.5 - 0.2548)), 1))
sens['per_cycle_per_boundary_pct'] = round(100 * (1 - T / (T + nb / clock * 1e6)), 4)
out['v41_sensitivities'] = sens
# Qwen: add c cycles to the boundary in the stream model
import arch_budget_qwen3 as Q
dq = U.hbm_gpu_design('qwen'); qc = dq['clock_hz']
q = {}
for c in (0, 2, 4, 6, 62):
    ops = U.qwen_hbm_ops(dq['element'], dq['barrier']['boundary_cycles'] + c, dq['drain_cycles'])
    t, _ = U.stream_overlap(ops, dq['hbm_Bpc'], dq['sm_count'] * dq['element']['ingest_Bpc'], dq['staging_kb_per_sm'] * 1024 * dq['sm_count'])
    q[c] = dict(cycles=round(t), tokens_s=round(qc / t, 2))
for c in q: q[c]['delta_pct'] = round(100 * (q[c]['tokens_s'] / q[0]['tokens_s'] - 1), 4)
out['qwen'] = q
out['qwen_record_tokens_s'] = [r for r in rec['rows'] if r['design'] == 'qwen_hbm_gpu'][0]['tokens_s']
out['v41_record'] = [r for r in rec['rows'] if r['design'] == 'v41_hbm_gpu_groupslot'][0]['tokens_s']
out['v41_mtp_record'] = [r for r in rec['speculation'] if r['design'] == 'v41_hbm_mtp'][0]['tokens_s']
out['V41_DRAFT_FRACTION'] = U.V41_DRAFT_FRACTION
print(json.dumps(out, indent=1))
json.dump(out, open('/tmp/claude-review-20261003/dshbm_term/compute_out.json', 'w'), indent=1)
