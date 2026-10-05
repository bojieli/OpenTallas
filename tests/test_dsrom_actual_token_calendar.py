from tools.dsrom_actual_token_calendar import observe


class Cached:
    users, steps, plen, ngen, nodes = 1, 4, 3, 2, 5
    def expected_output(self, user, pos):
        if user != 0 or not 0 <= pos < 4:
            raise ValueError('unowned')
        return [2815, 3537, 2047, 3676][pos]
    def input_token(self, user, pos, *, previous_completion=None):
        return [0, 3563, 3745][pos] if pos < 3 else previous_completion[2]


def complete():
    lines = []
    for pos, token in enumerate([2815, 3537, 2047, 3676]):
        lines += [f'TOK user=0 pos={pos} token={token} cycle={100 + 70*pos}',
                  f'CPL TOKEN tag=5a user=0 pos={pos} token={token} stamp={100 + 70*pos}']
    return '\n'.join(lines + ['CPL DONE tag=5a users=1 stamp=320',
        'HDC41_ARRAY nodes=5 users=1 generated=2 mismatches=0 logit_mismatch=0 lm_head_checks=4 state_mismatch=0 total_cycles=330',
        'USERS_DONE 1', 'PASS'])


def test_whole_token_reuses_actual_feedback_and_only_measured_intervals():
    r = observe(complete(), Cached(), terminal_rc=0)
    assert r['verdict'] == 'REDUCED_ACTUAL_TOKEN_COMPARISON_PASS'
    assert [x['input_token'] for x in r['tokens']] == [0, 3563, 3745, 2047]
    assert [x['interval_from_previous_token_cycles'] for x in r['tokens']] == [None, 70, 70, 70]
    assert r['first_token_latency_cycles'] is None and r['field_calendar'] is None


def test_live_or_unowned_completion_cannot_publish_terminal_pass():
    assert observe(complete(), Cached())['verdict'] == 'INCOMPLETE_ACTUAL_TOKEN_RECORD'
    text = complete().replace('CPL TOKEN tag=5a user=0 pos=2 token=2047 stamp=240\n', '')
    r = observe(text, Cached(), terminal_rc=0)
    assert r['verdict'] == 'INCOMPLETE_ACTUAL_TOKEN_RECORD'
    assert r['tokens'][3]['input_token'] is None
    assert observe(complete().replace('tag=5a', 'tag=3f'), Cached(), terminal_rc=0)['verdict'] == 'REJECTED_ACTUAL_TOKEN_RECORD'


def test_mismatch_duplicate_and_failed_process_are_retained_rejections():
    for text, rc in [(complete().replace('state_mismatch=0', 'state_mismatch=1'), 0),
                     (complete() + '\nTOK user=0 pos=3 token=3676 cycle=310', 0),
                     (complete(), 1)]:
        assert observe(text, Cached(), terminal_rc=rc)['verdict'] == 'REJECTED_ACTUAL_TOKEN_RECORD'
