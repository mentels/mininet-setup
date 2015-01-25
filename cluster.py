#!/usr/bin/python

"clusterdemo.py: demo of Mininet Cluster Edition prototype"

from mininet.examples.cluster import MininetCluster
from mininet.topo import LinearTopo
from mininet.log import setLogLevel
from mininet.node import RemoteController
from mininet.cli import CLI

def run():
    servers = [ 'localhost', 'mn2' ]
    topo = LinearTopo( k=2, n=2, sopts={'protocols' : 'OpenFlow13'} )
    controller = RemoteController( 'c0', ip='192.168.56.1', port = 6653)
    net = MininetCluster( topo=topo, servers=servers, controller=controller )
    net.start()
    CLI( net )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'debug' )
    run()

