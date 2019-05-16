# ddns script for DNSPod

A script to update ddns record using DNSPod API with token authentication

# Dependencies
* requests
* pyroute2 (IPv6 only)

# Usage
## IPv4 (A Record)
```sh
export DNSPOD_TOKEN="TokenId,Token"
./ddns.py xx.xx.com
```

## IPv6 (AAAA Record)
```sh
export DNSPOD_TOKEN="TokenId,Token"
./ddnsv6.py xx.xx.com
```

# Example

```sh
export DNSPOD_TOKEN="47118,79bc899999990000000dd5a20dc9a802"
./ddns.py xx.kxuan.tech
```
