#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel
from mininet.node import RemoteController, Node
from mininet.cli import CLI
from time import time
from select import poll, POLLIN

def setupIperfPair(client, server):
    setupIperfServer(server)
    setupIperfClient(client, server)
    while not checkIperfClientCompleted(client):
        pass
    teardownIperfServer(server)

def setupIperfServer(host):
    serverFile = getIperfServerFilename(host)
    cmd = 'touch %s && iperf -s -u -l 1470' % serverFile
    host.sendCmd(cmd)

def setupIperfClient(client, server):
    outFile = getIperfServerFilename(server)
    header  = '== SRC:%s DST:%s ==' % (client.IP(), server.IP())
    headerCmd = 'echo %s >> %s' % (header, outFile)
    clientCmd = 'iperf -c %s -u -l 1470 -b 1m >> %s' % (server.IP(), outFile)
    client.sendCmd('%s && %s' % (headerCmd, clientCmd))

def checkIperfClientCompleted(client):
    client.monitor()
    if client.waiting:
        return False
    return True

def teardownIperfServer(server):
    server.sendInt()

def getIperfServerFilename(server):
    return '%s-%s.iperf' % (server.name, server.IP())

def run():
    servers = [ 'localhost', 'mn2' ]
    topo = LinearTopo( k=2, n=2, sopts={'protocols' : 'OpenFlow13'} )
    controller = RemoteController( 'c0', ip='192.168.56.1', port = 6653)
    net = MininetCluster( topo=topo, servers=servers, controller=controller )
    net.start()
    h1 = net.hosts[0]
    h2 = net.hosts[1]
    setupIperfPair(h1,h2)
    CLI (net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'debug' )
    run()

