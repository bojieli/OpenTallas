#!/usr/bin/env python3
"""Render REPRICE3's measured-bandwidth scenario into the token composition record."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/arch/hbm_reprice_1019'

def main():
    import sys
    # optional: price json name (default REPRICE3's) -- LH-REPRICE3 passes reprice3b_current.json
    price = sys.argv[1] if len(sys.argv) > 1 else 'reprice3_current.json'
    d = json.loads((OUT / price).read_text())
    lane = d.get('lane', 'HBM-REPRICE3')
    rec = json.loads((OUT / 'record.json').read_text())
    terms = []
    for design, cyc in [('hbm_gen_ds', 'ds_ar_cycles'), ('hbm_gen_qwen', 'qwen_cycles')]:
        for name, a in d['attribution'].items():
            grade = 'measured-current-RTL' if a['grade'] == 'measured' else 'priced'
            terms.append(dict(design=design, workload='ar', slot='reprice.'+name, kind='adjust', n=1,
                cycles=a[cyc], grade=grade, pointer='attribution.'+name+'.'+cyc,
                note=f"{lane} [{a['grade']}] {a['applies']}; {a['source']}"))
        terms.append(dict(design=design, workload='ar', slot='reprice.interaction', kind='adjust', n=1,
            cycles=d['interaction'][cyc], grade='priced', pointer='interaction.'+cyc,
            note='Composed schedule interaction; mixed measured and analytic terms'))
        delta = round(d['table']['info_banklat_all'][cyc] - d['table']['all'][cyc], 1)
        terms.append(dict(design=design, workload='ar', slot='reprice.banklat_budget', kind='adjust', n=1,
            cycles=delta, grade='priced', pointer='banklat_budget.'+cyc,
            note='Conservative exposed GEN2c client budgets/pads incl VMGLUEg4 +10; not measured GEN2d die STA; SU/SFU/HC tap growth beyond these categories remains pending'))
    rec.update(lane=lane, tool=d.get('tool', 'tools/hgi_sim/d4g_reprice3_1019.py'),
        price='results/arch/hbm_reprice_1019/' + price, variants=d['table'],
        composed=d['banklat_projected'], attribution=d['attribution'], interaction=d['interaction'],
        by_grade=d['by_grade'], qualification=d['qualification'], bandwidth=d['bandwidth'],
        pending='GEN2d measured lane depths; SU/SFU/HC tap latency exposure; successor BW capacity/SAFE closure; physical binding of INT8/relative-service/safe tiles',
        banklat_budget={cyc:round(d['table']['info_banklat_all'][cyc] - d['table']['all'][cyc],1) for cyc in ('ds_ar_cycles','qwen_cycles')})
    for k in ('area', 'scenario', 'composed_banklat', 'accepted'):
        if k in d:
            rec[k] = d[k]
    rec['token_compose'] = dict(note=lane + ' provisional current-master physical BW45.03; conservative bank-client budgets; successor95.19 conditional, see qualification', terms=terms)
    (OUT/'record.json').write_text(json.dumps(rec, indent=1)+'\n')

if __name__ == '__main__':
    main()
