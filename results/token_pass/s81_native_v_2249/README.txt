Actual missing middle V transport, 2026-10-29 22:49 takeover

Three admitted functional component builds PASS, all at833ps:
1. Real Eng ot_s81eng_xq_n32 body with its realAQ/SRAM dependencies:
   1024 full276-bit checks, two body edges, cold/warm reset64;
   actual own-train collision/fault control observed164 collision cycles.
2. Gunit V-channel carve (the real five N2 pass cells plus L2 JREG0 stop)
   and BK/seqhost carve (real entry relay, BK stop, full dsdv_sh_vc):
   1920 fullword checks,12 and5 body edges, injection collision guard caught.
3. Those real bodies plus CURRENT evbind2 registered-station ages:
   3264 fullword checks, zero errors, GunitN/S114/96edges,
   BK/seqhostN/S235/229, EngN/S149/151. Actual collision guards1001.
Each build separately catches a payload corruption and a one-edge age error.
Logs/status files retain actual failures of these negative controls.

Current route export:24/24 complete276-bit words, no blocked/mixed bit ages,
no glue-driver aliases inferred. Frozen copy of S81 current event2 evbind2
bind-stage artifacts (source commit4be6686; full bind verification separately
pending). current_routes.json records source/asbuilt/bound-top/sinks hashes.
All45 RTL/dependency source files in the bodies match that event source byte
for byte (current_event_source_match.json). No RTL or latency change is made.

Compositions, including existing body cycles:
GunitN78+12+24=114; S24+12+60=96.
BK/seqhostN66+3+104+2+60=235; S58+2+106+3+60=229.
EngN54+2+93=149; S95+2+54=151.
The10 Gunit interleaf directions are actual0-age bound words, not defaults.
The fixture represents actual registered station ages with ot_hdc_delay;
functional missing middle bodies remain the real RTL cells/modules.

Scope: foreign XQ/XB four-fragment transport, controller injections held idle.
Gunit arithmetic and BK quarter/control bodies are outside the V-channel carve.
Own-injection conflicts are deliberate separate fault controls. This does not
prove that the production programme leaves those injection slots free. It does
not qualify the old80VQ fixture, all80 arithmetic, die clock phase, physical
START, the pending full bind verification, or a token pass. The old80 failures
remain preserved. Next: consume these exact middle-route contracts in a CURRENT
publication calendar with current16-slice transport/RSTD data and actual producer
dates; preserve the guards against mixed-source graphs and omitted bodies.

Runs: intel1:/srv/opentallas-scratch2/claude/codex-s81-native-v-2249
units2823707/2946605/3177778 all terminal0.
Current route export: intel2:codex-s81-middle-ages-2249 unit2790180 terminal0.
