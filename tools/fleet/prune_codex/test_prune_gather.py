#!/usr/bin/env python3
"""PRUNE-AUDIT-1 11-07: the keep rules that CODEX-PRUNE-1 missed. Each case is a real loss from its first pass, reduced."""
import gzip, json, os, subprocess, sys, tempfile, time, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gather  # noqa: E402

HOSTS = 'epyc6 epyc5 localhost intel2 epyc4 intel1 epyc2'.split()
C = '/srv/opentallas-scratch2/claude/'


def blockers(line):
    out = []
    gather.line_blockers(line, 'src', lambda k, h, t, s: out.append((k, t)))
    return out


class Gather(unittest.TestCase):
    def test_keyword_regex_matches_at_all(self):
        # The first gather had \\b in a raw string, so no strong keyword ever matched.
        self.assertTrue(gather.KW.search('compiled checkpoint retained'))
        self.assertTrue(gather.KW.search('do not delete'))

    def test_absolute_path_retained(self):
        p = C + 'codex-kv08-observer-1105/cache'
        self.assertIn(('Q', p), blockers(f'E6 {p} 28GB protected compiled checkpoint retained'))

    def test_bare_name_retained(self):
        got = blockers('Artifacts on Intel2 codex-head-phase-host-1106/boot_full_tt1, compiled archive retained')
        self.assertTrue(any(k == 'QREL' and 'codex-head-phase-host-1106' in t for k, t in got), got)

    def test_pruner_posts_do_not_protect(self):
        self.assertEqual(blockers(f'[CODEX-PRUNE-1 -> COORD] kept {C}codex-x-1106 as protected'), [])

    def test_unrelated_line(self):
        self.assertEqual(blockers(f'measured skew on {C}codex-x-1106 was 40 ps'), [])


def fixture(root, tree, global_rows, kw_empty_with_refs=False):
    """A minimal scan: only intel2 has dirs. tree = {path: depth}."""
    old = int(time.time()) - 3 * 86400
    with open(root + '/global.tsv', 'w') as f:
        for r in global_rows:
            f.write('\t'.join(r) + '\n')
    json.dump({'items': {}}, open(root + '/kit_wave_state.json', 'w'))
    open(root + '/kit_wave_stages.tsv', 'w').write('die\titem\n')
    json.dump({'plans': {}, 'signed_records': []}, open(root + '/cache.json', 'w'))
    for h in HOSTS:
        d = f'{root}/scan/{h}'
        os.makedirs(d)
        for n in 'proc.tsv kw.tsv odbs.tsv rec.jsonl git.tsv keeps.tsv'.split():
            open(f'{d}/{n}', 'w').close()
        with gzip.open(f'{d}/refs.tsv.gz', 'wt') as f:
            if kw_empty_with_refs and h == 'intel2':
                f.write(os.urandom(64).hex() + '\n')
        with gzip.open(f'{d}/dirs.jsonl.gz', 'wt') as f:
            if h == 'intel2':
                for p, depth in tree.items():
                    f.write(json.dumps(dict(path=p, depth=depth, bytes=1 << 30, shared=0, files=9, newest=old, keep=0, signed=0,
                                            git=0, locked=0, stub=0, syml=0, odb=0, other_uid=0, self_keep=0, self_git='',
                                            self_stub=0)) + '\n')


def classify(root, preview=True):
    env = dict(os.environ, CP_ROOT=root, CACHE=root + '/cache.json')
    env.pop('PREVIEW', None)
    if preview:
        env['PREVIEW'] = '1'
    return subprocess.run([sys.executable, '-I', HERE + '/classify.py'], env=env, capture_output=True, text=True)


def plan(root):
    return {l.split('\t')[0]: l.split('\t')[1] for l in open(root + '/plan/intel2.tsv')}


