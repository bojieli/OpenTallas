"""TEE-STATUS (FLOW-OPS-R2 11-22, FABLE-FLOW-2200 item 2; class of KEEP-RC-1121 650916ebb262): the run_kit container shell has no
pipefail, so `cmd | tee log` reports tee's status and hides cmd's.  Every `| tee` in gen_phys must take its input from a message
producer (echo / printf / grep / sed / cat) whose status nobody reads; a step whose status matters captures it first
(KL=$(cmd); kk=$?; echo "$KL" | tee ...).  A global `set -o pipefail` is NOT used there: conditions such as `cmd | grep -q` would
turn false on SIGPIPE."""
import re
from pathlib import Path

SRC = (Path(__file__).resolve().parent / "gen_phys.py").read_text()
OK = re.compile(r"^(?:\S+\)\s*)?(echo|printf|grep|sed|cat)\b")      # optional case label: *) echo ...
SEP = re.compile(r"(?:;|&&|\|\||\||\(|\{|\bthen\b|\belse\b|\bdo\b)")


def _unquote(s):
    s = re.sub(r"\\\\\"(?:[^\\\\]|\\\\[^\"])*?\\\\\"", " Q ", s)      # \"...\" inside python strings
    s = re.sub(r"\\\"(?:[^\\]|\\[^\"])*?\\\"", " Q ", s)
    s = re.sub(r"'[^']*'", " Q ", s)
    s = re.sub(r"\"[^\"]*\"", " Q ", s)
    return s


def tee_producers(src=SRC):
    out = []
    for n, line in enumerate(src.split("\n"), 1):
        for m in re.finditer(r"\|\s*tee\b", line):
            left = _unquote(line[:m.start()]).rstrip()
            parts = SEP.split(left)
            out.append((n, parts[-1].strip() if parts else ""))
    return out


def test_every_tee_reads_a_message_producer():
    bad = [(n, p[:80]) for n, p in tee_producers() if not OK.match(p)]
    assert not bad, f"| tee hides the status of a real command (capture it first, see KEEP-RC-1121): {bad}"
    assert len(tee_producers()) >= 30


def test_lint_catches_the_keep_rc_pattern():
    old = 'x && python3 -I /work/tt_setup_keep.py /work/a.log /work/b.log | tee -a /work/k.log && mv a b'
    assert [p for _n, p in tee_producers(old)] == ["python3 -I /work/tt_setup_keep.py /work/a.log /work/b.log"]
    fixed = 'x && ( KL=$(python3 -I /work/tt_setup_keep.py a b); kk=$?; echo \\"$KL\\" | tee -a /work/k.log; exit $kk )'
    assert all(OK.match(p) for _n, p in tee_producers(fixed))
