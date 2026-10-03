# Actual typed primary held/journal/context helper

Source base297b7036e2aa77bba6ec8aeb79afb024c1c41063; exact219 canonical map from10cb count/utility model. This is a NEW disjoint default-off combinational module, generator and directed actual RTL tests. No Nash source was edited. It reconstructs named records without generic352-bit truncation or dynamic address selection, using current sealed-codec repaired-payload wires plus CURRENT release_clean/CE/bad status from those same words.

Exact slots: heldrequest96..103(335bits), readquery104..110(297), writequery111(41), readdelivery112..118(300), write-selection119..124(6x5), round-robin131(3), query pipeline133..144(6x65), correctioncontexts145..168(8x96), preparedjournals169..186(9x87), scheduler187..188(79). Primary owns182words; secondary owns37, local secondary map0..5->125..130,6..35->189..218,36->132. Static seals/padding remain in caller codecs; no check/repair is bypassed by this view.

Integration ABI: flatten CURRENT P[0..218] into current_payload[44*g+:44], with current_clean=release_clean, current_ce=correctable, current_bad=uncorrectable||!seal_ok||!padding_ok. Tie OPT_PROTECTION to existing OPT_EXACT. Connect typed outputs to existing H/RQ/WQ/RD/J/X/Q/S/C/rr views. Zero-extend narrow held outputs into wider current local aliases if required. The per-record *_clean and primary_clean additionally exclude CE/bad, including contradictory clean+CE inputs. Disabled outputs and qualifiers are all0. Normal admission must ALSO join the existing37-word secondary qualification and current correction/debt/stop/reset logic; this helper is not a ready/release policy.

No new persistent state, ports, queued debt, pipeline edge, clock/reset ingress, codec or SRAM. Wiring and integrity reductions already belong to the primary219-word current-clean gate in10cb. This does not establish zero physical delay: loaded fanout/182-input reduction and eventual integration must remain priced/closed by the parent source context. It does not implement eight correction FSMs, count commits, nine journal execution engines or a fullcontroller.

Actual Icarus RTL test:660samples including every219word clean/CE/bad status, heldvalue restoration and defaultoff; 12pytest tests PASS including all named-record basisbits. Three real source mutants compile and fail actual RTL assertions: wrong journal globalword, ignoredCE, omitted primary schedulerword. Logs/toolversion/hash retained. Codec physical bitfault gates remain Nash's full219 controller qualification; these tests check this module's mapping/status, not codec correctness or bridge/fulltoken.

Commands:

    python3 -m pytest -q tests/test_w2_nc6_primary_record_helper.py
    python3 tools/w2_nc6_primary_record_helper.py --model /tmp/W2-HELPER-MODEL.json
    python3 tools/w2_nc6_primary_record_helper.py --emit-rtl /tmp/W2-HELPER.sv

Nash keeps sole shared primary source/integration ownership. The helper is available to wire into that source without replacing or modifying codec/corrector/caller architecture. No wholecontroller build, bridge or fulltoken run was launched; no predecessor PASS/FAIL record overwritten.
