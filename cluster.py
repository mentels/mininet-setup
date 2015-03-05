#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.cli import CLI


def setupPair(pair):
    (no, activeHost, passiveHost) = pair
    activeCmd = formatPairCmd(activeHost, passiveHost, 'active', no)
    passiveCmd = formatPairCmd(passiveHost, activeHost, 'passive', no)
    passiveHost.cmd(passiveCmd)
    activeHost.cmd(activeCmd)


def formatPairCmd(host, peer, state, no):
    cmd = 'cd pair && make dev state={state} ip="{ip}" \
    peer_ip="{peer_ip}" pair_no={no} it={it} intf={intf}'
    return cmd.format(state=state,
                      ip=host.IP(),
                      peer_ip=peer.IP(),
                      no=no,
                      it=10,
                      intf=host.intfs[0].str())


def designatePairs(hosts):
    pairs = []
    pair_no = 1
    for i in range(0, len(hosts) - 1, 2):
        pair = (pair_no, hosts([i]), hosts[i+1])
        pairs.append(pair)
        pair_no += 1
    return pairs


def run():
    servers = ['localhost', 'mn2']
    topo = LinearTopo(k=2, n=4, sopts={'protocols': 'OpenFlow13'})
    controller = RemoteController('c0', ip='192.168.56.1', port=6653)
    net = MininetCluster(topo=topo, servers=servers, controller=controller)
    net.start()
    pairs = designatePairs(net.hosts)
    [setupPair(p) for p in pairs]
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
