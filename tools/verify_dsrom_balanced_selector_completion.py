"""Strict prepared gate completion semantics; no command execution."""
import re
import prepare_dsrom_full_selector_dma_fixture as V

DIFF=re.compile(r'^MUTANT_DIFF mode=(\d+) case=(\d+) kind=(CAND_VALUE_DIFF|CAND_RETIRE_COUNT_DIFF) index=(\d+) expected=([0-9a-f]+) actual=([0-9a-f]+)$')
CASE=re.compile(r'^CASE_PASS case=(\d+) n=(\d+) k=(\d+) ref_words=(\d+) cand_words=(\d+) delta=(\d+) fetch_words=(\d+)$')
ABORT=re.compile(r'^ABORT_PASS phase=(\d+) case=(\d+)$')
FAULT=re.compile(r'^FAULT_PASS kind=(\d+) busy=(\d+)$')
TERMINAL='FULL_SELECTOR_DMA_PASS profile=0 cases=37 aborts=4 faults=15 functional_only=1'

def verify(text,mode):
    if mode not in (0,1,2,3,4):raise ValueError('unknown mode')
    lines=text.splitlines();markers=[l for l in lines if any(t in l for t in ('PASS','DIFF','fatal','%Error','MUTANT_'))]
    if mode in (1,2,3):
        if len(markers)!=1:raise ValueError('exactly one DIFF and no foreign marker required')
        m=DIFF.fullmatch(markers[0])
        if not m:raise ValueError('malformed DIFF')
        selected,case,kind,index,expected,actual=m.groups()
        if int(selected)!=mode or int(case)!=0 or int(index)!=0:raise ValueError('DIFF mode/case/index binding')
        if mode==2:
            if kind!='CAND_VALUE_DIFF' or len(expected)!=128 or len(actual)!=128:raise ValueError('value DIFF format')
            raw=V.scores(512,'all_tie');oracle=V.expected(512,1,raw)[0]
            if int(expected,16)!=oracle:raise ValueError('DIFF expectation differs from independent assertion')
            # Source mutant <=quota admits lane1 in addition to lane0.
            if int(actual,16)!=1<<32 or int(actual,16)==oracle:raise ValueError('DIFF actual not the exact source mutant witness')
        else:
            if kind!='CAND_RETIRE_COUNT_DIFF' or expected!='1' or actual!='0':raise ValueError('DIFF exact count witness')
        return dict(mode=mode,status='EXPECTED_MUTANT_DIFF',kind=kind,case=0,index=0)
    terminal_line=TERMINAL.replace('profile=0','profile='+str(mode))
    case_seen=set();abort_seen=set();fault_seen=set();terminal=0
    for line in markers:
        m=CASE.fullmatch(line)
        if m:
            index,n,k,ref,cand,delta,fetch=map(int,m.groups())
            if not 0<=index<37 or index in case_seen:raise ValueError('case index or duplicate')
            wn,wk,_=V.cases()[index]
            if (n,k,ref,cand,delta,fetch)!=(wn,wk,(wk+15)//16,(wk+15)//16,0 if mode==4 else 368,2*wn//16):raise ValueError('exact case counter/calibration mismatch')
            case_seen.add(index);continue
        m=ABORT.fullmatch(line)
        if m:
            phase,index=map(int,m.groups())
            if not 1<=phase<=4 or index!=5 or phase in abort_seen:raise ValueError('abort marker binding')
            abort_seen.add(phase);continue
        m=FAULT.fullmatch(line)
        if m:
            kind,busy=map(int,m.groups())
            if not 0<=kind<15 or kind in fault_seen or busy!=int(kind>=10):raise ValueError('fault marker binding')
            fault_seen.add(kind);continue
        if line==terminal_line:terminal+=1;continue
        raise ValueError('foreign/malformed completion marker')
    if terminal!=1 or case_seen!=set(range(37)) or abort_seen!=set(range(1,5)) or fault_seen!=set(range(15)):
        raise ValueError('missing or duplicated terminal/counters')
    # No marker may follow terminal; generated finish diagnostics may.
    if markers[-1]!=terminal_line:raise ValueError('terminal order')
    return dict(mode=mode,status='PASS_FULL_SHAPE_FUNCTIONAL_ONLY',cases=37,aborts=4,faults=15)
