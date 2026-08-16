---
name: audit-tune-tcp-node
description: Audit, benchmark, diagnose, and safely tune remote Linux TCP nodes over SSH. Use when a user provides SSH access and asks about BBR, congestion control, qdisc, TCP buffers, short-lived connections, cross-region throughput, packet loss, reordering, MTU, latency, iperf3 results, or persistent network tuning. Also use to compare bandwidth-versus-latency strategies and to distinguish host configuration problems from ISP, routing, Wi-Fi, policer, or application behavior.
---

# Audit and Tune TCP Node

Measurements are the source of truth. Treat provider speed, location, carrier, and
"optimized route" claims as hypotheses to test, not conclusions.

## Authorization

Broad self-tune is already granted: read-only audit, benchmarking, installing the tools a
benchmark needs (iperf3, mtr, ethtool, etc.), reversible runtime/route/qdisc experiments, and
narrowly scoped sysctl and network-hook persistence — do these without asking.

Confirm separately before: installing a new kernel; rebooting or restarting a production
service; changing firewall or provider security-group rules.

Before benchmarking, ask one concise bundled question for the facts that can't be probed and
that bound expectations: rough node profile (geographic location of both ends, line/route or
provider "optimized route" claim) and the benchmark rate ceiling (bandwidth/traffic cap). Do
not self-pick a default to skip this. Workload, direction, and throughput/latency preference
come up as relevant.

A missing ceiling is not a reason to skip benchmarking — measure achievable single-flow
goodput directly; the ceiling only bounds interpretation (whether a result is at line rate).

With no stated preference, optimize single-flow throughput: maximize the repeatably-measured
single-stream goodput in the direction that matters, without a material short-flow or
tail-latency regression.

Never request a password, private-key contents, or `.env` contents. Accept an SSH command,
host/user/port, key path, ProxyJump, or askpass workflow, and use the supplied method exactly.

## Temporary Test Ports

Reuse an existing iperf3/HTTP listener if present; otherwise start one on an unused high port.
Avoid declared production ports, and guarantee the listener and any test files are removed
before finishing — even after failure. This does not extend to firewall or security-group
changes.

## Workflow

1. Read applicable host instructions. Avoid `.env`; ask before reading nonstandard
   application configuration.
2. Establish SSH with noninteractive identity options. Use a temporary known-hosts file if
   appropriate.
3. Snapshot current state before any change: `scripts/collect-node.sh -- <ssh command>`.
4. Record client-side state when the client participates in the test: route, congestion
   control, interface type, Wi-Fi signal/rate, gateway loss, MTU, background traffic.
5. Compute BDP from measured RTT and the agreed ceiling:
   `BDP_bytes = bandwidth_bits_per_second * RTT_seconds / 8`.
6. Benchmark sequentially, low load to high. Read `references/benchmark-protocol.md` first.
7. Classify the bottleneck before tuning: node qdisc/buffer/application; access network or
   Wi-Fi; PMTU/MSS or middlebox; loss or reordering; near-capacity policer/queue/bufferbloat;
   asymmetric or poor inter-provider routing. When loss or reordering is present, classify its
   type and state the conclusion in the report: random loss already at low load (path defect,
   not node-tunable), loss only near capacity (policer/queue, sometimes avoidable), or
   time-of-day/diurnal (congestion — a single measurement is unreliable). This classification
   decides which parameters step 9 grinds and whether node tuning can help at all.
8. Read `references/tuning-decisions.md` before proposing or applying any change.
9. Grind the parameters the step-7 classification implicates — derive the targets from the
   measured bottleneck, not a fixed checklist. Sweep each as a range to a plateau: at least
   three points, stopping only when the median stops improving — never a single value declared
   "no gain". Change one variable at a time; take the median on a noisy path; restore anything
   inconclusive or harmful. A large gain on one axis does not excuse leaving the others
   unswept — do not stop at the first win. Apply the best-measured configuration for the
   objective. When a result looks off — a win with no mechanism, a margin small against the
   run-to-run swing, or one that contradicts theory or an earlier run — neither lock it in nor
   wave it away on theory alone: add targeted tests until the data settles it. Escalate on
   suspicion, not by rule.
10. Persist only what a test proved, using the distro's network lifecycle, and verify the
    live value. Report a rollback path for every persistent change.
11. Re-run representative short-flow and capacity tests; confirm SSH and production services
    still respond.
12. Stop every temporary service and remove every temporary test file.

## Benchmark Discipline

- No heavy tests in parallel. Never start at the advertised line rate.
- Check background traffic and CPU before interpreting throughput.
- TCP forward and reverse; sender-side retransmissions belong to the sender.
- UDP at low offered load to separate path loss/reordering from congestion-control behavior.
- MTR intermediate-hop loss is inconclusive unless it reaches the destination.
- Repeat A/B tests; prefer medians and tails over a single best run.
- A congestion-control comparison is diagnostic, not an automatic recommendation.
- Extreme mid-test stalls or dropped flows are a diagnostic signal, not a data point: the node
  itself may be failing, or the client's China-mainland carrier may have QoS-throttled the flow
  after repeated high-rate tests. Pause and isolate the cause before trusting further numbers.

## Scope

Keep the answer actionable on the node. Lead with which settings to change, keep, or test.
Treat access-network, carrier, and upstream-route findings as diagnostic constraints, not
recommendations — mention an uncontrollable path limit in a brief note, then return to
node-side controls. Discuss provider/route/region/carrier changes only when the user asks for
them or controls them. When a path finding invalidates a proposed change, say so briefly and
move on. If nothing node-side is proven, say that directly and list the reversible A/B
candidates worth trying — don't substitute "change the route" for a node-side answer.

## Reporting

Lead with the node-side disposition:

1. `Change`: proven beneficial and applied.
2. `Test`: reversible A/B candidates not yet proven.
3. `Keep`: inspected settings that should stay.

Deliver an ablation table — one row per parameter tested, with the numbers that decided it:

| Parameter | Before | After | Gain? | Objective metric before → after |

List every rung of a swept parameter and mark the kept value. Every row carries the deciding
number with units and delta, the `no`-gain rows included (`16M: 110 vs 111 Mbps, within
noise`) — never bare prose.

Then: measured RTT, loss, reordering, PMTU/MSS, single- and multi-flow capacity; why the
evidence points where it does; persistence paths and rollback; short-flow median/tail change
and the capacity guardrail result; tests not run and residual uncertainty.
