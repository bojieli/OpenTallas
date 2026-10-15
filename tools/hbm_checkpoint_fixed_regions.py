#!/usr/bin/env python3
"""Source-derived fixed HBM extent ledger and actual HC descriptor capacity gate."""
import hashlib,json,math,subprocess,ast
from pathlib import Path
from types import SimpleNamespace
from hbm_checkpoint_allocation import constants
from hgi_sim import ds_native as D
ROOT=Path(__file__).resolve().parents[1]

def run(out):
    config_path=ROOT/'compiler/models/deepseek-v4.1-flash/inference_config.json'
    c=json.loads(config_path.read_text());context=1048576
    mt=constants(ROOT/'tools/hgi_sim/ds_mtp_kernels.py',{'PMAX','BLK','NCOLSLOT','COLB','CSTR','EMBB','MTB','ROPEB','DSKX','ROWQ','ROWMIX','DLOG','WTAB','GOLDB','GSTR','GPOS','MHB','MEMB','WROW','VOCAB','EMB_ROW','MEMB_ROW','TSTR'})
    regions=[];address_vectors=[]
    def add(owner,stack,base,length,source_expr,mode='native/main or MTP',rank='all96'):
        assert 0<=base<base+length<=D.STACK_BYTES,(owner,base,length)
        regions.append(dict(owner=owner,rank=rank,stack=stack,local_bytes=[base,base+length],bytes=length,
            source_expression=source_expr,mode=mode,physical_sector_envelope=[base//32*32,math.ceil((base+length)/32)*32]))
        for byte in (base//32*32,(base+length-1)//32*32):address_vectors.append(((stack<<35)|byte,1))
    # Same main() nmax/cap_rows equations; context is the released W19 target.
    nmax=max((context-1)//c['compress_ratios'][s]+1 for s in c['kv_source_layers'])
    cap_rows=math.ceil(nmax/(8*96))*8
    add('compressed KV FP32 owner row stores',0,D.CKBASE,len(D.SOURCES)*cap_rows*2048,'ds_native.main CK_CAP0=ceil(nmax/(KEY_BLOCK*TP))*KEY_BLOCK*2048;4sources')
    ik_span=math.ceil(nmax*128/D.KALIGN)*D.KALIGN
    add('IKS fixed key regions',0,D.KBASE,len(D.SOURCES)*ik_span,'ds_native.Lower.ik_region:4*ceil(nmax*128/KALIGN)*KALIGN')
    add('selected compressed KV rows',1,0,D.SELB*len(D.SOURCES),'ds_native.SBASE=stack1local0; SELB*len(SOURCES)')
    add('software row gather staging',1,1<<33,math.ceil(D.RG_SLOTS/D.RG_C)*D.RG_C*96*2048,'ds_native.GBASE;ceil(RG_SLOTS/RG_C)*RG_C*TP*2048')
    add('per-layer tables',0,D.TBASE,5*D.TABLE_SPAN,'ds_mtp_kernels.TSLOT five16MiB regions; actual table buffers bounded by slot')
    add('Engram transient stage/list',0,D.EG_STG,2*D.EG_LSPAN,'ds_native.main EGSTG 2*EG_LSPAN')
    add('MTP whole embedding table',0,mt['EMBB'],mt['VOCAB']*mt['EMB_ROW'],'ds_mtp_kernels.full_table exact129280*10240')
    add('MTP constants',0,mt['MTB'],16,'ds_mtp_kernels np.array([1,0,0,0],float32)')
    # Bound every position the full1M decode target can address, not just a tiny replay prefix.
    add('plain RoPE rows',0,mt['ROPEB'],context*256,'ROPEB+position*256; full1M context')
    for stage in range(3):add(f'DSpark KV window{stage}',0,mt['DSKX']+stage*(1<<20),136*mt['WROW'],'ds_mtp_kernels np.zeros(136*WROW)')
    for name,size in [('ROWQ',mt['BLK']*2048),('ROWMIX',mt['BLK']*128),('DLOG',mt['BLK']*1352*4),('WTAB',mt['GPOS']*64),('MHB',16*61440),('MEMB',mt['VOCAB']*mt['MEMB_ROW'])]:
        add(name,0,mt[name],size,'ds_mtp_kernels actual whole registered region')
    add('GOLD_REPLAY diagnostic only',0,mt['GOLDB'],40*mt['GPOS']*mt['GSTR'],'ds_mtp_kernels gold(40*GPOS,GSTR/4) float32','diagnostic replay; not native source')
    for stack in range(4):
        add('MTP column swap slots',stack,mt['COLB'],mt['NCOLSLOT']*mt['CSTR'],'13*128KiB; all4 actual stack regions')
    # Exercise the actual source Lower.hc_row_load, preserving rows, slot, strides and all43 layers.
    hcd=[];vectors=0;seen=set();false_empty=0
    for layer in range(c['n_layers']+c['n_mtp_layers']):
        for which in ('attn','ffn'):
            for rank in range(96):
                rec=D.Lower.hc_row_load(SimpleNamespace(),layer,which,rank)
                if rec is None:false_empty+=1;continue
                a=rec.desc['A'];base=a.base&((1<<35)-1)
                assert a.base>>37==1 and a.n==2560 and a.m==8 and a.stride==10240
                assert D.HC_STRIPE_LOC==D.DATA_WIN
                assert D.DATA_WIN<=base<base+81920<=mt['COLB']
                key=(layer,which,rank//4);assert key not in seen;seen.add(key)
                for bank in range(8):
                    for edge in (0,319):
                        byte=base+bank*10240+edge*32
                        assert byte+32<=D.STACK_BYTES
                        s=byte>>5;assert s<1<<30
                        address_vectors.append((((bank%4)<<35)|byte,1));vectors+=1
                hcd.append(dict(layer=layer,which=which,rank=rank,local_bytes=[base,base+81920],
                    stripe4=True,sectors_per_bank=320,bank_stack='bank%4',native_delivery_join_qualified=False))
    for stack in range(4):address_vectors.append(((stack<<35)|(30<<30),0))
    old_iks=D.IKS[0];old_caps=list(D.CK_CAP)
    try:
        D.IKS[0]=True;D.CK_CAP[1]=nmax
        actual=D.Lower.__new__(D.Lower);actual.ent={};actual.man=D.Manifest()
        ik_actual=[actual.ik_region(s) for s in D.SOURCES]
        assert min(e['base'] for e in ik_actual)==D.KBASE
        assert max(e['base']+e['estride'] for e in ik_actual)<=D.K_LIMIT
    finally:
        D.IKS[0]=old_iks;D.CK_CAP[:]=old_caps
    hc_end=max(x['local_bytes'][1] for x in hcd)
    for stack in range(4):add('HC all released layer rows',stack,D.HC_STRIPE_LOC,hc_end-D.HC_STRIPE_LOC,'actual hc_row_load all43*2*24*81920B')
    candidate=[(16640<<20),(18688<<20)] #16.25..18.25GiB, 2048actual HBM rows
    coll=[r for r in regions if r['local_bytes'][0]<candidate[1] and candidate[0]<r['local_bytes'][1]]
    assert not coll
    overlap=[]
    for i,a in enumerate(regions):
        for b in regions[i+1:]:
            if a['stack']==b['stack'] and a['local_bytes'][0]<b['local_bytes'][1] and b['local_bytes'][0]<a['local_bytes'][1]:
                overlap.append(dict(a=a['owner'],b=b['owner'],a_mode=a['mode'],b_mode=b['mode'],stack=a['stack']))
    out.parent.mkdir(parents=True,exist_ok=True)
    vec=out.parent/'address_vectors.hex';tb=out.parent/'tb_fixed_region_addresses.sv';exe=out.parent/'address_gate.vvp'
    vec.write_text(''.join(f'{(valid<<37)|address:010x}\n' for address,valid in address_vectors))
    tb.write_text('''module tb;
reg[36:0]a;wire[1:0]st;wire[4:0]pc;wire[29:0]sec;wire valid;
reg[37:0]v[0:COUNT-1];integer i;reg[29:0]expected_s;
ot_hbm_loader_kport_address #(.ENABLE(1))u(.byte_address(a),.stack_bytes(36'd22500000000),.stack(st),.pc(pc),.sector_address(sec),.valid(valid));
initial begin $readmemh("VECTOR",v);for(i=0;i<COUNT;i=i+1)begin
 a=v[i][36:0];#1;expected_s=a[34:5];
 if(valid!==v[i][37]||st!==a[36:35]||sec!==expected_s||pc!==(expected_s[6:2]^expected_s[11:7]^expected_s[16:12]))$fatal(1,"address vector %0d",i);
 end $display("FIXED_REGION_ADDRESS_PASS vectors=%0d",COUNT);$finish;end
endmodule
'''.replace('COUNT',str(len(address_vectors))).replace('VECTOR',str(vec.resolve())))
    comp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(tb),str(ROOT/'rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv')],capture_output=True,text=True)
    assert comp.returncode==0,comp.stderr
    gate=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    (out.parent/'address_gate.log').write_text(gate.stdout+gate.stderr)
    assert gate.returncode==0 and 'FIXED_REGION_ADDRESS_PASS' in gate.stdout,gate.stdout+gate.stderr
    exe.unlink()
    predecessor_commit='649a91436'
    old_sources={}
    for path in ('tools/hgi_sim/ds_native.py','tools/hgi_sim/ds_mtp_kernels.py'):
        blob=subprocess.check_output(['git','show',predecessor_commit+':'+path],cwd=ROOT)
        env={}
        for node in ast.parse(blob.decode()).body:
            if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ('HC_STRIPE_LOC','KBASE','EG_STG','EG_LSPAN','GOLDB'):
                exec(compile(ast.Module(body=[node],type_ignores=[]),path,'exec'),{'__builtins__':{}},env)
        old_sources[path]=dict(sha256=hashlib.sha256(blob).hexdigest(),constants=env)
    olddn=old_sources['tools/hgi_sim/ds_native.py']['constants'];oldmtp=old_sources['tools/hgi_sim/ds_mtp_kernels.py']['constants']
    predecessor_errors=[
        dict(a='IKS fixed key regions',b='MTP embedding',overlap_bytes=[olddn['KBASE'],olddn['KBASE']+len(D.SOURCES)*ik_span]),
        dict(a='Engram transient',b='plain RoPE',overlap_bytes=[olddn['EG_STG'],olddn['EG_STG']+2*olddn['EG_LSPAN']]),
        dict(a='GOLD_REPLAY',b='persistent CKSTORE',overlap_bytes=[oldmtp['GOLDB'],oldmtp['GOLDB']+40*mt['GPOS']*mt['GSTR']]),
        dict(owner='HC stripe',local_base=olddn['HC_STRIPE_LOC'],stack_capacity=D.STACK_BYTES,out_of_capacity=True)]
    result=dict(schema='opentallas.hbm.fixed-region-source-ledger.v1',status='SOURCE_FIXED_RANGES_AND_HC_RELOCATION_CHECKED_NATIVE_JOINS_OPEN',
        context=context,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tools/hbm_checkpoint_fixed_regions.py','tools/hgi_sim/ds_native.py','tools/hgi_sim/ds_mtp_kernels.py','compiler/models/deepseek-v4.1-flash/inference_config.json','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv']},
        fixed_regions=regions,source_region_overlaps=overlap,actual_iks_fixed_guard=True,
        source_predecessor=dict(commit=predecessor_commit,sources=old_sources,errors=predecessor_errors),
        actual_address_facade_gate=dict(vectors=len(address_vectors),pass_gate=True,log_sha256=hashlib.sha256((gate.stdout+gate.stderr).encode()).hexdigest()),
        hc_relocation=dict(predecessor_local_base=30<<30,new_local_base=D.HC_STRIPE_LOC,
            bytes=hc_end-D.HC_STRIPE_LOC,protected_capacity=256<<20,actual_source_descriptors=len(hcd),
            nonowner_nops=false_empty,address_boundary_vectors=vectors,all_within_capacity=True,
            descriptors=hcd,hardware_install_and_delivery_qualified=False),
        prospective_weight_region=dict(local_bytes=candidate,row_base=16640,row_count=2048,
            disjoint_from_all_listed_fixed_ranges=True,installed=False,
            limitations=['Must validate source-published8home Engram intervals separately',
                'Old dense WBASE descriptors are a different address mode; actual static packed native programme translation/installation required',
                'This envelope is not permission to overwrite any existing installed native image']),
        remaining=['Actual shared-source table size bounds and all dynamic DMA descriptor end checks',
            'Native HC image regeneration, load/ACK/readback, and compiler/static delivery join',
            'Physical checkpoint source-owned complete native image/descriptor mapping and installed-range receipts'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(dict(hc_bytes=hc_end-D.HC_STRIPE_LOC,hc_descriptors=len(hcd),vectors=vectors,source_overlaps=overlap)))
    return result
if __name__=='__main__':run(ROOT/'results/arch/hbm_die_v15/fixed_regions/receipt.json')
