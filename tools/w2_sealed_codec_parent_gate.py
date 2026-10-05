"""Independent actual RTL codec gate; no NC6, clock or physical qualification."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mem_compiler import ecc

PC,INDEX,KIND=113,269,3
def encoded(data):
    systematic=ecc.encode(data,64)
    out=0
    for j,pos in enumerate(ecc.positions(64)):out|=((systematic>>j)&1)<<(pos-1)
    for j in range(7):out|=((systematic>>(64+j))&1)<<((1<<j)-1)
    return out|((systematic>>71)<<71)

def expected(word,width):
    systematic=0
    for j,pos in enumerate(ecc.positions(64)):systematic|=((word>>(pos-1))&1)<<j
    for j in range(7):systematic|=((word>>((1<<j)-1))&1)<<(64+j)
    systematic|=((word>>71)&1)<<71
    data,status=ecc.decode(systematic,64)
    seal=data>>44==((KIND<<17)|(INDEX<<7)|PC)
    padding=(data&((1<<44)-1))>>width==0
    flags=(status=='ok')|((status=='corrected')<<1)|((status=='uncorrectable')<<2)|(seal<<3)|(padding<<4)|((status=='ok' and seal and padding)<<5)
    valid=status!='uncorrectable' and seal and padding
    return flags,(data&((1<<44)-1)) if valid else 0,encoded(data) if valid else 0

def run(out):
    out=Path(out);out.mkdir(exist_ok=False)
    source=ROOT/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv'
    pins={str(source.relative_to(ROOT)):hashlib.sha256(source.read_bytes()).hexdigest(),
          'tools/mem_compiler/ecc.py':hashlib.sha256((ROOT/'tools/mem_compiler/ecc.py').read_bytes()).hexdigest(),
          'tools/w2_sealed_codec_parent_gate.py':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    rows=[];counts={'clean':0,'single':0,'double':0,'seal':0,'padding':0}
    def add(width,payload,current,category):
        f,p,w=expected(current,width)
        data=payload|(PC<<44)|(INDEX<<51)|(KIND<<61)
        rows.append(f'{width} {payload:011x} {current:018x} {encoded(data):018x} {f:02x} {p:011x} {w:018x}\n');counts[category]+=1
    for width in (17,44):
        for payload in (0,(1<<width)-1):
            data=payload|(PC<<44)|(INDEX<<51)|(KIND<<61);word=encoded(data)
            add(width,payload,word,'clean')
            for i in range(72):add(width,payload,word^(1<<i),'single')
            for i in range(72):
                for j in range(i):add(width,payload,word^(1<<i)^(1<<j),'double')
            for bit in range(44,64):add(width,payload,encoded(data^(1<<bit)),'seal')
        if width<44:
            for bit in range(width,44):add(width,0,encoded((PC<<44)|(INDEX<<51)|(KIND<<61)|(1<<bit)),'padding')
    vectors=out/'vectors.txt';vectors.write_text(''.join(rows))
    tb='''`timescale 1ps/1ps
module tb;
reg [43:0] payload; reg [71:0] current_word;
wire [71:0] encoded_word[0:1],repaired_word[0:1];
wire [43:0] repaired_payload[0:1];wire [5:0] flags[0:1];
genvar g;generate for(g=0;g<2;g=g+1) begin
ot_w2_sealed_secded72 #(.PC_ID(113),.WORD_INDEX(269),.WORD_KIND(3),.PAYLOAD_BITS(g==0?17:44)) dut(
.payload(payload),.current_word(current_word),.encoded_word(encoded_word[g]),
.syndrome(),.overall_odd(),.clean(flags[g][0]),.correctable(flags[g][1]),
.uncorrectable(flags[g][2]),.seal_ok(flags[g][3]),.padding_ok(flags[g][4]),
.release_clean(flags[g][5]),.repaired_payload(repaired_payload[g]),.repaired_word(repaired_word[g]));
end endgenerate
integer fd,n,width,k,checked;reg[71:0] ew,rw;reg[43:0] rp;reg[5:0] f;reg[2047:0] file_name;
initial begin
if(!$value$plusargs("VECTORS=%s",file_name)) $fatal(1,"vectors missing");
fd=$fopen(file_name,"r");if(!fd)$fatal(1,"open vectors");checked=0;
while(!$feof(fd)) begin
n=$fscanf(fd,"%d %h %h %h %h %h %h\\n",width,payload,current_word,ew,f,rp,rw);
if(n!=7)$fatal(1,"malformed vector");k=(width==17?0:1);#1;
if(encoded_word[k]!==ew||flags[k]!==f||repaired_payload[k]!==rp||repaired_word[k]!==rw)
 $fatal(1,"codec mismatch case=%0d width=%0d flags=%h expected=%h",checked,width,flags[k],f);
checked=checked+1;
end
$display("PASS_ACTUAL_SEALED_CODEC cases=%0d",checked);$finish;
end
endmodule
'''
    (out/'tb.sv').write_text(tb)
    stages=[]
    for name,args in [('compile',['iverilog','-g2012','-s','tb','-o',str(out/'sim.vvp'),str(source),str(out/'tb.sv')]),
                      ('run',['vvp',str(out/'sim.vvp'),'+VECTORS='+str(vectors)])]:
        p=subprocess.run(args,capture_output=True,text=True)
        (out/(name+'.log')).write_text(p.stdout+p.stderr)
        stages.append({'stage':name,'rc':p.returncode})
        if p.returncode:break
    stable=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pins.items())
    marker=f'PASS_ACTUAL_SEALED_CODEC cases={len(rows)}'
    passed=len(stages)==2 and all(x['rc']==0 for x in stages) and marker in (out/'run.log').read_text() and stable
    record={'status':'PASS_ACTUAL_CODEC_ONLY' if passed else 'FAIL_PRESERVED','source_stable':stable,
            'source_pins':pins,'cases':len(rows),'coverage':counts,'stages':stages,'full_NC6':False,'SS_FF':False,'latency_or_rate_adoption':False}
    record['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2));return 0 if record['status'].startswith('PASS') else 1
if __name__=='__main__':sys.exit(run(sys.argv[1]))
