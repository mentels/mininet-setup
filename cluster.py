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
import socket
import argparse

DEFAULT_PORT = 8099
SLEEP_SECS = 3
CTRL_CMD_REMOTE_PORT = 6753
CTRL_CMD_LOCAL_PORT = 6853


def runPassiveHosts(pair):
    (no, port, activeHost, passiveHost) = pair
    info('*** Starting pair no: %d \n' % no)
    passiveCmd = formatPairCmd(passiveHost.config)
    output = passiveHost.cmd(passiveCmd)
    if output:
        raise ValueError("Failed to start passive host %s: %s"
                         % (passiveHost.name, output))
    info('Started passive on %s: %s \n' % (passiveHost.name, passiveCmd))


def runActiveHosts(pair):
    (no, port, activeHost, passiveHost) = pair
    activeCmd = formatPairCmd(activeHost.config)
    output = activeHost.cmd(activeCmd)
    if output:
        raise ValueError("Failed to start active host %s: %s"
                         % (activeHost.name, output))
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


def generatePairSysConfigs(pair, iterations):
    (no, port, activeHost, passiveHost) = pair
    generateSysConfig(no, port, activeHost, passiveHost, iterations, 'active')
    generateSysConfig(no, port, passiveHost, activeHost, iterations, 'passive')


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


def killPairs(net, servers):
    for s in servers:
        if s == "localhost":
            quietRun('pkill -9 beam')
        else:
            ip = net.serverIP[s]
            dest = '%s@%s' % (net.user, ip)
            cmd = ['sudo', '-E', '-u', net.user]
            cmd += net.sshcmd + ['-n', dest, 'sudo pkill -9 beam']
            info(' '.join(cmd), '\n')
            quietRun(cmd),


def runRmoteCmd(net, server, raw_cmd):
    dest = '%s@%s' % (net.user, net.serverIP[server])
    cmd = ['sudo', '-E', '-u', net.user]
    cmd += net.sshcmd + ['-n', dest, raw_cmd]
    info(' '.join(cmd), '\n')
    return quietRun(cmd)


def createDirs(run_id, net, servers):
    log_dir = logDir(run_id)
    config_dir = configDir(run_id)
    cmd = 'mkdir -p %s && mkdir -p %s' % (log_dir, config_dir)
    for s in servers:
        if s == 'localhost':
            continue
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


def waitForFinish(pairs, sleep_secs):
    finishedPairs = []
    totalPairsNum = len(pairs)
    while pairs:
        doWaitForFinish(pairs, finishedPairs)
        info("**** The %i/%i pairs finished, waiting for the rest...\n"
             % (len(finishedPairs), totalPairsNum))
        time.sleep(sleep_secs)
    info("**** All the %i pairs finished\n" % len(finishedPairs))


def doWaitForFinish(pairs, finishedPairs):
    for p in pairs:
        if pairFinished(p):
            finishedPairs.append(p)
            pairs.remove(p)


def pairFinished(pair):
    (no, port, activeHost, passiveHost) = pair
    return hostFinished(activeHost)


def hostFinished(host):
    output = host.cmd('grep Finished %s' % host.log)
    if output:
        return True
    return False


def ensurePassiveStarted(pair, sleep_secs):
    (no, port, activeHost, passiveHost) = pair
    output = ""
    while not output:
        output = passiveHost.cmd('grep -s "pair started" %s\n'
                                 % passiveHost.log)
        debug('***** Starting %s output: %s' % (passiveHost, output))
        if not output:
            info('*** Waiting for host %s to start...\n' % passiveHost.name)
            time.sleep(sleep_secs)


def setupControlerCommandChannel(local_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", local_port))
    sock.settimeout(10.0)
    return sock


def ctrlPrepare(sock, run_id, ctrl_ip, remote_port):
    sock.sendto("prepare/%s" % run_id, (ctrl_ip, remote_port))
    msg = sock.recvfrom(1024)
    if msg != "ready":
        ValueError("Failed to prepare controller")


def teardownController(sock, ctrl_ip, run_id):
    sock.sendto("stop/%s" % run_id, (ctrl_ip, CTRL_CMD_REMOTE_PORT))
    msg = sock.recvfrom(1024)
    if msg != "stopped":
        ValueError("Failed to stop controller")


def mk_run_id(args):
    run_id = ('{tmstmp}-mh:{mn_hosts}-c:{containers}-sw:{switches}-it:{it}' +
              '-m:{mode}-sch:{schedulers_online}')
    return run_id.format(tmstmp=datetime.datetime.now().isoformat(),
                         mn_hosts=len(args.mn_hosts),
                         containers=args.hosts,
                         switches=args.switches,
                         it=args.iterations,
                         mode=args.mode,
                         schedulers_online=args.schedulers_online)


def run(args):
    run_id = mk_run_id(args)
    sock = setupControlerCommandChannel(args.ctrl_cmd_local_port)
    ctrlPrepare(sock, run_id, args.ctrl_ip, args.ctrl_cmd_port)
    # k switches n hosts
    topo = LinearTopo(k=args.switches, n=args.hosts,
                      sopts={'protocols': 'OpenFlow13'})
    controller = RemoteController('c0', ip=args.ctrl_ip,
                                  port=args.ctrl_of_port)
    net = MininetCluster(topo=topo, servers=args.mn_hosts,
                         controller=controller)
    net.start()
    createDirs(run_id, net, args.mn_hosts)
    try:
        pairs = designatePairs(net.hosts)
        setUpHostsFiles(run_id, pairs)
        info("**** CURRENT RUN ID: %s\n" % run_id)
        [generatePairSysConfigs(p, args.iterations) for p in pairs]
        [runPassiveHosts(p) for p in pairs]
        [ensurePassiveStarted(p, args.sleep_time) for p in pairs]
        [runActiveHosts(p) for p in pairs]
        waitForFinish(pairs, args.sleep_time)
    except Exception, arg:
        error("ERROR: %s \n" % arg)
    finally:
        net.stop(),
        killPairs(net, args.mn_hosts)
        os.system("pkill -9 beam")
        teardownController(sock, args.ctrl_ip, run_id)
        info("**** FINISHED RUN ID: %s\n" % run_id)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test Loom Switch')
    parser.add_argument('--ctrl-ip', default='192.168.56.1')
    parser.add_argument('--ctrl-of-port', type=int, default=6653)
    parser.add_argument('--ctrl-cmd-port', type=int, default=6753)
    parser.add_argument('--ctrl-cmd-local-port', type=int, default=6853)
    parser.add_argument('--mn-hosts', nargs='+', default=["localhost"])
    parser.add_argument('--switches', default=2, type=int)
    parser.add_argument('--hosts', default=10, type=int)
    parser.add_argument('--sleep-time', default=3, type=int)
    parser.add_argument('--iterations', default=50, type=int)
    parser.add_argument('--mode', default='regular')
    parser.add_argument('--schedulers-online', default="default")
    setLogLevel('info')
    run(parser.parse_args())
