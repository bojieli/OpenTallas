"""FLOW-HEALTH-1 11-19 (FABLE-FLOW-0755 item I, fourth window): a terminated host (epyc3/4/5/6) is never a TARGET in a default host list.

Scans the code of tools/fleet, tools/autopilot, tools/auto_owner for a host list default, a host dict key or a relay host that names one.  Deny lists
(RETIRED / OFF_LIMITS / retired_hosts / the node-name -> alias map), prose, docstrings and comments are not targets and are skipped."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRS = ("tools/fleet", "tools/autopilot", "tools/auto_owner")
SKIP_FILES = re.compile(r"(^|/)(test_[^/]*|[^/]*\.(json|md|log|tsv|txt|bak[^/]*)|epyc6_retire/.*|evidence/.*|prune_codex/.*|preserve_h1v_archives\.py|prestage_h1v_compressed\.py)$")
# prune_codex parses old host:path prefixes out of lane files (recognising a retired name is its job); the two h1v scripts are one-shot 10-10 archive jobs
TERM = r"(?:ot-)?epyc[3456]"
# a target: a quoted token that is exactly the host, or a quoted comma/colon/equals list that contains it
TARGET = re.compile(r"""["']""" + TERM + r"""["']|["'][^"'\n]*(?<![\w-])""" + TERM + r"""(?![\w-])[^"'\n]*[,=][^"'\n]*["']|["'][^"'\n]*[,=][^"'\n]*(?<![\w-])""" + TERM + r"""(?![\w-])[^"'\n]*["']""")
DENY_LINE = re.compile(r"\bnot in\b|\brow\(|\bdisk\(|drop_low_disk|RETIRED|OFF_LIMITS|retired_hosts|NODE_ALIAS|aware-parakeet|devoted-wren|eager-sunfish|terminated|retired|\bTERM_HOSTS\b", re.I)


def code_lines(text):
    in_doc = False
    for n, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if s.count('"""') % 2 == 1:
            in_doc = not in_doc
            continue
        if in_doc or not s or s.startswith("#"):
            continue
        yield n, ln.split("  #")[0] if "  #" in ln else ln


def test_no_terminated_host_is_a_target_in_the_tools():
    bad = []
    for d in DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            rel = p.relative_to(ROOT).as_posix()
            if not p.is_file() or SKIP_FILES.search(rel) or p.suffix in (".pyc", ".sh") and False:
                continue
            try:
                text = p.read_text(errors="replace")
            except OSError:
                continue
            if p.suffix not in ("", ".py", ".sh"):
                continue
            for n, ln in code_lines(text):
                if TARGET.search(ln) and not DENY_LINE.search(ln):
                    bad.append(f"{rel}:{n}: {ln.strip()[:110]}")
    assert not bad, "\n".join(bad)


def test_the_scanner_finds_what_it_should():
    hit = lambda s: bool(TARGET.search(s)) and not DENY_LINE.search(s)
    assert hit('HOSTS = ["intel1", "epyc4", "epyc7"]') and hit('os.environ.get("X", "epyc2,intel1,epyc4,epyc7")') and hit('x = {"ot-epyc4": 1}')
    assert hit('hosts = "epyc2=150,epyc4=150"')
    assert not hit('_alt = [h for h in HOSTS if h not in ("epyc4", "epyc5")]') and not hit('RETIRED_HOSTS = ("epyc4", "epyc5", "epyc6")') and not hit('OFF_LIMITS = set("epyc4,epyc5".split(","))')
    assert not hit('HOSTS = ["intel1", "epyc10", "epyc7"]') and not hit('print("epyc40")')
