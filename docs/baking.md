<!--
   - SPDX-FileCopyrightText: 2019 TQ Tezos <https://tqtezos.com/>
   -
   - SPDX-License-Identifier: LicenseRef-MIT-TQ
   -->
# Baking with tezos-packaging on Ubuntu

Tezos-packaging provides an easy way to install and set up infrastructure for
interacting with Tezos blockchain.

This article provides a step-by-step guide for setting up baking instance for Tezos on Ubuntu.

## Prerequisites

### Installing required packages

In order to run a baking instance, you'll need the following Tezos binaries:
`tezos-client`, `tezos-node`, `tezos-baker-<proto>`, `tezos-endorser-<proto>`.

Currently used proto's are `007-PsDELPH1` (used on mainnet and delphinet) and
`008-PtEdoTez` (used on edonet). Also, note that the corresponding ubuntu packages have protocol
suffix in lowercase, e.g. list of available baker packages can be found
[here](https://launchpad.net/~serokell/+archive/ubuntu/tezos/+packages?field.name_filter=tezos-baker&field.status_filter=published).

To install them run the following commands:
```
# Add PPA with Tezos binaries
sudo add-apt-repository ppa:serokell/tezos
sudo apt-get update
# Install packages
sudo apt-get install tezos-client tezos-node tezos-baker-<proto> tezos-endorser-<proto>
```

Packages for `tezos-node`, `tezos-baker-<proto>` and `tezos-endorser-<proto>` provide
systemd units for running the corresponding binaries in the background.


<!-- TODO: Should be removed once https://github.com/serokell/tezos-packaging/issues/132 is resolved -->
### Downloading zcash-params

Since v8.0 it's required to have the `sapling-output.params` and `sapling-spend.params` files from
the `zcash-params` within the `XDG_DATA_DIRS` to run the `tezos-node`.

We'll need these params to be accessible by different
users (because `systemd` services are usually run as a separate user), thus the suggested way of getting
them via [the zcash script](https://raw.githubusercontent.com/zcash/zcash/master/zcutil/fetch-params.sh), which will
download them to the `HOME` directory of the current user, is not convenient. Moreover, it will
download the large `sprout-groth16.params` which is unused at runtime.
So, it's better to download them to the `/usr/local/share/zcash-params`, the easiest way to do that
is to run [`fetch-sapling-params.sh`](../scripts/fetch-sapling-params.sh) script:
```
sudo ./fetch-sapling-params.sh
```

Sudo is required because the files are downloaded to the `/usr/local/share/zcash-params`.
This script also checks that hashsums of the downloaded files match the expected values.

## Setting up the tezos-node

The easiest way to set up a node running on the `mainnet` or on one of the
testnets (e.g. `delphinet` or `edonet`) is to use one of the predefined
`tezos-node-<network>.services` systemd services provided in the `tezos-node`
package.

However, by default, these services will start to bootstrap the node from scratch,
which will take a significant amount of time.
In order to avoid this, here we suggest bootstrapping from a snapshot instead.

### Setting up node service

`tezos-node-<network>.service` has `/var/lib/tezos/node-<network>` as a data directory
and `http://localhost:8732` as its RPC address by default.

In case you want to use different data directory or RPC address,
you should update the service configuration. To edit the service configuration run
```
sudo systemctl edit --full tezos-node-<network>.service
```

### Bootstrapping the node

In order to run a baker locally, you'll need a fully-synced local `tezos-node`.

The fastest way to bootstrap the node is to import a snapshot.
Snapshots can be downloaded from the following websites:
* https://snapshots.tulip.tools/#/
* https://snapshots-tezos.giganode.io/
* https://xtz-shots.io/

All commands within the service are run under the `tezos` user.

Download the snapshot for desired network. We recommend to use rolling snapshot, this is
the smallest and the fastest mode that is sufficient for baking (you can read more about other
`tezos-node` history modes [here](https://tezos.gitlab.io/user/history_modes.html#history-modes)).

In order to import the snapshot run the following command:
```
sudo -u tezos tezos-node snapshot import --data-dir /var/lib/tezos/node-<network>/ <path to the snapshot file>
```

#### Troubleshooting node snapshot import

Snapshot import requires that the `tezos-node` data directory doesn't contain the `context` and `store` folders.
Remove them in case you're getting such error about their presence.

In case you're getting an error similar to
```
tezos-node: Error:
              Invalid block BLjutMj47caB
                Failed to validate the economic-protocol content of the block: Error:
                                                                                Invalid signature for block BLjutMj47caB. Expected: tz1Na5QB98cDA.
```

You should init/update config in the data directory to match the desired network
before importing the snapshot. To do that run one of the following commands
depending on whether the config in the given data directory was initialized previously:
```
sudo -u tezos tezos-node config init --data-dir /var/lib/tezos/node-<network> --network <network>
#or
sudo -u tezos tezos-node config update --data-dir /var/lib/tezos/node-<network> --network <network>
```

### Starting the node

After the snapshot import, you can finally start the node by running
```
sudo systemctl start tezos-node-<network>.service
```

Note that even after the snapshot import the node can still be out of sync, it may require
some additional time to completely bootstrap. In order to check whether the node is bootstrapped,
you can use `tezos-client`:
```
tezos-client --endpoint <node-rpc-address> bootstrapped
```

To stop the node run:
```
sudo systemctl stop tezos-node-<network>.service
```

You can check the node logs via `journalctl`:
```
journalctl -u tezos-node-<network>.service
```

## Setting up baker and endorser daemons

### Setting up daemons data directory

Data directories for baker and endorser daemons are defined in the
`/etc/default/tezos-baker-<proto>` and `/etc/default/tezos-endorser-<proto>`. Make
sure to point them at the same directory to have the same set of known keys, e.g.
point both `DATA_DIR`s to `/var/lib/tezos/baker`. You should also
update `NODE_DATA_DIR` in the `/etc/default/tezos-baker-<proto>` to point at the desired
node data directory, e.g. `/var/lib/tezos/node-<network>`.


<!-- TODO: remove once https://github.com/serokell/tezos-packaging/issues/133 is resolved -->
Create the aformentioned daemons data directory:
```
sudo -u tezos mkdir -p /var/lib/tezos/baker
```

### Importing baker key

Import your baker secret key to the data directory. There are two ways to import
such key:
1) You know either the unencrypted or password-encrypted secret key for your address.

In order to import such key run:
```
sudo -u tezos tezos-client -d /var/lib/tezos/baker import secret key <alias> <secret-key>
```
2) The secret key is stored on a ledger.

Open the Tezoz Wallet app on your ledger and run the following
to import the key:
```
sudo -u tezos tezos-client -d /var/lib/tezos/baker import secret key <alias> <ledger-url>
```
Apart from importing the key, you'll also need to set it up for baking. Open Tezos Baking app
on your ledger and run the following:
```
sudo -u tezos tezos-client -d /var/lib/tezos/baker setup ledger to bake for <alias>
```

After importing the key, you'll need to update the `BAKER_ACCOUNT` and `ENDORSER_ACCOUNT` in
`/etc/default/tezos-baker-<proto>` and `/etc/default/tezos-endorser-<proto>` respectively, in
accordance to the alias of the imported key.

### Starting daemons

Once the key is imported and the configs are updated, you can start the baker and endorser daemons:
```
sudo systemctl start tezos-baker-<proto>.service
sudo systemctl start tezos-endorser-<proto>.service
```

If the node isn't bootstrapped yet, baker and endorser daemons will wait for it to bootstrap.

Note that if you're baking with the ledger key, you should have the Tezos Baking app open.
