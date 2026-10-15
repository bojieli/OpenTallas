# Source-bound independent physical prototypes

These assignments authorize building and measuring actual source-specific hard leaves. They are not die integration or timing qualification. Owners retain source functional proof, mapped area census, actual pin/PG readback, <=60% face occupancy after PG exclusion, native CTS, TT setup/FF hold, and routing checks.

* HC combined shell: source `5b0730d17`, 4,843 FF plus ten macro clocks. The core-aware macro edge correction is included. A 500.04 µm square exact body is requested; platform snap to 501.12 is allowed and must be reported. This is one combined memory/control shell, not the four-MAC arithmetic bank. The previous 461.465 µm inter-bank path fails the actual 406.491 µm ETM limit, so no whole-bank composition is granted.
* Native PC: actual 259.2 by 345.6 µm owner spec, one response SRAM and 13,650 clock sinks per PC. The explicit four-stack homes preserve selected D SM frame positions. These candidate homes do not admit old controller-bearing PHY abstractions together with new controllers. Command-only PHY binding is open. The north-SM translation in the compact-shared alternative conflicts with these new controller frames.
* SU: all 1,921 literal interface pins preserved. Moving the 840-bit offset bundle to north removes the south-face overrun without dropping mapped-unused ports. K0/K1/K2 have distinct source-parameter prototypes and measured area/census. Their actual source serial profile is 1111.111 ps; this is not production-rate qualification. The separate six-reader bank needs core-edge/channel verification before physical admission.

Absolute source paths and SHA256 values are recorded in each JSON. Source owners must version replacements explicitly; no view is inherited by a changed source.
