#!/usr/bin/env python3
"""Actual cfg7 ROM/sequence chirality and changed Q control cuts on pinned replay."""
import argparse,hashlib,json,struct,collections
from pathlib import Path
from s81.qbank_frame_audit import lef,read_json,world

def main():
    ap=argparse.ArgumentParser()
    for n in ['plan','transforms','q-lef','seq-lef','rom-lef','s-lef','out']:ap.add_argument('--'+n,required=True,type=Path)
    a=ap.parse_args();plan=read_json(a.plan);old={i['name']:i for i in plan['insts']};new=dict(old)
    for t in read_json(a.transforms):new[t['instance']]=t['candidate']
    q,seq,rom,bank=map(lef,[a.q_lef,a.seq_lef,a.rom_lef,a.s_lef]);pinmap=plan['pins'];digest=hashlib.sha256();counts=dict(rom_sequence=0,sequence_bank=0,sequence_q_direct=0);rows=[];missing=[]
    def pt(inst,port,bit,leaf,placement):
        i=placement[inst];names=pinmap.get(i['master']+'|'+port)
        name=names[bit].replace('\\','') if names else f'{port}[{bit}]'
        assert name in leaf['pins'],(inst,port,bit,name)
        return world(i,leaf['pins'][name][0][1],*leaf['size']),name
    def edge(src,sp,dst,dp,bits,sl,dl,kind,unchanged):
        longest=0
        for bit in range(bits):
            o0,sname=pt(src,sp,bit,sl,old);o1,dname=pt(dst,dp,bit,dl,old)
            n0,_=pt(src,sp,bit,sl,new);n1,_=pt(dst,dp,bit,dl,new)
            assert abs((n0[0]-n1[0])-(o0[0]-o1[0]))<1e-7,('chirality/X changed',src,dst)
            if unchanged:assert abs((n0[1]-n1[1])-(o0[1]-o1[1]))<1e-7,(src,dst,'cfg local geometry changed')
            longest=max(longest,abs(n0[0]-n1[0])+abs(n0[1]-n1[1]));counts[kind]+=1
            digest.update(f'{src}|{sname}|{dst}|{dname}|'.encode());digest.update(struct.pack('!dddd',*n0,*n1))
        return longest
    byinst=collections.defaultdict(list)
    for b in plan['buses']:
        if b[1] in ['col_clock','col_reset']:continue
        for inst,port in b[3]:byinst[inst].append(b)
    pairids=sorted(int(n[1:]) for n,i in old.items() if n.startswith('e') and n[1:].isdigit() and i['kind'] in ['q','bf','bf_nv'])
    assert len(pairids)==1973
    for p in pairids:
        sn=f's{p}';en=f'e{p}';i=old[sn]
        if i['master']!='ot_s81_cfg7_seq':
            missing.append(dict(pair=p,sequence_master=i['master'],reason='no matching actual closed LEF in pinned17b table; local source transform/identities preserved, native cuts pending'));continue
        maxima=dict(rom_sequence=0,sequence_bank=0,sequence_q_direct=0)
        # Enumerate actual connected bus widths/endpoint names. Native ROM rd is
        # 72 bits; the historical emitted graph uses48 connected bits per ROM.
        relevant=byinst[sn]
        for name,cls,bits,ends in relevant:
            if cls in ['rom_a','rom_ce','rom_q']:
                for dst,dp in ends[1:]:
                    src,sp=ends[0]
                    if {old[src]['kind'],old[dst]['kind']} != {'seq','cfg'}:continue
                    sl,dl=(seq,rom) if src==sn else (rom,seq)
                    maxima['rom_sequence']=max(maxima['rom_sequence'],edge(src,sp,dst,dp,bits,sl,dl,'rom_sequence',True))
            elif len(ends)==2 and any(z=='bs'+str(p) for z,port in ends):
                (src,sp),(dst,dp)=ends
                maxima['sequence_bank']=max(maxima['sequence_bank'],edge(src,sp,dst,dp,bits,seq,bank,'sequence_bank',True))
            elif len(ends)==2 and any(z==en for z,port in ends):
                (src,sp),(dst,dp)=ends;sl,dl=(seq,q) if src==sn else (q,seq)
                maxima['sequence_q_direct']=max(maxima['sequence_q_direct'],edge(src,sp,dst,dp,bits,sl,dl,'sequence_q_direct',False))
        rows.append(dict(pair=p,sequence_orientation=i['orient'],rom_orientations=[old[f'c{p}_{j}']['orient'] for j in range(7)],max_manhattan_um={k:round(v,6) for k,v in maxima.items()}))
    report=dict(scope=plan['scope'],source=plan['source_commit'],total_pairs=len(pairids),native_Q_cfg_pairs=len(rows),BF_pairs_without_actual_sequence_view=len(missing),checked_bit_edges=counts,endpoint_sha256=digest.hexdigest(),max_manhattan_um={k:max(r['max_manhattan_um'][k] for r in rows) for k in counts},local_rom_sequence_vectors_unchanged=True,local_sequence_bank_vectors_unchanged=True,Q_direct_gt_ef_normal_cycles_added=0,normal_cycle_scope='Geometric source transform only; full static hop replan may change priced stages.',orientation_legality='OPEN: geometric chirality/per-bit matching does not establish LEF orientation legality. Selected closed cfg7 LEF lacks SYMMETRY; MY use requires owner generic reconciliation, no waiver or header patch.',sequence_MY_geometric_only_count=sum(r['sequence_orientation']=='MY' for r in rows),native_rom_output_width=72,historical_connected_rom_payload_width=48,unused_rom_output_bits_per_macro=24,adoption=False,missing=missing,pairs=rows,leaf_sha256={k:v['sha256'] for k,v in [('Q',q),('sequence',seq),('ROM',rom),('qS',bank)]})
    a.out.write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['pairs','missing']},indent=1))
if __name__=='__main__':main()
