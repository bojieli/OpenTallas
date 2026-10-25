#!/usr/bin/env python3
"""Cron job (every minute) on rtx-pro: hand coordination between Claude and Codex around Claude usage limits.
Ported from tender-ray (epyc1) ~/bin/claude-autocontinue.py by lane INFRA 2026-10-24 (owner decision 11).

tmux layout on rtx-pro: session 0, window 0 pane 0 = Claude coordinator (CLAUDE_PANE 0:0.0),
window 1 pane 0 = Codex (CODEX_PANE 0:1.0). Keys are only sent into a pane whose current command is claude / codex
(or a shell for the Codex launch), never during --dry-run.

Limit detection (any of):
  * Claude pane: a usage/rate-limit message at the bottom of the coordinator pane while it is not working;
  * transcripts (NEW, owner decision 11): the coordinator's session transcript AND every lane-agent transcript
    (subagents/*.jsonl of the coordinator session, other session transcripts in the project dir) written in the last
    WINDOW minutes contain an API-error record (429 / rate_limit / "hit your ... limit") or a task notification
    "Agent terminated early due to an API error: ... limit", and no transcript has a normal assistant reply for
    QUIET_S since the newest limit record. This catches the 10-24 15:00-18:47 case: lane agents limited while the
    coordinator sat in a question dialog (its pane never showed the limit).
Modes:
  claude        normal watch. Limit seen -> write handoff, give Codex the coordinator role -> codex.
  codex         Codex works until the reset time (+2 min). Then ask Codex to hand back -> handing_back.
  handing_back  Codex replied "HANDOFF DONE" / wrote its handoff section (or 20 min passed) -> type "continue" into
                Claude's pane (closing an open question dialog first with Escape) -> resuming.
  resuming      Claude still limited -> back to codex; 10 min clean -> claude.
  plain         no Codex available: plain "continue" at the reset time.
Owner questions (decision 11): Codex and Claude ask them as plain text (OWNER? lines), never a blocking dialog.
  claude-autocontinue.py             one tick
  claude-autocontinue.py --dry-run   one tick: print detection + what would be sent; send nothing, change nothing
  claude-autocontinue.py --status    print state + detection
State and log: ~/.local/state/claude-autocontinue/.
"""
import glob, json, os, re, subprocess, sys, time, datetime as dt
from zoneinfo import ZoneInfo

CLAUDE = os.environ.get("CLAUDE_PANE", "0:0.0")
CODEX = os.environ.get("CODEX_PANE", "0:1.0")
PROJECT = os.path.expanduser(os.environ.get("CLAUDE_PROJECT_DIR_T", "~/.claude/projects/-home-ubuntu-OpenTallas"))
LOCAL_TZ = ZoneInfo("America/Los_Angeles")
GRACE = dt.timedelta(minutes=2)
NO_TIME_RETRY = dt.timedelta(minutes=5)
HANDBACK_TIMEOUT = dt.timedelta(minutes=20)
WINDOW_S = 45 * 60            # transcripts written in the last 45 min are watched
QUIET_S = 8 * 60              # no normal reply anywhere for 8 min after the newest limit record -> limited
COORD = os.path.expanduser("~/coord")
ROLE = os.path.join(COORD, "CODEX-ROLE.md")
CODEX_LOG = os.path.join(COORD, "CODEX-LOG.md")
HANDOFF_DIR = os.path.join(COORD, "handoff")
STATE_DIR = os.path.expanduser("~/.local/state/claude-autocontinue")
STATE = os.path.join(STATE_DIR, "state.json")
LOG = os.path.join(STATE_DIR, "log.txt")
CODEX_CMD = "cd ~/coord && codex -a never -s danger-full-access"
DRY = "--dry-run" in sys.argv or "--status" in sys.argv

# Claude Code's own limit messages, e.g. "Claude usage limit reached. Your limit will reset at 3pm (America/Los_Angeles)",
# "5-hour limit reached ∙ resets 3pm", "You've hit your limit · resets 10am (...)", "API Error: 429 ... rate_limit_error".
LIMIT_RE = re.compile(r"(usage limit reached|limit will reset|hit your (?:\w+ )?limit|(?:5-hour|weekly|session|opus|daily)"
                      r" limit reached|API Error:?\s*429|rate_limit_error|HTTP 429)", re.I)
