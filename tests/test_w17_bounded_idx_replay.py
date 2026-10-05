"""Ensure the evidence verifier rejects timing and handshake corruption."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('replay', ROOT/'tools/w17_bounded_idx_replay.py')
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)

class ComparisonTests(unittest.TestCase):
    def test_scalar_trace_edges(self):
        summary, trace = replay.scalar_trace(12300)
        self.assertEqual(len(trace), 2176)
        self.assertEqual(trace[0]['request_cycle'], 12303)
        self.assertEqual(trace[-1]['response_cycle']+2, summary['end_cycle'])
        for i in range(1, len(trace)):
            self.assertEqual(trace[i]['request_cycle'], trace[i-1]['response_cycle']+2+(3 if i%17==0 else 0))

    def test_trace_mutations_are_rejected(self):
        summary, trace = replay.scalar_trace(12300)
        log = '\n'.join('R '+' '.join(map(str,[i,e['request_cycle'],e['pc'],e['address'],e['tag'],e['tcol_ps'],e['refreshes'],e['activations']]))+'\nS '+' '.join(map(str,[i,e['response_cycle'],e['pc'],e['tag'],0])) for i,e in enumerate(trace))
        log += '\n'+'\n'.join(f'PC {p} 68 68 68 0 0' for p in range(32))
        log += '\nSUMMARY '+' '.join(map(str,[12300,summary['end_cycle']-2,summary['end_cycle'],2176,2176,summary['refresh_events_all_channels'],summary['activations'],1,1]))
        self.assertEqual(replay.compare(log,trace,summary)['mismatch_count'],0)
        # Independently corrupt request edge, address, tag, tcol, refresh, response edge/tag.
        for marker, field in [('R',1),('R',3),('R',4),('R',5),('R',6),('S',1),('S',3)]:
            lines=log.splitlines()
            n=next(i for i,l in enumerate(lines) if l.startswith(marker+' '))
            words=lines[n].split(); words[field+1]=str(int(words[field+1])+1)
            lines[n]=' '.join(words)
            self.assertGreater(replay.compare('\n'.join(lines),trace,summary)['mismatch_count'],0)

if __name__=='__main__':
    unittest.main()
