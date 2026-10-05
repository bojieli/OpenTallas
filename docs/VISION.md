# Why instantaneous inference matters

[Project home](../README.md) · [Plain-English overview](OVERVIEW.md) ·
[Performance methodology](METHODOLOGY.md) · [Source register](SOURCES.md)

AI inference is usually discussed as a capacity problem: how many requests can
one system serve? OpenTallas begins with a different question: **what becomes
possible when one user can receive a large amount of high-quality reasoning
almost immediately?**

That question is no longer purely hypothetical. Taalas reports that its
fabricated HC1 accelerator runs Llama 3.1 8B at **16,960 tokens/s** <!-- figure: 16,960 src="configs/hardware/technology.json#reference_parts.taalas_hc1.published_tokens_s_per_user.value" name="Taalas HC1 published per-user rate, vision" -->
per user at batch one.
The number is a first-party result rather than an independent benchmark, but the
[product page](https://taalas.com/products/), [public
chatbot](https://chatjimmy.ai/), and [API documentation](https://api.taalas.com/)
make the system publicly inspectable. Taalas describes the broader motivation
in [The path to ubiquitous
AI](https://taalas.com/the-path-to-ubiquitous-ai/).

OpenTallas is an independent open research project. It does not reproduce HC1
and is not affiliated with Taalas. It studies the same broad architectural
trade—giving up general-purpose weight storage in exchange for highly local,
model-specific inference—through assumptions, models, software, RTL, and circuit
experiments that can be inspected and challenged.

## The thesis

Ten thousand tokens per second is not merely a faster version of today's API.
At that rate, model generation can stop being the long pole in many interactive
systems. Two consequences matter most:

1. **The cost of useful model output can fall.** A system that finishes more
   useful work during each paid second can amortize hardware and operating cost
   over more tokens.
2. **Reasoning can enter the real-time control loop.** A model can reconsider a
   plan quickly enough for its answer to remain relevant to a person, an
   interface, a robot, or a simulated world that is changing around it.

Neither consequence follows from tokens per second alone. The tokens must retain
the required model quality; the system must stay utilized; and prompt processing,
tools, networks, sensors, actuators, and safety checks must fit within the same
latency budget. High decode throughput creates the opportunity. System design
decides whether the opportunity becomes a product benefit.

## Throughput as an economic lever

Infrastructure cost is paid in time: capital is amortized over a useful life,
and power, cooling, and operations accumulate while the system runs. If a model
serves more useful output per second without a proportionate increase in those
costs, the infrastructure component of cost per token falls.

Model-specific silicon can improve that equation in three ways:

- local immutable-weight storage reduces repeated external data movement;
- spatially distributed weight service exposes more parallelism for low-batch
  decoding; and
- a known model graph allows hardware, placement, schedules, and data formats to
  be optimized together.

The trade is substantial. Mask cost and non-recurring engineering must be spread
across enough units and enough useful tokens. A checkpoint must remain valuable
long enough to recover that investment. Yield, repair, power delivery, cooling,
packaging, and utilization can erase a theoretical advantage. The OpenTallas
[partial-TCO studies](../README.md#1-more-useful-work-from-every-dollar-of-infrastructure)
therefore treat lower cost as a modeled outcome with explicit assumptions, not
as an automatic property of ROM.

The cost model is deliberately incomplete. It includes assumed acquisition,
allocated NRE, utilization, electricity, and PUE, but not the full cost of a
business. It should be read as an architectural comparison, not as a cloud price
forecast or a profitability claim.

## Throughput as a latency lever

An agentic system alternates between model work and environment work:

```text
observe → reason → act → wait for the environment → observe again
```

When reasoning takes tens of seconds, the natural product is asynchronous: send
a job, leave, and return later. When reasoning is much faster than the relevant
environment changes, the same workflow can become interactive.

Consider an illustrative reasoning-heavy phase that generates 100,000 tokens.
At 500 tokens/s, generation alone takes 200 seconds. At 10,000 tokens/s, it takes
10 seconds. This is not an OpenTallas benchmark; it is simple latency arithmetic.
It also omits prompt processing, tool calls, network delay, and parallel work.
Its purpose is to show why a throughput change of this scale can alter the user
experience rather than merely improve a chart.

The benefit is greatest when the workflow has serial dependencies. If one step
cannot begin until the model completes the previous step, every saved second
shortens the critical path. Parallel workloads benefit economically, but serial
agent loops benefit perceptually.

## What faster reasoning could unlock

### Agentic software projects

A capable coding or research agent may generate and inspect far more intermediate
reasoning than it presents to the user. Higher per-user throughput allows it to
try alternatives, run checks, critique failures, and revise the result without
turning each feedback cycle into a long wait. Some reasoning-heavy phases that
currently take minutes could complete in seconds; external tools and tests may
then become the dominant latency.

### Computer use

Computer-use agents operate in an environment that changes after every click,
keystroke, or network response. Faster inference shortens the time between
observation and action, reducing the chance that the interface has changed before
the agent responds. A reliable real-time system still needs fast perception,
state tracking, input safety, and recovery from unexpected UI behavior.

### Robotics and physical AI

A robot benefits when planning completes within the lifetime of its sensor data.
Fast model inference could support more frequent replanning and richer semantic
reasoning around changing tasks. It cannot replace deterministic control,
collision avoidance, safety certification, or hard real-time fallbacks. For many
robots, network round trips and deployment power are also stricter constraints
than server-side token generation.

### Voice

Natural conversation is sensitive to pauses and interruption. Faster reasoning
can reduce dead air, let a voice agent consider more context before speaking, and
make mid-sentence correction less awkward. The end-to-end budget still includes
speech recognition, turn detection, audio generation, transport, and buffering;
text-token throughput is only one part of conversational latency.

### Generative interfaces

Today's software usually chooses among views designed in advance. A sufficiently
fast model could assemble an interface around the user's immediate goal, update
it as the goal changes, and explain its own controls without waiting for an
offline generation step. This requires strong constraints: generated interfaces
must remain predictable, accessible, secure, and easy to undo.

### Interactive video and world models

If the model-specific approach transfers beyond language, it could support
world models that generate the next visual state quickly enough to respond to
input. The original [Oasis](https://oasis-model.github.io/) demonstration showed
an interactive, AI-generated open world at 20 frames per second. That is the
kind of qualitative transition high-throughput inference can enable: from
requesting a clip to inhabiting a continuously generated environment.

This repository does not implement a video generator, a world model, or an
Oasis-like system. Video architectures also have different bandwidth, state,
quality, and temporal-consistency requirements. The example defines a research
horizon, not a current OpenTallas claim. The reproducible [Oasis causal-state
and MiniMax-H3 study](../results/world-model/REPORT.md) makes the architectural
boundary concrete: causal next-frame state can conditionally expose immutable
weight service, while a full-clip bidirectional DiT is much less favorable to
ROM and remains compute/communication dominated.

## What throughput does not solve

Per-user decode rate should not be confused with any of the following:

- model intelligence, factuality, or reasoning quality;
- time to process a long prompt;
- aggregate throughput across many simultaneous users;
- the number of sessions that fit in memory;
- tool, database, network, sensor, or actuator latency;
- tail latency and availability in a production service;
- energy, cost, or thermal feasibility; or
- the safety of giving a model a faster action loop.

A 10,000-token/s model that waits five seconds for every tool call is not a
10,000-token/s agent. A fast quantized model that no longer meets the task's
quality threshold is not an improvement. A low-latency system with inadequate
safety controls can simply fail faster.

The research goal is therefore **balanced latency**: make model reasoning fast
enough that the rest of the system becomes visible, then engineer the complete
loop around the new bottleneck.

## Why an open implementation matters

Model-specific inference binds together choices that general accelerators can
usually separate: checkpoint, numerical format, memory layout, arithmetic,
interconnect, packaging, compiler, runtime, and manufacturing. A strong result
in one layer can be invalidated by an unstated assumption in another.

OpenTallas is organized as an evidence chain so those assumptions can be tested:

```text
model representation
        ↓
exact work and traffic
        ↓
architecture and cost envelopes
        ↓
compiler + runtime semantics
        ↓
RTL and verification
        ↓
physical and circuit evidence
        ↓
eventually: target silicon measurement
```

The last step does not exist today. The project's enthusiasm comes from the size
of the opportunity; its credibility depends on keeping that boundary explicit.

## Continue reading

- [OpenTallas in plain English](OVERVIEW.md) explains one token from model to
  hardware and derives a central performance point.
- [The root README](../README.md#performance-comparison) presents the main
  stock-versus-ROM comparisons, deterministic envelopes, and area-aware results.
- [Methodology](METHODOLOGY.md) defines the fairness and evidence rules.
- [Assumptions](ASSUMPTIONS.md) records the hardware, cost, and interpretation
  inputs.
- [Sources](SOURCES.md) separates primary references, secondary reports, and
  unresolved evidence.
- [Program report](ABI3_PROGRAM_REPORT.md) states what the executable stack and
  hardware evidence currently cover.
