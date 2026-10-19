"""Bounded source-rectangle review. No generated views or routing claims."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'qwen_dualclk_geometry_1019'
spec = importlib.util.spec_from_file_location('reference', HERE/'source/reference_checker.py')
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def terminal_review(m):
    # The reference's path algorithm is applicable after substituting this
    # master's actual 206 paths, outline and OBS; no 437-path constants used.
    return ref.audit(m)

def native_rules(text):
    result = {}
    for name in ('M4', 'M5'):
        body = text.split('LAYER '+name+'\n')[1].split('END '+name)[0]
        def number(key):
            return float(re.search(r'\b'+key+r'\s+([0-9.]+)\s*;', body).group(1))
        result[name] = dict(pitch_nm=round(number('PITCH')*1000),
                            offset_nm=round(number('OFFSET')*1000),
                            width_nm=round(number('WIDTH')*1000),
                            area_nm2=round(number('AREA')*1e6),
                            rightway_on_grid_only='RIGHTWAYONGRIDONLY' in body,
                            prl_width_spacing_nm=[[round(float(a)*1000),round(float(b)*1000)]
                                for a,b in re.findall(r'WIDTH ([0-9.]+) ([0-9.]+)',body)],
                            eol_corner_density_full_evaluation=False)
    return result

def review(m, i, tech):
    rules = native_rules(tech)
    terminal = terminal_review(m)
    errors = []
    for layer in rules:
        assert rules[layer]['width_nm'] == i['rules']['width_nm'] == 24
        assert rules[layer]['area_nm2'] == i['rules']['minimum_area_nm2'] == 2000
        assert rules[layer]['prl_width_spacing_nm'] == [[0,24],[25,72]]
    # Independently replay scalar width/PRL/cut/enclosure/connectivity from
    # source input. Existing model may not supply its own PASS as evidence.
    spec = importlib.util.spec_from_file_location('planner', BASE/'reference_planner.py')
    planner = importlib.util.module_from_spec(spec); spec.loader.exec_module(planner)
    replay = planner.plan(i)
    assert replay['paths'] == m['paths']
    assert replay['pg_rectangles'] == m['pg_rectangles']
    assert replay['proposed_obstruction_rectangles'] == m['proposed_obstruction_rectangles']
    assert replay['proof'] == m['proof']
    grid = []
    for p in m['paths']:
        for s in p['shapes']:
            r = s['rect_nm']; layer = s['layer']; axis = 1 if layer == 'M4' else 0
            center = (r[axis]+r[axis+2])//2
            rule = rules[layer]
            if (center-rule['offset_nm']) % rule['pitch_nm']:
                grid.append(dict(pin=p['pin'],layer=layer,rect_nm=r,
                                 center_nm=center,phase_nm=center%rule['pitch_nm'],
                                 native_offset_nm=rule['offset_nm']))
    # Preserve all original PG rectangles, not merely one VDD/VSS contact.
    offset = m['core_offset_nm'][0] if isinstance(m['core_offset_nm'],list) else m['core_offset_nm']
    translated = [dict(p,rect_nm=[p['rect_nm'][0]+offset,p['rect_nm'][1],
                                 p['rect_nm'][2]+offset,p['rect_nm'][3]]) for p in i['pg']]
    assert translated == m['pg_rectangles'] and len(translated) == 44
    pg = []
    obs = m['proposed_obstruction_rectangles']
    for p in translated:
        r = p['rect_nm']; x = ((r[0]+r[2])//2)//48*48; y=(r[1]+r[3])//2
        # Candidate access rectangle only: not added to the geometry/prices.
        v4=[x-23,y-12,x+23,y+12]; v5=[x-12,y-42,x+12,y+42]
        metal_fit=ref.contains(r,v4)
        m5_clear=not any(o['layer']=='M5' and ref.intersects(v5,o['rect_nm']) for o in obs)
        pg.append(dict(net=p['net'],rect_nm=r,
                       m4_obs_overlap=any(o['layer']=='M4' and ref.intersects(r,o['rect_nm']) for o in obs),
                       hypothetical_via_m4_enclosure_nm=v4,hypothetical_m5_patch_nm=v5,
                       enclosure_within_pg=metal_fit,m5_patch_area_nm2=2016,
                       m5_patch_clear_of_declared_obs=m5_clear,
                       actual_native_access_or_connection=None))
        if not (metal_fit and m5_clear): errors.append(['PG_ACCESS_CANDIDATE_BLOCKED',p])
    return dict(status='HOLD',terminal_protection=terminal,
        scalar_replay=replay['proof'],native_rules=rules,
        native_grid=dict(status='HOLD',master_origin_assumed_nm=[0,0],
            mismatched_shapes=len(grid),shapes=grid,
            interpretation='Centers disagree with technology pitch/offset; actual master orientation, routing track phase and RIGHTWAYONGRIDONLY interpretation require native validation. Not a routed DRC verdict.'),
        pg=dict(status='HOLD',rectangles=pg,
            scope='44 rectangles preserved; candidate via landing fits and M5 core is unobstructed. M4 PIN/OBS overlap requires exact native own-pin access semantics. No PG routes, ownership, binding or connectivity proved.'),
        errors=errors,additional_geometry_cost=None,
        cost_policy='Original 52.440x21.144 outline, 26-bank 28828.575um2, 52-clock 581.910fF TT and 11.452pJ full-activity TT retained. No silent phase or geometry repair. Repair price awaits explicit mechanism.',
        outside_scope=['LEF58 EOL/corner/density full evaluation','actual parent tracks/access points and bank escapes',
                       'all-PG terminal connectivity and real PG vias','native write/read clock phase, reset, first-use, K/R versus R+1',
                       'macro internals and coupling/extracted RC','minimum CQ or timing signoff'])

def main():
    m=json.loads((BASE/'model.json').read_text()); i=json.loads((BASE/'input.json').read_text())
    tech=(HERE/'source/asap7_tech.lef').read_text()
    assert sha(HERE/'source/asap7_tech.lef') == i['source_provenance']['platform_and_calibration']['technology_sha256']
    assert sha(HERE/'source/platform_rules.txt') == i['source_provenance']['platform_and_calibration']['platform_rules_sha256']
    result=review(m,i,tech)
    mutants={}
    for name in ('wide_gap','missing_west_m5','blocked_terminal','exposed_via'):
        q=copy.deepcopy(m)
        if name=='wide_gap': next(o for o in q['proposed_obstruction_rectangles'] if o['layer']=='M4')['rect_nm'][0]=120
        elif name=='missing_west_m5': q['proposed_obstruction_rectangles']=[o for o in q['proposed_obstruction_rectangles'] if not(o['layer']=='M5' and o['rect_nm'][0]==72)]
        elif name=='blocked_terminal': next(o for o in q['proposed_obstruction_rectangles'] if o['layer']=='M4')['rect_nm'][0]=0
        else: next(o for o in q['proposed_obstruction_rectangles'] if o['layer']=='M5')['rect_nm'][0]=300
        mutants[name]=terminal_review(q)
        assert mutants[name]['status']=='FAIL',name
    assert result['terminal_protection']['status']=='PASS'
    assert result['native_grid']['mismatched_shapes'] > 0
    assert not result['errors']
    result['mutants']=mutants
    result['source_sha256']={str(p.relative_to(HERE.parent)):sha(p) for p in
        [BASE/'input.json',BASE/'model.json',BASE/'reference_planner.py',HERE/'audit.py',
         HERE/'source/reference_checker.py',HERE/'source/asap7_tech.lef',HERE/'source/platform_rules.txt']}
    (HERE/'audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status=result['status'],terminal=result['terminal_protection']['counts'],
        native_grid_mismatches=result['native_grid']['mismatched_shapes'],pg_rectangles=44,
        mutants={k:v['status'] for k,v in mutants.items()})))

if __name__=='__main__': main()
