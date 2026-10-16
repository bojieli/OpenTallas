#!/usr/bin/env python3
"""Source-pinned physical lower bound and regional placement screens, no timing claim."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/qwen_vm_residual_1015/physical_inventory'
VIEWS={
'qvm_bank_banked_native':('qvm_bank_entries_my_native','qvm_bank_banked_native'),
'qvm_su_bank_native':('qvm_su_bank_native','qvm_su_bank_native'),
'ot_qfd_vm_bctl_nx':('qfd_vm_bctl_nx','ot_qfd_vm_bctl_nx'),
'ot_qfd_vm_delay1_t':('qfd_tree_delay1_t','ot_qwen_tree_delay1_t'),
'ot_qfd_vm_delay2_t':('qfd_tree_delay2_t','ot_qwen_tree_delay2_t'),
'ot_qfd_vm_rr2_nx':('qfd_vm_rr2_nx','ot_qfd_vm_rr2_nx'),
'ot_qfd_vm_rr4_t':('qfd_vm_rr4_t','ot_qfd_vm_rr4_t'),
'ot_qfd_vm_sctl_t':('qfd_vm_sctl_t','ot_qfd_vm_sctl_t'),
'ot_qfd_vm_su1024_t':('qfd_vm_su1024_codex','ot_qfd_vm_su1024_t'),
'qfd_vm_qcommit':('qfd_vm_qcommit','qfd_vm_qcommit')}
PER={'qvm_bank_banked_native':8,'qvm_su_bank_native':6,'ot_qfd_vm_bctl_nx':8,'ot_qfd_vm_delay1_t':8,'ot_qfd_vm_delay2_t':14,'ot_qfd_vm_rr2_nx':1,'ot_qfd_vm_rr4_t':2,'ot_qfd_vm_sctl_t':6,'ot_qfd_vm_su1024_t':3}
def show(p):return subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
def shelf(items,width,gap=20):
    # Every rectangle has 20um horizontal/vertical channel; no rotation, all R0.
    x=y=row_h=0; placed=[]
    for it in sorted(items,key=lambda z:(-z['h'],-z['w'],z['class'],z['n'])):
        if x and x+it['w']>width+1e-9:x=0;y+=row_h+gap;row_h=0
        assert it['w']<=width
        placed.append(dict(it,x=x,y=y,orient='R0'))
        x+=it['w']+gap;row_h=max(row_h,it['h'])
    return placed,y+row_h

def main():
    OUT.mkdir(parents=True,exist_ok=True); inv={}
    for cls,(kit,master) in VIEWS.items():
        path=f'physical/ref_tile/{kit}/views/{master}/{master}.lef';data=show(path);text=data.decode();m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text);w,h=map(float,m.groups());count=39 if cls=='qfd_vm_qcommit' else PER[cls]*8
        inv[cls]={'count':count,'w':w,'h':h,'area_mm2':count*w*h/1e6,'lef':path,'sha256':hashlib.sha256(data).hexdigest(),'view_master':master,'source_alias_needs_binding':master!=cls,'clock_pins_per_instance':9 if cls.startswith('qvm_') else 1}
    assert sum(v['count'] for v in inv.values())==487
    raw=sum(v['area_mm2'] for v in inv.values());banks=sum(inv[k]['area_mm2'] for k in ['qvm_bank_banked_native','qvm_su_bank_native']);oldarea=4708.8*2203.2/1e6
    record={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'scope':'Exact class census from resid2 and actual published LEF rectangles; source aliases and all native qualifications still require review. No source instance connectivity or routed fit is inferred.','inventory':inv,'counts':{'native_banks':112,'other_regional_leaves':336,'observers':39,'total_existing':487},'area_mm2':{'native_banks':banks,'all_existing_leaves':raw,'legacy_parent':oldarea,'minimum_overage_existing':max(0,raw-oldarea)},'clocks':{'old_parent_clock_nets':487,'existing_hard_clock_pins':sum(v['count']*v['clock_pins_per_instance'] for v in inv.values()),'native_bank_source_note':'ot_qfd_vm_region_nx ties each bank\'s9 clock pins to one old bank lc net; independent phi-R compensation is NOT established','new_return_read_control_clock_pins':99},'not_in_raw_area':['All unpartitioned BV residual87507FF','parent wrapper/Q export/relay FFs','repeaters','clock/reset delivery','channels'],'alternatives':{}}
    for label,width in [('regional_wide',1188.0),('regional_tall',810.0)]:
        regions=[]
        for r in range(8):
            items=[]
            for cls,v in inv.items():
                count=(0 if r<3 else (7 if r==7 else 8)) if cls=='qfd_vm_qcommit' else PER[cls]
                for n in range(count):items.append({'class':cls,'n':n,'region':r,'w':v['w'],'h':v['h']})
            boxes,h=shelf(items,width);regions.append((boxes,h))
        H=max(h for _,h in regions);placed=[]
        for r,(boxes,h) in enumerate(regions):
            ox=(r%4)*(width+40);oy=(r//4)*(H+40)
            for b in boxes:placed.append(dict(b,x=b['x']+ox,y=b['y']+oy))
        W=4*width+120;HH=2*H+40
        assert len(placed)==487
        for i,a in enumerate(placed):
            assert a['x']>=0 and a['y']>=0 and a['x']+a['w']<=W+1e-8 and a['y']+a['h']<=HH+1e-8
            for b in placed[i+1:]:assert min(a['x']+a['w'],b['x']+b['w'])<=max(a['x'],b['x']) or min(a['y']+a['h'],b['y']+b['h'])<=max(a['y'],b['y'])
        record['alternatives'][label]={'outline_um':[W,HH],'area_mm2':W*HH/1e6,'region_outline_um':[width,H],'channels_um':20,'inter_region_channel_um':40,'rectangles':placed,'overlap':0,'outside':0,'qualification':'Existing-leaf packing screen only; residual roots, all incident wire cuts/reach and clock/PG still OPEN; NOT proposed production adoption'}
    (OUT/'inventory.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k not in ['inventory','alternatives']},indent=2));print({k:v['outline_um'] for k,v in record['alternatives'].items()})
if __name__=='__main__':main()
