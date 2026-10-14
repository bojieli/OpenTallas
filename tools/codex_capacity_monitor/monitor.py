#!/usr/bin/env python3
"""Scoped app-server capacity failure monitor. No credentials, TTY, or model changes."""
from __future__ import annotations
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import random
import subprocess
import threading
import time

CONTINUE = 'Continue from preserved state; do not duplicate live jobs.'
READ_METHODS = {'initialize', 'thread/read', 'thread/list', 'thread/turns/list',
                'thread/queue/list', 'thread/goal/get'}
DENY_CODES = {'contextWindowExceeded', 'sessionBudgetExceeded', 'usageLimitExceeded',
              'rateLimitExceeded', 'unauthorized', 'badRequest', 'sandboxError', 'misalignmentPolicyViolation'}


def capacity(error):
    if not isinstance(error, dict): return False
    code = error.get('codexErrorInfo')
    if isinstance(code, str) and code in DENY_CODES: return False
    if code in ('serverOverloaded', 'server_overloaded'): return True
    import re
    message = (error.get('message') or '') + ' ' + (error.get('additionalDetails') or '')
    return bool(re.search(r'\b(server[_ -]?overloaded|server is overloaded|at capacity|temporarily unavailable due to capacity)\b', message, re.I))


def lock_valid(path, expected_since, now):
    try:
        lock = json.loads(Path(path).read_text())
        return lock.get('owner') == 'codex' and lock.get('since') == expected_since and \
            dt.datetime.fromisoformat(lock['until']).timestamp() > now
    except (OSError, ValueError, KeyError, TypeError): return False


class RPC:
    """One persistent newline-delimited JSON-RPC connection to an existing daemon."""
    def __init__(self, socket=None, on_event=None):
        cmd = ['codex', 'app-server', 'proxy'] + (['--sock', socket] if socket else [])
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
        self.on_event = on_event or (lambda event: None)
        self.pending = {}; self.counter = 0; self.mutex = threading.Lock()
        self.reader = threading.Thread(target=self._read, daemon=True); self.reader.start()
        try:
            self.call('initialize', {'clientInfo': {'name':'codex_capacity_monitor',
                'title':'Scoped capacity failure monitor','version':'0.1'}, 'capabilities': {'experimentalApi':True}})
            self._write({'method':'initialized'})
        except Exception:
            self.close()
            raise

    def _write(self, value):
        self.process.stdin.write(json.dumps(value,separators=(',',':'))+'\n');self.process.stdin.flush()

    def _read(self):
        try:
            for line in self.process.stdout:
                event = json.loads(line)
                request_id = event.get('id')
                if request_id in self.pending and ('result' in event or 'error' in event):
                    self.pending[request_id].put(event)
                else:
                    self.on_event(event)
        finally:
            for waiter in list(self.pending.values()):
                waiter.put({'error': {'message':'proxy connection closed'}})

    def call(self, method, params, timeout=15):
        # thread/resume only attaches already loaded threads after policy checks.
        if method not in READ_METHODS | {'thread/resume','turn/steer'}:
            raise ValueError('unsupported monitor RPC: '+method)
        with self.mutex:
            self.counter += 1; request_id=self.counter; waiter=queue.Queue()
            self.pending[request_id]=waiter
            self._write({'id':request_id,'method':method,'params':params})
        try:
            result = waiter.get(timeout=timeout)
            if 'error' in result: raise RuntimeError(result['error'].get('message','RPC failure'))
            return result['result']
        finally:
            self.pending.pop(request_id,None)

    def close(self):
        # Close only this client's stdio. Never kill/restart the daemon or agents.
        self.process.stdin.close()


