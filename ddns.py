import json
import os
import argparse
from time import sleep

import requests
import sys

from dnspod import DnsPod
from pprint import pprint

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
        rep = dnspod.Record.List(domain_id=domain_id, sub_domain=sub_domain)
        if int(rep["info"]["record_total"]) != 1:
            raise LookupError()
        rec = rep["records"][0]
        self.record_id = rec["id"]
        if rec["name"] == "@":
            self.fqdn = rep["domain"]["punycode"]
        else:
            self.fqdn = "%s.%s" % (rec["name"], rep["domain"]["punycode"])
        self.value = rec["value"]
        self.name = rec["name"]
        self.line_id = rec["line_id"]

    def __str__(self):
        return "%s(%d:%d)" % (self.fqdn, self.domain_id, self.record_id)

    def ddns(self, ip):
        self.dnspod.Record.Ddns(domain_id=self.domain_id,
                                record_id=self.record_id,
                                sub_domain=self.name,
                                record_line_id=self.line_id,
                                value=ip)
        self.value = ip
        print("%s: updated to %s" % (self.fqdn, ip))


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
    raise LookupError("Fail to lookup the domain name %s" % fqdn)


def getip():
    while True:
        try:
            r = requests.get("http://ip.taobao.com/service/getIpInfo.php?ip=myip")
        except requests.RequestException as ex:
            print("Fail to request public ip. %s", file=sys.stderr)
            print(ex, file=sys.stderr)
            sleep(0.2)  # ip.taobao.com said that they limit the frequency to 10qps, so we have 5qps now
            continue
        return json.loads(r.text)["data"]["ip"]


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
            print("External IP Address: %s" % ip)
            old_ip = ip
        for r in all_records:
            if r.value != ip:
                r.ddns(ip)
        sleep(1)


if __name__ == '__main__':
    main()
