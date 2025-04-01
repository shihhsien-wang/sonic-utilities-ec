import click
import utilities_common.cli as clicommon
import utilities_common.asic_info as asic_info
from natsort import natsorted
from tabulate import tabulate


#
# 'acl' group ###
#

@click.group(cls=clicommon.AliasedGroup)
def acl():
    """Show ACL related information"""
    pass


# 'rule' subcommand  ("show acl rule")
@acl.command()
@click.argument('table_name', required=False)
@click.argument('rule_id', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def rule(table_name, rule_id, verbose):
    """Show existing ACL rules"""
    cmd = ['acl-loader', 'show', 'rule']

    if table_name is not None:
        cmd += [str(table_name)]

    if rule_id is not None:
        cmd += [str(rule_id)]

    clicommon.run_command(cmd, display_cmd=verbose)


# 'table' subcommand  ("show acl table")
@acl.command()
@click.argument('table_name', required=False)
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def table(table_name, verbose):
    """Show existing ACL tables"""
    cmd = ['acl-loader', 'show', 'table']

    if table_name is not None:
        cmd += [str(table_name)]

    clicommon.run_command(cmd, display_cmd=verbose)


# 'type' subcommand  ("show acl table-type")
@click.command("table-type")
@click.pass_context
@click.argument("type_name", required=False)
def table_type(ctx, type_name):
    """Show existing ACL types"""

    MATCH_MAP = {
        "vlan_id": "VLAN ID",
        "vlan_pri": "COS",
        "src_ip": "Src IPv4 address",
        "dst_ip": "Dst IPv4 address",
        "src_ipv6": "Src IPv6 address",
        "dst_ipv6": "Dst IPv6 address",
        "dscp": "DSCP",
        "l4_src_port": "TCP/UDP src port",
        "l4_dst_port": "TCP/UDP dst port",
        "ip_type": "IP type",
        "in_ports": "In ports",
        "in_port": "In port",
        "out_port": "Out port",
    }

    config_db = ctx.obj.cfgdb

    db_data = config_db.get_table("ACL_TABLE_TYPE")

    header = ("Name", "Bind Point", "Match", "Policer")

    data = []

    for k, v in db_data.items():
        if type_name and k != type_name:
            continue

        bind_points = v["bind_points"] if "bind_points" in v else []
        matches = v["matches"] if "matches" in v else []
        actions = v["actions"] if "actions" in v else []
        has_policer = "set_policer" in v.get("actions", "")

        _data = [
            k,
            "",
            "",
            "Yes" if has_policer else "",
        ]

        for idx, a in enumerate(actions[:]):
            if a == "packet_action":
                actions.pop(idx)

        while len(bind_points) or len(matches):
            if len(bind_points):
                _data[1] = bind_points.pop(0)

            if len(matches):
                match_str = matches.pop(0)
                _data[2] = MATCH_MAP.get(match_str, match_str)

            data.append(_data)

            _data = ["", "", "", ""]

    print(tabulate(data, headers=header, tablefmt="simple", missingval=""))


def is_table_type_supported():
    asic = asic_info.get_asic_info()
    if asic.is_bf:
        return False

    return True

if is_table_type_supported():
    acl.add_command(table_type)
