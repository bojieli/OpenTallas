"""Mutation tests for the read-only checker; fixture logs are not RTL evidence."""
import hashlib
import unittest
from types import SimpleNamespace

from dsrom_reduced_system_readback import check_log, user_accepted_three_tokens


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.b = SimpleNamespace(users=1, steps=4,
                                 prep={'config': {'fixture': True}, 'input_sha256': {'fixture': 'sha'}},
                                 expected_output=lambda u, p: [2815, 3537, 2047, 3676][p])
        rows = []
        for p, token in enumerate([2815, 3537, 2047, 3676]):
            rows += [f'TOK user=0 pos={p} token={token} cycle=10',
                     f'CPL TOKEN tag=5a user=0 pos={p} token={token} stamp=10']
        for n in range(5):
            rows += [f'NODE node={n} jobs=4 state_mismatch=0',
                     f'HBM_NODE node={n} q_bad=0 q_fault=0 q_words=1 q_reads=1 idx_records=1 idx_writes=12',
                     f'LINK link={n} fault=0 code=0']
        rows += ['HOSTCQ tokens_dev=4 tokens_cpl=4 done_cpl=1 err_cpl=0 cpl_mismatch=0 fault=0 code=0 wdog=0',
                 'KVHBM ops=1 words=1 writes=1 state_bad=0 fault=00000',
                 'IDXHBM_USERS read=1 wrote=1',
                 'HDC41_ARRAY nodes=5 users=1 generated=2 mismatches=0 logit_mismatch=0 lm_head_checks=8 state_mismatch=0 total_cycles=100',
                 'USERS_DONE 1', 'PASS']
        self.text = '\n'.join(rows) + '\n'

    def terminal(self, text, rc=0):
        return {'returncode': rc, 'config_name': 'sys_b5_p3g2',
                'config': self.b.prep['config'], 'input_sha256': self.b.prep['input_sha256'],
                'log_sha256': hashlib.sha256(text.encode()).hexdigest()}

    def test_complete_fixture_scopes_internal_comparisons_only(self):
        r = check_log(self.text, self.b, self.terminal(self.text))
        self.assertEqual(r['compared_logit_words'], 16160)
        for k in ('raw_field_export', 'full_shape_qualified',
                  'accepted_write_visibility_qualified', 'global_drain_qualified'):
            self.assertFalse(r[k])

    def test_no_terminal_never_qualifies_even_with_pass(self):
        self.assertFalse(check_log(self.text, self.b, None)['numerical_qualified'])

    def test_bare_pass_rejected(self):
        with self.assertRaises(ValueError):
            check_log('PASS\n', self.b, self.terminal('PASS\n'))

    def test_missing_or_false_coverage(self):
        mutations = [self.text.replace('lm_head_checks=8', 'lm_head_checks=1'),
                     self.text.replace('NODE node=4 jobs=4 state_mismatch=0\n', ''),
                     self.text.replace('pos=3 token=3676', 'pos=3 token=3118'),
                     self.text.replace('tag=5a', 'tag=5b'),
                     self.text.replace('q_words=1', 'q_words=0'),
                     self.text.replace('fault=00000', 'fault=0000x'),
                     self.text.replace('USERS_DONE 1', 'USERS_DONE 0'),
                     self.text.replace('writes=1 state_bad', 'writes=0 state_bad'),
                     self.text + 'LOGIT node=4 mismatch=1\n',
                     self.text + 'TOK user=0 pos=3 token=3676 cycle=10\n',
                     self.text.replace('state_mismatch=0', 'state_mismatch=1')]
        for text in mutations:
            with self.subTest(text=text[-150:]), self.assertRaises(ValueError):
                check_log(text, self.b, self.terminal(text))

    def test_authoritative_rc_and_log_pin_required(self):
        for t in [self.terminal(self.text, 1), self.terminal('other'),
                  {**self.terminal(self.text), 'input_sha256': {}}]:
            with self.subTest(t=t), self.assertRaises(ValueError):
                check_log(self.text, self.b, t)

    def test_explicit_user_stop_retains_three_tokens_without_final_pass(self):
        text = '\n'.join(line for line in self.text.splitlines()
                         if line.startswith(('TOK ', 'CPL TOKEN ')) and 'pos=3' not in line) + '\n'
        r = user_accepted_three_tokens(text, self.b)
        self.assertEqual(r['status'], 'INTENTIONAL_USER_STOP_ACCEPTED_THREE_TOKENS')
        self.assertEqual([t['token'] for t in r['tokens']], [2815, 3537, 2047])
        self.assertTrue(r['token_comparison_pass'])
        self.assertFalse(r['numerical_qualified'])
        self.assertFalse(r['full_four_position_pass'])
        self.assertFalse(r['final_state_checks_available'])
        with self.assertRaises(ValueError):
            user_accepted_three_tokens(self.text, self.b)
        with self.assertRaises(ValueError):
            user_accepted_three_tokens(text.replace('tag=5a', 'tag=5b'), self.b)


if __name__ == '__main__':
    unittest.main()
