# HBM-GEOM-2 11-12: 3rd pin layer M2 on the NW_mcb.E / PHY_NW.W abutment (DIE-HBM-100 decision for t40w).
# q_mcb_nw: face_layers E += M2, its 4 E-face ft_slots (L8x5 out, L21x1 in, L63wx5 out, L114wx1 in) on [M6, M4, M2].
# PHY_NW: face_layers W += M2 (its buses take their geometry from the port, i.e. from the q_mcb_nw slot).
import json, sys
src, out = sys.argv[1:3]
P = json.load(open(src)); T = P['partition_types']
L3 = ['M6', 'M4', 'M2']
T['q_mcb_nw']['face_layers']['E'] = L3
T['PHY_NW']['face_layers']['W'] = L3
n = 0
for s in T['q_mcb_nw']['ft_slots']:
    for side in ('in', 'out'):
        if s.get(side + '_face') == 'E':
            s[side + '_layers'] = list(L3); n += 1
json.dump(P, open(out, 'w'), indent=1)
print('slots', n)
