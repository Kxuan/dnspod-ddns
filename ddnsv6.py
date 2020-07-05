import os
import argparse
import socket
from time import sleep

import sys

from dnspod import DnsPod
import pyroute2
import pyroute2.netlink.rtnl

all_domains = []
records = []
ipr = pyroute2.IPRoute()


class Record:
    dnspod = None
    domain_id = 0
    record_id = 0
    line_id = 0
    fqdn = ""
    sub_domain = ""

    def __init__(self, dnspod, fqdn, domain_id, sub_domain, record_id, line_id):
        self.dnspod = dnspod
        self.fqdn = fqdn
        self.domain_id = domain_id
        self.sub_domain = sub_domain
        self.record_id = record_id
        self.line_id = line_id

    def __str__(self):
        return "{}({:d}:{:d})".format(self.fqdn, self.domain_id, self.record_id)

    def set(self, ip):
        self.dnspod.Record.Modify(domain_id=self.domain_id,
                                  record_type="AAAA",
                                  record_id=self.record_id,
                                  sub_domain=self.sub_domain,
                                  record_line_id=self.line_id,
                                  value=ip)
        print("{}: updated to {}".format(self.fqdn, ip))


def parse_fqdn(dnspod, all_domains, fqdn, ip):
    """

    :param dnspod:
    :param all_domains:
    :param str fqdn:
    :return:
    """
    sub_domain = None
    for d in all_domains:
        if d["name"] == fqdn:
            sub_domain = "@"
            break
        if fqdn.endswith("." + d["name"]):
            sub_domain = fqdn[0:len(fqdn) - len(d["name"]) - 1]
            break

    if sub_domain is None:
        raise LookupError("No such domain name {}".format(fqdn))

    rep = dnspod.Record.List(domain_id=d["id"], sub_domain=sub_domain, record_type="AAAA")
    count = int(rep["info"]["record_total"])
    if count == 0:
        r = dnspod.Record.Create(domain_id=d["id"],
                                 sub_domain=sub_domain,
                                 record_type="AAAA",
                                 value=ip,
                                 record_line_id=0
                                 )
        if r["status"]["code"] != "1":
            print(r["status"]["message"], file=sys.stderr)
            sys.exit(1)
        print("Created new AAAA record {} = {}".format(fqdn, ip))
        return Record(dnspod, "{}.{}".format(sub_domain, rep["domain"]["punycode"]),
                      domain_id=d["id"],
                      sub_domain=sub_domain,
                      record_id=r["record"]["id"],
                      line_id=0
                      )
    else:
        rec = rep["records"][0]

        r = Record(dnspod, "{}.{}".format(sub_domain, rep["domain"]["punycode"]),
                   domain_id=d["id"],
                   sub_domain=sub_domain,
                   record_id=rec["id"],
                   line_id=rec["line_id"]
                   )
        r.set(ip)
        return r


def get_ipv6():
    all_rt = ipr.get_routes(socket.AF_INET6, lambda x: x["dst_len"] == 0)
    if len(all_rt) == 0:
        print("Unable to find the default ipv6 gateway", file=sys.stderr)
        return None
    for rt in all_rt:
        oif = rt.get_attr('RTA_OIF')
        if oif is None:
            continue
        all_addrs = ipr.get_addr(socket.AF_INET6, index=oif)
        if len(all_addrs) == 0:
            continue
        for addr in all_addrs:
            if addr['scope'] != 0:  # Ignore link local addres
                continue
            ipa = addr.get_attr('IFA_ADDRESS')
            if ipa.startswith("fc") or ipa.startswith("fd") or ipa.startswith("fe"):
                continue
            return ipa

    print("Unable to get a valid ipv6 address", file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser(description="DDns Script for dnspod")
    parser.add_argument('domains', metavar="domain", type=str, nargs=1, help="The domain to update")
    return parser.parse_args()


def main():
    if "DNSPOD_TOKEN" not in os.environ:
        print("You should provider the user's token by environment variable \"DNSPOD_TOKEN\"")
        exit(1)

    args = parse_args()
    old_ip = get_ipv6()

    dnspod = DnsPod(os.environ["DNSPOD_TOKEN"])
    print("Listing domains...")
    all_domains = dnspod.Domain.List()["domains"]
    print("Finding records...")
    record = parse_fqdn(dnspod, all_domains, args.domains[0], old_ip)

    ipr.bind(pyroute2.netlink.rtnl.RTMGRP_IPV6_IFADDR)
    while True:
        for m in ipr.get():
            print(m)
        ip = get_ipv6()
        if old_ip != ip:
            print("IPv6 Address Changed: {}".format(ip))
            record.set(ip)
            old_ip = ip


if __name__ == '__main__':
    main()
