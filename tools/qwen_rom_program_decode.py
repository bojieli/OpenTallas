import sys
sys.path.insert(0, sys.argv[1] + '/tools')
import hdc_isa as I
words = [l.strip() for l in open(sys.argv[2]) if l.strip() and not l.startswith('@')]
units = {getattr(I, n): n[5:] for n in dir(I) if n.startswith('UNIT_')}
for a, w in enumerate(words):
    f = I.decode(int(w, 16))
    u = units.get(f.get('unit'), f.get('unit'))
    extra = ''
    if u == 'ME': extra = f"nout={f.get('me_nout')} k={f.get('me_k')} tiles={f.get('me_tiles')} wsrc={f.get('me_wsrc')}"
    elif u == 'SU': extra = f"nout={f.get('su_nout')} nin={f.get('su_nin')} dst={f.get('dst')} sfu={f.get('sfu')}"
    print(a, u, 'b' if f.get('barrier') else '', extra, 'pos', (int(w, 16) >> 900) & 7)
