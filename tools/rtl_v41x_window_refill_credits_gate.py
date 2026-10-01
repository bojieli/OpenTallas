"""Compare refill credits with identical bounded OOO memory service in both arms."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from tools.rtl_v41x_window_stream_gate import ROOT, SOURCES
BENCH = ROOT/'rtl/test/tb_window_refill_credits.sv'
OUT = ROOT/'results/rtl/v41x_window_refill_credits.json'

def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [*SOURCES, BENCH, Path(__file__), ROOT/'tools/rtl_v41x_window_stream_gate.py']}

def run():
    cases=[]
    with tempfile.TemporaryDirectory(prefix='window-credits-') as tmp:
        for credits in (1,8):
            exe=str(Path(tmp)/f'c{credits}.vvp')
            subprocess.run(['iverilog','-g2012','-s','tb_window_refill_credits',
                            f'-Ptb_window_refill_credits.REFILL_CREDITS={credits}',
                            '-o',exe,*map(str,SOURCES),str(BENCH)],check=True,capture_output=True,text=True)
            for latency,limit in [(2,8),(15,8),(64,8),(15,1)]:
                p=subprocess.run(['vvp',exe,f'+LATENCY={latency}',f'+QUEUE_LIMIT={limit}', '+EPOCH_WRAP'],
                                 check=True,capture_output=True,text=True,timeout=1800)
                assert 'WINDOW_PRODUCER_COMPOSE_PASS' in p.stdout
                def fields(prefix):
                    line=next(x for x in p.stdout.splitlines() if x.startswith(prefix))
                    return {k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',line)}
                metric=fields('EDGE_CONTRACT'); result=fields('WINDOW_PRODUCER_COMPOSE_PASS')
                assert metric['reads']==4352 and metric['writes']==4096 and metric['accepted']==64
                assert metric['max_outstanding']<=min(credits,limit)
                cases.append({'credits':credits,'latency':latency,'queue_limit':limit,'metrics':metric,'result':result})
            if credits==8:
                for kind in ['STALE_EPOCH','UNKNOWN_SECTOR','POISON','DUPLICATE']:
                    p=subprocess.run(['vvp',exe,'+'+kind],check=True,capture_output=True,text=True,timeout=1800)
                    assert 'REFILL_BAD_REPLY_REJECTED' in p.stdout,p.stdout
    for base,fast in zip(cases[:4],cases[4:]):
        assert fast['result']['refill0']<base['result']['refill0']
    rec={'status':'pass','sources':hashes(),'cases':cases,
         'fault_cases':['STALE_EPOCH','UNKNOWN_SECTOR','POISON','DUPLICATE'],
         'scope':'Same actual synthetic producer writes and exact128-row replay twice; identical variable-latency OOO memory model for both arms. No numeric attention, shared K/W arbitration, routed timing or token rate claim.',
         'contract':{'credits':8,'sectors_per_request':1,'sector_bytes':32,'issue_per_cycle':1,'reply_per_cycle':1,'stage_write_ports':1,'new_payload_buffer_bytes':0,'issued_and_received_bits':34,'counter_bits':10,'epoch_bits':11,'extra_state_bits':55,'epoch_wrap':'test initialized nearwrap; newepoch onlyafteroldrow drained; resetrequiresexternaldrain','scale_publication':'requestsector16 onlyafter16code repliescommitted','fault':'stopnewrequests andsuppresspublication untilreset','serial_control':'queue_limit1 preservesoneoutstanding memory; pipelinedcontroller maystillremove FSMturnaroundcycles'}}
    OUT.write_text(json.dumps(rec,indent=2)+'\n')
    return rec

if __name__=='__main__': print(json.dumps(run(),indent=2))
