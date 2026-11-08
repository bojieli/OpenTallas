"""Extract the actual six-bus face-register mechanism and native PI operands."""
import json,re,sys
from pathlib import Path
BUS=('fhN','piN','piN_d1','piN_d2','piN_d3','rhN')
def producer(file):
    s=file.read_text();out={}
    for width,bus,expr in re.findall(r'ot_dp_st #\(\.W\((\d+)\)\) u_bout_(o_phy_Q__sN_\w+) \(\.clk\(clk\), \.rst_n\(rst_n\), \.d\((.*?)\), \.ea\(rst_n\)',s):
        key=bus.removeprefix('o_phy_Q__sN_')
        if key in BUS:out[key]=(int(width),expr)
    assert set(out)==set(BUS),(file,out.keys())
    return out
def consumer(file):
    s=file.read_text();operands=re.findall(r'\.pc__pi\(([^\n]+)\),',s)
    assert len(operands)==4,(file,len(operands))
    return operands
def atoms(expr):
    expr=expr.strip()
    if expr.startswith('{')and expr.endswith('}'):
        out=[]
        for x in reversed(expr[1:-1].split(',')):out+=atoms(x)
        return out
    m=re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]',expr);assert m,expr
    hi=int(m[2]);lo=int(m[3]or m[2])
    assert hi>=lo,expr
    return [(m[1],i)for i in range(lo,hi+1)]
def projection(prod,cons):
    bm={key:atoms(expr)for key,(_,expr)in prod.items()}
    out=[]
    for expr in cons:
        row=[]
        for name,bit in atoms(expr):
            key=name.removeprefix('i_phy_Q__sN_').removesuffix('_q')
            assert key in bm,(name,key)
            row.append(bm[key][bit])
        assert len(row)==289,len(row)
        out+=row
    assert all(name.startswith('w_core_pi') for name,bit in out)
    return out
def emit(name,prod,cons):
    lines=[f'module {name}(input wire clk,input wire [288:0] w_core_pi0,w_core_pi1,w_core_pi2,w_core_pi3,input wire[3:0] w_core_fh0,w_core_fh1,w_core_fh2,w_core_fh3,w_core_rh0,w_core_rh1,w_core_rh2,w_core_rh3,output wire[1155:0] result);']
    for key,(width,expr) in prod.items():
        lines += [f'reg [{width-1}:0] tx_{key};',f'reg [{width-1}:0] i_phy_Q__sN_{key}_q;',f'always @(posedge clk) begin tx_{key}<={expr}; i_phy_Q__sN_{key}_q<=tx_{key}; end']
    lines += ['assign result={'+','.join(reversed(cons))+'};','endmodule']
    return '\n'.join(lines)+'\n'
def main():
    old,new,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
    cases=[];sv=[]
    for phy in ('kv3_phy','kv3_phy_v1'):
        op=producer(old/(phy+'_part.sv'));np=producer(new/(phy+'_part.sv'))
        for pc in sorted(x for x in new.glob('kv3_pc*.sv')if 'i_phy_Q__sN_piN_d3_q'in x.read_text()):
            oldpc=old/pc.name
            oc=consumer(oldpc);nc=consumer(pc)
            a,b=projection(op,oc),projection(np,nc)
            assert a==b,(phy,pc.name,'live PI projection changed')
            assert len(set(a))==1156,'payload bit duplicate/drop'
            number=len(cases);sv += [emit('old'+str(number),op,oc),emit('new'+str(number),np,nc)]
            cases.append({'phy':phy,'pc':pc.stem,'live_bits':1156,'projection_equal':True,'cycles':2})
    assert len(cases)==12,len(cases)
    test=['module tb;reg clk=0;always #5 clk=~clk;reg[288:0]p0,p1,p2,p3;wire[3:0]c={4{clk}};integer failures=0;integer hits[0:11];integer n,j;',
          'function automatic[288:0] random_payload(input integer unused);integer k;begin for(k=0;k<9;k=k+1)random_payload[k*32+:32]=$urandom;random_payload[288]=$urandom_range(0,1);end endfunction']
    con=lambda mutate:'.clk(clk),.w_core_pi0('+('p0^289\'d1'if mutate else'p0')+'),.w_core_pi1(p1),.w_core_pi2(p2),.w_core_pi3(p3),'+','.join(f'.w_core_{k}(c)'for k in ('fh0','fh1','fh2','fh3','rh0','rh1','rh2','rh3'))
    for i in range(12):
        test += [f'wire[1155:0]a{i},b{i},m{i};old{i} oa{i}({con(False)},.result(a{i}));new{i} nb{i}({con(False)},.result(b{i}));new{i} nm{i}({con(True)},.result(m{i}));']
    test += ['initial begin for(j=0;j<12;j=j+1)hits[j]=0; p0=0;p1=0;p2=0;p3=0;for(n=0;n<1000;n=n+1)begin @(negedge clk);p0=random_payload(0);p1=random_payload(0);p2=random_payload(0);p3=random_payload(0);@(posedge clk);#1;if(n>3)begin']
    for i in range(12):test += [f'if(a{i}!==b{i})failures=failures+1;if(a{i}!==m{i})hits[{i}]=hits[{i}]+1;']
    test += ['end end for(j=0;j<12;j=j+1)if(hits[j]==0)failures=failures+1;if(failures)$fatal(1,"MAPPING_FAIL %0d",failures);$display("MAPPING_LOCKSTEP_PASS cases=12 cycles=1000; LIVE_PI_MUTANT_CAUGHT cases=12");$finish;end endmodule']
    (out/'miter.sv').write_text('\n'.join(sv+test)+'\n')
    (out/'projection.json').write_text(json.dumps({'verdict':'PASS','cases':cases,'scope':'actual producer/consumer face wiring, every live native PI bit; no complete native core behavior claim'},indent=1))
    print('PASS actual projection, 12 cases; emitted miter.sv')
if __name__=='__main__':main()
