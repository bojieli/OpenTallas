#!/usr/bin/env python3
"""auto_clean_hub (FLEET-OPS-R, COORD 11-18, OWNER: aggressive cleanup automated on each host): WATCHDOG + 4-hourly report only.  The cleanup itself is the user timer ot-auto-clean on each build host
(install_auto_clean.sh).  This hub cron (every 15 min) alerts when a host last pass is older than 90 min and posts the 4-hourly report.
The per-host pass (formerly driven from here):  Per host (intel1 epyc2 epyc7 epyc8 epyc9 epyc10) it runs tools/fleet/ot-auto-retire-run.sh apply with AC_FULL=1 over ssh:
  source trees superseded (reference proof), failed / cancelled / superseded kit-wave attempts at once (30 min quiet), old-event attempts and idle lane trees after 12 h,
  every delete through ot_delete_guard (live process, protected refs, SIGNED not in the signed store, git work not pushed / bare repo, hub post of the last 24 h, pending adoption).
Log: ~/.local/state/auto-clean/<host>.log (one line per run: time, df before, df after, deleted, refused, failed) + log.jsonl per tree on each host.
Every 4 h (state file) it posts one INFO to FLEET-OPS-R: GB freed per host since the last report and the top 5 writers per host (lane_quota scan, last 4 h).
usage: auto_clean_hub.py [--hosts h1,h2] [--report] [--dry]"""
import concurrent.futures as cf, fcntl, json, os, re, subprocess, sys, time

HOSTS = ["intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10"]
STATE = os.path.expanduser("~/.local/state/auto-clean")
RT = "/srv/opentallas-scratch2/claude/rt/current/tools/fleet"
REPORT_EVERY_S = 4 * 3600
STALE_S = 90 * 60
POST = os.path.expanduser("~/coord/bin/post.sh")
SSH = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none"]


def read_status(host, run=subprocess.run):
    """-> (age_s of the host's last pass or None, [host.log lines]) over ssh"""
    cmd = "cat ~/.local/state/auto-clean/last-pass 2>/dev/null; echo ---; tail -n 120 ~/.local/state/auto-clean/host.log 2>/dev/null"
    try:
        r = run(SSH + [host, cmd], capture_output=True, text=True, timeout=60)
        head, _, tail = (r.stdout or "").partition("---\n")
        return (time.time() - float(head.strip())) if head.strip() else None, tail.splitlines()
    except Exception:
        return None, []


def freed_since(lines, since):
    """GB freed (sum of positive after-before) by passes logged after `since` (epoch)"""
    tot = 0.0
    for l in lines:
        m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) .*before_gb=(\d+) free_gb=(\d+)", l)
        if not m:
            continue
        try:
            if time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")) > since:
                tot += max(0, int(m.group(3)) - int(m.group(2)))
        except ValueError:
            pass
    return tot


def watchdog(hosts, st, now=None, run=subprocess.run, poster=None):
    """ALERT (one per host per hour) when a host's last pass is older than STALE_S or missing; -> ({host: lines}, [alerts])"""
    now = now or time.time(); alerts, logs = [], {}
    al = st.setdefault("alerted", {})
    for h in hosts:
        age, lines = read_status(h, run); logs[h] = lines
        if (age is None or age > STALE_S) and now - al.get(h, 0) >= 3600:
            al[h] = now
            t = "ALERT [AUTO-CLEAN -> FLEET-OPS-R, COORD] %s: the automatic cleanup timer has not completed a pass for %s (limit %d min): check `systemctl --user status ot-auto-clean.timer` on %s" % (
                h, "ever" if age is None else "%d min" % (age / 60), STALE_S // 60, h)
            alerts.append(t)
            (poster or (lambda x: subprocess.run(["bash", POST, "FLEET-OPS-R", x], capture_output=True, timeout=120)))(t)
    return logs, alerts


def top_writers(host, run=subprocess.run, window_h=4):
    cmd = "timeout 900 python3 -I %s/lane_quota.py scan --root /srv/opentallas-scratch2/claude --window-h %d --quota-gb 0" % (RT, window_h)
    try:
        r = run(SSH + [host, cmd], capture_output=True, text=True, timeout=1000)
        d = json.loads((r.stdout or "").strip().splitlines()[-1])
        return sorted(d.items(), key=lambda kv: -kv[1])[:5]
    except Exception:
        return None


def report(freed, now=None, run=subprocess.run, poster=None):
    """freed = {host: GB freed since the last report}; one post with the top 5 writers per host"""
    with cf.ThreadPoolExecutor(max_workers=len(HOSTS)) as ex:
        tw = dict(zip(HOSTS, ex.map(lambda h: top_writers(h, run), HOSTS)))
    parts = []
    for h in HOSTS:
        w = tw.get(h)
        parts.append("%s freed %.0f GB, top writers 4 h: %s" % (h, freed.get(h, 0.0), ", ".join("%s %.0f GB" % kv for kv in w) if w else "scan did not return"))
    text = "INFO [AUTO-CLEAN -> COORD] 4-hourly cleanup report: " + " | ".join(parts)
    (poster or (lambda t: subprocess.run(["bash", POST, "FLEET-OPS-R", t], capture_output=True, timeout=120)))(text)
    return text


def main(argv=None):
    """watchdog every run; the 4-hourly report"""
    a = sys.argv[1:] if argv is None else argv
    hosts = a[a.index("--hosts") + 1].split(",") if "--hosts" in a else HOSTS
    os.makedirs(STATE, exist_ok=True)
    lk = open(os.path.join(STATE, "lock"), "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    sf = os.path.join(STATE, "state.json")
    try:
        st = json.load(open(sf))
    except (OSError, ValueError):
        st = {}
    logs, alerts = watchdog(hosts, st)
    for t in alerts:
        print(t)
    now = time.time()
    if "--report" in a or now - st.get("report_t", 0) >= REPORT_EVERY_S:
        since = st.get("report_t", now - REPORT_EVERY_S)
        print(report({h: freed_since(logs.get(h, []), since) for h in hosts}, now))
        st["report_t"] = now
    json.dump(st, open(sf, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
