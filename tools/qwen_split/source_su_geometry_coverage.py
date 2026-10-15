#!/usr/bin/env python3
"""Inventory actual SU clock entries without crediting a legacy parent box as fit."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('out',type=Path);p.add_argument('--source',default='c6c44c12c');a=p.parse_args()
    def git(rev,path):return subprocess.check_output(['git','-C',str(a.repo),'show',f'{rev}:{path}'])
    parent='rtl/qwen_split/qfd_sp_su64_sfu.sv';raw=git(a.source,parent);text=raw.decode();header=text.split(');',1)[0]
    clocks=re.findall(r'\bck(?:_(?:head|exp|rcp|rsq|align|lane|red)\d+)?\b',header);clocks=list(dict.fromkeys(clocks))
    expected=['ck']+[f'ck_{family}{i}'for family,n in [('head',64),('exp',64),('rcp',64),('rsq',64),('align',16),('lane',64),('red',9)]for i in range(n)]
    if set(clocks)!=set(expected):raise ValueError('Actual source clock ABI differs; do not silently infer child counts')
    recipes={'head':'qfd_su_lane_h_native_crom5','exp':'qfd_su_sfu_exp_native45','rcp':'qfd_su_sfu_rcp_native45','rsq':'qfd_su_sfu_rsq_native45','red_region':'qfd_su_vred_region8','red_tail':'qfd_su_vred_tail64'}
    views={}
    for family,name in recipes.items():
        path=f'physical/ref_tile/{name}/floorplan.json';blob=git('HEAD',path);f=json.loads(blob);die=f['die']
        views[family]=dict(recipe=name,source=path,sha256=hashlib.sha256(blob).hexdigest(),w=die[2]-die[0],h=die[3]-die[1],status='recipe outline only; actual source-equivalent LEF/timing/orientation admission required')
    rows=[]
    for clock in expected:
        match=re.fullmatch(r'ck_(head|exp|rcp|rsq|align|lane|red)(\d+)',clock)
        family,index=(match.group(1),int(match.group(2)))if match else('base',None)
        view=views.get('red_tail'if family=='red'and index==8 else'red_region'if family=='red'else family)
        rows.append(dict(clock_port=clock,family=family,lane_or_group=index,candidate_leaf_outline=view,home=None,qualification=False,missing='actual physical home, bound LEF, pin/OBS/halo/orientation, compensated phi-R and incident production routes'if view else'actual hardened glue/alignment boundary, dimensions and physical pins; source root alone is not a placed tile'))
    area=sum(r['candidate_leaf_outline']['w']*r['candidate_leaf_outline']['h']for r in rows if r['candidate_leaf_outline'])
    grouping=[dict(name=f'octet_{g}',lane_indices=list(range(g*8,g*8+8)),clock_ports=[f'ck_{f}{i}'for i in range(g*8,g*8+8)for f in ('head','exp','rcp','rsq','lane')]+[f'ck_align{g*2}',f'ck_align{g*2+1}',f'ck_red{g}'],basis='Existing eight-lane broadcast group, two four-lane alignment groups and matching eight-lane regional reducer; preserve arithmetic order',home=None,qualification=False)for g in range(8)]
    if any(len(g['clock_ports'])!=43 for g in grouping):raise ValueError('Grouping lost a source clock')
    if set(q for g in grouping for q in g['clock_ports'])|{'ck','ck_red8'}!=set(expected):raise ValueError('Incomplete or duplicated proposed source grouping')
    out=dict(schema='opentallas.qwen.actual-su-geometry-coverage.v1',source_commit=a.source,parent_source=parent,parent_sha256=hashlib.sha256(raw).hexdigest(),actual_clock_entries=len(rows),recipe_outline_entries=sum(r['candidate_leaf_outline']is not None for r in rows),entries_without_outline=sum(r['candidate_leaf_outline']is None for r in rows),known_recipe_outline_area_um2=round(area,3),placed_source_qualified_entries=0,legacy_container=dict(w=3240,h=3672,qualified=False,count_as_additional_silicon=False),external_embedding=dict(selected_parameter=1,embedded_row_sram_counted_inside_su=False,provider_physical_hardware_must_be_counted_separately=True),entries=rows,structural_grouping_candidate=dict(octets=grouping,central_roots=['ck','ck_red8'],added_pipeline_edges=0,adopted=False,physical_homes_qualified=False),qualification=False,notes=['Do not count both the legacy container and its physical children as silicon.','Recipe dimensions are candidate homes, not proof that physical leaf source/config matches the actual parent.','All 346 roots need measured insertion, actual pins and clock delivery, including 81 roots without candidate outlines.','Memory, independent lane relay/control glue, alignment, copy/controller glue, channels and reset distribution cannot be assigned zero area.','Source-only census does not establish a full hierarchy leaf count or production area.'])
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in ('actual_clock_entries','recipe_outline_entries','entries_without_outline','known_recipe_outline_area_um2')}))
if __name__=='__main__':main()
