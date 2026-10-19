#!/usr/bin/env python3
"""Actual cmd-cal store playback of source-derived local boundary words.
Not a complete token bench. Uses production4096/128 ABI and all36stageIDs.
"""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(HERE),str(ROOT/'tools'),str(ROOT/'tools/qwen_layerbench')]
import mu_seq_bench as B
import dv_lower as D
import dv_lower_vec as V
import global_boundary as G


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--vl',required=True);a=ap.parse_args()
    a.work.mkdir(parents=True,exist_ok=True)
    vm=V.vm_map_vec(D.ownership());contract=G.layer_contract(ROOT/V.PROG)
    cmds=[]
    for s in range(12):
        cmds.append(D.cmd_root(s,int(s==0),32,vm['SSX']['base'],int(s==0),vm['RX']['base'],D.f32(1e-6),12))
        cmds.append(D.cmd_stream(s,1 if s==0 else 3,1))
        cmds.append(D.cmd_stn(s,1,0,8,8,1,vm['QKV']['base']))
    cmds.append(D.cmd_stn(0,2,0,8,264,0,18720,amax=1))
    cmds+=[D.cmd_ports(15,vm['T']['base'],vm['ATT']['base'],1,1,vm['X']['base'],1),D.cmd_su(11,15)]
    B.SEGS={1:[(8+4*i,c) for i,c in enumerate(cmds)],0:[(8,D.cmd_su(0,15))],2:[(8,D.cmd_su(0,15))],3:[(4,D.cmd_setid(0))]}
    results={}
    for mut in (0,17,18,19):
        d=a.work/f'm{mut}';d.mkdir(exist_ok=True);exe=d/'Vtb_mu_cmd_cal'
        cmd=[a.vl,'--binary','--timing','-j','4','-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb_mu_cmd_cal',
             '-GNU=4',f'-GMUT={mut}','-GUVM_STRIDE=4096','-GPIDX_STRIDE=128','-GBOUNDARY_RELOC=1','-Mdir',str(d)]
        cmd += [str(ROOT/p) for p in B.SOURCES]+[str(B.TB)]
        r=subprocess.run(cmd,capture_output=True,text=True);(d/'build.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError('build failed '+str(d))
        ev=B.load_events(1);start=1200;expected=[]
        for stage in range(1,37):
            for user in range(4):
                ev.append(B.start(start,user,stage))
                for c in cmds:
                    kind=c>>1&7;e=c
                    def put(lsb,w,val):
                        nonlocal e
                        e=(e&~(((1<<w)-1)<<lsb))|val<<lsb
                    if kind==3:
                        put(11,24,vm['SSX']['base']+4096*user);put(36,24,vm['RX']['base']+4096*user)
                    elif kind==5:put(12,2,user)
                    elif kind==2:
                        if not (c>>50&1):put(15,9,8+[0,272,344,416][user])
                        if c>>24&1:put(26,24,vm['QKV']['base']+4096*user)
                    elif kind==4:
                        for lsb in (4,28,54):put(lsb,24,(c>>lsb&((1<<24)-1))+4096*user)
                    elif kind==1:put(4,9,11+128*user)
                    expected.append((user,e))
                start+=220
        out=B.run(d,exe,'all36',ev,start+100)
        actual=[(u,w) for _,k,u,w in out['ev'] if k=='CMD']
        # The boot SETID precedes stage execution.
        if actual and actual[0][1]==D.cmd_setid(0):actual=actual[1:]
        mism=sum(x!=y for x,y in zip(actual,expected))+abs(len(actual)-len(expected))
        good=out['end'][0]==0 and mism==0
        results[mut]=dict(mismatches=mism,commands=len(actual),expected=len(expected),fault=out['end'][0],pass_=good)
        print(('BOUNDARY_JOIN_PASS' if good else 'BOUNDARY_JOIN_FAIL'),mut,results[mut],flush=True)
        if good != (mut==0):raise RuntimeError('positive/negative-control outcome wrong')
        if mut==0:
            bads=[D.cmd_root(0,1,32,4096,1,vm['RX']['base']),D.cmd_stn(0,2,0,8,268,0,0,amax=1),
                  D.cmd_stn(0,1,0,8,68,1,0),D.cmd_stream(0,1,64)]
            saved=B.SEGS
            for i,bad in enumerate(bads):
                B.SEGS=dict(saved);B.SEGS[1]=[(8,bad)]
                badout=B.run(d,exe,f'guard{i}',B.load_events(1)+[B.start(1200,0,1)],1300)
                if badout['end'][0]!=1 or not(int(badout['end'][1],2)&8):raise RuntimeError('invalid boundary accepted '+str(i))
            B.SEGS=saved
            print('BOUNDARY_GUARDS_PASS 4',flush=True)
    # Refuse overlapping scalar live state, including across user/stage.
    base=dict(user=0,stage=1,arm=10,retire=20,resources=['scalar'],producer_sha256='1'*64,consumer_sha256='2'*64)
    G.check_lifetimes([base])
    try:G.check_lifetimes([base,dict(base,user=1,stage=2,arm=19,retire=21)])
    except ValueError:pass
    else:raise RuntimeError('lifetime overlap admitted')
    (a.work/'summary.json').write_text(json.dumps(dict(results=results,vm=vm,x_contract=contract),indent=2)+'\n')
    print('BOUNDARY_JOIN_MATRIX_PASS',flush=True)
if __name__=='__main__':main()
