"""Mock smart home: a small local HTTP tool server with realistic device latencies.
Latencies are modelled per device class (radio + confirmation round trip); the caller measures real wall time."""
import json, random, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
rng = random.Random(7); L = threading.Lock()
STATE = {
  'clock': '2026-10-09 22:41',
  'locks': {'front_door': 'unlocked', 'back_door': 'unlocked', 'garage_entry': 'locked'},
  'doors': {'front_door': 'closed', 'back_door': 'closed', 'garage_door': 'closed'},
  'windows': {'kitchen': 'open', 'living_room': 'closed', 'bedroom': 'closed', 'office': 'open'},
  'lights': {'kitchen': 'on', 'living_room': 'on', 'hallway': 'on', 'bedroom': 'on', 'office': 'off', 'porch': 'on'},
  'thermostat': {'mode': 'heat', 'target_c': 21.5, 'current_c': 21.0},
  'appliances': {'oven': 'off', 'tv': 'on', 'dishwasher': 'running'},
  'alarms': [],
}
CAL = {'2026-10-10': [{'start': '09:30', 'end': '10:00', 'title': 'Dentist (Dr. Okafor)'},
                      {'start': '08:15', 'end': '08:45', 'title': 'Standup with Lisbon team'},
                      {'start': '13:00', 'end': '14:00', 'title': 'Lunch with Maya'}]}
LAT = {'get_home_state': (0.10, 0.16), 'set_lights': (0.18, 0.32), 'lock_door': (1.05, 1.45), 'set_thermostat': (0.55, 0.85),
       'get_calendar': (0.28, 0.42), 'set_alarm': (0.06, 0.11), 'turn_off_appliance': (0.35, 0.6)}
def call(name, a):
    time.sleep(rng.uniform(*LAT[name]))
    with L:
        s = STATE
        if name == 'get_home_state': return s
        if name == 'set_lights':
            rooms = list(s['lights']) if a.get('room') in (None, 'all') else [a['room']]
            for r in rooms:
                if r not in s['lights']: return {'error': f'no light in {r}'}
                s['lights'][r] = 'on' if a.get('on') else 'off'
            return {'ok': True, 'lights': {r: s['lights'][r] for r in rooms}}
        if name == 'lock_door':
            d = a.get('door')
            if d not in s['locks']: return {'error': f'no lock on {d}'}
            if s['doors'].get(d) == 'open': return {'error': f'{d} is open; cannot lock'}
            s['locks'][d] = 'locked'; return {'ok': True, 'door': d, 'state': 'locked'}
        if name == 'set_thermostat':
            s['thermostat'].update(target_c=float(a['target_c']), mode=a.get('mode', s['thermostat']['mode'])); return {'ok': True, 'thermostat': s['thermostat']}
        if name == 'get_calendar': return {'date': a.get('date'), 'events': CAL.get(a.get('date'), [])}
        if name == 'set_alarm':
            s['alarms'].append({'time': a['time'], 'label': a.get('label', '')}); return {'ok': True, 'alarm': s['alarms'][-1]}
        if name == 'turn_off_appliance':
            ap = a.get('appliance')
            if ap not in s['appliances']: return {'error': f'no appliance {ap}'}
            if ap == 'dishwasher': return {'error': 'dishwasher is mid-cycle; it cannot be stopped remotely'}
            s['appliances'][ap] = 'off'; return {'ok': True, 'appliance': ap, 'state': 'off'}
    return {'error': 'unknown tool'}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        b = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/reset':
            return self._j({'ok': True})
        out = call(self.path.strip('/'), b)
        self._j(out)
    def do_GET(self): self._j(STATE)
    def _j(self, o):
        d = json.dumps(o).encode(); self.send_response(200); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(d))); self.end_headers(); self.wfile.write(d)
ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()
