import json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
TOOLS = [
 {'type': 'function', 'function': {'name': 'get_home_state', 'description': 'Read every sensor: door locks, door and window contacts, lights, thermostat, appliances, alarms.', 'parameters': {'type': 'object', 'properties': {}}}},
 {'type': 'function', 'function': {'name': 'set_lights', 'description': 'Turn the lights in one room (or "all") on or off.', 'parameters': {'type': 'object', 'properties': {'room': {'type': 'string'}, 'on': {'type': 'boolean'}}, 'required': ['room', 'on']}}},
 {'type': 'function', 'function': {'name': 'lock_door', 'description': 'Lock a smart lock: front_door, back_door or garage_entry.', 'parameters': {'type': 'object', 'properties': {'door': {'type': 'string'}}, 'required': ['door']}}},
 {'type': 'function', 'function': {'name': 'set_thermostat', 'description': 'Set the thermostat target temperature in Celsius and optionally the mode (heat/cool/off).', 'parameters': {'type': 'object', 'properties': {'target_c': {'type': 'number'}, 'mode': {'type': 'string'}}, 'required': ['target_c']}}},
 {'type': 'function', 'function': {'name': 'get_calendar', 'description': "List the user's calendar events for a date (YYYY-MM-DD).", 'parameters': {'type': 'object', 'properties': {'date': {'type': 'string'}}, 'required': ['date']}}},
 {'type': 'function', 'function': {'name': 'set_alarm', 'description': 'Set a wake-up alarm at HH:MM on the next occurrence.', 'parameters': {'type': 'object', 'properties': {'time': {'type': 'string'}, 'label': {'type': 'string'}}, 'required': ['time']}}},
 {'type': 'function', 'function': {'name': 'turn_off_appliance', 'description': 'Turn off an appliance: oven, tv or dishwasher.', 'parameters': {'type': 'object', 'properties': {'appliance': {'type': 'string'}}, 'required': ['appliance']}}},
]
SYSTEM = ("You are the on-device assistant of a smart-home hub. Current local time: Friday 2026-10-09 22:41. "
          "Use the tools to act; call several tools in one turn when they are independent. Never invent device states. "
          "Finish with a short spoken-style reply to the user.")
def run_calls(port, calls):
    """execute a turn's tool calls concurrently (as a hub would); return results with measured wall times"""
    def one(c):
        t0 = time.time()
        req = urllib.request.Request(f'http://127.0.0.1:{port}/{c["name"]}', data=json.dumps(c['arguments']).encode(), headers={'Content-Type': 'application/json'})
        out = json.loads(urllib.request.urlopen(req, timeout=30).read())
        return dict(name=c['name'], arguments=c['arguments'], result=out, t_start=t0, t_end=time.time(), ms=round((time.time() - t0) * 1000, 1))
    t0 = time.time()
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, calls))
    return res, round((time.time() - t0) * 1000, 1)
