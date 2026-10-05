"""Source-bound rectangle feasibility screen; no legal-placement assertion."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
raw=(ROOT/'final/candidate.json').read_bytes()
d=json.loads(raw)
commit=subprocess.check_output(['git','rev-parse','541a1d2f'],text=True).strip()
path='results/floorplan/v41_pack_refit_w10_interim.json'
src=subprocess.check_output(['git','show',commit+':'+path])
g=json.loads(src)['geometry']
cx0,cy0,cx1,cy1=g['core']
hx,hy,hw,hh=g['hub']
bands={'left':hx-cx0,'right':cx1-hx-hw,'below':hy-cy0,'above':cy1-hy-hh}
t=d['variants']['planning_75Mbit']['geometry']
w,h=t['grid_width_um'],t['grid_height_um']
assert min(w,h)>max(bands.values())
out=dict(schema='opentallas.engram.retained-hub-rectangle-screen.v1',
    source_pin=dict(commit=commit,path=path,sha256=hashlib.sha256(src).hexdigest()),
    candidate_sha256=hashlib.sha256(raw).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    core_bounds_um=g['core'],hub_origin_size_um=g['hub'],
    planning_grid_size_um=[w,h],maximum_point_relative_to_grid_origin_um=[w,h],
    free_axis_band_depth_um=bands,
    verdict='FAIL_CONTIGUOUS_96_HOME_GRID_IN_RETAINED_HUB_CORE_EVEN_WITH_90DEG_ROTATION',
    proof='An axis-aligned rectangle not intersecting the hub must fit wholly left, right, above or below it. Both grid dimensions exceed all four free band depths. No translation or 90degree rotation can place this complete rectangular grid inside this core while retaining this hub.',
    qualification='Rejects this specific intact grid on current hub-retained geometry; not physical impossibility of Engram ROM. A new table-only floorplan, fragmented selector grid, or further sharding requires Ram approval through composed model and explicit new costs, not user reapproval.',
    alternative_192_home_screen=dict(shards_per_column=4,slots_per_home=8192,grid_shape=[128,64],
        width_um=w,height_um=h/2,below_hub_vertical_slack_um=bands['below']-h/2,
        status='RECTANGLE_ONLY_CONDITIONAL; power, halo, tracks, IO/control, selectors and slot capacity not joined; not an admitted alternative'),
    current_clock_power_join='Confucius owns source-typed ungated all-state budget; Ram owns whole-design join',
    new_table_only_hub_removal_or_control_replacement_qualified=False,
    link_packet_frame_CRC_shared_port_qualified=False,L1_generated_source=None,
    checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False)
target=ROOT/'retained_hub_screen.json'
assert not target.exists()
target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bands=bands,verdict=out['verdict'])))
