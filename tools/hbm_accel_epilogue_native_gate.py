#!/usr/bin/env python3
"""Exact numerical component gate against ONLY pinned NativePrimitiveVM. No model inference."""
import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE='results/uarch/c0_pc40_payload_lease_20261003/inputs/h3_qwen_bounded_native.py'
SOURCE_SHA='282e57ab97f2dcdd0205b6f4e11ec189b669e3cc48548fab5f6d3c373d63c32b'
OPS=('COPY','BITCAST_U','BITCAST_F','AND','OR','XOR','IADD','ISUB','SHR','SHL',
     'FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE','SELECT','FMAX','FMIN')
RTL='rtl/hbm_accel/epilogue/ot_hbm_accel_native_bits.sv'


def vm(root):
    raw=(root/SOURCE).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise ValueError('released primitive source pin')
    tree=ast.parse(raw)
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativePrimitiveVM')
    const=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='COMMON_NATIVE' for t in n.targets))
    ns=dict(np=np,F=np.float32,Counter=Counter)
    # No whole module import, TrainedByteBackend, checkpoint, inference or source-provider constructor.
    exec(compile(ast.Module(body=[const,node],type_ignores=[]),'pinned-scalar-primitive','exec'),ns)
    return ns['NativePrimitiveVM']()


def words(bits,t):
    u=np.asarray(bits,np.uint64)
    if t==0:return u.astype(np.uint32).view(np.float32)
    if t==1:return u.astype(np.uint32)
    return u.view(np.int64)


def bits(value,t):
    x=np.asarray(value)
    if t==0:return int(x.astype(np.float32).view(np.uint32))
    if t==1:return int(x.astype(np.uint32))
    return int(x.astype(np.int64).view(np.uint64))


def pack(xs):return ''.join(f'{int(x):016x}' for x in reversed(xs))


def vectors(v):
    rng=np.random.default_rng(20261003)
    cases=[]
    special=[0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,
             0x7fc00001,0x7f800001,0xffc00002,1,0x80000001,0x7f7fffff,0xff7fffff]
    integers=[0,1,31,32,63,64,0xffffffff,0x100000000,0x100000001,
              0x7fffffffffffffff,0x8000000000000000,0xffffffffffffffff]
    def add(op,dt,at,bt,ct,a,b,c,sc=0,mask=15,tag=''):
        outt=at if op=='COPY' else 1 if op in ('BITCAST_U','FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE') else 0 if op in ('BITCAST_F','FMAX','FMIN') else dt
        aa,bb,cc=words(a,at),words(b,bt),words(c,ct)
        result=[0]*4;fault=0
        for lane in range(4):
            if not(mask>>lane&1):continue
            av=aa[0 if sc&1 else lane];bv=bb[0 if sc&2 else lane];cv=cc[0 if sc&4 else lane]
            args=[av] if op in ('COPY','BITCAST_U','BITCAST_F') else [av,bv,cv] if op=='SELECT' else [av,bv]
            try:
                value=v.primitive(op,args,{'dtype':('F32','U32','I64')[dt]})
                result[lane]=bits(value,outt)
            except ValueError:fault|=1<<lane
        cases.append(dict(op=op,dt=dt,at=at,bt=bt,ct=ct,sc=sc,mask=mask,a=a,b=b,c=c,result=result,outt=outt,fault=fault,tag=tag))
    for op in OPS:
        for n in range(160):
            dt=1 if n%2==0 else 2
            at=bt=ct=dt
            a=rng.integers(0,2**64,size=4,dtype=np.uint64).tolist()
            b=rng.integers(0,2**64,size=4,dtype=np.uint64).tolist()
            c=rng.integers(0,2**64,size=4,dtype=np.uint64).tolist()
            if op in ('BITCAST_U','FMAX','FMIN') or op.startswith('FCMP_') and n%3==0:
                at=bt=0;dt=0 if op in ('FMAX','FMIN') else 1
                a=[special[(n+j)%len(special)] if n<80 else x&0xffffffff for j,x in enumerate(a)]
                b=[special[(n*3+j)%len(special)] if n<80 else x&0xffffffff for j,x in enumerate(b)]
            if op=='BITCAST_F':at=1 if n%2==0 else 2;dt=0
            if op=='COPY':at=n%3;dt=at
            if op=='SELECT':
                dt=n%3;bt=ct=dt;at=n%3
                a=[special[(n+j)%len(special)] if at==0 else integers[(n+j)%len(integers)] for j in range(4)]
            if op in ('SHR','SHL'):
                # Explicit U32 casting of a wide shift count must occur before range checking.
                b=[integers[(n+j)%len(integers)] if n<60 else int(x%70) for j,x in enumerate(b)]
                bt=2
            if op.startswith('FCMP_') and n%3==1:at=1;bt=2
            add(op,dt,at,bt,ct,a,b,c,sc=n%8,mask=n%16,tag='random/directed')
    # Literal seven-step BF16 recipe: no algebraic folding of its integer stages.
    for n in range(64):
        x=[special[(n+j)%len(special)] if n<20 else int(z) for j,z in enumerate(rng.integers(0,2**32,size=4,dtype=np.uint32))]
        env={'x':x}
        seq=[('BITCAST_U','bits',x,[0]*4),('SHR','hi',x,[16]*4)]
        add('BITCAST_U',1,0,1,1,x,[0]*4,[0]*4,tag='BF16 step0')
        add('SHR',1,1,1,1,x,[16]*4,[0]*4,tag='BF16 step1')
        hi=[int(z)>>16 for z in x];lsb=[z&1 for z in hi]
        add('AND',1,1,1,1,hi,[1]*4,[0]*4,tag='BF16 step2')
        add('IADD',1,1,1,1,x,[32767]*4,[0]*4,tag='BF16 step3')
        bias=[(z+32767)&0xffffffff for z in x]
        add('IADD',1,1,1,1,bias,lsb,[0]*4,tag='BF16 step4')
        rounded=[(z+q)&0xffffffff for z,q in zip(bias,lsb)]
        add('AND',1,1,1,1,rounded,[0xffff0000]*4,[0]*4,tag='BF16 step5')
        add('BITCAST_F',0,1,1,1,[z&0xffff0000 for z in rounded],[0]*4,[0]*4,tag='BF16 step6')
    return cases


