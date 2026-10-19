import unittest
from identity_verdict import Identity, Scoreboard, parse_verdict


I = Identity(3, 7, 19, 2)
WRONG = Identity(4, 7, 19, 2)


def active(cls=Scoreboard):
    board = cls([I])
    assert board.accept(I, 2, monitors_known=True)
    assert board.run(I, run_ok=True)
    return board


def complete(board):
    assert board.result(I, 0)
    assert board.result(I, 1)
    assert board.source_complete(I)


class FallbackMutant(Scoreboard):
    def status(self, identity, **kwargs):
        if identity not in self.requests:
            identity = next(iter(self.requests))
        return super().status(identity, **kwargs)


class TraceMaskMutant(Scoreboard):
    def observe_status(self, **kwargs):
        if not kwargs.get('trace_on'):
            return False
        return super().observe_status(**kwargs)


class UnguardedMutant(Scoreboard):
    def observe_status(self, **kwargs):
        kwargs['authoritative'] = True
        return super().observe_status(**kwargs)


class IdentityControls(unittest.TestCase):
    def test_success_requires_actual_programme(self):
        board = active()
        complete(board)
        self.assertTrue(board.observe_status(authoritative=True, valid=True,
                                            identity=I, trace_on=False))
        self.assertTrue(board.finish())
        self.assertEqual(board.successful_count, 1)

    def test_raw_startup_not_transaction(self):
        board = Scoreboard([I])
        board.observe_status(authoritative=False, valid=True, identity=WRONG)
        self.assertEqual(board.raw_status_count, 1)
        self.assertEqual(len(board.raw), 1)
        self.assertFalse(board.requests)
        self.assertFalse(board.errors)
        self.assertFalse(board.finish())
        self.assertIn('PROGRAMME_EXECUTED', board.errors[0])
        mutant = UnguardedMutant([I])
        mutant.observe_status(authoritative=False, valid=True, identity=WRONG)
        self.assertTrue(mutant.errors, 'unguarded startup mutant must be detected')
        print('MUTANT_CAUGHT unguarded-startup: pre-authority error ledger mutated')

    def test_first_known_idle_and_trace_mask_control(self):
        for cls, expected_error in [(Scoreboard, True), (TraceMaskMutant, False)]:
            board = cls([I])
            board.observe_status(authoritative=True, valid=True, identity=WRONG,
                                 payload_valid=False, trace_on=False)
            self.assertEqual(bool(board.errors), expected_error)
            self.assertEqual(board.successful_count, 0)
        print('MUTANT_CAUGHT trace-mask: first-known idle malformed STATUS hidden')

    def test_no_fallback_control(self):
        for cls, expected_count in [(Scoreboard, 0), (FallbackMutant, 1)]:
            board = active(cls)
            complete(board)
            board.observe_status(authoritative=True, valid=True, identity=WRONG)
            self.assertEqual(board.successful_count, expected_count)
        # The same required oracle rejects the fallback mutant.
        self.assertNotEqual(expected_count, 0)
        print('MUTANT_CAUGHT fallback: wrong identity retired an owned request')

    def test_duplicates_and_order(self):
        board = active()
        self.assertFalse(board.result(I, 1))
        self.assertTrue(board.result(I, 0))
        self.assertFalse(board.result(I, 0))
        self.assertFalse(board.status(I))
        self.assertFalse(board.status(WRONG))
        self.assertEqual(board.successful_count, 0)
        self.assertTrue(board.result(I, 1))
        self.assertTrue(board.source_complete(I))
        self.assertTrue(board.status(I))
        self.assertFalse(board.status(I))
        self.assertEqual(board.successful_count, 1)
        self.assertFalse(board.finish())

    def test_missing_run_or_admission(self):
        board = Scoreboard([I])
        self.assertFalse(board.accept(I, 2, monitors_known=False))
        self.assertFalse(board.run(I, run_ok=True))
        self.assertTrue(board.accept(I, 2, monitors_known=True))
        self.assertFalse(board.status(I))
        self.assertFalse(board.finish())
        self.assertTrue(any('PROGRAMME_EXECUTED' in e for e in board.errors))

    def test_error_status_is_not_success(self):
        board = active()
        self.assertTrue(board.status(I, success=False))
        self.assertTrue(board.requests[I].terminal)
        self.assertEqual(board.successful_count, 0)
        self.assertFalse(board.finish())

    def test_unknown_valid_and_malformed(self):
        board = active()
        complete(board)
        self.assertFalse(board.observe_status(authoritative=True, valid=None))
        self.assertFalse(board.status(I, payload_valid=False))
        self.assertFalse(board.status(I, success=None))
        self.assertEqual(board.successful_count, 0)

    def test_exact_identity_fields(self):
        for wrong in [Identity(4,7,19,2), Identity(3,8,19,2),
                      Identity(3,7,20,2), Identity(3,7,19,3), None]:
            board = active()
            complete(board)
            self.assertFalse(board.status(wrong))
            self.assertEqual(board.successful_count, 0)

    def test_verdicts(self):
        for text, rc, passed in [
            ('SMOKE_PASS',0,True), ('SMOKE_FAIL errors=19',0,False),
            ('SMOKE_PASS',1,False), ('',0,False),
            ('SMOKE_PASS\nSMOKE_PASS',0,False),
            ('SMOKE_FAIL\nSMOKE_PASS',0,False),
            ('SMOKE_PASS\nSMOKE_FAIL',0,False),
            ('NOT_SMOKE_PASS',0,False), ('SMOKE_PASSING',0,False)]:
            self.assertEqual(parse_verdict(text,rc)[0],passed, (text,rc))


if __name__ == '__main__':
    unittest.main(verbosity=2)
