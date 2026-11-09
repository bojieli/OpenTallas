#!/bin/bash
# HBM-HARD-7: private build of d44v_epm (d44v + EP-MOD-1108 + 1108d) in a shallow private clone.
set -u
export GIT_SSH_COMMAND='ssh -o ControlPath=none'
S=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/epm
cd /
rm -rf "$S"; mkdir -p "$S"; cd "$S" || exit 1
timeout 500 git clone -q --depth 1 --filter=blob:none --no-checkout --single-branch --branch main intel2:/home/ubuntu/OpenTallas repo || { echo CLONE_FAILED; exit 2; }
cd repo || exit 1
M=$(git rev-parse origin/main); echo "main $M"
timeout 200 git fetch -q --depth 1 origin claude/die-hbm-92-ep-1108 || { echo FETCH_FAILED; exit 3; }
E=$(git rev-parse FETCH_HEAD); echo "ep branch $E"
[ "$E" = 8bdd1d64526400928390f9e0474923a6bdcde29e ] || { echo EP_BRANCH_MOVED; exit 4; }
timeout 400 git archive "$M" \
  physical/die_plan/hbm/plan_of_record/d35a physical/die_plan/hbm/plan_of_record/d35b \
  physical/die_plan/hbm/plan_of_record/d35c physical/die_plan/hbm/plan_of_record/d44v \
  results/hbm_hfdep_native_0250/selected_host/hfd_ep_host_vc.sv \
  results/hbm_hfdep_native_0250/selected_vc2/hfd_ep_static_vc2.sv \
  results/hbm_hfdep_native_0250/selected/hfd_ep_static.sv | tar -C "$S" -xf - || { echo ARCHIVE_FAILED; exit 5; }
git show "$E:physical/die_plan/hbm/delta_ep_mod_1108.py" > "$S/delta.py"
cd "$S" || exit 1
cat results/hbm_hfdep_native_0250/selected_vc2/hfd_ep_static_vc2.sv results/hbm_hfdep_native_0250/selected_host/hfd_ep_host_vc.sv > ep_both.sv
python3 -I - <<'P'
import gzip, pathlib
root = pathlib.Path('physical/die_plan/hbm/plan_of_record'); base = pathlib.Path('src_d44v'); base.mkdir()
for ov in ('d35a', 'd35b', 'd35c', 'd44v'):
    od = root / ov
    for f in sorted(od.rglob('*')):
        if not f.is_file():
            continue
        rel = f.relative_to(od).as_posix(); rel = rel[:-3] if rel.endswith('.gz') else rel
        if rel in ('die_plan.json', 'SHA256SUMS'):
            continue
        t = base / rel; t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(gzip.decompress(f.read_bytes()) if f.name.endswith('.gz') else f.read_bytes())
(base / 'die_plan.json').write_bytes(gzip.decompress((root / 'd44v/die_plan.json.gz').read_bytes()))
for n in ('README.md', 'SHA256SUMS'):
    if not (base / n).exists():
        (base / n).write_text('')
print('materialized files', sum(1 for _ in base.rglob('*')),
      [(n, (base / n).exists()) for n in ('clock_entries.json', 'core_macros.json', 'core_clock_regions.json')])
P
python3 -I delta.py src_d44v --rtl ep_both.sv --base-rtl results/hbm_hfdep_native_0250/selected/hfd_ep_static.sv --out-dir o1 2>&1 | tail -3 | cut -c1-300
python3 -I delta.py o1 --add-dirs --rtl ep_both.sv --out-dir o2 2>&1 | tail -3 | cut -c1-300
python3 -I - <<'P'
import json, hashlib
for f in ('o1/ep_mod_1108_event.json', 'o2/ep_mod_1108d_event.json'):
    d = json.load(open(f)); print(f, d['changed_types'], d['changed_top_level'], d['sha_in'][:12], d['sha_out'][:12], json.dumps(d.get('side_changes', ''))[:400])
for m in ('hfd_ep_host_vc', 'hfd_ep_static_vc2'):
    p = 'o2/cores/%s__427.68x246.24__epmod1108d.json' % m
    print(m, hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12])
P
echo BUILD_DONE
