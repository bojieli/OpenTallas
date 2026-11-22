"""FLOW-FLEET-R2 P1: fleet ticket keeps the queue age of a --dir across ot-run clients; spill is admit-first."""
import importlib.machinery, importlib.util, json, pathlib, subprocess
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_tkt", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_tkt", l)); l.exec_module(RUN)
RUN.ADMIT_FIRST = True


def test_ticket_keeps_first_seen_while_waiting(tmp_path):
    p = str(tmp_path / "t.json")
    assert RUN.ticket_open("/srv/x/k/", now=1000.0, path=p, lane="A") == 1000.0            # first submit
    assert RUN.ticket_open("/srv/x/k", now=1500.0, path=p) == 1000.0                        # a new client for the same dir keeps the age
    assert RUN.ticket_open("/srv/x/other", now=1600.0, path=p) == 1600.0                    # another dir: its own ticket
    t = json.load(open(p))
    assert t["/srv/x/k"]["first"] == 1000.0 and t["/srv/x/k"]["last"] == 1500.0 and t["/srv/x/k"]["lane"] == "A" and t["/srv/x/k"]["state"] == "waiting"


def test_started_or_stale_ticket_starts_fresh(tmp_path):
    p = str(tmp_path / "t.json")
    RUN.ticket_open("/srv/x/k", now=1000.0, path=p)
    RUN.ticket_touch("/srv/x/k", "started", "epyc8", now=1100.0, path=p)
    assert json.load(open(p))["/srv/x/k"]["state"] == "started" and json.load(open(p))["/srv/x/k"]["host"] == "epyc8"
    assert RUN.ticket_open("/srv/x/k", now=1200.0, path=p) == 1200.0                        # the job started: the next submit is a new ticket
    assert RUN.ticket_open("/srv/x/k", now=1200.0 + RUN.TICKET_TTL_S + 5, path=p) == 1200.0 + RUN.TICKET_TTL_S + 5   # not touched for > TTL


def test_no_dir_no_ticket_and_bad_file_never_raises(tmp_path):
    p = tmp_path / "t.json"
    p.write_text("not json")
    assert RUN.ticket_open("", now=5.0, path=str(p)) == 5.0
    assert RUN.ticket_open("/srv/a", now=7.0, path=str(p)) == 7.0
    assert RUN.ticket_open("/srv/a", now=8.0, path="/proc/nope/t.json") == 8.0              # unwritable: the age is simply now


def test_admit_first_refuses_only_on_an_explicit_no():
    out = []
    mk = lambda txt, rc=0: (lambda dst, cmd, timeout=0: subprocess.CompletedProcess([], rc, txt, ""))
    assert RUN.admit_first_ok("epyc8", 48, ["bash", "run.sh"], out.append, run_ssh=mk("NO 7 route | CPU_CHARGE: 186 > 96\n")) is False and "nothing copied" in out[0]
    assert RUN.admit_first_ok("epyc8", 48, ["bash", "run.sh"], out.append, run_ssh=mk("OK 7 route | x\n")) is True
    assert RUN.admit_first_ok("epyc8", 48, ["bash", "run.sh"], out.append, run_ssh=mk("", 255)) is True            # ssh failure / old host: fail open
    assert RUN.admit_first_ok("epyc8", 48, ["bash", "run.sh"], out.append, run_ssh=lambda *a, **k: (_ for _ in ()).throw(OSError("x"))) is True


def test_probe_cmd_carries_threads_and_quoted_argv():
    c = RUN.admit_probe_cmd(48, ["bash", "-c", "echo 'a b'"], 16)
    assert c.startswith("OT_HEAVY_THREADS=16 timeout 60 /usr/local/bin/ot-heavy-reconcile --gate 48 -- bash -c ") and "'echo '\"'\"'a b'\"'\"''" in c


def test_spill_run_copies_nothing_when_the_destination_says_no(monkeypatch):
    monkeypatch.setattr(RUN, "ssh_sh", lambda dst, cmd, timeout=0: subprocess.CompletedProcess([], 0, "NO 7 x | y\n", ""))
    called = []
    monkeypatch.setattr(RUN, "spill_copy_fwd", lambda *a, **k: called.append(1))
    monkeypatch.setattr(RUN, "spill_room", lambda *a, **k: called.append("room") or (True, ""))
    assert RUN.spill_run("intel2", "epyc8", ["/srv/opentallas-scratch2/claude/l/k"], 1.0, 48, ["bash", "x"], "/srv/opentallas-scratch2/claude/l/k", None, lambda m: None) is None
    assert not called
