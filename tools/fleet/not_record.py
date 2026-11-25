"""The ONE definition of "canary / test run, never a sign-off of record" (FABLE-FLOW-0000 F9; DISK-RECLAIM 11-25 COORD ruling).
auto_export.py sets such runs aside (never exports them) and ot_delete_guard.signed_unexported_refusal must not refuse them as "not exported":
both import this predicate, nobody copies the regex."""
import re

NOT_RECORD = re.compile(r"/(flow-canary|test_[^/]*|[^/]*pyt-[^/]*|[^/]*pytest[^/]*|fixtures?)/")
