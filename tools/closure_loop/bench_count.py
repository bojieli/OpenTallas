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
