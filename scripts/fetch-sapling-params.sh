#! /usr/bin/env bash
# SPDX-FileCopyrightText: 2021 TQ Tezos <https://tqtezos.com/>
#
# SPDX-License-Identifier: LicenseRef-MIT-TQ

# This script is an alternative for
# https://raw.githubusercontent.com/zcash/zcash/master/zcutil/fetch-params.sh.
# This script downloads only `sapling-*.params` files to the `/usr/local/share/zcash-params`,
# so that the downloaded files can be used by different users. Since it downloads files
# to `/usr/local/share`, it should be run with sudo.
set -euo pipefail

if [ "$EUID" -ne 0 ]; then 
        echo "This script requires root privileges."
        echo "Please run it again with sudo or as root."
        exit 1
fi

sapling_spend_hash="8e48ffd23abb3a5fd9c5589204f32d9c31285a04b78096ba40a79b75677efc13"
sapling_output_hash="2f0ebbcbb9bb0bcffe95a397e7eba89c29eb4dde6191c339db88570e3f3fb0e4"

sudo mkdir -p /usr/local/share/zcash-params
sudo wget https://gitlab.com/tezos/opam-repository/-/raw/v8.1/zcash-params/sapling-output.params \
     -O /usr/local/share/zcash-params/sapling-output.params
sudo wget https://gitlab.com/tezos/opam-repository/-/raw/v8.1/zcash-params/sapling-spend.params \
     -O /usr/local/share/zcash-params/sapling-spend.params
echo "$sapling_spend_hash /usr/local/share/zcash-params/sapling-spend.params" | sha256sum --check
echo "$sapling_output_hash /usr/local/share/zcash-params/sapling-output.params" | sha256sum --check
