#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel, info, debug
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.util import quietRun
import os
import time

DEFAULT_PORT = 8099


def runPassiveHosts(pair):
    (no, port, activeHost, passiveHost) = pair
    info('*** Starting pair no: %d \n' % no)
    passiveCmd = formatPairCmd(sysConfigFile(no, 'passive'))
    passiveHost.cmd(passiveCmd)
    info('Started passive on %s: %s \n' % (passiveHost.name, passiveCmd))


def runActiveHosts(pair):
    (no, port, activeHost, passiveHost) = pair
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
    generateSysConfig(no, port, activeHost, passiveHost, 50, 'active')
    generateSysConfig(no, port, passiveHost, activeHost, 50, 'passive')


def sysConfigFile(no, state):
    pattern = filePattern(no, state, 'config')
    return os.path.join(os.environ['HOME'], 'pair', 'config',
                        pattern)

def sysConfigGenScript():
    return os.path.join(os.environ['HOME'], 'pair', 'config_gen')


def logFile(no, state):
    pattern = filePattern(no, state, 'log')
    return os.path.join(os.environ['HOME'], 'pair', 'log',
                        pattern)


def filePattern(no, state, ext):
    return 'sys-%d-%s.%s' % (no, state, ext)


def generateSysConfig(no, port, host, peer, iterations, state):
    cmd = '{script} {no} {port} {ip} {peer_ip} {intf} {it} {state} {cfg_file} {log_file}'
    formatted = cmd.format(script=sysConfigGenScript(),
                           no=no,
                           port=port,
                           ip=host.IP(),
                           peer_ip=peer.IP(),
                           intf=host.intfs[0],
                           it=iterations,
                           state=state,
                           cfg_file=sysConfigFile(no, state),
                           log_file=logFile(no, state))
    # info('*** Generating sys.config with %s' % formatted)
    host.cmd(formatted)


def killPairs(net):
    ip  =  net.serverIP['mn2']
    dest = '%s@%s' % ( net.user, ip )
    cmd = [ 'sudo', '-E', '-u', net.user ]
    cmd += net.sshcmd + [ '-n', dest, 'sudo pkill -9 beam' ]
    info( ' '.join( cmd ), '\n' )
    quietRun( cmd ),
    quietRun('pkill -9 beam')

def run():
    servers = ['localhost', 'mn2']
    # k switches n hosts
    topo = LinearTopo(k=2, n=10, sopts={'protocols': 'OpenFlow13'})
    controller = RemoteController('c0', ip='192.168.56.1', port=6653)
    net = MininetCluster(topo=topo, servers=servers, controller=controller)
    net.start()
    pairs = designatePairs(net.hosts)
    [generatePairSysConfigs(p) for p in pairs]
    [runPassiveHosts(p) for p in pairs]
    [runActiveHosts(p) for p in pairs]
    CLI(net)
    net.stop(),
    killPairs(net)
    os.system("pkill -9 beam")

if __name__ == '__main__':
    setLogLevel('info')
    run()