TB=r'''module tb;
 reg [4:0]opcode;reg [1:0]dtype,a_type,b_type,c_type;reg a_scalar,b_scalar,c_scalar;
 reg [3:0]lane_mask;reg [255:0]a_data,b_data,c_data;
 wire [255:0]result,off_result;wire [1:0]result_type,off_type;wire[3:0]lane_fault,off_fault;wire supported,off_supported;
 ot_hbm_accel_native_bits #(.ENABLE(1))dut(.*);
 ot_hbm_accel_native_bits #(.ENABLE(0))off(.opcode(opcode),.dtype(dtype),.a_type(a_type),.b_type(b_type),.c_type(c_type),
 .a_scalar(a_scalar),.b_scalar(b_scalar),.c_scalar(c_scalar),.lane_mask(lane_mask),.a_data(a_data),.b_data(b_data),.c_data(c_data),
 .result(off_result),.result_type(off_type),.lane_fault(off_fault),.supported(off_supported));
 integer fd,r,k,n=0,errors=0,op,dt,at,bt,ct,sc,mask,typ,err;
 reg[255:0]expected;reg[2047:0]file;
 initial begin
 if(!$value$plusargs("VECTORS=%s",file))$fatal(1,"vectors required");fd=$fopen(file,"r");
 while(!$feof(fd))begin
 r=$fscanf(fd,"%d %d %d %d %d %d %d %h %h %h %h %d %d\n",op,dt,at,bt,ct,sc,mask,a_data,b_data,c_data,expected,typ,err);
 if(r==13)begin
 opcode=op;dtype=dt;a_type=at;b_type=bt;c_type=ct;{c_scalar,b_scalar,a_scalar}=sc;lane_mask=mask;#1;
 if(!supported||result_type!==typ[1:0]||lane_fault!==err[3:0])begin errors=errors+1;$display("METAFAIL case%0d op%0d type%0d/%0d err%0h/%0h",n,op,result_type,typ,lane_fault,err);end
 for(k=0;k<4;k=k+1)if(!err[k]&&result[k*64+:64]!==expected[k*64+:64])begin errors=errors+1;$display("DATAFAIL case%0d op%0d lane%0d got%h exp%h",n,op,k,result[k*64+:64],expected[k*64+:64]);end
 if(off_supported!==0||off_result!==0||off_fault!==0)begin errors=errors+1;$display("DEFAULTFAIL");end
 n=n+1;
 end end
 $display("DONE cases=%0d errors=%0d",n,errors);if(errors)$fatal(1,"numerical mismatch");$finish;
 end endmodule'''


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise SystemExit('Existing verdict retained')
    a.work.mkdir(parents=True,exist_ok=False)
    oracle=vm(a.source_root);cases=vectors(oracle)
    vec=a.work/'vectors.txt'
    vec.write_text(''.join(f"{OPS.index(c['op'])} {c['dt']} {c['at']} {c['bt']} {c['ct']} {c['sc']} {c['mask']} {pack(c['a'])} {pack(c['b'])} {pack(c['c'])} {pack(c['result'])} {c['outt']} {c['fault']}\n" for c in cases))
    tb=a.work/'tb.sv';tb.write_text(TB);binary=a.work/'sim'
    inputs={str(ROOT/RTL):hashlib.sha256((ROOT/RTL).read_bytes()).hexdigest(),str(ROOT/'rtl/hdc/ot_hdc_prefix.sv'):hashlib.sha256((ROOT/'rtl/hdc/ot_hdc_prefix.sv').read_bytes()).hexdigest(),str(a.source_root/SOURCE):SOURCE_SHA,str(vec):hashlib.sha256(vec.read_bytes()).hexdigest()}
    build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(ROOT/RTL),str(ROOT/'rtl/hdc/ot_hdc_prefix.sv'),str(tb)],capture_output=True,text=True)
    (a.work/'build.log').write_text(build.stdout+build.stderr)
    run=subprocess.run(['vvp',str(binary),'+VECTORS='+str(vec)],capture_output=True,text=True) if build.returncode==0 else None
    if run:(a.work/'run.log').write_text(run.stdout+run.stderr)
    verdict=dict(schema='opentallas.ha3.native_datapath_exact.v1',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),host=socket.gethostname(),run_pid=os.getpid(),input_sha256=inputs,build_returncode=build.returncode,run_returncode=None if run is None else run.returncode,status='PASS_NUMERICAL_COMPONENT' if run and run.returncode==0 else 'FAILED',cases=len(cases),lanes=4,opcodes=dict(Counter(c['op'] for c in cases)),golden='Pinned NativePrimitiveVM scalar/vector primitive only; no checkpoint or model inference',scope='17 stateless beat datapaths including explicit BF16 integer stages; NOT Pauli wholeprimitive controller/realRF/Nashgrant/nativefactory/1737token',measured_controller_cycles=None,ss_wns=None,ff_wns=None,adopt=False)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:json.dump(verdict,f,indent=2);f.write('\n')
    print(json.dumps({k:verdict[k] for k in ('status','cases','run_returncode')},indent=2))
    return 0 if verdict['status']=='PASS_NUMERICAL_COMPONENT' else 1


if __name__=='__main__':raise SystemExit(main())