RESET_RE = re.compile(r"reset[s]?\s*(?:at\s*)?(?:(\w{3,9}\s+\d{1,2},?\s+)?)(\d{1,2})(?::(\d{2}))?\s*([ap]m)"
                      r"(?:\s*\(([^)]+)\))?", re.I)
BUSY_RE = re.compile(r"esc to interrupt", re.I)          # Claude Code and Codex both show this while working
DIALOG_RE = re.compile(r"Enter to (?:select|confirm)|↑/↓ to navigate|Esc to cancel", re.I)  # open question/selection dialog


def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def local(t):
    return t.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M %Z")

def log(msg):
    if DRY:
        print("[dry] " + msg); return
    with open(LOG, "a") as f:
        f.write(f"{dt.datetime.now(LOCAL_TZ):%F %T %Z} {msg}\n")

def tmux(*a):
    return subprocess.run(["tmux", *a], capture_output=True, text=True)

def capture(pane, n=40):
    r = tmux("capture-pane", "-p", "-t", pane, "-S", f"-{n}")
    return None if r.returncode else [l for l in r.stdout.splitlines() if l.strip()]

def pane_cmd(pane):
    r = tmux("display-message", "-p", "-t", pane, "#{pane_current_command}")
    return r.stdout.strip() if r.returncode == 0 else None

def send_key(pane, key):
    if DRY:
        print(f"[dry] would press {key} in {pane}"); return
    tmux("send-keys", "-t", pane, key)

def type_line(pane, text):
    if DRY:
        print(f"[dry] would type into {pane}: {text[:300]}"); return
    tmux("send-keys", "-t", pane, "-l", text)
    time.sleep(0.5)
    tmux("send-keys", "-t", pane, "Enter")

def busy(lines):
    # the Claude status line ("... esc to interrupt ...") sits above the background-agent list, ~10 lines from the bottom
    return bool(BUSY_RE.search("\n".join(lines[-20:])))

def load():
    try:
        return json.load(open(STATE))
    except Exception:
        return {}

def save(s):
    if DRY:
        print(f"[dry] would save state {json.dumps(s)}"); return
    json.dump(s, open(STATE, "w"), indent=1)

def reset_time(m, now):
    hour, minute, ampm, tzname = int(m.group(2)), int(m.group(3) or 0), m.group(4).lower(), m.group(5)
    hour = hour % 12 + (12 if ampm == "pm" else 0)
    try:
        tz = ZoneInfo(tzname) if tzname else LOCAL_TZ
    except Exception:
        tz = LOCAL_TZ
    n = now.astimezone(tz)
    t = n.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if m.group(1):                                       # dated reset, e.g. "resets Oct 27, 9am"
        try:
            parts = m.group(1).replace(",", " ").split()
            d = dt.datetime.strptime(parts[0][:3] + " " + parts[1], "%b %d")
            t = t.replace(month=d.month, day=d.day)
            if t < n - dt.timedelta(days=1):
                t = t.replace(year=t.year + 1)
            return t
        except (ValueError, IndexError):
            pass
    if t <= n - dt.timedelta(minutes=30):                # time already passed today -> tomorrow
        t += dt.timedelta(days=1)
    return t

def claude_limit(lines):
    """-> (limited: bool, due: datetime|None, text) from the bottom of Claude's pane."""
    # only a line that carries both a limit phrase and a reset time (Claude's own banner), so a report that merely
    # mentions 429 / rate limits cannot trigger a takeover
    hits = [l for l in lines[-30:] if LIMIT_RE.search(l) and RESET_RE.search(l)]
    if not hits or busy(lines):
        return False, None, ""
    tail = hits[-1]
    hit = LIMIT_RE.search(tail)
    m = RESET_RE.search(tail)
    now = now_utc()
    due = (reset_time(m, now) + GRACE) if m else (now + NO_TIME_RETRY)
    return True, due.astimezone(dt.timezone.utc), (m or hit).group(0)


