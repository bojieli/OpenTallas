#!/usr/bin/env python3
"""Prepare source-pinned P1 vectors/model/commands only. NEVER launches a build."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_golden_v41 as G
import rtl_hdc_v41x_hcp_campaign as hc
from lower_hbm_hc_owned_p1_sys1_calendar import prepare
from hgi_sim.records import decode_one
FN_SHA='11c9abd39f35e3364aad812c3f2dcb9c5fa5cf71e0f837a1af684112a00f930c'
PHYS128='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v'
PHYS128_SHA='dba769863f502de28853a78ac30544a406c7cb66fd3249019ef9fa5a5b73e36e'
BASE='rtl/hbm_accel/generic/peers/static_hc/'
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(c,p):return subprocess.check_output(['git','show',c+':'+p],cwd=ROOT)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint-fn',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    raw=a.checkpoint_fn.read_bytes();assert sha(raw)==FN_SHA and len(raw)==1966080
    fn=np.frombuffer(raw,dtype='<f4').reshape(24,20480).copy();rng=np.random.default_rng(20261015);G.set_arith('chunk8')
    # Exactly advance the current native fixture RNG through its discarded
    # synthetic FN and eight residuals, then select declared P1 residual0.
    rng.standard_normal((24,20480));xs=G.to_bf16(rng.standard_normal((8,20480)).astype(G.F));x=xs[0]
    bases=rng.normal(0,1,(1,24)).astype(G.F)[0];scales=rng.uniform(.1,2,(1,3)).astype(G.F)[0]
    mixes=hc.golden_mixes(fn,x.reshape(4,-1),1e-6)[2]
    pre=G.add(G.sigmoid(G.add(G.mul(mixes[:4],scales[0]),bases[:4])),G.F(1e-6))
    post=G.mul(G.sigmoid(G.add(G.mul(mixes[4:8],scales[1]),bases[4:8])),G.F(2))
    c=G.add(G.mul(mixes[8:],scales[2]),bases[8:]).reshape(4,4);e=G.exp(G.add(c,G.neg(np.max(c,axis=1,keepdims=True))))
    c=G.add(G.div(e,G.seqsum([e[:,k] for k in range(4)])[:,None]),G.F(1e-6))
    def cols(v):return G.div(v,G.add(G.seqsum([v[k,:] for k in range(4)]),G.F(1e-6))[None,:])
    def rows(v):return G.div(v,G.add(G.seqsum([v[:,k] for k in range(4)]),G.F(1e-6))[:,None])
    c=cols(c)
    for _ in range(19):c=cols(rows(c))
    tail=np.concatenate((pre,post,c.reshape(-1)))
    weights=fn[0].view(np.uint32).reshape(80,32,8).transpose(2,0,1)
    residual=(x.view(np.uint32)>>16).reshape(80,32,8).transpose(2,0,1)
    for n,v,fmt in [('owned_weights',weights,'%08x'),('residual',residual,'%04x'),('mix_expected',mixes.view(np.uint32),'%08x'),('tail_expected',tail.view(np.uint32),'%08x'),('bases',bases.view(np.uint32),'%08x'),('scales',scales.view(np.uint32),'%08x')]:np.savetxt(a.out/(n+'.mem'),v.reshape(-1),fmt=fmt)
    image,model=prepare();(a.out/'owned_p1_programme.mem').write_text(''.join(f'{w:064x}\n' for w in image));(a.out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    deps=[]
    def dep(c,path):
        b=blob(c,path);target=a.out/'frozen'/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b);deps.append({'commit':c,'path':path,'sha256':sha(b)})
    for f in ['ot_hgi_hc_engine_sys1_split_mtp_static.sv','ot_hgi_hc_projection_sys1_split_static.sv','ot_hgi_hc_programmed_sys1_split_mtp_static.sv','ot_hdc_v41x_hcp_sys1_static.sv','ot_hgi_hc_programme_mtp_static.sv','ot_hgi_hc_tail_static.sv']:dep('c629ab65d',BASE+f)
    for f in ['ot_hgi_hc_bank_control_static.sv','ot_hgi_hc_weight_quarter_static.sv','ot_hgi_hc_residual_half_static.sv']:dep('473756fb3',BASE+f)
    for f in ['ot_hgi_hc_vm_gather_adapter_static.sv','ot_hgi_hc_gathered_mix_reader_static.sv']:dep('3f91b5dba',BASE+f)
    for path in ['rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv','rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv']:dep('3f91b5dba',path)
    dep('bda2a23ae','rtl/hbm_accel/generic/peers/ot_hgi_sfu_program_stripe_static.sv')
    for path in [PHYS128,'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fastfp_lat.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_sfu.sv','rtl/hdc/v41x/ot_hdc_v41x_hcp.sv','rtl/hdc/v41x/ot_hdc_v41x_sfu.sv','rtl/hdc/v41/ot_hdc_fdiv.sv','rtl/hdc/v41/ot_hdc_sinkhorn.sv','rtl/hdc/v41/ot_hdc_sk_arith.sv','rtl/hdc/v41/ot_hdc_sk_recip_rom.sv']:dep('c629ab65d',path)
    assert next(d['sha256'] for d in deps if d['path']==PHYS128)==PHYS128_SHA
    frozen='results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json';frozenblob=blob('c629ab65d',frozen);g25=json.loads(frozenblob);record=g25['layers'][0]['records'][15];decoded,_=decode_one(bytes.fromhex(record['hex']),0);assert decoded.unit=='CTL' and decoded.op=='NOP'
    ownership_path='tools/hgi_sim/ds_native.py';ownership=blob('c629ab65d',ownership_path);assert b'lo, hi = 24 * rank // TP, 24 * (rank + 1) // TP' in ownership
    files=[ROOT/'rtl/test/tb_hgi_hc_owned_p1_sys1_prepared.sv',ROOT/'rtl/test/hgi_hc_owned_p1_sys1_prepared_harness.cpp']
    for f in files:
        target=a.out/'frozen'/f.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(f.read_bytes())
    command=['verilator','--cc','--exe','--build','-j','4','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','--output-split','10000','--top-module','tb_hgi_hc_owned_p1_sys1_prepared','-Mdir','obj',*[str(Path('frozen')/d['path']) for d in deps],*[str(Path('frozen')/f.relative_to(ROOT)) for f in files]]
    events=model['tail'];tail_cycle=model['tail_launch']+events['result'];args=[f'+WORDS={len(image)}',f'+TAIL_RESULT={tail_cycle}']
    receipt={'status':'PREPARED_NOT_RUN','build_or_simulation_launched':False,'requires_parent_actual92_verdict_and_internal_launch_go':True,'dependency_sources':deps,'new_source_sha256':{str(f.relative_to(ROOT)):sha(f.read_bytes()) for f in files+[Path(__file__),ROOT/'tools/lower_hbm_hc_owned_p1_sys1_calendar.py']},'checkpoint_fn':{'path':str(a.checkpoint_fn),'sha256':FN_SHA,'shape':[24,20480],'owned_row':0},'synthetic_fixture':{'residual':'native RNG20261015 first of8 BF16-valued residuals','bases_scales':'native RNG20261015 synthetic values, not released checkpoint'},'all24_mixes':'independent golden declared post-collective input; NOT fake local24rowprojection or actualHCOLLproducer','local_projection':'exactly one G22 rank3 owned row0, checked independently before gathered landing','ownership_source':{'path':ownership_path,'commit':'c629ab65d','sha256':sha(ownership)},'G25_rank0_row15':{'source':frozen,'commit':'c629ab65d','source_sha256':sha(frozenblob),'tag':record['tag'],'unit':decoded.unit,'op':decoded.op,'record_hex':record['hex']},'fixture_sha256':{p.name:sha(p.read_bytes()) for p in a.out.glob('*.mem')},'build_command_NOT_RUN':command,'runtime_commands_NOT_RUN':[['obj/Vtb_hgi_hc_owned_p1_sys1_prepared',*args],['obj/Vtb_hgi_hc_owned_p1_sys1_prepared',*args,'+MUT_OWNED_ROW'],['obj/Vtb_hgi_hc_owned_p1_sys1_prepared',*args,'+MUT_GATHER']],'qualification':{'canonical_wholeprofile':False,'physical_phase':False,'arithmetic_successor':False,'real128_macro_successor':False}}
    (a.out/'prepared.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PREPARED_NOT_RUN: real64weight+16residual+24VM+2programme SRAMs, oneowned row, declared24mix landing; heavybuild NOT launched')
if __name__=='__main__':main()
