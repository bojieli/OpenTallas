#!/usr/bin/env python3
"""Export a recorded fleet window as one self-contained HTML file (data embedded, plays offline).

  export_replay.py --from 2026-10-08T03:00 --to 2026-10-08T05:00 --safe -o fleet.html
  export_replay.py --from -30m -o last30.html          # times: epoch, ISO (local), 'now', '-30m', '-2h'

Long windows are downsampled to --max-frames frames (default 1500; change streams coalesce per bucket).
"""
import argparse, json, os, pathlib, sys, time
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import recorder

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('--from', dest='t0', required=True); ap.add_argument('--to', dest='t1', default='now')
ap.add_argument('--safe', action='store_true', help='share-safe: labels only, no job table/verdicts/names')
ap.add_argument('--max-frames', type=int, default=1500)
ap.add_argument('--recordings', default=os.environ.get('FLEET_VIZ_RECORDINGS', os.path.expanduser('~/.local/state/fleet-viz/recordings')))
ap.add_argument('-o', '--output', required=True)
a = ap.parse_args()
now = time.time(); t1 = recorder.parse_time(a.t1, now)
t0 = recorder.parse_time(a.t0, t1 if a.t0.startswith('-') else now)
pkg = recorder.load_window(a.recordings, t0, t1, safe=a.safe, max_frames=a.max_frames)
if not pkg or not pkg['frames']: sys.exit('no recorded frames between %s and %s' % (time.ctime(t0), time.ctime(t1)))
page = (HERE / 'index.html').read_text()
data = json.dumps(pkg, separators=(',', ':')).replace('</', '<\\/')
inj = '<script>window.REPLAY_DATA=%s;</script>\n' % data
i = page.index('<script>')
page = page[:i] + inj + page[i:]
page = page.replace('<title>OpenTallas Fleet Live</title>', '<title>OpenTallas Fleet Replay</title>')
pathlib.Path(a.output).write_text(page)
print('%s: %d frames (1 in %d), %s .. %s, %.1f MB%s' % (a.output, len(pkg['frames']), pkg['step'], time.ctime(pkg['t0']),
      time.ctime(pkg['t1']), len(page) / 1e6, ', share-safe' if a.safe else ''))