# ------------------------------------------------------------------ transcripts (coordinator + lane agents)
def watched_transcripts(now_s):
    files = [f for f in glob.glob(os.path.join(PROJECT, "*.jsonl")) + glob.glob(os.path.join(PROJECT, "*", "subagents", "*.jsonl"))
             if now_s - os.path.getmtime(f) < WINDOW_S]
    return files

def tail_records(path, nbytes=3_000_000):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - nbytes))
        if size > nbytes:
            f.readline()
        for raw in f:
            if b'"timestamp"' not in raw:
                continue
            if b'isApiErrorMessage' not in raw and b'"type":"assistant"' not in raw and b'queue-operation' not in raw:
                continue
            try:
                yield json.loads(raw)
            except Exception:
                continue

def transcript_limit(now):
    """-> dict(last_limit, last_ok, due, text, who, files) over every watched transcript."""
    now_s = now.timestamp()
    res = dict(last_limit=None, last_ok=None, due=None, text="", who="", files=0)
    for p in watched_transcripts(now_s):
        res["files"] += 1
        who = "lane " + os.path.basename(p)[:20] if "/subagents/" in p else "session " + os.path.basename(p)[:8]
        for d in tail_records(p):
            try:
                ts = dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
            except Exception:
                continue
            if now_s - ts.timestamp() > WINDOW_S:
                continue
            kind = d.get("type")
            text = ""
            if d.get("isApiErrorMessage"):
                text = json.dumps((d.get("message") or {}).get("content", ""), ensure_ascii=False)
                if not (d.get("error") == "rate_limit" or d.get("apiErrorStatus") == 429 or LIMIT_RE.search(text)):
                    continue
            elif kind == "queue-operation":
                c = d.get("content") or ""
                if "terminated early due to an API error" not in c or not LIMIT_RE.search(c):
                    continue
                text = c[c.find("API error"):][:200]
            elif kind == "assistant":
                if res["last_ok"] is None or ts > res["last_ok"]:
                    res["last_ok"] = ts
                continue
            else:
                continue
            if res["last_limit"] is None or ts > res["last_limit"]:
                m = RESET_RE.search(text)
                res.update(last_limit=ts, who=who, text=(m.group(0) if m else LIMIT_RE.search(text).group(0) if LIMIT_RE.search(text) else "429"),
                           due=((reset_time(m, ts) + GRACE) if m else (ts + NO_TIME_RETRY)).astimezone(dt.timezone.utc))
    return res

def lanes_limited(now):
    t = transcript_limit(now)
    lim = bool(t["last_limit"] and (now - t["last_limit"]).total_seconds() >= QUIET_S and t["due"] and now < t["due"]
               and (t["last_ok"] is None or t["last_ok"] <= t["last_limit"]))
    return lim, t


# ------------------------------------------------------------------ handoff / codex
def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    return (r.stdout + r.stderr).strip()

def write_handoff(due, text):
    os.makedirs(HANDOFF_DIR, exist_ok=True)
    ts = dt.datetime.now(LOCAL_TZ)
    p = os.path.join(HANDOFF_DIR, f"claude_to_codex_{ts:%Y%m%d_%H%M}.md")
    if DRY:
        print(f"[dry] would write {p} and regenerate CODEX-HANDOFF.md"); return p
    hand = sh("tail -n 40 ~/coord/HANDOFF.md")
    main = sh("git -C ~/OpenTallas log -1 --format='%h %ci %s' origin/main")
    status = sh("ssh -o ConnectTimeout=10 epyc1 ~/.local/bin/ot-run --status 2>&1 | head -3")
    lanes = sh("ls -t ~/coord/lanes/*.md | head -40 | xargs -n1 basename")
    doc = sh(f"/usr/bin/python3 {os.path.expanduser('~/bin/make-codex-handoff.py')} "
             f"'Claude hit its usage limit ({text}); expected back at {local(due)}.'")
    with open(p, "w") as f:
        f.write(f"# Claude -> Codex handoff {ts:%Y-%m-%d %H:%M %Z}\n\n"
                f"Claude (pane {CLAUDE}) hit its usage limit: `{text}`. Expected back at {local(due)}.\n"
                f"Your role and rules: {ROLE}. Full handoff document (project status, every lane's step / next / failures): "
                f"{os.path.join(COORD, 'CODEX-HANDOFF.md')} (generator said: {doc}). Log to {CODEX_LOG} and HANDOFF.md "
                f"(prefix `CODEX:`).\n\n"
                f"## main\n{main}\n\n## fleet\n```\n{status}\n```\n\n## lane files (most recent first)\n```\n{lanes}\n```\n\n"
                f"## last 40 HANDOFF lines\n```\n{hand}\n```\n")
    return p

