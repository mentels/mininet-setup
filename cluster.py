#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.cli import CLI
from sets import Set
import random
import string


def setupIperfPair(client, server):
    setupIperfServer(server)
    setupIperfClient(client, server)
    while not checkIperfClientCompleted(client):
        pass
    teardownIperfServer(server)


def setupIperfServer(host):
    cmd = 'iperf -s > %s' % getIperfServerFilename(host)
    host.sendCmd(cmd)


def setupIperfClient(client, server):
    clientCmd = 'iperf -c %s -t 1s' % (server.IP())
    client.sendCmd(clientCmd)


def checkIperfClientCompleted(client):
    if client.waiting:
        client.monitor(timeoutms=200)
        if client.waiting:
            return False
    return True


def teardownIperfServer(server):
    server.sendInt()
    server.waitOutput()


def getIperfServerFilename(server):
    return '%s-%s.iperf-srv' % (server.name, server.IP())


def designateClientsAndServers(hosts):
    servers = []
    clients = []
    for i in range(0, len(hosts) - 1, 2):
        servers.append(hosts[i])
        clients.append(hosts[i+1])
    print "CLIENTS: %s" % string.translate(str(clients), None, "'")
    print "SERVERS: %s" % string.translate(str(servers), None, "'")
    return clients, servers


def loop(runs, clients, servers):
    freeClients = Set(clients)
    runningClients = Set()
    for r in range(0, runs):
        while freeClients:
            c = freeClients.pop()
            runningClients.add(c)
            s = servers[random.randint(0, len(servers) - 1)]
            print "Running: %s:%s -> %s:%s" % (c.name, c.IP(), s.name, s.IP())
            setupIperfClient(c, s)
        freeClients = findFreeClients(clients)
    for c in clients:
        while not checkIperfClientCompleted(c):
            pass


def findFreeClients(clients):
    free = Set()
    while not free:
        for c in clients:
            if not c.waiting:
                free.add(c)
            else:
                c.monitor(timeoutms=300)
    return free


def run():
    servers = ['localhost', 'mn2']
    topo = LinearTopo(k=2, n=4, sopts={'protocols': 'OpenFlow13'})
    controller = RemoteController('c0', ip='192.168.56.1', port=6653)
    net = MininetCluster(topo=topo, servers=servers, controller=controller)
    net.start()
    clients, servers = designateClientsAndServers(net.hosts)
    [setupIperfServer(s) for s in servers]
    loop(50, clients, servers)
    [teardownIperfServer(s) for s in servers]
    # h1 = net.hosts[0]
    # h2 = net.hosts[1]
    # setupIperfPair(h1,h2)
    # setupIperfPair(h2,h1)
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()

