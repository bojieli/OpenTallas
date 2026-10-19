"""Bounded source-geometry audit; does not run a PDK or claim routed closure."""
import hashlib, json, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pins(text):
    result={}
    for name,body in re.findall(r"  PIN (\S+)\n(.*?)  END \1",text,re.S):
        layer=None; rects=[]
        for line in body.splitlines():
            m=re.search(r"LAYER (\S+) ;",line)
            if m: layer=m[1]
            m=re.search(r"RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;",line)
            if m: rects.append([layer,*map(float,m.groups())])
        result[name]=rects
    return result
masters=[]
for name,inst in [('ot_s81_pma_rxm','u_prx'),('ot_s81_pma_txm','u_ptx')]:
    path=ROOT/'physical/asap7_memory_macros'/name/(name+'.lef')
    txt=path.read_text(); pp=pins(txt)
    obs=[0.,.6,129.6,2245.8]
    pg={}
    for net in ('VDD','VSS'):
        rects=pp[net]
        covered=sum(layer=='M4' and obs[0]<=x0 and obs[1]<=y0 and x1<=obs[2] and y1<=obs[3] for layer,x0,y0,x1,y1 in rects)
        pg[net]={'rectangles':len(rects),'entirely_under_M5_OBS':covered,'layer':'M4'}
        assert covered==len(rects)
    masters.append({'instance':inst,'master':name,'lef_sha256':sha(path),'PG':pg,'M5_OBS':obs,
                    'signal_pins':sum(len(v) for k,v in pp.items() if k not in ('VDD','VSS'))})
recordpath=ROOT/'rtl/dsrom_sys/s81_link/col/lp/ot_pdie_serdes_col_lp_record.json'
r=json.loads(recordpath.read_text())
model={'schema':'opentallas.s81-serdes-terminal-pickup.v1','source_commit':'247c97136',
       'status':'FAIL_PDN_NO_NATIVE_FINAL_QUALIFICATION','masters':masters,
       'all_PMA_PG_rectangles':sum(x['PG'][n]['rectangles'] for x in masters for n in ('VDD','VSS')),
       'intended_domain':{'name':'CORE','power':'VDD','ground':'VSS','existing_macro_connect':['M4','M5']},
       'source_lp_flops':r['flops'],'source_compiler_offsets':r['compiler'],
       'outline_um':[518.4,3844.8], 'outline_area_um2':518.4*3844.8,
       'synthesis_report_FF':19514,
       'conditional_structural_model':{
           'selected':False,'distinct_new_master_required':True,
           'preserve_all_old_M4_PG_rectangles':True,'preserve_signal_pins_and_clock_ABI':True,
           'new_PG_stem_centres_x_um':{'VDD':.72,'VSS':128.88},
           'new_M5_PG_stem_width_um':.288,'reserved_M5_corridor_width_um':.432,
           'internal_via_box_budget_um':[.288,.288],
           'one_via45_and_one_via56_per_old_PG_rectangle':3738,
           'export':'M6 same-net stripes, retaining existing M4 terminals; parent macro PG connect M6-M7',
           'OBS':'Split M5 obstruction only around actual protected same-net PG stems; retain all other OBS',
           'area_increment_if_internal_geometry_qualifies_um2':0,
           'data_edge_increment':0,'extra_FF':0,
           'native_via_enclosure_spacing_and_internal_analog_reservation':'UNPROVED: root selection and complete constructive proof required',
           'resistance_capacitance_power_and_analog_current_capacity':None,
       },
       'prerequisites':[
         'Root selects structural PG model before source/view generation or gate.',
         'Enumerate all 3738 original M4 supply rectangles, via enclosures, M5 protection and M6 terminals; no removed terminals or open supply windows.',
         'Validate actual PDK min-area/width/PRL/cut spacing and same-net connectivity; proposed .288 box is a budget, not native-rule proof.',
         'All 14 hard-child PG ITerms must reach intended supply component in post-repair/final ODB; count every rectangle, not net-name presence.',
         'Remeasure all nonclock native roots <=32 including comb/reset/input/ties; FF/root list currently unknown.',
         'Native registered boundary, all single-edge reaches <=405 and clock-spread<=80 TT/FF including macro pins and neighbor matching remain unproved.',
         '4096-bit indexed two-clock rate-match FIFO requires real dual-clock SRAM/OLD/lifetime model; README waiver does not establish owner authorization.',
         'Keep real distinct core/recovered clock families and gray FIFO; do not convert async relation into a PLL assumption.',
         'PMA boundary libs are assumed analog models; no measured CQ, slew, power or hold claim.',
         'MUT3 status-path six-stage pad remains unobservable; need encoder-fault/status-specific causal witness preserving edges/reset.',
         'Root PNG/checklist review required after legal physical model; old gate never reached CTS.',
         'RC=[] textbook scope must be reconciled against actual pinned helper logs; do not patch generic rules based on missing verdict.',
         'Install and verify exact +3 TX/+7 RX-status/+5 reset compiler offsets with actual parent placement/calendar and SU/MU token stream.'
       ], 'evidence_scope':'LEF source geometry plus pre-PDN stage ODB terminals; no final connectivity, native timing, physical escape, or die adoption'}
(HERE/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
print('SOURCE_GEOMETRY_REPRODUCED',model['all_PMA_PG_rectangles'],'PMA PG rectangles wholly under M5 OBS; no PASS closure claim')
