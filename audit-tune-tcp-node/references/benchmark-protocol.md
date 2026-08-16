# Benchmark Protocol

Use this protocol only within the user's authorized traffic ceiling. Run tests sequentially.

## Address Family

Detect reachability first. Single-stack: use that family, don't ask. Dual-stack: ask which
to test, or both — v4 and v6 take different paths, so report them separately. Substitute
`-4` or `-6` for the `-F` placeholder below.

## Preflight

1. Confirm `iperf3` versions and the server listener.
2. Sample CPU, interface counters, qdisc counters, and background traffic.
3. Record client and server congestion control, qdisc, route, MTU, and socket buffers.
4. Measure idle RTT before load.

## Path and Access Checks

- Ping the local gateway separately from the remote node.
- On Wi-Fi clients, record signal, frequency, TX/RX negotiated rate, and gateway loss.
- Probe PMTU with DF packets at a safe size ladder. Do not interpret an oversized local
  rejection as remote packet loss.
- Run ICMP and TCP MTR for about 20 probes. Intermediate-hop loss is evidence only when it
  propagates to later hops or the destination.

## TCP Baseline

Use 10-15 second runs unless the user authorizes longer tests.

```bash
iperf3 -F -c HOST -p PORT -R -t 15 -i 1 --get-server-output
iperf3 -F -c HOST -p PORT    -t 15 -i 1 --get-server-output
iperf3 -F -c HOST -p PORT -R -P 4 -t 15 -i 3
```

Interpret retransmissions at the sender. Multi-flow capacity much higher than single-flow
capacity points toward RTT, loss, reordering, per-flow policing, or congestion-control
behavior rather than a hard port limit.

Compare congestion algorithms per socket only when supported. Do not persist the result
automatically:

```bash
iperf3 -F -c HOST -p PORT -R -C cubic -t 15 -i 1 --get-server-output
```

Run comparisons in alternating order when possible. TCP metrics learned by one test may
affect later connections.

## UDP Loss and Reordering

Start well below the ceiling. A typical ladder is 10 Mbps, 25% of the ceiling, 50%, and 90%.
Deduplicate rates and stop if loss, host load, billing, or production impact becomes unsafe.
Use 1200-byte datagrams to reduce PMTU ambiguity:

```bash
iperf3 -F -c HOST -p PORT -R -u -b RATE -l 1200 -t 8 -i 1 --get-server-output
```

Repeat low-rate stages when results are surprising. Repeatable loss or reordering at low
offered load is a path-quality problem; larger TCP buffers or an egress shaper will not cure
it. Loss that appears only near the port ceiling may indicate a policer or queue.

## Short-Flow A/B

Reuse an existing HTTP endpoint if present; otherwise start a temporary listener on an unused
high port and clean it up afterward. Create fixed 64 KiB, 256 KiB, and 1 MiB objects. For
each profile and size, make at least five new TCP connections:

```bash
curl --noproxy '*' -F -sS --connect-timeout 5 --max-time 20 \
  -o /dev/null \
  -w 'PROFILE\tSIZE\tRUN\t%{time_connect}\t%{time_starttransfer}\t%{time_total}\t%{speed_download}\n' \
  http://HOST:PORT/OBJECT
```

Feed the TSV to `scripts/summarize-shortflows.py`. Prefer A/B/A or alternating runs when the
route is variable. Compare median and p95, not only mean throughput.

## Validation

After tuning, repeat:

1. Representative short-flow sizes.
2. Single-flow forward/reverse TCP.
3. Multi-flow capacity guardrail.
4. SSH and production service health.
5. Active sysctls, route metrics, qdisc, and persistent files.

Stop temporary listeners and remove test objects in a guaranteed cleanup step.
