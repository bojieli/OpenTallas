#!/usr/bin/env python3
"""Actual LEF/ETM per-bit screen of NORM bottom internal joins (not whole die qualification)."""
import argparse,json,re,sys,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as A

def pins(path):
    text=path.read_text();out={}
    for m in re.finditer(r'PIN (\S+)\n(.*?)END \1',text,re.S):
        if 'USE POWER' in m[2] or 'USE GROUND' in m[2]:continue
        r=re.search(r'LAYER (\S+) ;\s+RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',m[2])
        if r:out[m[1]]=((float(r[2])+float(r[4]))/2,(float(r[3])+float(r[5]))/2)
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);ap.add_argument('--layout',help='Explicit trial layout JSON; default is die-assigned layout');args=ap.parse_args()
    layout_path=Path(args.layout) if args.layout else ROOT/'physical/s81_die_pins/v19_ntree/layout.json'
    layout=json.loads(layout_path.read_text())['cnbot']['subslots']
    entries={};hashes={}
    def load(key,kit,cell,slot):
        view=ROOT/'physical/ref_tile'/kit/'views'/cell
        ins=json.loads((view/'insertion.json').read_text());metrics={}
        for corner in ['tt','ff']:
            p=view/f'{cell}_{corner}.lib';lib=A.parse_lib(p);refs=A.clock_refs(lib,ins,corner);metrics[corner]=A.pin_metrics(lib,refs)
            hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        xy=pins(view/f'{cell}.lef');x,y,w,h=layout[slot];xy={p:(a+x,b+y) for p,(a,b) in xy.items()}
        hashes[str((view/'insertion.json').relative_to(ROOT))]=hashlib.sha256((view/'insertion.json').read_bytes()).hexdigest()
        hashes[str((view/f'{cell}.lef').relative_to(ROOT))]=hashlib.sha256((view/f'{cell}.lef').read_bytes()).hexdigest()
        entries[key]={'metrics':metrics,'xy':xy,'R':ins['tt']['boundary']['mean'],'view':str(view.relative_to(ROOT))}
    for c in range(3):
        for half in ['a','b']:load(f'{half}{c}',f's81hc_cncl{half}{c}_ref',f'ot_s81_hc_cncl{half}',f'cncl{half}_C{c}')
    load('tree','s81hc_cntreeh2_ref','ot_s81_hc_cntree','cntree (CLOSED h2 view, R0)')
    load('scalar','s81hc_cnrsq_ref','ot_s81_hc_cnrsq','cnrsq')
    joins=[]
    def link(a,pa,b,pb):joins.append((a,pa,b,pb))
    NS=32;NL=128;NP=11
    def lev(n):return 7-n.bit_length()+1
    def owner(n):
        k=lev(n);sz=1<<k;s0=((n<<k)-NL)%NS
        for c,start,count in [(0,0,11),(1,11,10),(2,21,11)]:
            if sz<=NS and s0>=start and s0+sz<=start+count:return c
        return 3
    def exported(n,c):return owner(n)==c and (n==1 or owner(n//2)!=c)
    for c,face in [(0,'w'),(1,'c'),(2,'e')]:
        all_nodes=[n for n in range(1,2*NL) if exported(n,c)];counts={0:0,1:0}
        assert len(all_nodes)==[12,16,12][c],(c,all_nodes)
        for ix,n in enumerate(all_nodes):
            half=(((n<<lev(n))-NL)//NS)//2;hix=counts[half];counts[half]+=1
            for bit in range(32):link(('a' if half==0 else 'b')+str(c),f'ex[{hix*32+bit}]','tree',f'{face}_ex[{ix*32+bit}]')
        for p in ['rvt','pi']:
            for bit in range(1 if p=='rvt' else 8):link(f'a{c}',p if p=='rvt' else f'{p}[{bit}]','tree',f'{face}_{p}' if p=='rvt' else f'{face}_{p}[{bit}]')
        link(f'b{c}','flt',f'a{c}','flt_b');link(f'a{c}','flt','scalar',f'cflt[{c}]')
    for p,width in [('ss',32),('ss_v',1),('tflt',1)]:
        for bit in range(width):link('tree',f'{p}[{bit}]' if width>1 else p,'scalar',f'{p}[{bit}]' if width>1 else p)
    link('scalar','ngo','tree','ngo_i')
    results=[]
    rtl=(ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv').read_text()
    cncla=re.search(r'^module ot_s81_hc_cncla\b.*?^endmodule',rtl,re.M|re.S).group()
    constant_pi="pi <= {5'd0, i_q};" in cncla
    for a,pa,b,pb in joins:
        ea,eb=entries[a],entries[b];r={'a':a,'aport':pa,'b':b,'bport':pb}
        if constant_pi and a in ['a0','a1','a2'] and re.fullmatch(r'pi\[[3-7]\]',pa):
            r.update(status='CONSTANT_RTL',value=0,basis="cncla pi <= {5'd0, i_q}; three-bit vector index; no dynamic timing arc expected");results.append(r);continue
        try:
            ax,ay=ea['xy'][pa];bx,by=eb['xy'][pb];L=abs(ax-bx)+abs(ay-by);ma=ea['metrics'];mb=eb['metrics'];o=ma['tt'][pa]['out'];s=mb['tt'][pb]['inp'];l=ma['ff'][pa]['lmin'];h=mb['ff'][pb]['hold']
            if any(v is None for v in [o,s,l,h]):raise ValueError('missing registered TT/FF timing arc')
            avail=833.333-60-(150 if max(ea['R'],eb['R'])>300 else 90)
            setup=avail-o-s-0.76*L;hold=l+0.112*L-h-100
            r.update(length_um=round(L,4),launch_ps=round(o,4),capture_ps=round(s,4),setup_margin_ps=round(setup,4),hold_margin_ps=round(hold,4),status='PASS' if setup>=0 and hold>=0 and L<=500 else 'FAIL')
        except (KeyError,ValueError) as e:r.update(status='MISSING',why=str(e))
        results.append(r)
    counts={s:sum(r['status']==s for r in results) for s in ['PASS','FAIL','MISSING','CONSTANT_RTL']}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'schema':'opentallas.s81.norm_bottom_pairs.v1','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'clock_model':'Per-leaf TREE phi-R, common epoch; physical clock/reset assignment still separate gate','wire_model':'TT .76 ps/um, conservative FF .112ps/um credit, Manhattan actual LEF pin centres','scope':'Internal cnbot joins only; far-tile/collector and scale-return external hops omitted/unverified; source ownership of ngo must publish a new scalar view before its join can pass.','counts':counts,'layout':str(layout_path),'mapping_source':'Current cnbot heap-order export mapping NG256/GS8/NCOL3, registered cncla pi padding classified separately','hashes':hashes,'joins':results},indent=2)+'\n');print(counts)
    return 0 if counts['FAIL']==counts['MISSING']==0 else 1
if __name__=='__main__':sys.exit(main())
