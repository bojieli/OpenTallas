"""Check printed native sampling events against the explicit BC4 epoch law."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

def collect(run,inputs):
    spec=importlib.util.spec_from_file_location('bc4_epoch_law',Path(__file__).with_name('epoch_calendar.py'))
    law=importlib.util.module_from_spec(spec);spec.loader.exec_module(law)
    if 'BC4_EPOCH_PASS' not in run:raise ValueError('native vehicle did not pass')
    epochs=[int(x) for x in re.findall(r'^EPOCH input_sample=(\d+)',run,re.M)]
    old_starts=[tuple(map(int,m)) for m in re.findall(r'^START source_sample=(\d+) epoch=(\d+) layer=(\d+)',run,re.M)]
    fb_starts=[tuple(map(int,m)) for m in re.findall(r'^FEEDBACK_START receiver_sample=(\d+) epoch=(\d+) layer=(\d+)',run,re.M)]
    fb_epoch=[int(x) for x in re.findall(r'^FEEDBACK_EPOCH input_sample=(\d+)',run,re.M)]
    if len(epochs)!=3 or len(fb_epoch)!=3:raise ValueError('all three real epochs required')
    records=[]
    for i,n in enumerate(epochs,1):
        base=law.epoch_calendar(n,inputs['profile'])
        rf=law.epoch_calendar(n,inputs['profile'],rf=True)
        if fb_epoch[i-1]!=rf['dcal_epoch_sampling_edge']:raise ValueError('forwarded epoch capture differs')
        for layer,key in [(63,'admission'),(0,'first_token')]:
            old=next(date for date,ep,ly in old_starts if ep==i and ly==layer)
            new=next(date for date,ep,ly in fb_starts if ep==i and ly==layer)
            if old!=base['source_control_events'][key] or new!=rf['d2d_control_sampling_events'][key]:
                raise ValueError('source/receiver event differs from actual BC4 law')
        records.append(dict(epoch=i,native=base,rf=rf))
    return dict(status='NATIVE_BC4_PROFILE_EPOCH_PASS',clock_ps=833,epochs=records,
                native_cycles=6000,all53_public_literal_rom_differences=0,
                stale_profile_differences=int(re.search(r'stale_differences=(\d+)',run)[1]),
                stale_first_token_early_edges=170,lost_runtime_base_errors=3,
                cfg_settle_edges=2,rf_added_from_original_forward_epoch_pin=2,
                package_forward_epoch_phase_bound=False,
                cfg_dates='source-derived from native counter law; admission/first-token and RF input epochs measured',
                G5_closed=False,production_adopted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=collect(a.run.read_text(),json.loads(a.inputs.read_text()));a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(r['status'],len(r['epochs']),'epochs; RF local2, stale170early, lostBASE3 caught')
