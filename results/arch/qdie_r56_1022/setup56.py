from pathlib import Path
import os, shutil, json, hashlib
r = Path('/srv/opentallas-scratch/claude/codex-qdie-2000')
NEWPY = Path('/tmp/qdie_r56_b3r2.py'); NEWT = Path('/tmp/qdie_r56_test_mixed.py')
COMMIT = '96d96401e'
for suffix, variant in [('c', 'a'), ('d', 'b')]:
    old = 'dv2f21g5r55cx' + suffix; new = 'dv2f21g5r56cx' + suffix; so = r / old; s = r / new
    assert not s.exists(); s.mkdir()
    for p in so.iterdir():
        if p.is_file() and (p.suffix == '.sh' or p.name in ('receiver_plan.json', 'land_plan_bi_chain.json', 'reset_release_prior_g4try3.json', 'slice_slot.json', 'fault_emit_plan.json', 'source.json', 'STAND_INS.json', 'DIAG_SET.json')):
            q = s / p.name; shutil.copy2(p, q)
            if p.suffix == '.sh': q.write_text(q.read_text().replace(old, new))
    shutil.copytree(so / 'src', s / 'src', copy_function=os.link, symlinks=True)
    for rel, srcf in (('tools/qwen_rom_fulldie_b3r2.py', NEWPY), ('tools/qwen_split/test_reset_pad64_mixed.py', NEWT)):
        p = s / 'src' / rel
        if p.exists() or p.is_symlink(): p.unlink()      # never truncate a shared hardlinked inode
        shutil.copyfile(srcf, p)
    p = s / 'src/SOURCE_COMMIT'; prev = p.read_text(); p.unlink()
    p.write_text(COMMIT + ' claude/qdie-r56-1022 (8ade34452 + OT_RST_PAD64_MIXED mixed legal reset palette) PAD62 ' + variant + '\n')
    h = s / 'src/SOURCE_COMMIT.history'
    if h.exists():
        t = h.read_text(); h.unlink(); h.write_text(t + 'r55: ' + prev)
    p = s / 'hp_env.sh'; p.write_text(p.read_text() + 'export OT_RST_PAD64_MIXED=1 OT_DIE_REPAIR_MAX_WIRE=600   # QDIE-R56 mixed legal reset palette; rep600 explicit\n')
    (s / 'PILOT.log').write_text('QDIE-R56 r56 = r55 compact64 ' + variant + ' + OT_RST_PAD64_MIXED=1 (compact PAD62 where legal, else 6xp8+2xrep same 64 cycles on the same edge); same functional source; current seam-only image diagnostic, F16/INIT integration still owed\n')
    meta = json.loads((so / 'source.json').read_text())
    meta.update(commit=COMMIT, source_branch='claude/qdie-r56-1022', base_run=old, variant=variant,
                overlay_r56={'tools/qwen_rom_fulldie_b3r2.py': hashlib.sha256(NEWPY.read_bytes()).hexdigest(),
                             'tools/qwen_split/test_reset_pad64_mixed.py': hashlib.sha256(NEWT.read_bytes()).hexdigest()},
                case='r55 + mixed legal reset palette (OT_RST_PAD64_MIXED=1)')
    (s / 'source.json').write_text(json.dumps(meta, indent=2) + '\n')
    link = Path('/srv/opentallas-scratch/claude/qwen-split-compute') / new
    assert not link.exists(); link.symlink_to(s)
    print(new, 'READY', COMMIT)
