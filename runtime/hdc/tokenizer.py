"""The model's Hugging Face tokenizer, folded into the reduced vocabulary.

The reduced vehicles keep the shipped model's tokenizer and fold its ids
into the reduced vocabulary by ``id % vocab`` -- the rule that derived the
reduced workloads from the governed ones (build/workloads/*-reduced-*/
``derived_from.rule``).  Encoding is therefore the shipped tokenizer plus the
fold; a generated reduced id is decoded as the shipped token with that id.
Only ``tokenizer.json`` is read from the Hugging Face cache; no weights.

Chat rendering follows each model's template with thinking disabled, as the
governed workloads render it:

* Qwen3: ``<|im_start|>{role}\\n{content}<|im_end|>\\n`` per message, then
  ``<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n``;
* DeepSeek-V4.1: ``<｜begin▁of▁sentence｜>{system}``, ``<｜User｜>{content}`` and
  ``<｜Assistant｜>{content}<｜end▁of▁sentence｜>`` per turn, then
  ``<｜Assistant｜></think>``.
"""

from __future__ import annotations

from tokenizers import Tokenizer

from runtime.hdc.targets import Target


class ModelTokenizer:
    def __init__(self, target: Target):
        path = target.tokenizer_path()
        if path is None:
            raise RuntimeError(f"no cached tokenizer for {target.tokenizer_repo} under ~/.cache/huggingface/hub")
        self.tok = Tokenizer.from_file(str(path))
        self.vocab = target.vocab
        self.chat_kind = target.chat
        self.eos = set(target.eos)
        self.source = str(path)

    def render_chat(self, messages: list[dict]) -> str:
        if self.chat_kind == "qwen3":
            s = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages)
            return s + "<|im_start|>assistant\n<think>\n\n</think>\n\n"
        bos, eos = "<｜begin▁of▁sentence｜>", "<｜end▁of▁sentence｜>"
        s = bos + "".join(m["content"] for m in messages if m["role"] == "system")
        for m in messages:
            if m["role"] == "user":
                s += "<｜User｜>" + m["content"]
            elif m["role"] == "assistant":
                s += "<｜Assistant｜>" + m["content"] + eos
        return s + "<｜Assistant｜></think>"

    def shipped_ids(self, text: str) -> list[int]:
        return self.tok.encode(text, add_special_tokens=False).ids

    def encode(self, text: str) -> list[int]:
        return [i % self.vocab for i in self.shipped_ids(text)]

    def encode_chat(self, messages: list[dict]) -> list[int]:
        return self.encode(self.render_chat(messages))

    def decode(self, ids: list[int]) -> str:
        return self.tok.decode([i for i in ids if i not in self.eos], skip_special_tokens=False)
