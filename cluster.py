#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel, info, debug
from mininet.node import RemoteController
from mininet.cli import CLI
import os
import time

DEFAULT_PORT = 8099


def runPair(pair):
    (no, port, activeHost, passiveHost) = pair
    info('*** Starting pair no: %d \n' % no)
    passiveCmd = formatPairCmd(sysConfigFile(no, 'passive'))
    passiveHost.cmd(passiveCmd)
    info('Started passive on %s: %s \n' % (passiveHost.name, passiveCmd))
    activeCmd = formatPairCmd(sysConfigFile(no, 'active'))
    activeHost.cmd(activeCmd)
    info('Started active on %s: %s \n' % (activeHost.name, activeCmd))


def formatPairCmd(configFile):
    [stripped, rest] = str.split(configFile, '.')
    cmd = 'cd ~/pair/ && ./_rel/pair/bin/pair -config {config} -detached'
    return cmd.format(config=stripped)


def designatePairs(hosts):
    pairs = []
    pair_no = 1
    for i in range(0, len(hosts) - 1, 2):
        pair = (pair_no, DEFAULT_PORT, hosts[i], hosts[i+1])
        pairs.append(pair)
        pair_no += 1
    return pairs


def generatePairSysConfigs(pair):
    (no, port, activeHost, passiveHost) = pair
    generateSysConfig(no, port, activeHost, passiveHost, 10, 'active')
    generateSysConfig(no, port, passiveHost, activeHost, 10, 'passive')


def sysConfigFile(no, state):
    pattern = filePattern(no, state, 'config')
    return os.path.join(os.environ['HOME'], 'pair', 'config',
                        pattern)


def logFile(no, state):
    pattern = filePattern(no, state, 'log')
    return os.path.join(os.environ['HOME'], 'pair', 'log',
                        pattern)


def filePattern(no, state, ext):
    return 'sys-%d-%s.%s' % (no, state, ext)


def generateSysConfig(no, port, host, peer, iterations, state):
    cfg = '[(pair,\n{pair_cfg}),\n(lager,\n{lager_cfg})].\n'
    pair_cfg = pairConfig(no, port, host, peer, iterations, state)
    lager_cfg = lagerConfig(no, state)
    formatted = cfg.format(pair_cfg=pair_cfg, lager_cfg=lager_cfg)
    formatted = formatted.replace('(', '{').replace(')', '}')
    with open(sysConfigFile(no, state), 'w') as f:
        f.write(formatted)


def pairConfig(no, port, host, peer, iterations, state):
    cfg = '[(pair_no, {no}), \n\
(port, {port}), \n\
(ip, "{ip}"), \n\
(peer_ip, "{peer_ip}"), \n\
(intf_name, \'{intf}\'), \n\
(iterations, {it}), \n\
(state, {state})]'
    return cfg.format(no=no,
                      port=port,
                      ip=host.IP(),
                      peer_ip=peer.IP(),
                      intf=host.intfs[0],
                      it=iterations,
                      state=state)


def lagerConfig(no, state):
    cfg = '[(handlers, [\n\
(lager_file_backend, [(file, "{log_file}"), (level, info)])])]'
    return cfg.format(log_file=logFile(no, state))


def run():
    servers = ['localhost']  # , 'mn2']
    # k switches n hosts
    topo = LinearTopo(k=1, n=2, sopts={'protocols': 'OpenFlow13'})
    controller = RemoteController('c0', ip='192.168.56.1', port=6653)
    net = MininetCluster(topo=topo, servers=servers, controller=controller)
    net.start()
    pairs = designatePairs(net.hosts)
    [generatePairSysConfigs(p) for p in pairs]
    [runPair(p) for p in pairs]
    CLI(net)
    net.stop(),
    os.system("pkill -9 beam")

if __name__ == '__main__':
    setLogLevel('info')
    run()
