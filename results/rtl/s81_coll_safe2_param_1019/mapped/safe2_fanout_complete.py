from pathlib import Path
import sys,re,json
p=Path('src/tools/textbook_lint.py');s=p.read_text().replace('hf[:8]','hf[:1000]').replace('bad[:12] + ([f"... {len(bad) - 12} more"] if len(bad) > 12 else [])','bad')
net=next(Path('map_safe2/work/orfs/results').glob('asap7/*/base/1_2_yosys.v'))
t=net.read_text()
names=re.findall(r'\bot_sram_showahead_hit5\s+\\?([^\s(]+)\s*\(',t)
Path('map_safe2/compare_instances.json').write_text(json.dumps({'count':len(names),'instances':names},indent=2)+'\n')
print('LOCAL_HIT_COMPARE_INSTANCES',len(names),names)
sys.argv=[str(p),'check','--netlist',str(net),'--top','dsfd_coll_lane_w_safe2','--set','hf_report=1','hf_max=32','--out','map_safe2/fanout_complete.json']
exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p.resolve())})