class Classify(unittest.TestCase):
    TREE = {C + 'codex-top-1106': 0, C + 'codex-top-1106/kid': 1,
            C + 'codex-rel-1106': 0, C + 'codex-rel-1106/kid': 1,
            C + 'codex-deep-1106': 0, C + 'codex-deep-1106/obs': 1, C + 'codex-deep-1106/obs/sibling': 2,
            C + 'codex-free-1106': 0}
    ROWS = [('Q', 'any', C + 'codex-top-1106', 'q:1'),
            ('QREL', 'any', 'codex-rel-1106', 'q:2'),
            ('Q', 'any', C + 'codex-deep-1106/obs/model.a', 'q:3')]

    def test_cites_keep_their_trees(self):
        with tempfile.TemporaryDirectory() as r:
            fixture(r, self.TREE, self.ROWS)
            p = classify(r)
            self.assertEqual(p.returncode, 0, p.stderr[-2000:])
            a = plan(r)
            for k in ('codex-top-1106', 'codex-rel-1106', 'codex-deep-1106/obs'):
                self.assertNotIn(a.get(C + k, 'absent'), ('DELETE', 'GITRM'), (k, a))
            self.assertNotIn(a.get(C + 'codex-top-1106/kid', 'absent'), ('DELETE',), a)
            self.assertNotIn(a.get(C + 'codex-rel-1106/kid', 'absent'), ('DELETE',), a)
            # a retained file keeps what sits beside it: "observer/model.a retained" needs the rest of observer
            self.assertNotIn(a.get(C + 'codex-deep-1106/obs/sibling', 'absent'), ('DELETE',), a)
            self.assertEqual(a.get(C + 'codex-free-1106'), 'DELETE', a)

    def test_incomplete_scan_refused(self):
        with tempfile.TemporaryDirectory() as r:
            fixture(r, self.TREE, self.ROWS, kw_empty_with_refs=True)
            self.assertNotEqual(classify(r, preview=False).returncode, 0)
            self.assertEqual(classify(r, preview=True).returncode, 0)


class QueueArchive(unittest.TestCase):
    """COORD-COMMIT-SPEED-1 11-13: the queue was rotated; posts before 2026-11-12 live in lanes/archive/COORD-REVIEW-QUEUE-*.md.
    A retention post there must still protect its tree inside QDAYS, and an archive line older than the window must not."""

    def test_archive_read_inside_window_only(self):
        p_new = C + 'codex-archived-keep-1110/ckpt'
        p_old = C + 'codex-ancient-keep-1020/ckpt'
        p_live = C + 'codex-live-keep-1113/ckpt'
        now = time.mktime(time.strptime('2026-11-13 08:00', '%Y-%m-%d %H:%M'))
        with tempfile.TemporaryDirectory() as coord:
            os.makedirs(coord + '/lanes/archive')
            with open(coord + '/lanes/archive/COORD-REVIEW-QUEUE-20261024-20261111.md', 'w') as f:
                f.write('# COORD-REVIEW-QUEUE (ROOT-MERGE, 2026-10-24)\n'
                        f'- 2026-10-20 09:00 PST STATE [X-1 -> COORD] {p_old} retained\n'
                        f'- 2026-11-10 09:00 PST STATE [X-2 -> COORD] {p_new} retained, do not delete\n')
            with open(coord + '/lanes/COORD-REVIEW-QUEUE.md', 'w') as f:
                f.write('# COORD-REVIEW-QUEUE (live)\n'
                        f'- 2026-11-13 07:00 PST STATE [X-3 -> COORD] {p_live} kept\n')
            rows = gather.queue_window(coord, 14, now=now)
            got = []
            for src, i, l in rows:
                gather.line_blockers(l, '%s:%d' % (src, i), lambda k, h, t, s: got.append((k, t, s)))
            paths = {t for k, t, s in got}
            self.assertIn(p_new, paths)
            self.assertIn(p_live, paths)
            self.assertNotIn(p_old, paths)
            srcs = {t: s for k, t, s in got}
            self.assertEqual(srcs[p_new], 'COORD-REVIEW-QUEUE-20261024-20261111:2')
            self.assertEqual(srcs[p_live], 'queue:1')

    def test_live_only_still_works(self):
        now = time.mktime(time.strptime('2026-11-13 08:00', '%Y-%m-%d %H:%M'))
        with tempfile.TemporaryDirectory() as coord:
            os.makedirs(coord + '/lanes')
            with open(coord + '/lanes/COORD-REVIEW-QUEUE.md', 'w') as f:
                f.write(f'- 2026-11-12 07:00 PST STATE [X-3 -> COORD] {C}codex-only-1112 retained\n')
            rows = gather.queue_window(coord, 14, now=now)
            self.assertEqual([(s, i) for s, i, _ in rows][:1], [('queue', 0)])


if __name__ == '__main__':
    unittest.main()
