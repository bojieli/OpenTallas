"""BIND-REPORT-STALE-1123 (COORD 16:1x, KV K3e): a bind that crashed before writing OUT/bind_report.json left the previous run's
report in place (11:11), and the driver read it as this run's result four times until NO_FIXED_POINT.

  set_aside(out)          at bind run start: an existing OUT/bind_report.json is renamed to OUT/bind_report.json.prev (never
                          rewritten in place: the file may be a hardlink shared with published trees), so a crashed run leaves
                          no report at all
  load_fresh(out, t0)     a consumer that has just run a bind reads the report only when its mtime is not older than the run
                          start t0; otherwise (or when it is missing) StaleBindReport, message starting BIND-REPORT-STALE
"""
import json
import os
import time
from pathlib import Path

NAME = "bind_report.json"
PREV = NAME + ".prev"
SLACK_S = 2.0          # coarse file-system timestamps never make a report written by this run read as stale


class StaleBindReport(RuntimeError):
    pass


def set_aside(out):
    """rename OUT/bind_report.json to OUT/bind_report.json.prev -> the .prev path, or None when there was no report"""
    p = Path(out) / NAME
    if not (p.is_file() or p.is_symlink()):
        return None
    prev = Path(out) / PREV
    os.replace(p, prev)
    return prev


def check_fresh(out, t0, slack=SLACK_S):
    """-> the report path when OUT/bind_report.json was written by the run that started at t0 (epoch s); else StaleBindReport"""
    p = Path(out) / NAME
    try:
        m = p.stat().st_mtime
    except FileNotFoundError:
        raise StaleBindReport(f"BIND-REPORT-STALE {p}: no report from this bind run (started {_ts(t0)}); the bind ended "
                              f"before writing it (see its log)") from None
    if m < t0 - slack:
        raise StaleBindReport(f"BIND-REPORT-STALE {p}: written {_ts(m)}, before this bind run started {_ts(t0)}; the bind "
                              f"ended before writing a new report (see its log): the old report is not this run's result")
    return p


def load_fresh(out, t0, slack=SLACK_S):
    """check_fresh + json load"""
    return json.loads(check_fresh(out, t0, slack).read_text())


def _ts(t):
    return time.strftime("%m-%d %H:%M:%S", time.localtime(t))