class Monitor:
    def __init__(self, rpc, root, state_dir, lock, lock_since, clock=time.time, rng=None,
                 retry_cap=4, base_delay=30, max_delay=600, notify=False):
        self.rpc=rpc;self.root=root;self.directory=Path(state_dir);self.directory.mkdir(parents=True,exist_ok=True)
        self.lock=lock;self.lock_since=lock_since;self.clock=clock;self.rng=rng or random.Random()
        self.retry_cap=retry_cap;self.base_delay=base_delay;self.max_delay=max_delay;self.notify=notify
        self.path=self.directory/'state.json';self.log_path=self.directory/'events.jsonl'
        self.events=queue.Queue();self.scope={};self.attached=set();self.requests={}
        if self.path.exists():
            self.state=json.loads(self.path.read_text())
            if self.state.get('rootThreadId') != root or self.state.get('lockSince') != lock_since:
                raise ValueError('state belongs to another coordinator generation/thread')
        else: self.state={'schema':'opentallas.codex.capacity_monitor.v1','rootThreadId':root,
                          'lockSince':lock_since,'failures':{},'attempts':{}}

    def log(self, event, **fields):
        with self.log_path.open('a') as f:
            f.write(json.dumps({'at':self.clock(),'event':event,**fields},sort_keys=True)+'\n')

    def save(self):
        temp=self.path.with_suffix('.tmp')
        with temp.open('w') as f:
            os.chmod(temp,0o600);f.write(json.dumps(self.state,indent=2)+'\n');f.flush();os.fsync(f.fileno())
        temp.replace(self.path)
        fd=os.open(self.directory,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def refresh_scope(self):
        root=self.rpc.call('thread/read',{'threadId':self.root,'includeTurns':False})['thread']
        if root.get('id') != self.root: raise ValueError('root identity mismatch')
        candidates={self.root:root}; cursor=None
        while True:
            params={'ancestorThreadId':self.root,'archived':False,'limit':100,
                    'sourceKinds':['subAgent','subAgentThreadSpawn','subAgentOther'], 'useStateDbOnly':True}
            if cursor: params['cursor']=cursor
            response=self.rpc.call('thread/list',params)
            for thread in response['data']: candidates[thread['id']]=thread
            cursor=response.get('nextCursor')
            if not cursor: break
        proven={self.root:root}
        while True:
            additions={tid:t for tid,t in candidates.items() if tid not in proven and
                t.get('parentThreadId') in proven and t.get('sessionId') == root.get('sessionId')}
            if not additions:break
            proven.update(additions)
        self.scope=proven
        return proven

    def attach_loaded(self):
        """Attach only explicitly direct-input-capable, already loaded tree threads."""
        for tid, thread in self.scope.items():
            if tid in self.attached or thread.get('canAcceptDirectInput') is not True: continue
            current=self.rpc.call('thread/read',{'threadId':tid,'includeTurns':False})['thread']
            if current.get('status',{}).get('type') not in ('idle','active'): continue
            if current.get('canAcceptDirectInput') is not True: continue
            # No history/path/config/model overrides, no new thread, no stored child loading.
            resumed=self.rpc.call('thread/resume',{'threadId':tid,'excludeTurns':True})['thread']
            if resumed.get('id') != tid:raise ValueError('subscription thread identity mismatch')
            self.attached.add(tid)
            self.log('subscribed_loaded',threadId=tid)

    def receive(self, event): self.events.put(event)

    def drain(self):
        while True:
            try:event=self.events.get_nowait()
            except queue.Empty:break
            self.process_event(event)

    def process_event(self, event):
        params=event.get('params') or {};tid=params.get('threadId');method=event.get('method')
        if tid not in self.scope:return
        if event.get('id') is not None and method:
            self.requests[str(event['id'])]=tid
            return  # Monitor never answers tools, approvals, or user-input requests.
        if method=='serverRequest/resolved':
            self.requests.pop(str(params.get('requestId')),None);return
        if method=='error':
            error=params.get('error');turn=params.get('turnId')
            if not turn or params.get('willRetry') is not False or not capacity(error):return
            key=hashlib.sha256((tid+'\0'+turn).encode()).hexdigest()
            if key not in self.state['failures']:
                count=self.state['attempts'].get(tid,0)
                delay=min(self.max_delay,self.base_delay*2**min(count,10))
                self.state['failures'][key]={'threadId':tid,'turnId':turn,'error':error,
                    'willRetry':False,'terminal':False,'due':self.clock()+delay*self.rng.uniform(0.8,1.2),
                    'action':'pending'}
                self.log('capacity_error_observed',threadId=tid,turnId=turn,willRetry=False)
                self.save()
        elif method=='turn/completed':
            turn=params.get('turn') or {}
            for failure in self.state['failures'].values():
                if failure['threadId']==tid and failure['turnId']==turn.get('id'):
                    failure['terminal']=turn.get('status')=='failed' and capacity(turn.get('error'))
            if turn.get('status')=='completed':self.state['attempts'][tid]=0
            self.save()

    def inspect_failure(self, failure):
        tid=failure['threadId']
        if tid not in self.scope:return None,'outside_current_tree'
        if not lock_valid(self.lock,self.lock_since,self.clock()):return None,'coordinator_lock_changed'
        if failure.get('willRetry') is not False or not failure.get('terminal'):return None,'not_terminal_no_retry_failure'
        if tid in self.requests.values():return None,'pending_server_request'
        thread=self.rpc.call('thread/read',{'threadId':tid,'includeTurns':False})['thread']
        if thread.get('id')!=tid:return None,'thread_identity_mismatch'
        if thread.get('status',{}).get('type')!='idle':return None,'thread_not_idle'
        goal=self.rpc.call('thread/goal/get',{'threadId':tid}).get('goal')
        if goal is not None and goal.get('status')!='active':return None,'goal_not_active'
        queued=self.rpc.call('thread/queue/list',{'threadId':tid,'limit':1})
        if queued.get('data') or queued.get('nextCursor'):return None,'pending_user_input'
        turns=self.rpc.call('thread/turns/list',{'threadId':tid,'limit':1,'sortDirection':'desc','itemsView':'notLoaded'})['data']
        if not turns or turns[0].get('id')!=failure['turnId']:return None,'newer_or_missing_turn'
        if turns[0].get('status')!='failed' or not capacity(turns[0].get('error')):return None,'failure_changed_or_success'
        return thread,None

    def tick(self):
        self.drain()
        for key,failure in self.state['failures'].items():
            if failure['action']!='pending' or self.clock()<failure['due']:continue
            tid=failure['threadId'];count=self.state['attempts'].get(tid,0)
            if count>=self.retry_cap:
                failure['action']='retry_cap';self.log('retry_cap',threadId=tid);self.save();continue
            thread,reason=self.inspect_failure(failure)
            if reason:
                failure['last_skip']=reason
                self.log('skip',threadId=tid,turnId=failure['turnId'],reason=reason)
                if reason in ('newer_or_missing_turn','failure_changed_or_success','outside_current_tree'):
                    failure['action']='obsolete'
                failure['due']=self.clock()+self.base_delay;self.save();continue
            # A second full read catches state changes before notification. Direct turn/start
            # is intentionally absent: installed schema has no atomic idle-turn precondition.
            _,reason=self.inspect_failure(failure)
            if reason:
                failure['last_skip']=reason;failure['due']=self.clock()+self.base_delay;self.save();continue
            message=('Capacity monitor: terminal server-capacity failure in thread '+tid+' turn '+failure['turnId']+
                '. '+CONTINUE+' Use coordinator followup_task for this exact existing child if direct input is unsupported. '
                'Root direct-start requires an atomic idle-start capability; do not create another agent instance.')
            notice=self.directory/('notification-'+key+'.json')
            notice.write_text(json.dumps({'threadId':tid,'turnId':failure['turnId'],'message':message,
                'requiresCoordinatorFollowup':True,'directInputSupported':thread.get('canAcceptDirectInput')},indent=2)+'\n')
            if not self.notify:
                failure['action']='notification_file';self.log('notification_file',threadId=tid,path=str(notice));self.save();continue
            # Notify the active coordinator through an exact-turn guarded supported RPC.
            # This is a notification, never an unguarded automatic restart/resume.
            root=self.rpc.call('thread/read',{'threadId':self.root,'includeTurns':False})['thread']
            latest=self.rpc.call('thread/turns/list',{'threadId':self.root,'limit':1,'sortDirection':'desc','itemsView':'notLoaded'})['data']
            if root.get('status',{}).get('type')!='active' or root.get('status',{}).get('activeFlags') or \
                    root.get('canAcceptDirectInput') is not True or not latest or latest[0].get('status')!='inProgress':
                failure['last_skip']='coordinator_not_available';failure['due']=self.clock()+self.base_delay;self.save();continue
            goal=self.rpc.call('thread/goal/get',{'threadId':self.root}).get('goal')
            if goal is not None and goal.get('status')!='active':
                failure['last_skip']='coordinator_goal_not_active';failure['due']=self.clock()+self.base_delay;self.save();continue
            queued_root=self.rpc.call('thread/queue/list',{'threadId':self.root,'limit':1})
            if queued_root.get('data') or queued_root.get('nextCursor') or self.root in self.requests.values() or not lock_valid(self.lock,self.lock_since,self.clock()):
                failure['last_skip']='coordinator_pending_input_or_lock_change';failure['due']=self.clock()+self.base_delay;self.save();continue
            # Persist before a write: an uncertain transport outcome cannot duplicate notifications.
            failure['action']='notification_attempted';self.state['attempts'][tid]=count+1;self.save()
            try:
                self.rpc.call('turn/steer',{'threadId':self.root,'expectedTurnId':latest[0]['id'],
                    'clientUserMessageId':'capacity-monitor-'+key,'input':[{'type':'text','text':message}]})
                failure['action']='coordinator_notified';self.log('coordinator_notified',threadId=tid,turnId=failure['turnId'])
            except Exception as error:
                failure['action']='notification_outcome_unknown';self.log('notification_outcome_unknown',threadId=tid,error=type(error).__name__)
            self.save()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root-thread',required=True)
    parser.add_argument('--socket');parser.add_argument('--state-dir',required=True)
    parser.add_argument('--lock',required=True);parser.add_argument('--lock-since',required=True)
    parser.add_argument('--notify-coordinator',action='store_true');parser.add_argument('--subscribe-loaded',action='store_true')
    parser.add_argument('--once',action='store_true');parser.add_argument('--interval',type=float,default=15)
    args=parser.parse_args();directory=Path(args.state_dir);directory.mkdir(parents=True,exist_ok=True)
    handle=(directory/'monitor.lock').open('w');fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (directory/'pid').write_text(str(os.getpid())+'\n')
    rpc=None
    monitor=Monitor(None,args.root_thread,directory,args.lock,args.lock_since,notify=args.notify_coordinator)
    monitor.save()
    while not (directory/'STOP').exists():
        if not lock_valid(args.lock,args.lock_since,time.time()):break
        try:
            if rpc is None:
                rpc=RPC(args.socket,on_event=monitor.receive)
                monitor.rpc=rpc
            monitor.refresh_scope()
            if args.subscribe_loaded:monitor.attach_loaded()
            monitor.tick()
        except Exception as error:
            with (directory/'health.jsonl').open('a') as f:
                f.write(json.dumps({'at':time.time(),'status':'blocked','errorType':type(error).__name__,
                    'message':str(error)[:300]})+'\n')
            if rpc is not None:rpc.close()
            rpc=None
        if args.once:break
        time.sleep(args.interval)
    if rpc is not None:rpc.close()

if __name__=='__main__':main()
