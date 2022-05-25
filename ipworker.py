import ipwhois
import re


class IpWorker:

    __pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    __slash = r'(/\d{1,2})?'

    __allnum = 2**32
    
    __spec_ranges = [
        # "0.0.0.0/8"
        (0, 16777215),
        # "10.0.0.0/8",
        (167772160, 184549375),
        # "100.64.0.0/10"
        (1681915904, 1686110207),
        # "127.0.0.0/8",
        (2130706432, 2147483647),
        # "169.254.0.0/16"
        (2851995648, 2852061183),
        # "172.16.0.0/12"
        (2886729728, 2887778303),
        # "192.0.0.0/24"
        (3221225472, 3221225727),
        # "192.0.2.0/24"
        (3221225984, 3221226239),
        # "192.88.99.0/24"
        (3227017984, 3227018239),
        # "192.168.0.0/16",
        (3232235520, 3232301055),
        # "198.18.0.0/15"
        (3323068416, 3323199487),
        # "198.51.100.0/24"
        (3325256704, 3325256959),
        # "203.0.113.0/24"
        (3405803776, 3405804031),
        # "224.0.0.0/4"
        (3758096384, 4026531839),
        # "233.252.0.0/24"
        (3925606400, 3925606655),
        # "240.0.0.0/4"
        (4026531840, 4294967295),
        # "255.255.255.255/32"
        (4294967295, 4294967295)
    ]

    @staticmethod
    def is_ip(source: str) -> bool:
        return bool(re.fullmatch(IpWorker.__pattern, source))

    @staticmethod
    def ip2num(source_ip: str) -> int:
        if not re.fullmatch(IpWorker.__pattern, source_ip):
            raise Exception("Wrong ipv4 format")
        source_ipnum = sum(
            [
                (int(x)*2**y
                 if int(x) < 256
                 else IpWorker.__allnum)
                for x, y in zip(source_ip.split('.'), [24, 16, 8, 0])
            ]
        )
        if source_ipnum >= IpWorker.__allnum:
            raise Exception(f"Source ip {source_ip} out of ipv4 range")
        return source_ipnum

    @staticmethod
    def cidr_ip2num(cidr_ip: str) -> tuple:
        if not re.fullmatch(IpWorker.__pattern + IpWorker.__slash, cidr_ip):
            raise Exception("Wrong ipv4 format")
        ip, sub = cidr_ip.split("/") if '/' in cidr_ip else (cidr_ip, 32)
        if int(sub) < 0 or int(sub) > 32:
            raise Exception("Wrong subnet number")
        allnum = IpWorker.__allnum
        ipnum = sum(
            [
                (int(x)*2**y if int(x) < 256 else allnum)
                for x, y in zip(ip.split('.'), [24, 16, 8, 0])
            ]
        )
        if ipnum >= allnum:
            raise Exception(f"Ip {ip} out of ipv4 range")
        subnum = (allnum - 1) - (2 ** (32-int(sub)) - 1)
        wildnum = allnum - subnum - 1
        gate = (ipnum | allnum) & (subnum | allnum) - allnum
        cast = ((ipnum | allnum) | (wildnum | allnum)) - allnum
        return gate, cast

    @staticmethod
    def ip_contains(source_ip: str, cidr_ip: str) -> bool:
        source_ipnum = IpWorker.ip2num(source_ip)
        gate, cast = IpWorker.cidr_ip2num(cidr_ip)
        return gate <= source_ipnum <= cast
    
    @staticmethod
    def ip_spec_contains(source_ip: str) -> bool:
        source_ipnum = IpWorker.ip2num(source_ip)
        for gate, cast in IpWorker.__spec_ranges:
            if gate <= source_ipnum <= cast:
                return True
        return False
    
    @staticmethod
    def num2ip(source_ipnum: int) -> str:
        if source_ipnum >= IpWorker.__allnum:
            raise Exception(f"Source ip number {source_ipnum} out of ipv4 range")
        source_ipbin = bin(source_ipnum | IpWorker.__allnum)[3:]
        source_iplist = [
            int(source_ipbin[x*8:(x+1)*8], 2).__str__()
            for x in range(4)
        ]
        return '.'.join(source_iplist)
    
    @staticmethod
    def ip2cidr(gate_ip: str, cast_ip: str) -> str:
        gate = IpWorker.ip2num(gate_ip)
        cast = IpWorker.ip2num(cast_ip)
        if gate > cast:
            raise Exception(f"Gate ip more than cast ip ({gate} > {cast})")
        if gate == cast:
            sub = 32
        else:
            sub = 32 - bin(cast - gate)[2:].__len__()
        cidr_range = IpWorker.cidr_ip2num(f"{gate_ip}/{sub}")
        if cast < cidr_range[0] or cast > cidr_range[1]:
            sub -= 1
        return f"{gate_ip}/{sub}"

    @staticmethod
    def get_asn_cidr_by_ip(source_ip: str):
        if not IpWorker.is_ip(source_ip):
            raise Exception("Wrong ipv4 format")
        return ipwhois.IPWhois(source_ip).lookup_rdap().get("asn_cidr", source_ip + "/32")
