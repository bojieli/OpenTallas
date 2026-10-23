# QDIE-R56: Codex qchain_prep_split recipe (setup_prep_split.py, r51) applied to r54/r56 c/d, plus a prep-only follow
# (diag gate -> fault census -> reset projection -> phase2 -> phase3 with OT_STOP=prep: case + PDN + die clock, stop
# before GEN hard checks / GRT, writes PREPARED_WAIT_GRT).  Resume = guarded_resume200.sh (OT_FROM=grt).  Pinned src untouched.
from pathlib import Path
import json, hashlib
base = Path('/srv/opentallas-scratch/claude/codex-qdie-2000')
for t in ('dv2f21g5r54cxc', 'dv2f21g5r54cxd', 'dv2f21g5r56cxc', 'dv2f21g5r56cxd'):
    s = base / t; src = s / 'src'; overlay = s / 'prep_source'; h = overlay / 'tools/qwen_kv_die/chain'
    assert not overlay.exists(), t
    h.mkdir(parents=True)
    orig = src / 'tools/qwen_kv_die/chain/die_chain.sh'; text = orig.read_text()
    checkpoint = '''# QCHAIN 10-22 opt-in measured prep checkpoint, no full-route credit.
if [ "${OT_STOP:-}" = prep ]; then
  say "PREPARED_WAIT_GRT: validated case/PDN/clock prepared; full GRT/STA still required"
  printf '%s\\n' PREPARED_WAIT_GRT > "$R/PREPARED_WAIT_GRT"
  exit 0
fi
'''
    marker = '# ROOT14 10-20 (owner: reduce die closure risk): GEN hard checks before any GRT'
    assert text.count(marker) == 1
    (h / 'die_chain.sh').write_text(text.replace(marker, checkpoint + marker))
    for f in orig.parent.iterdir():
        if f.name != 'die_chain.sh' and not (h / f.name).exists(): (h / f.name).symlink_to(f)
    aft = (src / 'tools/qwen_split/chain_after_build.sh').read_text()
    assert 'bash $S/src/tools/qwen_kv_die/chain/die_chain.sh' in aft
    aft = aft.replace('bash $S/src/tools/qwen_kv_die/chain/die_chain.sh', f'bash {h}/die_chain.sh')
    a0 = aft.index('# several closed revisions'); a1 = aft.index('# owner no-stub gate')
    aft = aft[:a0] + 'if [ "${OT_FROM:-case}" != grt ]; then\n' + aft[a0:a1] + 'fi\n' + aft[a1:]
    ap = overlay / 'chain_after_build.sh'; ap.write_text(aft)
    ch = (s / 'chain.sh').read_text(); assert 'bash tools/qwen_split/chain_after_build.sh' in ch
    (overlay / 'chain.sh').write_text(ch.replace('bash tools/qwen_split/chain_after_build.sh', f'bash {ap}'))
    ph = (s / 'phase3.sh').read_text(); assert 'bash $S/chain.sh' in ph
    (overlay / 'phase3.sh').write_text(ph.replace('bash $S/chain.sh', f'bash {overlay}/chain.sh'))
    df = (s / 'diag_follow.sh').read_text(); assert 'bash $S/phase3.sh' in df
    df = df.replace('CORE=1 bash $S/phase3.sh', 'OT_STOP=prep CORE=1 bash $S/prep_source/phase3.sh')
    assert 'prep_source/phase3.sh' in df
    (s / 'diag_follow_prep.sh').write_text(df)
    (s / 'guarded_prep.sh').write_text(f'''#!/bin/bash
set -u
R={base}
T={t}
. "$R/$T/hp_env.sh"
bash "$R/hold_arm.sh" "$T" &
ARM=$!
bash "$R/$T/diag_follow_prep.sh" "$T"
RC=$?
kill "$ARM" 2>/dev/null || true
[ "$RC" = 0 ] && [ -s "$R/$T/chain/PREPARED_WAIT_GRT" ] && echo "PREPARED_WAIT_GRT: no GRT/STA qualification"
exit "$RC"
''')
    (s / 'guarded_resume200.sh').write_text(f'''#!/bin/bash
set -u
S={s}
. "$S/hp_env.sh"
[ -f "$S/DIAGNOSTIC_BIND_OPEN" ] && export OT_CHAIN_DIAGNOSTIC=1
unset OT_STOP
export OT_FROM=grt
bash "$S/prep_source/phase3.sh" {t}
''')
    files = [orig, src / 'tools/qwen_split/chain_after_build.sh', s / 'chain.sh', s / 'phase3.sh', s / 'diag_follow.sh',
             h / 'die_chain.sh', ap, s / 'diag_follow_prep.sh', s / 'guarded_prep.sh', s / 'guarded_resume200.sh']
    rec = dict(scope='QDIE-R56 prep phase split (Codex qchain_prep_split recipe); pinned src untouched',
               original_source=(src / 'SOURCE_COMMIT').read_text().strip(), prep_disk_GB=5,
               evidence='r48 run dir through PDN 651 MB, r51 prep 369 MB excluding hardlinked src',
               checkpoint='after case, PDN, die clock; PREPARED_WAIT_GRT only, no closure credit',
               files={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    (overlay / 'PREP_PROVENANCE.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(t, 'PREP READY')
