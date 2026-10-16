"""min_count_regex shape check shared by the daemon's spec validation and submit_exact (ROOT 2026-10-16).

bench_work() counts re.findall(min_count_regex): with no capture group it counts the whole match text (never a digit
string -> vacuous), with more than one group findall returns tuples (never digits -> vacuous).  So exactly one group."""
import re


def count_regex_errors(benches):
    out = []
    for b in benches or []:
        mcr = b.get("min_count_regex") if isinstance(b, dict) else None
        if not mcr:
            continue
        try:
            ng = re.compile(mcr).groups
        except re.error as x:
            out.append(f"bench {b.get('name')}: min_count_regex does not compile: {x}")
            continue
        if ng != 1:
            out.append(f"bench {b.get('name')}: min_count_regex needs one capture group around the count: {mcr!r}"
                       + ("" if ng == 0 else f" (has {ng} groups; use (?:...) for the others)"))
    return out


# BENCH-LINT (ROOT 2026-10-16): three recurring bench-spec defects cost full routes today --
#  * benches calling git (git show <commit>:path, rev-parse ...) although benches run in a NON-GIT source export: the
#    bench dies after the route (rc 128 'not a git repository') unless the line carries its own fallback;
#  * expect=fail benches with no fail_regex: rc != 0 alone reads a crash / missing file as "mutant detected";
#  * fail_regex / pass_regex never matched against the bench's REAL output (a regex for a line the bench never prints).
# bench_lint() returns (errors, warnings).  Errors: a git call with no fallback on its line ('||') and no declared
# bench "git_fallback": "<how it works without git>"; a regex that does not compile; a declared witness log
# ("fail_witness" / "pass_witness": repo path, at the source commit, of a captured REAL bench output) that is missing
# or not matched.  Warnings: expect=fail without fail_regex; a fail_regex with no fail_witness.  `show(path)` (optional)
# returns a repo file's text at the source commit (scripts the bench command calls are scanned one level deep).
GIT_SH_RE = re.compile(r"\bgit\s+(?:(?:-C|-c|--git-dir|--work-tree)[\s=]+\S+\s+|--no-pager\s+)*"
                       r"(show|rev-parse|ls-files|ls-tree|log|diff|cat-file|describe|status|archive|grep|blame|checkout|worktree)\b")
GIT_PY_RE = re.compile(r"""["']git["']\s*,\s*(?:["'][^"']*["']\s*,\s*|[\w.()\[\]]+\s*,\s*)*?"""
                       r"""["'](show|rev-parse|ls-files|ls-tree|log|diff|cat-file|describe|status|archive|grep|blame)["']""")
SCRIPT_RE = re.compile(r"(?<![\w$}/])(?:\{SRC\}/|\$\{?SRC\}?/|\./)?((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:sh|py|tcl))\b")


def git_calls(text):
    """[(line_no, line)] of git invocations with no same-line fallback, comments skipped.  A fallback is '||' after the
    call, or the call sits in an if condition / else branch on its line (if git rev-parse ..; then git show ..; or
    if [ -f x ]; then cp ..; else git show ..; fi)"""
    out = []
    for n, line in enumerate((text or "").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        for rx in (GIT_SH_RE, GIT_PY_RE):
            m = rx.search(line)
            if m and "||" not in line[m.end():] and not re.search(r"\b(?:if|elif|else)\b", line[:m.start()]):
                out.append((n, s[:160]))
                break
    return out


def _regex_error(b, key):
    rx = b.get(key)
    if not rx:
        return None
    try:
        re.compile(rx, re.M)
    except re.error as x:
        return f"bench {b.get('name')}: {key} does not compile: {x}"
    return None


def bench_lint(benches, show=None):
    errors, warnings = [], []
    for b in benches or []:
        if not isinstance(b, dict):
            continue
        name, cmd = b.get("name"), b.get("cmd") or ""
        texts = [("cmd", cmd)]
        if show is not None:
            for sc in sorted(set(SCRIPT_RE.findall(cmd))):
                body = show(sc)
                if body:
                    texts.append((sc, body))
        fb = b.get("git_fallback")
        if not (isinstance(fb, str) and fb.strip()):
            hits = [f"{where}:{n}: {line}" for where, t in texts for n, line in git_calls(t)]
            if hits:
                errors.append(f"bench {name}: calls git but benches run in a NON-GIT source export ({'; '.join(hits[:3])}) "
                              f"-- read the file from the snapshot (add its directory to source.extra_paths), give the "
                              f"line its own '|| <fallback>', or declare git_fallback: '<how it works without git>'")
        for key in ("fail_regex", "pass_regex"):
            e = _regex_error(b, key)
            if e:
                errors.append(e)
        expect = b.get("expect")
        if expect == "fail" and not b.get("fail_regex"):
            warnings.append(f"bench {name}: expect=fail without fail_regex -- any rc != 0 (a crash, a missing file) "
                            f"reads as a detected mutant; set fail_regex to the mutant's real verdict line")
        for key, wkey in (("fail_regex", "fail_witness"), ("pass_regex", "pass_witness")):
            rx, wit = b.get(key), b.get(wkey)
            if wit and not rx:
                errors.append(f"bench {name}: {wkey} given without {key}")
                continue
            if not rx or _regex_error(b, key):
                continue
            if not wit:
                if key == "fail_regex":
                    warnings.append(f"bench {name}: fail_regex {rx!r} not verified against real mutant output "
                                    f"(commit a captured mutant log and name it in fail_witness)")
                continue
            if show is None:
                continue
            body = show(str(wit).lstrip("./"))
            if body is None:
                errors.append(f"bench {name}: {wkey} {wit} not in the source commit")
            elif re.search(rx, body, re.M) is None:
                errors.append(f"bench {name}: {key} {rx!r} does not match its {wkey} {wit} (the bench's real output)")
    return errors, warnings
