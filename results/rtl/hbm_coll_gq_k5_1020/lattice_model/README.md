# GQ lattice and channels: old k5 FAIL, proposed model only

Six old SRAM origins are off literal43.2um lattice: y166.944,247.488,328.032 in each of two quantizers. The abutted stack gaps0.072um do not satisfy the20um channel rule. The old lane statement that only each stack base must be on lattice is invalid; no exception is authorized. Existing r4 native-first gate was already launched; retain it as diagnostic only, with no submit or samegeometry follow-up.

MODEL_ONLY.json puts all macro origins on literal43.2: tall SRAM rows43.2,172.8,302.4,432, pitch129.6; actual height80.472 gives49.128um clear rows. Outline475.2x561.6, fullcenterchannel121.176um, outerpinchannels86.4/77.976um, VMringchannels24.84um. Busy-face density410/80.472=5.095pins/um. This passes literalorigin/channel arithmetic only.

The enlarged outline does not prove logical reach. Before any layout gate, enumerate exact source/capture endpoint regions for all registered ports, FFs and macro data pins. In particular both quantizer VMrr consumers and control crossings must remain<=405um through all combinational logic/buffers, or receive real source/region landings with measured static-schedule cost. No ABI or rate credit is claimed. No new kit is generated or gated from this model.