def start_codex(handoff, st):
    prompt = (f"You take over the OpenTallas push while Claude is usage-limited. Read {ROLE}, then "
              f"{os.path.join(COORD, 'CODEX-HANDOFF.md')} (full handoff: status, every lane) and {handoff}, and follow "
              f"them now. Follow AGENTS.md, BRIEFING and the review-before-route rule. Cover ALL lanes' remaining tasks, "
              f"collect results and diagnose every failure so nothing is left unhandled. Spend little time on "
              f"validation, verification, provenance or routine bookkeeping. Push toward completing the project. "
              f"Owner questions: write them as plain text under OWNER? in {CODEX_LOG} and keep working; never open a "
              f"blocking question dialog and never wait for an answer. Keep working until you are told Claude's limit has reset.")
    lines = capture(CODEX) or []
    cmd = pane_cmd(CODEX)
    if cmd in ("codex", "node"):
        if busy(lines):
            log("codex pane busy with another task; not taking it over")
            return None
        type_line(CODEX, prompt)                         # idle codex session: hand it the work
        st["codex_ours"] = True
        return "reused"
    if cmd not in ("bash", "zsh", "sh"):
        log(f"codex pane runs {cmd!r}; not starting codex there")
        return None
    q = prompt.replace("'", "'\\''")
    send_key(CODEX, "C-u")
    type_line(CODEX, f"{CODEX_CMD} '{q}'")
    st["codex_ours"] = True
    return "started"

def handoff_back_done(since_iso):
    """Codex appended a '## Handoff to Claude' section after we asked, or replied HANDOFF DONE."""
    lines = capture(CODEX, 80) or []
    if any(re.fullmatch(r"\W*HANDOFF DONE\W*", l.strip()) for l in lines[-25:]) and not busy(lines):
        return True
    try:
        if os.path.getmtime(CODEX_LOG) > dt.datetime.fromisoformat(since_iso).timestamp():
            with open(CODEX_LOG) as f:
                tail = f.read()[-20000:]
            return "## Handoff to Claude" in tail and not busy(lines)
    except OSError:
        pass
    return False

def claude_type(text, cl):
    """type into Claude's pane only when it runs claude and is idle; close an open question dialog first."""
    if pane_cmd(CLAUDE) not in ("claude", "node"):
        log(f"Claude pane runs {pane_cmd(CLAUDE)!r}; nothing typed"); return False
    if busy(cl):
        return False
    if DIALOG_RE.search("\n".join(cl[-12:])):
        send_key(CLAUDE, "Escape"); time.sleep(1)
        text += (" (An open question dialog was closed so this message could reach you: owner rule 11 -- ask owner "
                 "questions as plain text OWNER? lines, never a blocking dialog.)")
    type_line(CLAUDE, text)
    return True


