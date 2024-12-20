#!/usr/bin/env python3

# Source: https://github.com/O-X-L/nftables_addon_failover
# Copyright (C) 2024 Rath Pascal
# License: MIT

from socket import socket, AF_INET, AF_INET6, SOCK_STREAM

from util import validate_and_write, load_config, format_var, ensure_list

PROCESS_IPv6 = True

# paths are set in util (shared between addons)
CONFIG_FILE = 'failover.json'
CONFIG_FILE_KEY = 'failover'
OUT_FILE = 'failover.nft'
TIMEOUT = 2  # sec
PROCESS_PROTOS = ['ip4']
if PROCESS_IPv6:
    PROCESS_PROTOS.append('ip6')


def _is_reachable(ip: str, port: (str, int), ip_proto: str) -> bool:
    ip_proto = AF_INET if ip_proto == 'ip4' else AF_INET6

    with socket(ip_proto, SOCK_STREAM) as s:
        s.settimeout(TIMEOUT)
        return s.connect_ex((ip, port)) == 0


CONFIG = load_config(file=CONFIG_FILE, key=CONFIG_FILE_KEY)

if CONFIG is None or len(CONFIG) == 0:
    raise SystemExit(f"Config file could not be loaded: '{CONFIG_FILE}'!")


lines = []
vars_defined = []

for var, data in CONFIG.items():
    if ('ip4' not in data and 'ip6' not in data) or 'port' not in data:
        print(f"ERROR: Either ('ip4' & 'ip6') or 'port' missing for variable '{var}'!")
        continue

    for proto in PROCESS_PROTOS:
        proto_version = 4 if proto == 'ip4' else 6

        if proto not in data or len(data[proto]) == 0:
            lines.append(
                format_var(
                    name=var,
                    data=[],
                    version=proto_version,
                )
            )
            continue

        values = ensure_list(data[proto])
        if 'values' in data:
            values = ensure_list(data['values'])

        if not isinstance(data[proto], list):
            data[proto] = [data[proto]]

        proto_var = f"{var}_{proto}"

        for idx, host in enumerate(data[proto]):
            if _is_reachable(ip=host, port=data['port'], ip_proto=proto):
                lines.append(
                    format_var(
                        name=var,
                        data=[values[idx]],
                        version=proto_version,
                    )
                )
                vars_defined.append(proto_var)
                break

        if proto_var not in vars_defined:
            lines.append(
                format_var(
                    name=var,
                    data=[],
                    version=proto_version,
                    fallback=values[0],
                )
            )

validate_and_write(lines=lines, file=OUT_FILE, key=CONFIG_FILE_KEY)
