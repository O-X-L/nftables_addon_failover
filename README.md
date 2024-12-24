# NFTables Addon - Failover

This failover addon enables you to have one NFTables variable that will always point to a server that is online.

Why would you want that?

It's an alternative to using a load-balancer/reverse-proxy to perform a failover between nodes.

Many times a central endpoint is a better solution - but if it is a high-traffic or low-latency application it might be smarter to send the traffic directly to the target node.

<img src="https://github.com/superstes/nftables_addon_failover/blob/latest/docs/failover.png" alt="Failover - Proxy/LB vs direct" width="600"/>

Currently only TCP port-checks are supported.

Links: [NFTables Documentation](https://docs.o-x-l.com/firewall/nftables.html) |
[Addon for DNS-Resolution](https://github.com/O-X-L/nftables_addon_dns) |
[Addon for IP-Lists](https://github.com/O-X-L/nftables_addon_iplist)

----

## Install

* Create directories:

   ```bash
   mkdir -p /var/local/lib/nftables_addons /etc/nftables.d/addons/
   ```

* Add the script-files:

   * [util.py](https://github.com/O-X-L/nftables_addon_dns/blob/latest/lib/util.py)
   * [iplist.py](https://github.com/O-X-L/nftables_addon_failover/blob/latest/lib/failover.py)

* Add the config file:

   `/etc/nftables.d/addons/failover.json`

* Optional: Create a service user

   * Add sudoers privileges
   * Allow to read lib-dir
   * Allow to write to addons-config-dir

* Add cron or systemd-timer to execute the script on a schedule: `python3 /var/local/lib/nftables_addons/failover.py`

* Test it and verify it's working as expected

----

## Result

```text
cat /etc/nftables.d/addons/failover.nft 
> # Auto-Generated config - DO NOT EDIT MANUALLY!
> 
> define endpoint_filer_v4 = 192.168.87.100
> define endpoint_filer_v6 = 2001:DB8:2:2
> define endpoint_print_v4 = 192.168.93.52  # if first one is offline
> define endpoint_print_v6 = ::
> define mark_proxy_v4 = 200
> define mark_proxy_v6 = ::  # unused
```

----

## How does it work?

1. A configuration file needs to be created:

    `/etc/nftables.d/addons/failover.json`

    ```json
    {
      "failover": {
        "endpoint_filer": {
          "ip4": ["192.168.87.100", "192.168.87.101"],
          "ip6": ["2001:DB8:2:2", "2001:DB8:2:3"],
          "port": 443
        },
        "endpoint_print": {
          "ip4": ["192.168.93.51", "192.168.93.52"],
          "port": 631
        },
        "mark_proxy": {  // set fwmark for policy routing
          "ip4": ["192.168.132.2", "192.168.132.3"],
          "port": 3129,
          "values": [200, 201]
        }
      }
    }
    ```

    **Config options**:

      * `port`: required

        TCP Port to check for online-status

      * `values`: optional; default = using IPs

        1-to-1 mapping to ip-lists. Lists must be of the same length


2. The script is executed

    `python3 /var/local/lib/nftables_addons/failover.py`

  * It will load the configuration
  * Run port-checks for all configured variables - use first host that is online
  * Map hosts to values if supplied
  * If no host is online - will use first host/value
  * The new addon-config is written to `/tmp/nftables_failover.nft`
  * Its md5-hash is compared to the existing config to check if it changed

  * **If it has changed**:
    * **Config validation** is done:

      * An include-file is written to `/tmp/nftables_main.nft`:

        ```nft
        include /tmp/nftables_failover.nft
        # including all other adoon configs
        include /etc/nftables.d/addons/other_addon1.nft
        include /etc/nftables.d/addons/other_addon2.nft
        # include other main configs
        include /etc/nftables.d/*.nft
        ```

      * This include-file is validated:

        `sudo nft -cf /tmp/nftables_main.nft`

    * The new config is written to `/etc/nftables.d/addons/failover.nft`
    * The actual config is validated: `sudo nft -cf /etc/nftables.conf`
    * NFTables is reloaded: `sudo systemctl reload nftables.service`


3. You will have to include the addon-config in your main-config file `/etc/nftables.conf`:

    ```
    ...
    include /etc/nftables.d/addons/*.nft
    ...
    ```

----

## Privileges

If the script should be run as non-root user - you will need to add a sudoers.d file to add the needed privileges:

```text
Cmnd_Alias NFTABLES_ADDON = \
  /usr/bin/systemctl reload nftables.service,
  /usr/sbin/nft -cf *

service_user ALL=(ALL) NOPASSWD: NFTABLES_ADDON
```

You may not change the owner of the addon-files as the script will not be able to overwrite them.

----

## Safety

As explained above - there is a config-validation process to ensure the addon will not supply a bad config and lead to a failed nftables reload/restart.

If you want to be even safer - you can add a config-validation inside the `nftables.service`:

```text
# /etc/systemd/system/nftables.service.d/override.conf
[Service]
# catch errors at start
ExecStartPre=/usr/sbin/nft -cf /etc/nftables.conf

# catch errors at reload
ExecReload=
ExecReload=/usr/sbin/nft -cf /etc/nftables.conf
ExecReload=/usr/sbin/nft -f /etc/nftables.conf

# catch errors at restart
ExecStop=
ExecStop=/usr/sbin/nft -cf /etc/nftables.conf
ExecStop=/usr/sbin/nft flush ruleset

Restart=on-failure
RestartSec=5s
```

This will catch and log config-errors before doing a reload/restart.

----

## Scheduling

You can either:

* Add a Systemd Timer: [example](https://github.com/ansibleguy/addons_nftables/tree/latest/templates/etc/systemd/system)
* Add a cron job

----

## Ansible

Here you can find an Ansible Role to manage NFTables Addons:

* [ansibleguy.addons_nftables](https://github.com/ansibleguy/addons_nftables)
* [examples](https://github.com/ansibleguy/addons_nftables/blob/latest/Example.md)

----

## License

MIT
