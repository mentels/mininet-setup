#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel, info, debug, error
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.util import quietRun
import os
import datetime
import time

DEFAULT_PORT = 8099
SLEEP_SECS = 3
servers = ['mn2']


def runPassiveHosts(pair):
    (no, port, activeHost, passiveHost) = pair
    info('*** Starting pair no: %d \n' % no)
    passiveCmd = formatPairCmd(passiveHost.config)
    passiveHost.cmd(passiveCmd)
    info('Started passive on %s: %s \n' % (passiveHost.name, passiveCmd))


def runActiveHosts(pair):
    (no, port, activeHost, passiveHost) = pair
    activeCmd = formatPairCmd(activeHost.config)
    activeHost.cmd(activeCmd)
    info('Started active on %s: %s \n' % (activeHost.name, activeCmd))


def formatPairCmd(configFile):
    [config_file] = str.split(configFile, '.config')[:-1]
    cmd = 'cd ~/pair/ && ./_rel/pair/bin/pair -config {config} -detached'
    return cmd.format(config=config_file)


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
    generateSysConfig(no, port, activeHost, passiveHost, 1, 'active')
    generateSysConfig(no, port, passiveHost, activeHost, 1, 'passive')


def sysConfigGenScript():
    return os.path.join(os.environ['HOME'], 'pair', 'config_gen')


def pairDir():
    return os.path.join(os.environ['HOME'], 'pair')


def configDir(run_id):
    return os.path.join(pairDir(), 'files', run_id, 'config')


def logDir(run_id):
    return os.path.join(pairDir(), 'files', run_id, 'log')


def logFile(run_id, host_name, no, state):
    pattern = filePattern(host_name, no, state, 'log')
    return os.path.join(logDir(run_id), pattern)


def sysConfigFile(run_id, host_name, no, state):
    pattern = filePattern(host_name, no, state, 'config')
    return os.path.join(configDir(run_id), pattern)


def filePattern(host_name, no, state, ext):
    return '{host_name}-{pair_no}-{state}.{extension}'.format(
      host_name=host_name,
      pair_no=no,
      state=state,
      extension=ext)


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
                           cfg_file=host.config,
                           log_file=host.log)
    output = host.cmd(formatted)
    if output:
        raise ValueError("Failed generating config file on %s: %s"
                         % (host.name, output))


def killPairs(net):
    ip = net.serverIP['mn2']
    dest = '%s@%s' % (net.user, ip)
    cmd = ['sudo', '-E', '-u', net.user]
    cmd += net.sshcmd + ['-n', dest, 'sudo pkill -9 beam']
    info(' '.join(cmd), '\n')
    quietRun(cmd),
    quietRun('pkill -9 beam')


def runRmoteCmd(net, server, raw_cmd):
    dest = '%s@%s' % (net.user, net.serverIP[server])
    cmd = ['sudo', '-E', '-u', net.user]
    cmd += net.sshcmd + ['-n', dest, raw_cmd]
    info(' '.join(cmd), '\n')
    return quietRun(cmd)


def createDirs(run_id, net):
    log_dir = logDir(run_id)
    config_dir = configDir(run_id)
    cmd = 'mkdir -p %s && mkdir -p %s' % (log_dir, config_dir)
    for s in servers:
        output = runRmoteCmd(net, s, cmd)
        if output:
            raise ValueError("Failed to create dirs %s, %s. %s" % (log_dir,
                                                                   config_dir,
                                                                   output))
    output = quietRun(cmd)
    if output:
        raise ValueError("Failed to create dirs %s, %s. %s" % (log_dir,
                                                               config_dir,
                                                               output))


def setUpHostsFiles(run_id, pairs):
    for p in pairs:
        (no, port, activeHost, passiveHost) = p
        activeHost.config = sysConfigFile(run_id, activeHost.name, no,
                                          'active')
        passiveHost.config = sysConfigFile(run_id, passiveHost.name, no,
                                           'passive')
        activeHost.log = logFile(run_id, activeHost.name, no, 'active')
        passiveHost.log = logFile(run_id, passiveHost.name, no, 'passive')


def waitForFinish(pairs):
    finishedPairs = []
    totalPairsNum = len(pairs)
    while pairs:
        doWaitForFinish(pairs, finishedPairs)
        info("**** The %i/%i pairs finished, waiting for the rest..."
             % (len(finishedPairs), totalPairsNum))
        time.sleep(SLEEP_SECS)
    info("**** All the %i pairs finished " % len(finishedPairs))


def doWaitForFinish(pairs, finishedPairs):
    for p in pairs:
        if pairFinished(p):
            finishedPairs.append(p)
            pairs.remove(p)


def pairFinished(pair):
    (no, port, activeHost, passiveHost) = pair
    return hostFinished(activeHost) and hostFinished(passiveHost)


def hostFinished(host):
    output = host.cmd('grep Finished %s' % host.log)
    if output:
        return True
    return False


def run():
    run_id = datetime.datetime.now().isoformat()
    # k switches n hosts
    topo = LinearTopo(k=2, n=10, sopts={'protocols': 'OpenFlow13'})
    controller = RemoteController('c0', ip='192.168.56.1', port=6653)
    net = MininetCluster(topo=topo, servers=['localhost'] + servers,
                         controller=controller)
    net.start()
    createDirs(run_id, net)
    try:
        pairs = designatePairs(net.hosts)
        setUpHostsFiles(run_id, pairs)
        info("**** CURRENT RUN ID: %s\n" % run_id)
        [generatePairSysConfigs(p) for p in pairs]
        [runPassiveHosts(p) for p in pairs]
        [runActiveHosts(p) for p in pairs]
        waitForFinish(pairs)
    except Exception, arg:
        error("ERROR: %s \n" % arg)
    finally:
        net.stop(),
        killPairs(net)
        os.system("pkill -9 beam")
        info("**** FINISHED RUN ID: %s\n" % run_id)

if __name__ == '__main__':
    setLogLevel('info')
    run()
