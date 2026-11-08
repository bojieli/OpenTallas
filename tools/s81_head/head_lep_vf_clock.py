"""Reproduce the existing LEP vF four-pair clock trial; no release adoption.

The measured body uses the already-published vE_1106 pair views. Qualification
of that child cohort and the die's corresponding clock event remains separate.
"""
import copy

VIEW = 'results/head_lep_pair_views_vE_1106/ot_s81hd_lep_pair'
SITES = [[1279.2, 552.736], [467.04, 659.296], [428.192, 515.744], [1260.96, 659.296]]


def apply(raw):
    out = copy.deepcopy(raw)
    t = out['partition_types']['hd_lep0N']
    c = t['clock']
    if c.get('insertion_ps') != 450 or c.get('insertion_ff_ps') != 380:
        raise ValueError('LEP trial requires its actual 450/380 parent clock budget')
    taps = [dict(name=f'u_core.u.g_pp[{i}].u_pair.clk', xy=xy, kind='core',
                 insertion_ps=529.22, insertion_ff_ps=434.56,
                 note='Existing vF trial: exact vE_1106 pair mean; child/parent adoption unqualified')
            for i, xy in enumerate(SITES)]
    if c.get('core_taps') not in (None, 'early') or c.get('taps', []) not in ([], taps):
        raise ValueError('different clock cohort already present; no implicit replacement')
    pairs = [h for h in t['hard_cores'] if h.get('module') == 'ot_s81hd_lep_pair']
    if {h['inst'] for h in pairs} != {f'u_core.u.g_pp[{i}].u_pair' for i in range(4)}:
        raise ValueError('exact four existing pair macros required')
    for h in pairs:
        if h.get('lef') not in (VIEW + '.lef', 'results/head_lep_pair_views_1101/ot_s81hd_lep_pair.lef') or h.get('lib') not in (VIEW + '_tt.lib', 'results/head_lep_pair_views_1101/ot_s81hd_lep_pair_tt.lib'):
            raise ValueError('different pair view cohort; no implicit replacement')
        h['lef'] = VIEW + '.lef'
        h['lib'] = VIEW + '_tt.lib'
    c['core_taps'] = 'early'
    c['taps'] = taps
    return out
