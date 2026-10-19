#!/usr/bin/env python3
"""LH-P3UNITS/UNIONVAR 10-19: composed MTP / per-user reprice of the factored ordered-cardinality union scheme on
f4c_t9p3 (767.41 mm2) with every cost term explicit.  Replaces the unmeasured 108-cycle prep assumption.

Base: key_profile_tight.json (factored exact-cardinality WORK price, all measured unit IIs; no prep).  Added per
main-model union layer (40 per verify step and per MU step; draft/seed loops are U15 no-sharing => c = 1, immediate
static counts, no dispatcher):
  prep        measured (tb_hnx_union_factored run0.log: prefix ready edges BEFORE the real IDX union done) -> exposed
              max(0, -slack) = 0
  dispatch    measured RTL timeline: S = done + 1, first launch at S + B1, B1 = 4 (READ, CAP, FORM, WAIT)
  wire        dispatcher (beside idx_sel) -> farthest quadrant kernel store: Manhattan / 405 um hops, charged at FULL
              cycle per hop (conservative; half-cycle forwarded hops would halve it) + one landed crossing (2 + E, E = 2)
  kstore      quadrant kernel-store read + capture rung (2 edges)
  port        0: metadata SRAM write/read phases are disjoint; one kernel read per launch >= 4 edges apart while every
              production kernel span is >> 4 edges (no throughput loss)
  load        0 per layer / per token: all 40 layers x c = 1..N kernels resident from boot (capacity.json)
These are latency terms on the static critical path, charged as NOT overlapped (conservative).  Area is added to the die
outline as a separate line (rate is per die; tok/s per mm2 reported).
"""
import argparse, json, math, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UV = ROOT / 'results/arch/hbm_next_1019/cmtp/unionvar'
FLOOR_MTP, FLOOR_USER = 3364.0, 1000.0
DIE_MM2 = 767.41
REACH = 405.0


def geometry():
    g = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show',
        'HEAD:physical/hbm_next/die/f4c_t9p3/grants_hnx_f4c_t9p3.json']))
    s = {x['name']: x for x in g['slots']}
    def ctr(n):
        o, w = s[n]['origin'], s[n]['outline']; return o['x'] + w['w'] / 2, o['y'] + w['h'] / 2
    src = ctr('idx_sel')
    d = {q: abs(ctr('calendar_' + q)[0] - src[0]) + abs(ctr('calendar_' + q)[1] - src[1]) for q in ('SW', 'SE', 'NW', 'NE')}
    return src, d


def main(a):
    prof = json.loads((UV / 'key_profile_tight.json').read_text())
    cap = json.loads((UV / 'factored/capacity.json').read_text())
    log = (UV / 'factored/run0.log').read_text()
    m = re.search(r'prep_ready_before_union_done_edges min(-?\d+) max(-?\d+)', log)
    assert m and 'UNION_FACTORED PASS' in log
    slack_min = int(m.group(1))
    src, dist = geometry()
    far = max(dist.values()); hops = math.ceil(far / REACH)
    terms = dict(prep=max(0, -slack_min), dispatch=1 + 4, wire_full_cycle_hops=hops, landed_crossing=2 + 2, kstore=2,
                 port=0, load=0)
    per_layer = sum(terms.values())
    per_layer_half = per_layer - hops + math.ceil(hops / 2)
    L = 40
    p = prof['price']
    mtp_cyc, mtp_tok = p['mtp']['step_cycles'], p['mtp']['tok_s']
    mu_cyc, mu_agg, users = p['mu']['step_cycles'], p['mu']['agg_tok_s'], p['mu']['users']
    def rate(cyc, tok, add): return tok * cyc / (cyc + add)
    out = dict(schema='hnx.unionvar.factored.reprice.v1', die='f4c_t9p3', die_mm2=DIE_MM2,
               base='key_profile_tight.json (factored exact-cardinality work; measured v2+frames/FUSED tree/SM3 IIs)',
               base_mtp=mtp_tok, base_mtp_step_cycles=mtp_cyc, base_mu_agg=mu_agg, base_mu_step_cycles=mu_cyc,
               replaced_assumption='108 cycles/layer prep (unmeasured) -> measured/derived terms below',
               bench_prep_slack_edges=dict(min=slack_min, max=int(m.group(2))),
               geometry=dict(dispatcher_at='idx_sel centre %.0f,%.0f um' % src, to_quadrant_um=dist, farthest_um=far,
                             hops_405=hops),
               per_layer_terms=terms, per_layer_cycles=per_layer, union_layers=L, per_step_cycles=L * per_layer)
    for tag, add in (('conservative_full_cycle_hops', L * per_layer), ('half_cycle_hops', L * per_layer_half),
                     ('old_108_assumption', L * 108)):
        mtp = rate(mtp_cyc, mtp_tok, add); agg = rate(mu_cyc, mu_agg, add)
        out[tag] = dict(added_cycles_per_step=add, mtp_tok_s=round(mtp, 2), mtp_margin_pct=round(100 * (mtp / FLOOR_MTP - 1), 3),
                        mu_agg_tok_s=round(agg, 1), per_user_tok_s=round(agg / users, 2),
                        per_user_margin_pct=round(100 * (agg / users / FLOOR_USER - 1), 2))
    ks = cap['kernel_store']; md = cap['dispatcher']['metadata']
    area_macros = 4 * ks['macros'] * ks['area_mm2'] / ks['macros'] + md['area_mm2']
    area_slot = area_macros / 0.55 + 0.01                 # 55 % fill + dispatcher logic (~2k flops, estimate)
    out['area'] = dict(kernel_store='4 quadrant replicas x %d macros (kref broadcast, no 1408-b descriptor wires)' % ks['macros'],
                       macro_mm2=round(area_macros, 4), slot_mm2_estimate=round(area_slot, 3),
                       die_mm2_after=round(DIE_MM2 + area_slot, 2), status='estimate from macro abstracts; no gate yet')
    c = out['conservative_full_cycle_hops']
    out['verdict'] = ('MTP %.2f (%+.3f%% vs 3,364) / %.2f per user (%+.2f%% vs 1,000) with all exposed per-layer terms '
                      'charged unoverlapped; area +%.2f mm2 (est.) -> %.2f mm2'
                      % (c['mtp_tok_s'], c['mtp_margin_pct'], c['per_user_tok_s'], c['per_user_margin_pct'], area_slot,
                         DIE_MM2 + area_slot))
    out['still_owed'] = ['TT/FF physical gate of the dispatcher + kernel-store tile (no gate yet)',
                         'native HGI-1R -> unit programme lowering of the per-c kernels (descriptor fetch at the SM '
                         'quadrant is modelled as a 2-edge kernel-store read)',
                         'exact bank-by-bank model proof (pooled S2/histogram expectation remains the work price)',
                         'captured routing for rejected verify lanes (decorrelated estimator)']
    (UV / 'factored/reprice.json').write_text(json.dumps(out, indent=1) + '\n')
    print(out['verdict'])
    print(json.dumps({k: out[k] for k in ('per_layer_terms', 'conservative_full_cycle_hops', 'half_cycle_hops',
                                          'old_108_assumption')}, indent=0))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__); main(ap.parse_args())