def main():
    os.makedirs(STATE_DIR, exist_ok=True)
    st = load()
    mode = st.get("mode", "claude")
    now = now_utc()
    if pane_cmd(CLAUDE) not in ("claude", "node"):
        log(f"Claude pane {CLAUDE} runs {pane_cmd(CLAUDE)!r}; not watching"); return
    cl = capture(CLAUDE)
    if cl is None:
        log("cannot capture Claude pane"); return
    limited, due, text = claude_limit(cl)
    llim, t = lanes_limited(now)
    if not limited and llim:
        limited, due, text = True, t["due"], f"{t['text']} ({t['who']}, no normal reply anywhere since {local(t['last_limit'])})"
    if "--status" in sys.argv or DRY:
        print(json.dumps(dict(mode=mode, state=st, claude_pane=dict(target=CLAUDE, cmd=pane_cmd(CLAUDE), busy=busy(cl), dialog=bool(DIALOG_RE.search("\n".join(cl[-12:]))), limit_on_screen=claude_limit(cl)[0]),
                              codex_pane=dict(target=CODEX, cmd=pane_cmd(CODEX)),
                              transcripts=dict(files=t["files"], last_limit=t["last_limit"] and local(t["last_limit"]), limit_text=t["text"], who=t["who"],
                                               last_ok=t["last_ok"] and local(t["last_ok"]), due=t["due"] and local(t["due"]), lanes_limited=llim),
                              decision=dict(limited=limited, due=due and local(due), text=text)), indent=1, default=str))
        if "--status" in sys.argv:
            return
    codex_ok = os.path.exists(os.path.expanduser("~/.local/bin/codex")) and tmux("has-session", "-t", CODEX.split(":")[0]).returncode == 0

    if mode == "claude":
        if not limited:
            return
        if not codex_ok:                                 # fallback: plain continue at reset time
            st.update(mode="plain", due=due.isoformat(), text=text); save(st)
            log(f"limit seen ({text!r}); no codex -> plain continue at {local(due)}"); return
        handoff = write_handoff(due, text)
        how = start_codex(handoff, st)
        st.update(mode="codex" if how else "plain", due=due.isoformat(), text=text, since=now.isoformat(),
                  handoff=handoff)
        save(st)
        log(f"limit seen ({text!r}); codex {how or 'NOT started (plain continue)'}; Claude due {local(due)}; {handoff}")
        return

    if mode == "plain":
        if now >= dt.datetime.fromisoformat(st["due"]) and claude_type("continue", cl):
            log("plain: sent continue")
            st.update(mode="resuming", resumed_at=now.isoformat()); save(st)
        return

    if mode == "codex":
        if limited and due and due > dt.datetime.fromisoformat(st["due"]):   # a later reset replaced the old one
            st.update(due=due.isoformat(), text=text); save(st); log(f"Claude due moved to {local(due)}")
        if now < dt.datetime.fromisoformat(st["due"]):
            return
        type_line(CODEX, "Claude's usage limit has reset. Follow the 'Handing back' section of "
                         f"{ROLE}: park your current step, write the '## Handoff to Claude' section in {CODEX_LOG}, "
                         "reply HANDOFF DONE and stop.")
        st.update(mode="handing_back", asked=now.isoformat()); save(st)
        log("asked codex to hand back")
        return

    if mode == "handing_back":
        asked = st["asked"]
        if not (handoff_back_done(asked) or now - dt.datetime.fromisoformat(asked) > HANDBACK_TIMEOUT):
            return
        since = dt.datetime.fromisoformat(st["since"])
        if claude_type(f"continue. While you were usage-limited ({local(since)} to now), Codex in tmux pane {CODEX} "
                       f"covered coordination per {ROLE}. Read the latest '## Handoff to Claude' section of {CODEX_LOG} "
                       f"and the CODEX: lines in ~/coord/HANDOFF.md, reconcile them with your lanes (start fresh short lane "
                       f"agents for lanes that died on the limit), then resume. Ask owner questions as plain text.", cl):
            log("sent continue + handoff pointer to Claude")
            st.update(mode="resuming", resumed_at=now.isoformat()); save(st)
        return

    if mode == "resuming":
        if limited and claude_limit(cl)[0]:              # Claude itself still limited: give the work back to Codex
            if codex_ok and st.get("codex_ours"):
                type_line(CODEX, f"Claude is still usage-limited (until {local(due)}). Resume taking over all "
                                 f"lanes' remaining tasks per {ROLE}: guidelines and review rules apply, diagnose failures, "
                                 f"minimal routine verification, push toward completion.")
                st.update(mode="codex", due=due.isoformat(), text=text); save(st)
                log(f"Claude still limited; back to codex until {local(due)}")
            else:
                st.update(mode="plain", due=due.isoformat(), text=text); save(st)
            return
        if now - dt.datetime.fromisoformat(st["resumed_at"]) > dt.timedelta(minutes=10):
            save({"mode": "claude", "codex_ours": st.get("codex_ours", False)})
            log("Claude working again; back to normal watch")


if __name__ == "__main__":
    import fcntl
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "lock"), "w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(0)
        main()
