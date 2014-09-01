#!/usr/bin/env python
import sys
import urllib2
import urlparse
import xml.etree.ElementTree as ET
import socket
from telnetlib import Telnet

def search_device(timeout=3):
    payload = """M-SEARCH * HTTP/1.1
MX: %d
HOST: 239.255.255.250:1900
MAN: "ssdp:discover"
ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1

""" % timeout
    payload = payload.replace('\n', '\r\n')

    print >>sys.stderr, "[+] searching device...",

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)
    s.sendto(payload, ('239.255.255.250', 1900))
    try:
        data, addr = s.recvfrom(8192)
    except socket.timeout:
        print >>sys.stderr, "timeout error"
        sys.exit(1)
    s.close()
    for line in data.splitlines():
        kv = line.split(':', 1)
        if kv[0] == 'Location':
            location = kv[1].strip()
            break
    else:
        print >>sys.stderr, "location not found"
        sys.exit(1)

    print >>sys.stderr, location
    return location

def get_internal_ip_address(location):
    print >>sys.stderr, "[+] getting internal ip address...",

    u = urlparse.urlsplit(location)
    location_ip = u.netloc.split(':')[0]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((location_ip, 80))
    in_ip = s.getsockname()[0]
    s.close()

    print >>sys.stderr, in_ip
    return in_ip

def get_control_url(location):
    namespaces = dict(x='urn:schemas-upnp-org:device-1-0')
    path_control_url = './/x:service[x:serviceType="urn:schemas-upnp-org:service:WANPPPConnection:1"]/x:controlURL'

    print >>sys.stderr, "[+] getting control_url...",

    f = urllib2.urlopen(location)
    data = f.read()
    f.close()
    root = ET.fromstring(data)
    control_url = root.findall(path_control_url, namespaces)[0].text
    control_url = urlparse.urljoin(location, control_url)

    print >>sys.stderr, control_url
    return control_url

def get_external_ip_address(control_url):
    headers = {'Content-Type': 'text/xml; charset="utf-8"', 'SOAPACTION': '"urn:schemas-upnp-org:service:WANPPPConnection:1#GetExternalIPAddress"'}
    payload = """<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <SOAP-ENV:Body>
    <m:GetExternalIPAddress xmlns:m="urn:schemas-upnp-org:service:WANPPPConnection:1">
    </m:GetExternalIPAddress>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
"""
    namespaces = dict(x='urn:schemas-upnp-org:service:WANPPPConnection:1')
    path_new_external_ip_address = './/x:GetExternalIPAddressResponse/NewExternalIPAddress'

    print >>sys.stderr, "[+] getting external ip address...",

    req = urllib2.Request(control_url, payload, headers)
    f = urllib2.urlopen(req)
    code = f.getcode()
    data = f.read()
    f.close()
    if code != 200:
        print >>sys.stderr, "[!] get_external_ip_address error: %d" % code
        sys.exit(1)
    root = ET.fromstring(data)
    ex_ip = root.findall(path_new_external_ip_address, namespaces)[0].text

    print >>sys.stderr, ex_ip
    return ex_ip

def add_port_mapping(control_url, ex_addr, in_addr, duration=0):
    headers = {'Content-Type': 'text/xml; charset="utf-8"', 'SOAPACTION': '"urn:schemas-upnp-org:service:WANPPPConnection:1#AddPortMapping"'}
    payload = """<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV:="http://schemas.xmlsoap.org/soap/envelope/" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <SOAP-ENV:Body>
    <m:AddPortMapping xmlns:m="urn:schemas-upnp-org:service:WANPPPConnection:1">
      <NewRemoteHost></NewRemoteHost>
      <NewExternalPort>%d</NewExternalPort>
      <NewProtocol>TCP</NewProtocol>
      <NewInternalPort>%d</NewInternalPort>
      <NewInternalClient>%s</NewInternalClient>
      <NewEnabled>1</NewEnabled>
      <NewPortMappingDescription>upnpbind</NewPortMappingDescription>
      <NewLeaseDuration>%d</NewLeaseDuration>
    </m:AddPortMapping>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>""" % (ex_addr[1], in_addr[1], in_addr[0], duration)

    print >>sys.stderr, "[+] add_port_mapping: %r -> %r" % (ex_addr, in_addr)

    req = urllib2.Request(control_url, payload, headers)
    f = urllib2.urlopen(req)
    code = f.getcode()
    f.close()
    if code != 200:
        print >>sys.stderr, "[!] add_port_mapping error: %d" % code
        sys.exit(1)
    return

def delete_port_mapping(control_url, ex_addr):
    headers = {'Content-Type': 'text/xml; charset="utf-8"', 'SOAPACTION': '"urn:schemas-upnp-org:service:WANPPPConnection:1#DeletePortMapping"'}
    payload = """<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV:="http://schemas.xmlsoap.org/soap/envelope/" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
  <SOAP-ENV:Body>
    <m:DeletePortMapping xmlns:m="urn:schemas-upnp-org:service:WANPPPConnection:1">
      <NewRemoteHost></NewRemoteHost>
      <NewExternalPort>%d</NewExternalPort>
      <NewProtocol>TCP</NewProtocol>
    </m:DeletePortMapping>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>""" % ex_addr[1]

    print >>sys.stderr, "[+] delete_port_mapping: %r" % (ex_addr,)

    req = urllib2.Request(control_url, payload, headers)
    f = urllib2.urlopen(req)
    code = f.getcode()
    f.close()
    if code != 200:
        print >>sys.stderr, "[!] delete_port_mapping error: %d" % code
        sys.exit(1)
    return

def upnpbind(ex_port=None):
    location = search_device()
    in_ip = get_internal_ip_address(location)
    control_url = get_control_url(location)
    ex_ip = get_external_ip_address(control_url)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((in_ip, 0))
    s.listen(1)
    in_addr = s.getsockname()
    if ex_port:
        ex_addr = (ex_ip, ex_port)
    else:
        ex_addr = (ex_ip, in_addr[1])
    print >>sys.stderr, "[+] bind: %r" % (in_addr,)

    add_port_mapping(control_url, ex_addr, in_addr)

    try:
        c, remote_addr = s.accept()
        print >>sys.stderr, "[+] accept: %r" % (remote_addr,)
        s.close()

        t = Telnet()
        t.sock = c
        t.interact()
        t.close()
    finally:
        delete_port_mapping(control_url, ex_addr)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ex_port = int(sys.argv[1])
        upnpbind(ex_port)
    else:
        upnpbind()
