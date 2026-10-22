# S81-ELEM2-SEQ 10-21: dsdv_seq_host_hw = FALLBACK of dsdv_seq_host_h (CLOSED lk s10hq view): same stack/pins, lk|sq channel
# 43.2 -> 86.4 (room for the ~1,000 lk N -> sq S nets and the spine delay that balances lk TT insertion 647.6 vs sq 315.4 /
# vc 376.6), sq|vc 43.2 kept; outline 475.2 x 1036.8.  Run from the repo root: python3 tools/ref_tile/specs_pl_seq/mk_dsdv_seq_host_hw.py
import json, copy
h = json.load(open('tools/ref_tile/specs_pl_seq/dsdv_seq_host_h.json'))
d = copy.deepcopy(h); d['name'] = 'dsdv_seq_host_hw'; dy = 43.2
for c in d['children']:
    if c['inst'] in ('*u_l1', '*u_l2'): c['at'] = [c['at'][0], round(c['at'][1] + dy, 2)]
d['outline'] = {'w': h['outline']['w'], 'h': round(h['outline']['h'] + dy, 2), 'exact': True}
lk_top = 43.2 + 453.6; sqy = [c for c in d['children'] if c['inst'] == '*u_l1'][0]['at'][1]; yc = round((lk_top + sqy) / 2, 2)
d['pin_ranges']['ck'] = [round(yc - 0.15, 2), round(yc + 0.15, 2)]; d['pin_ranges']['rst_n'] = [round(yc + 2.25, 2), round(yc + 2.55, 2)]
d['structural_change'] = ("S81-ELEM2-SEQ 10-21 FALLBACK of dsdv_seq_host_h: lk|sq channel 43.2 -> 86.4 (lk N -> sq S ~1,000 nets + spine "
    "delay for lk TT insertion 647.6 vs sq 315.4 / vc 376.6), sq/vc moved N by 43.2, ck/rst_n centred in the wider channel; outline "
    f"{d['outline']['w']}x{d['outline']['h']}. " + h['structural_change'])[:6000]
j = d['job']; j['tag'] = 'shphw'; j['views_to'] = 'physical/ref_tile/dsdv_seq_host_hw/views'; j['record_to'] = 'results/rtl/ref_tile/dsdv_seq_host_hw'
j['purpose'] = 'S81-ELEM2-SEQ dsdv_seq_host_hw (FALLBACK, 86.4 lk|sq channel): CLOSED lk s10hq (649101c0d) + CLOSED sq + vc views'
json.dump(d, open('tools/ref_tile/specs_pl_seq/dsdv_seq_host_hw.json', 'w'), indent=1)
print(d['name'], d['outline'], [c['at'] for c in d['children']], 'ck', d['pin_ranges']['ck'])
