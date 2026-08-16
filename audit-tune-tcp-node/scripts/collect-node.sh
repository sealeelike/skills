#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf 'Usage: %s -- ssh [ssh-options] user@host\n' "${0##*/}" >&2
}

if [[ ${1:-} != "--" || $# -lt 3 ]]; then
    usage
    exit 2
fi
shift

ssh_cmd=("$@")
if [[ ${ssh_cmd[0]##*/} != "ssh" ]]; then
    printf 'error: command after -- must be ssh\n' >&2
    exit 2
fi

"${ssh_cmd[@]}" 'bash -s' <<'REMOTE'
set -u

section() {
    printf '\n== %s ==\n' "$1"
}

run_optional() {
    "$@" 2>&1 || true
}

sysctl_bin=$(command -v sysctl 2>/dev/null || true)
if [[ -z "$sysctl_bin" && -x /usr/sbin/sysctl ]]; then
    sysctl_bin=/usr/sbin/sysctl
fi

section identity
run_optional date -Is
run_optional hostname
run_optional uname -a
if [[ -r /etc/os-release ]]; then
    run_optional sed -n '1,80p' /etc/os-release
fi
run_optional id
run_optional systemd-detect-virt
printf 'SSH_CONNECTION=%s\n' "${SSH_CONNECTION:-unset}"

section resources
run_optional uptime
run_optional nproc
run_optional free -h

section tcp-sysctls
keys=(
    net.ipv4.tcp_available_congestion_control
    net.ipv4.tcp_congestion_control
    net.core.default_qdisc
    net.ipv4.tcp_rmem
    net.ipv4.tcp_wmem
    net.core.rmem_default
    net.core.wmem_default
    net.core.rmem_max
    net.core.wmem_max
    net.ipv4.tcp_mtu_probing
    net.ipv4.tcp_slow_start_after_idle
    net.ipv4.tcp_no_metrics_save
    net.ipv4.tcp_ecn
    net.ipv4.tcp_fastopen
    net.ipv4.tcp_max_syn_backlog
    net.ipv4.tcp_syncookies
    net.ipv4.ip_local_port_range
    net.core.somaxconn
    net.ipv4.tcp_tw_reuse
    net.ipv4.tcp_notsent_lowat
    net.ipv4.tcp_window_scaling
    net.ipv4.tcp_reordering
    net.ipv4.tcp_max_reordering
    net.ipv4.tcp_recovery
    net.ipv4.tcp_sack
    net.ipv4.tcp_dsack
)
if [[ -n "$sysctl_bin" ]]; then
    for key in "${keys[@]}"; do
        run_optional "$sysctl_bin" "$key"
    done
else
    printf 'sysctl not found\n'
fi

section network
run_optional ip -br address
run_optional ip route
run_optional ip -s link
run_optional ss -s

default_dev=$(ip route show default 2>/dev/null | awk 'NR == 1 { for (i=1; i<=NF; i++) if ($i == "dev") { print $(i+1); exit } }')
printf 'DEFAULT_DEV=%s\n' "${default_dev:-unset}"

if [[ -n "${default_dev:-}" ]]; then
    section qdisc
    if command -v tc >/dev/null 2>&1; then
        run_optional tc -s -d qdisc show dev "$default_dev"
    elif [[ -x /usr/sbin/tc ]]; then
        run_optional /usr/sbin/tc -s -d qdisc show dev "$default_dev"
    else
        printf 'tc not found\n'
    fi

    section interface-features
    if command -v ethtool >/dev/null 2>&1; then
        run_optional ethtool "$default_dev"
        run_optional ethtool -k "$default_dev"
    elif [[ -x /usr/sbin/ethtool ]]; then
        run_optional /usr/sbin/ethtool "$default_dev"
        run_optional /usr/sbin/ethtool -k "$default_dev"
    else
        printf 'ethtool not found\n'
    fi
fi

section congestion-modules
if command -v lsmod >/dev/null 2>&1; then
    lsmod | awk 'NR == 1 || $1 ~ /^(tcp_bbr|sch_fq|sch_fq_codel|sch_cake)$/'
else
    printf 'lsmod not found\n'
fi

# SSH_CONNECTION = "<client-ip> <client-port> <server-ip> <server-port>".
# The first field is the CLIENT address (the machine that opened this SSH
# session). Route/metrics back to the client are the audited node's egress path
# toward whoever ran the audit, so label it as such and do not treat it as the
# path to some other tuning peer.
read -r client_ip _client_port _server_ip _server_port <<<"${SSH_CONNECTION:-}"
if [[ -n "${client_ip:-}" ]]; then
    section route-to-ssh-client
    printf 'CLIENT_IP=%s\n' "$client_ip"
    run_optional ip route get "$client_ip"
    run_optional ip tcp_metrics show "$client_ip"
fi
REMOTE
