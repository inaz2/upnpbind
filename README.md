# upnpbind

TCP bind over NAT by using UPnP IGD Protocol

```
$ python upnpbind.py 80
[+] searching device... http://192.168.0.1:5432/upnp/rootdevice.xml
[+] getting internal ip address... 192.168.0.2
[+] getting control_url... http://192.168.0.1:5432/upnp/control/WANPPPConn1
[+] getting external ip address... 198.51.100.10
[+] bind: ('192.168.0.2', 52015)
[+] add_port_mapping: ('198.51.100.10', 80) -> ('192.168.0.2', 52015)
[+] accept: ('203.0.113.20', 26346)
GET / HTTP/1.1
User-Agent: curl/7.33.0
Host: 198.51.100.10
Accept: */*

*** Connection closed by remote host ***
[+] delete_port_mapping: ('198.51.100.10', 80)
```
