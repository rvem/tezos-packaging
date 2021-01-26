# SPDX-FileCopyrightText: 2020 TQ Tezos <https://tqtezos.com/>
#
# SPDX-License-Identifier: LicenseRef-MIT-TQ
import os, shutil, sys, subprocess, json

from .model import Service, ServiceFile, SystemdUnit, Unit, Package

networks = ["mainnet", "delphinet", "edonet"]

signer_units = [
    SystemdUnit(
        ServiceFile(Unit(after=["network.target"],
                         description="Tezos signer daemon running over TCP socket"),
                    Service(environment_file="/etc/default/tezos-signer-tcp",
                            environment=["ADDRESS=127.0.0.1", "PORT=8000", "TIMEOUT=1"],
                            exec_start="/usr/bin/tezos-signer-start launch socket signer " \
                            + " --address ${ADDRESS} --port ${PORT} --timeout ${TIMEOUT}",
                            state_directory="tezos", user="tezos")),
        suffix="tcp",
        startup_script="tezos-signer-start",
        config_file="tezos-signer.conf"),
    SystemdUnit(
        ServiceFile(Unit(after=["network.target"],
                         description="Tezos signer daemon running over UNIX socket"),
                    Service(environment_file="/etc/default/tezos-signer-unix",
                            environment=["SOCKET="],
                            exec_start="/usr/bin/tezos-signer-start launch local signer " \
                            + "--socket ${SOCKET}",
                            state_directory="tezos", user="tezos")),
        suffix="unix",
        startup_script="tezos-signer-start",
        config_file="tezos-signer.conf"),
    SystemdUnit(
        ServiceFile(Unit(after=["network.target"],
                         description="Tezos signer daemon running over HTTP"),
                    Service(environment_file="/etc/default/tezos-signer-http",
                            environment=["CERT_PATH=", "KEY_PATH=", "ADDRESS=127.0.0.1", "PORT=8080"],
                            exec_start="/usr/bin/tezos-signer-start launch http signer " \
                            + "--address ${ADDRESS} --port ${PORT}",
                            state_directory="tezos", user="tezos")),
        suffix="http",
        startup_script="tezos-signer-start",
        config_file="tezos-signer.conf"),
    SystemdUnit(
        ServiceFile(Unit(after=["network.target"],
                         description="Tezos signer daemon running over HTTPs"),
                    Service(environment_file="/etc/default/tezos-signer-https",
                            environment=["CERT_PATH=", "KEY_PATH=", "ADDRESS=127.0.0.1", "PORT=8080"],
                            exec_start="/usr/bin/tezos-signer-start launch https signer " \
                            + "${CERT_PATH} ${KEY_PATH} --address ${ADDRESS} --port ${PORT}",
                            state_directory="tezos", user="tezos")),
        suffix="https",
        startup_script="tezos-signer-start",
        config_file="tezos-signer.conf")
]

packages = [
    Package("tezos-client",
            "CLI client for interacting with tezos blockchain",
            optional_opam_deps=["tls", "ledgerwallet-tezos"]),
    Package("tezos-admin-client",
            "Administration tool for the node",
            optional_opam_deps=["tls"]),
    Package("tezos-signer",
            "A client to remotely sign operations or blocks",
            optional_opam_deps=["tls", "ledgerwallet-tezos"],
            systemd_units=signer_units),
    Package("tezos-codec",
            "A client to decode and encode JSON")
]

node_units = []
for network in networks:
    env = [f"DATA_DIR=/var/lib/tezos/node-{network}", f"NETWORK={network}", "NODE_RPC_ADDR=127.0.0.1:8732",
           "CERT_PATH=", "KEY_PATH="]
    service_file = ServiceFile(Unit(after=["network.target"], requires=[],
                                    description=f"Tezos node {network}"),
                               Service(environment=env,
                                       exec_start="/usr/bin/tezos-node-start",
                                       state_directory="tezos", user="tezos"
                                   ))
    node_units.append(SystemdUnit(suffix=network,
                                  service_file=service_file,
                                  startup_script="tezos-node-start"))

node_units.append(SystemdUnit(suffix="custom",
                              service_file=ServiceFile(
                                  Unit(after=["network.target"], requires=[],
                                       description=f"Tezos node with custom config"),
                                  Service(environment=[
                                      "DATA_DIR=/var/lib/tezos/node-custom",
                                      "NODE_RPC_ADDR=127.0.0.1:8732",
                                      "CERT_PATH=", "KEY_PATH=",
                                      "CUSTOM_NODE_CONFIG="],
                                          exec_start="/usr/bin/tezos-node-start",
                                          state_directory="tezos", user="tezos")),
                              startup_script="tezos-node-start"))

packages.append(Package("tezos-node",
                        "Entry point for initializing, configuring and running a Tezos node",
                        node_units))

active_protocols = json.load(open(f"{os.path.dirname( __file__)}/../../protocols.json", "r"))["active"]

daemons = ["baker", "accuser", "endorser"]

daemon_decs = {
    "baker": "daemon for baking",
    "accuser": "daemon for accusing",
    "endorser": "daemon for endorsing"
}

default_testnets = {
    "007-PsDELPH1": "delphinet",
    "008-PtEdoTez": "edonet"
}

for proto in active_protocols:
    service_file_baker = ServiceFile(Unit(after=["network.target"],
                                          description="Tezos baker"),
                                     Service(environment_file=f"/etc/default/tezos-baker-{proto}",
                                             environment=[f"PROTOCOL={proto}"],
                                             exec_start="/usr/bin/tezos-baker-start",
                                             state_directory="tezos", user="tezos"))
    service_file_accuser = ServiceFile(Unit(after=["network.target"],
                                            description="Tezos accuser"),
                                       Service(environment_file=f"/etc/default/tezos-accuser-{proto}",
                                               environment=[f"PROTOCOL={proto}"],
                                               exec_start="/usr/bin/tezos-accuser-start",
                                               state_directory="tezos", user="tezos"))
    service_file_endorser = ServiceFile(Unit(after=["network.target"],
                                             description="Tezos endorser"),
                                        Service(environment_file=f"/etc/default/tezos-endorser-{proto}",
                                                environment=[f"PROTOCOL={proto}"],
                                                exec_start="/usr/bin/tezos-endorser-start",
                                                state_directory="tezos", user="tezos"))
    packages.append(Package(f"tezos-baker-{proto}", "Daemon for baking",
                            [SystemdUnit(service_file=service_file_baker,
                                         startup_script="tezos-baker-start",
                                         config_file="tezos-baker.conf")],
                            proto,
                            optional_opam_deps=["tls", "ledgerwallet-tezos"]))
    packages.append(Package(f"tezos-accuser-{proto}", "Daemon for accusing",
                            [SystemdUnit(service_file=service_file_accuser,
                                         startup_script="tezos-accuser-start",
                                         config_file="tezos-accuser.conf")],
                            proto,
                            optional_opam_deps=["tls", "ledgerwallet-tezos"]))
    packages.append(Package(f"tezos-endorser-{proto}", "Daemon for endorsing",
                            [SystemdUnit(service_file=service_file_endorser,
                                         startup_script="tezos-endorser-start",
                                         config_file="tezos-endorser.conf")],
                            proto,
                            optional_opam_deps=["tls", "ledgerwallet-tezos"]))

