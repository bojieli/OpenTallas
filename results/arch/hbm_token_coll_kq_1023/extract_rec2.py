"""TOKj-HBM: rec2 component replay extracted from a TRANSPORTED ds_l0 slice replay (no hand retiming): stream drives
cyc <= 450 + every check of record 2 (Codex prepare_corrected_rec2 selection, without its shifts)."""
import sys, json, shutil
from pathlib import Path
src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
a = {n: [int(x, 16) for x in (src / f'{n}.mem').read_text().split()] for n in ('hdr', 'val', 'msk')}
ev = []; d = c = 0
for h, v, m in zip(a['hdr'], a['val'], a['msk']):
    k, dom, cyc = h >> 62, (h >> 60) & 3, h & 0xffffffff; rec = ((h >> 32) & 0xfff) - 1
    if k == 1 and dom == 0 and cyc <= 450: d += 1
    elif k == 2 and dom == 0 and rec == 2: c += 1
    else: continue
    ev.append((h, v, m))
ev.sort(key=lambda x: ((x[0] >> 60) & 3, x[0] & 0xffffffff, x[0] >> 62)); n = len(ev); last = max(h & 0xffffffff for h, _, _ in ev)
ev += [(3 << 62, 0, 0)] * (len(a['hdr']) - n)
for j, nm in enumerate(('hdr', 'val', 'msk')): (out / f'{nm}.mem').write_text(''.join(f'{r[j]:x}\n' for r in ev))
shutil.copyfile(src / 'vm_pre.txt', out / 'vm_pre.txt')
(out / 'index.json').write_text(json.dumps(dict(events=n, drives=d, checks=c, vm_preload_words=len((out / 'vm_pre.txt').read_text().splitlines()), last_stream_cyc=last, scope='component_probe', qualifies_native_layer=False, qualifies_native_chain=False, state_seed_provenance=['released_checkpoint_fixture'], records=[2], extracted_from=str(src)), indent=2) + '\n')
print(out.name, 'events', n, 'drives', d, 'checks', c, 'last', last)
