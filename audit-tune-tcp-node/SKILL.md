---
name: audit-tune-tcp-node
description: Audit, benchmark, diagnose, and safely tune remote Linux TCP nodes over SSH. Use when a user provides SSH access and asks about BBR, BBR pacing-gain overshoot against a policer, congestion control, qdisc, TCP buffers, short-lived connections, cross-region throughput, packet loss, reordering, MTU, latency, iperf3 results, or persistent network tuning. Also use to compare bandwidth-versus-latency strategies and to distinguish host configuration problems from ISP, routing, Wi-Fi, policer, or application behavior.
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

With no stated preference, distinguish the network topology before selecting the optimization focus:
- **High-BDP / Long-Fat Pipes (e.g. trans-oceanic/long-haul, capacity >= 100 Mbps, RTT >= 120 ms)**:
  Optimize single-flow throughput. Maximizing single-stream goodput naturally drives optimal
  BBR window growth, and ample bandwidth absorbs small multi-flow bursts.
- **Low-BDP / Constrained-Bandwidth Short-Haul Routes (e.g. low-RTT regional paths, capacity <= 50 Mbps, RTT 20-70 ms)**:
  Do NOT rely solely on single-flow tests. Single-stream benchmarks introduce a dangerous blind
  spot where clean port-rate results mask severe cold-start stalls. For these routes, evaluate
  both sustained line rate and concurrent multi-stream short-flow burst completion (P = 6–10),
  protecting modern interactive messaging and web cold-start performance against token-bucket
  policer drops.

Never request a password, private-key contents, or `.env` contents. Accept an SSH command,
host/user/port, key path, ProxyJump, or askpass workflow, and use the supplied method exactly.

Do not go looking for what else the host runs. Enumerating processes, services, containers, or
application configuration adds nothing to the network picture and the user will rightly object
to it; once the network facts above are collected, start work immediately at the workflow's
default entry points. If a concrete reason exists to suspect another workload is distorting
network behavior, ask whether one exists and wait for the answer or permission — do not
investigate it yourself.

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
   Counters and sockets must also be sampled *while* a flow runs; a snapshot taken outside a
   flow reports zeros. See `references/live-diagnostics.md`.
4. Record client-side state when the client participates in the test: route, congestion
   control, interface type, Wi-Fi signal/rate, gateway loss, MTU, background traffic.
5. Compute BDP from measured RTT and the agreed ceiling:
   `BDP_bytes = bandwidth_bits_per_second * RTT_seconds / 8`.
6. Benchmark sequentially, low load to high. Read `references/benchmark-protocol.md` first, and
   `references/live-diagnostics.md` as soon as loss, stalls, or an unexplained gap appears.
7. Classify the bottleneck before tuning: node qdisc/buffer/application; access network or
   Wi-Fi; PMTU/MSS or middlebox; loss or reordering; near-capacity policer/queue/bufferbloat;
   asymmetric or poor inter-provider routing. When loss or reordering is present, classify its
   type and state the conclusion in the report: random loss already at low load (path defect,
   not node-tunable), loss only near capacity (policer/queue, sometimes avoidable), or
   time-of-day/diurnal (congestion — a single measurement is unreliable). This classification
   decides which parameters step 9 grinds and whether node tuning can help at all.
   Establish each claim with its control, not a single run: a below-ladder low-rate UDP floor, an
   equal-rate forward/reverse pair, a second destination measured in the same minute, or an
   egress-cap sweep. Flat RTT under full load with no queue growth, retransmits confined to the
   first seconds of a connection, and `pacing_gain:2.88672` on the sender socket together mean a
   *policed path with no queue*: the host is over-running the policer by itself, which is
   host-fixable. `references/live-diagnostics.md` holds the probes and the signature table.
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
   For an egress pacing ceiling (`fq maxrate`), sweep at least three values up to the port rate
   and keep the highest one that removes the retransmissions — a ceiling below the measured knee
   only adds collapse risk. Falsify before persisting: if loss does not fall as the cap falls,
   the loss is not the host's, so persist nothing.
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
- Repeat A/B tests; prefer medians and tails over a single best run. Prefer paired, interleaved
  comparisons (per-round differences, win counts) over medians of independent samples on a lossy
  path, and report the stalled/lossy run count next to the median.
- Take RTT from the TCP socket (`ss -tin` `minrtt`), not from ping: ICMP is often rate-limited and
  once reported 223-286 ms with mdev 16.6 on a path whose TCP RTT was a flat 165 ms.
- To A/B the *server's* congestion control, set `net.ipv4.tcp_congestion_control` and then
  restart the listener: iperf3 refuses `-C` in server mode ("client only"), and a listening
  socket caches its CC at creation, so accepted sockets ignore a later sysctl change. Verify the
  CC actually in use with `ss` mid-flow; a client-side `-C` never changes what the server sends.
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
For any persisted pacing ceiling, state the falsification test that justified it (a lower cap that
reduced no loss, or a below-ladder low-rate UDP floor) and the measured latency cost (`fq` EDT
pacing adds no queue, so RTT under load must be unchanged). Name the signature and the controls
from `references/live-diagnostics.md` that established the classification.

Then: measured RTT, loss, reordering, PMTU/MSS, single- and multi-flow capacity; why the
evidence points where it does; persistence paths and rollback; short-flow median/tail change
and the capacity guardrail result; tests not run and residual uncertainty.
