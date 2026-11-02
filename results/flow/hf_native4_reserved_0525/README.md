HFDEP native4 reserved-bit bounded diagnosis

Original official native4 report remains NOT EQUIVALENT: 14002 points / 14000 proved / 2 differs, with no die reset contract. Actual reserved fault_cause[3:4] source resets to zero then holds. Raw four-edge symbolic reset-prefix BASE proves zero; wrong-constant BASE controls differ. Raw universal Boolean STEP fails because native Slang frontends expose reserved leaf bits as anonymous RTL-X inputs 18/19/47/48. Existing official RTL-X-validity STEP proves both zero hypotheses; wrong-constant1 STEP controls both differ. This uses the checker's existing validity semantics, no added mask/constraint/reset override.

Actual units: prefix Intel2 oth-ubuntu-2328234-1793624163; official-validity Intel2 oth-ubuntu-2954021-1793626613 exit0. Exact runtime /srv/opentallas-scratch2/claude/codex-flow-hf-validity-step-0515. No full official replay, source qualification or ABI credit. Constant physical pins still require actual source/ABI pruning.
