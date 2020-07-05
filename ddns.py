import json
import os
import argparse
import re
from time import sleep
import requests
import sys
from dnspod import DnsPod

all_domains = []
records = []

class Record:
    dnspod = None
    domain_id = 0
    record_id = 0
    fqdn = ""
    value = ""
    name = ""
    line_id = ""

    def __init__(self, dnspod, domain_id, sub_domain):
        self.dnspod = dnspod
        self.domain_id = domain_id
        rep = dnspod.Record.List(domain_id=domain_id, sub_domain=sub_domain, record_type="A")
        if int(rep["info"]["record_total"]) != 1:
            raise LookupError()
        rec = rep["records"][0]
        self.record_id = rec["id"]
        if rec["name"] == "@":
            self.fqdn = rep["domain"]["punycode"]
        else:
            self.fqdn = "{}.{}".format(rec["name"], rep["domain"]["punycode"])
        self.value = rec["value"]
        self.name = rec["name"]
        self.line_id = rec["line_id"]

    def __str__(self):
        return "{}({:d}:{:d})".format(self.fqdn, self.domain_id, self.record_id)

    def ddns(self, ip):
        self.dnspod.Record.Ddns(domain_id=self.domain_id,
                                record_id=self.record_id,
                                sub_domain=self.name,
                                record_line_id=self.line_id,
                                value=ip)
        self.value = ip
        print("{}: updated to {}".format(self.fqdn, ip))


def parse_fqdn(dnspod, all_domains, fqdn):
    """

    :param dnspod:
    :param all_domains:
    :param str fqdn:
    :return:
    """
    for d in all_domains:
        if d["name"] == fqdn:
            return Record(dnspod, d["id"], "@")
        if not fqdn.endswith("." + d["name"]):
            continue
        sub_domain = fqdn[0:len(fqdn) - len(d["name"]) - 1]
        try:
            return Record(dnspod, d["id"], sub_domain)
        except LookupError:
            continue
    raise LookupError("Fail to lookup the domain name {}".format(fqdn))

def getip_taobao():
    try:
        r = requests.get("http://ip.taobao.com/service/getIpInfo.php?ip=myip",timeout=3)
        return json.loads(r.text)["data"]["ip"]
    except json.decoder.JSONDecodeError as ex:
        print("taobao: json decode error: ", r.text)
        print(ex, file=sys.stderr)
    except requests.RequestException as ex:
        print("Error on ip.taobao.com:", file=sys.stderr)
        print(ex, file=sys.stderr)
    return None

def getip_ipcn():
    try:
        r= requests.get("http://ip.cn",headers={
            "User-Agent":"curl/0.ddns (kxuanobj@gmail.com)"
        },timeout=3)
        m = re.search("：(.+?)\s",r.text)
        if m is None:
            return None
        return m.group(1)
    except Exception as ex:
        print("ipcn Error", file=sys.stderr)
        print(ex,file=sys.stderr)
    return None

def getip_cip():
    try:
        r= requests.get("http://cip.cc",headers={
            "User-Agent":"curl"
        },timeout=3)
        m=r.text.split("\n")
        for line in m:
            if line.startswith("IP"):
                return line[line.index(":")+1:].strip()
    except Exception as ex:
        print("cip Error", file=sys.stderr)
        print(ex,file=sys.stderr)
    return None

ip_candidates=[getip_ipcn, getip_cip]
def getip():
    while True:
        for fn in ip_candidates:
            ip=fn()
            if ip is not None:
                return ip
        print("All candidate fails, retry in 1 minute")
        sleep(60)

def parse_args():
    parser = argparse.ArgumentParser(description="DDns Script for dnspod")
    parser.add_argument('domains', metavar="domain", type=str, nargs='+', help="Domains to update")
    return parser.parse_args()


def main():
    if "DNSPOD_TOKEN" not in os.environ:
        print("You should provider the user's token by environment variable \"DNSPOD_TOKEN\"")
        exit(1)

    args = parse_args()

    dnspod = DnsPod(os.environ["DNSPOD_TOKEN"])
    print("Listing domains...")
    all_domains = dnspod.Domain.List()["domains"]
    print("Finding records...")
    all_records = [parse_fqdn(dnspod, all_domains, fqdn) for fqdn in args.domains]

    old_ip=""
    while True:
        ip = getip()
        if old_ip != ip:
            print("External IP Address: {}".format(ip))
            old_ip = ip
        for r in all_records:
            if r.value != ip:
                r.ddns(ip)
        sleep(60)


if __name__ == '__main__':
    main()
