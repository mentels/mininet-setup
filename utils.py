#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel
from mininet.node import RemoteController, Node
from mininet.cli import CLI
from time import time
from select import poll, POLLIN

def cmd_ping(h1, h2):
    poller = poll()
    poller.register(h1.stdout.fileno(), POLLIN)
    endTime = time() + 10
    print h1.cmd('ping %s &' % h2.IP())
    while time() < endTime:
        readable = poller.poll(1000)
        for fd, _mask in readable:
            node = Node.outToNode[ fd ]
            print '%s:' % node.name, node.monitor().strip()

def send_cmd_ping(h1, h2):
    poller = poll()
    poller.register(h1.stdout.fileno(), POLLIN)
    endTime = time() + 10
    print h1.sendCmd('ping -c 5 %s' % h2.IP())
    while h1.waiting:
        readable = poller.poll(1000)
        for fd, _mask in readable:
            node = Node.outToNode[ fd ]
            print '%s:' % node.name, node.monitor().strip()

def interrupt_send_cmd_ping(h1, h2):
    poller = poll()
    poller.register(h1.stdout.fileno(), POLLIN)
    print h1.sendCmd('ping  %s' % h2.IP())
    endTime = time() + 3
    while True:
        if time() > endTime:
            h1.sendInt()
            break
        h1.monitor(timeoutms=500)
print "h1.waiting = %s" % h1.waiting

def run():
    servers = [ 'localhost', 'mn2' ]
    topo = LinearTopo( k=2, n=2, sopts={'protocols' : 'OpenFlow13'} )
    controller = RemoteController( 'c0', ip='192.168.56.1', port = 6653)
    net = MininetCluster( topo=topo, servers=servers, controller=controller )
    net.start()
    h1 = net.hosts[0]
    h2 = net.hosts[1]
    setupIperfPair(h1,h2)
    # CLI (net)
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'debug' )
    run()
