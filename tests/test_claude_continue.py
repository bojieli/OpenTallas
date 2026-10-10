import datetime as dt
import fcntl
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.takeover import claude_continue as C

UTC=dt.timezone.utc
STAMP=dt.datetime(2026,10,10,19,15,tzinfo=UTC) # 12:15 Pacific, after noon
IDLE='❯ continue\n● Completed engineering work\n✻ Worked for 3m · done 12:10 PM\n❯ \n  ⏵⏵ bypass permissions on · 67 shells\n'
LIMITED="❯ continue\n  You've hit your weekly limit · resets 12pm\n● Goal paused · usage limit reached\n✻ Worked for 1s · done 12:10 PM\n❯ \n  67 shells\n"

class ContinueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.patches=[]
        for obj,key,value in [(C.H,'COORD',self.root),(C.H,'STATE',self.root/'handoff.json'),
                              (C,'STATE',self.root/'continue.json'),(C,'LOG',self.root/'log.jsonl'),
                              (C,'LOCK',self.root/'continue.lock')]:
            p=patch.object(obj,key,value);p.start();self.patches.append(p)
        self.handoff={'nonce':'initial-owner-nonce','status':'handoff_sent','sent_utc':STAMP.isoformat()}
        C.H.STATE.write_text(json.dumps(self.handoff))
        self.calls=[];self.loaded=[]
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def tick(self,pane=IDLE,stamp=STAMP,**kw):
        return C.tick(stamp,capture_fn=kw.pop('capture_fn',lambda:pane),
                      load_fn=kw.pop('load_fn',lambda b,t:self.loaded.append((b,t))),
                      run_fn=kw.pop('run_fn',lambda *a:self.calls.append(a)),**kw)
    def test_no_interference_before_noon_even_sent_state(self):
        result=self.tick(stamp=STAMP-dt.timedelta(minutes=16))
        self.assertEqual(result['outcome'],'BEFORE_NOON_RESET')
        self.assertFalse(self.calls);self.assertFalse(self.loaded)
    def test_never_competes_with_initial_or_uncertain_handoff(self):
        for status in ['monitoring_reset','usage_requested','usage_checked_reset','delivery_reserved',None]:
            self.handoff['status']=status;C.H.STATE.write_text(json.dumps(self.handoff))
            self.assertEqual(self.tick()['outcome'],'INITIAL_HANDOFF_NOT_CONFIRMED')
        self.assertFalse(self.calls);self.assertFalse(self.loaded)
    def test_send_buffer_and_enter_once_bind_initial_nonce(self):
        before=C.H.STATE.read_bytes()
        self.assertEqual(self.tick()['outcome'],'CONTINUATION_SENT')
        self.assertEqual(len(self.loaded),1)
        self.assertIn('Continue ALL Codex and prior Claude streams',self.loaded[0][1])
        self.assertIn('Preserve progressing pinned jobs',self.loaded[0][1])
        self.assertIn('30-minute drive and hourly',self.loaded[0][1])
        self.assertEqual([x[1] for x in self.calls],['paste-buffer','send-keys'])
        self.assertEqual(self.calls[0][-1],'%4')
        self.assertEqual(self.calls[1][-1],'Enter')
        self.assertEqual(C.H.STATE.read_bytes(),before)
        self.assertEqual(self.tick()['outcome'],'DUPLICATE_SLOT')
        self.assertEqual(len(self.loaded),1)
    def test_limit_logs_and_retries_only_at_next_30min(self):
        self.assertEqual(self.tick(LIMITED)['prompt_status'],'limited_idle')
        self.assertEqual(self.tick(LIMITED,stamp=STAMP+dt.timedelta(minutes=20))['outcome'],'CADENCE_NOT_DUE')
        self.assertEqual(self.tick(LIMITED,stamp=STAMP+dt.timedelta(minutes=30))['outcome'],'CONTINUATION_SENT')
        self.assertEqual(len(self.loaded),2)
        self.assertEqual(len(C.LOG.read_text().splitlines()),3)
    def test_old_rate_error_does_not_override_current_busy_footer(self):
        pane=LIMITED+'  esc to interrupt\n'
        self.assertEqual(self.tick(pane)['prompt_status'],'busy')
        self.assertFalse(self.loaded)
    def test_old_rate_error_does_not_override_later_active_spinner(self):
        pane="❯ continue\nYou've hit your weekly limit\n✻ Engineering… (40s · 2k tokens)\n❯ \n"
        self.assertEqual(self.tick(pane)['prompt_status'],'busy')
        self.assertFalse(self.loaded)
    def test_completed_spinner_is_history(self):
        pane="You've hit your weekly limit\n❯ continue\n✻ Engineering… (40s)\n✻ Worked for 40s · done 12:14 PM\n❯ \n"
        self.assertEqual(C.prompt_status(pane),'idle')
        self.assertEqual(self.tick(pane)['outcome'],'CONTINUATION_SENT')
    def test_partial_input_and_no_prompt_never_modified(self):
        for pane in ['❯ fix the','❯\u00a0partial command\n','A menu without a prompt','❯ \n  unfinished multiline input\n────────\n permissions footer']:
            self.assertEqual(self.tick(pane)['outcome'],'PANE_NOT_IDLE_EMPTY')
        self.assertFalse(self.calls);self.assertFalse(self.loaded)
    def test_recheck_stops_paste_if_user_starts_typing(self):
        panes=iter([IDLE,'❯ current user input\n'])
        self.assertEqual(self.tick(capture_fn=lambda:next(panes))['outcome'],'PROMPT_CHANGED_NO_PASTE')
        self.assertEqual([x[1] for x in self.calls],['delete-buffer'])
        self.assertEqual(self.tick()['outcome'],'DUPLICATE_SLOT')
    def test_paste_crash_has_durable_reservation_never_same_slot_retry(self):
        def fail(*args):raise subprocess.CalledProcessError(1,args)
        self.assertEqual(self.tick(run_fn=fail)['outcome'],'DELIVERY_UNCERTAIN_RESERVED')
        self.assertEqual(json.loads(C.STATE.read_text())['status'],'delivery_reserved')
        self.assertEqual(self.tick()['outcome'],'DUPLICATE_SLOT')
        self.assertEqual(len(self.loaded),1)
    def test_buffer_load_crash_does_not_type(self):
        def fail(*args):raise subprocess.CalledProcessError(1,args)
        self.assertEqual(self.tick(load_fn=fail)['outcome'],'DELIVERY_UNCERTAIN_RESERVED')
        self.assertFalse(self.calls)
    def test_malformed_state_fails_closed(self):
        C.STATE.write_text('{')
        self.assertEqual(self.tick()['outcome'],'STATE_UNREADABLE')
        self.assertFalse(self.loaded)
    def test_evidence_ready_status_is_eligible(self):
        self.handoff['status']='takeover_evidence_ready_for_coordinator'
        C.H.STATE.write_text(json.dumps(self.handoff))
        self.assertEqual(self.tick()['outcome'],'CONTINUATION_SENT')
    def test_initial_sender_lock_prevents_any_capture(self):
        with (self.root/'codex-claude-reset-watch.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(C.H,'capture',side_effect=AssertionError('must not capture')),patch('sys.argv',['claude_continue']):
                self.assertEqual(C.main(),0)
        self.assertIn('SENDER_LOCK_BUSY',C.LOG.read_text())
    def test_unavailable_pane_logged_no_commands(self):
        def fail():raise subprocess.CalledProcessError(1,['tmux'])
        self.assertEqual(self.tick(capture_fn=fail)['outcome'],'PANE_UNAVAILABLE')
        self.assertFalse(self.calls)

if __name__=='__main__':unittest.main()
