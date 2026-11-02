from pathlib import Path
import argparse,csv,collections,json,re,math

def rows(p):return list(csv.DictReader(open(p),delimiter='\t'))
def canon(r):
    name=r['instance'].replace('\\','').split('$_')[0]
    return name, (r['master'],r['clock_pin'],r['clock_net'])

def summarize(root):
    root=Path(root);k=root/'kit'
    assert (root/'RESULT').read_text().strip()=='SYNTH_PREVIEW_PASS'
    old=rows(k/'nf2_baseline_ff.tsv');new=rows(k/'candidate_ff.tsv')
    oldclock=dict(collections.Counter(r['clock_net'] for r in old));newclock=dict(collections.Counter(r['clock_net'] for r in new))
    a=dict(canon(r) for r in old if 'gqv' not in r['instance']);b=dict(canon(r) for r in new if 'gqv' not in r['instance'])
    assert a==b, 'non-fault-bank clock role/master census changed'
    assert len(new)-len(old)==16
    assert sum('gqv' in r['instance'] for r in old)==5 and sum('gqv_groups' in r['instance'] for r in new)==21
    assert newclock['ck[0]']-oldclock['ck[0]']==16
    assert all(newclock[x]==n for x,n in oldclock.items() if x!='ck[0]')
    def gate(f):
        o=json.load(open(k/f));return o.get('verdict',o.get('summary',o))
    area=json.load(open(next((k/'run/logs').rglob('1_synth.json'))))
    raw=json.load(open(k/'face_guard.json'));odb=json.load(open(k/'face_guard_odb.json'))
    assert raw['verdict']==odb['verdict']=='PASS' and raw['checked']==raw['ok']==odb['checked']==odb['ok']==623
    out=dict(status='DISABLED_SYNTH_PREVIEW_PASS',source_qualification=json.load(open(root/'qualification/COMPOSITE.json'))['verdict'],
      native_synthesis='ONE fresh SYNTH; no floorplan/PLACE/CTS/GRT/DRT/STA',pin_abi='623/623 RAW and ODB boundary PASS',
      baseline=dict(origin='intel2:die-kv-60/ahub/G',reference_1_2_yosys_sha256='c137ce5c31b84b1ce7d8c09f6d3a9ee5dad4cbf4d50383cb259310e4d91da766',native_ff=len(old),fault_bank_ff=5,clock_sinks=oldclock),
      candidate=dict(native_ff=len(new),fault_bank_ff=21,clock_sinks=newclock),
      price=dict(added_physical_ff=16,added_clock_sinks=16,clock_net='ck[0]',other_clock_roles_and_masters_unchanged=True,
                 total_native_ff_pct=100*16/len(old),ck0_clock_sink_pct=100*16/oldclock['ck[0]'],added_cycles=0,added_macros=0),
      mapped_geometry=dict(outline_um=[604.8,440.64],stdcell_count=area['synth__design__instance__count__stdcell'],
        stdcell_area_um2=area['synth__design__instance__area__stdcell'],macro_count=area['synth__design__instance__count__macros'],
        macro_area_um2=area['synth__design__instance__area__macros'],actual_new_ff_sites='not placed; no invented sites'),
      review='nf2_disabled_geometry_clock_preview.png personally viewed; unchanged five real macro sites and seven original clock pins; no P&R authorization',
      limitations=['Timing and clock insertion/load/buffer qualification NOT RUN','Child clock expansion remains a separate release gate','Mapped new-netlist proof is not claimed by this synthesis preview','Canonical activation OFF; no production plan/recipe/source changes'],
      preserved_wrong_vehicle_comparison=dict(origin='codex-kv-ahub-1131/kits/G',native_ff=3605,
        observed_delta_to_candidate=36,diagnosis='Older CodexG lacks20 nblk_zmask keeper FFs already in the qualified NF2 reference; comparison is not the NF2 event price.',
        receipt='kit/baseline_ff.tsv; original native read retained'))
    (root/'SYNTH_PREVIEW.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('root');v=a.parse_args();print(json.dumps(summarize(v.root),indent=2))
