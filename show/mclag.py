import click
from natsort import natsorted
from tabulate import tabulate
from swsscommon.swsscommon import ConfigDBConnector, SonicV2Connector

import utilities_common.cli as clicommon


#
# ' mclag' command ("show mclag")
#
@click.group(cls=clicommon.AliasedGroup)
def mclag():
    """Show MCLAG related information"""
    pass

#
# 'mclag brief' command ("show mclag brief")
#
@mclag.command('brief')
@clicommon.pass_db
def brief(db):
    """Show all MCLAG information"""
    config_db = db.cfgdb
    app_db = db.appldb
    state_db = db.statedb

    domain_keys = config_db.get_keys('MCLAG_DOMAIN')
    if not domain_keys:
        click.echo("No MCLAG domain configured.")
        return

    output = ''
    for domain_id in natsorted(domain_keys):
        config_entry = config_db.get_entry('MCLAG_DOMAIN', domain_id)
        if not config_entry:
            continue
        peer_link = config_entry.get('peer_link') or ''
        peer_link_status = ''
        if peer_link:
            peer_tbl = 'PORT_TABLE' if peer_link.startswith('Ethernet') else 'LAG_TABLE'
            peer_entry = app_db.get_entry(peer_tbl, peer_link)
            if peer_entry:
                peer_link_status = peer_entry.get('oper_status').capitalize() if peer_entry.get('oper_status') else ''

        keepalive_interval = config_entry.get('keepalive_interval') or '1'
        session_timeout = config_entry.get('session_timeout') or '15'
        mclag_system_mac = config_entry.get('mclag_system_id') or ''

        state_entry = state_db.get_entry('MCLAG_TABLE', domain_id)
        session_status = ''
        role = ''
        system_mac = ''
        if state_entry:
            session_status = state_entry.get('oper_status').capitalize() if state_entry.get('oper_status') else 'Down'
            role = state_entry.get('role').capitalize() if state_entry.get('role') else ''
            system_mac = state_entry.get('system_mac') or ''

        #if output != '': output += '\n'
        output += '\t{0: <28} : {s}\n'.format('Domain ID', s=domain_id)
        output += '\t{0: <28} : {s}\n'.format('Role', s=role)
        output += '\t{0: <28} : {s}\n'.format('Session Status', s=session_status)
        output += '\t{0: <28} : {s}\n'.format('Peer Link Status', s=peer_link_status)
        output += '\t{0: <28} : {s}\n'.format('Source Address', s=config_entry.get('source_ip'))
        output += '\t{0: <28} : {s}\n'.format('Peer Address', s=config_entry.get('peer_ip'))
        output += '\t{0: <28} : {s}\n'.format('Peer Link', s=peer_link)
        output += '\t{0: <28} : {s} secs\n'.format('Keepalive Interval', s=keepalive_interval)
        output += '\t{0: <28} : {s} secs\n'.format('Session Timeout', s=session_timeout)
        output += '\t{0: <28} : {s}\n'.format('System MAC', s=system_mac)
        output += '\t{0: <28} : {s}\n'.format('MCLAG System MAC', s=mclag_system_mac)

        portchannel_member_keys = config_db.get_keys('MCLAG_INTERFACE|{}'.format(domain_id))
        portchannel_member_cnt = len(portchannel_member_keys)
        output += '\t{0: <28} : {s}\n'.format('Number of MCLAG Interfaces', s=portchannel_member_cnt)
        if 0 < portchannel_member_cnt:
            output += '\t{0: <28} {s}\n'.format('MCLAG Interface', s='Local/Remote Status')
            for domain_id, member in natsorted(portchannel_member_keys):
                local_status = 'Down'
                remote_status = 'Down'
                lag_entry = app_db.get_entry('LAG_TABLE', member)
                if lag_entry:
                    local_status = lag_entry.get('oper_status').capitalize() if lag_entry.get('oper_status') else 'Down'
                remote_interface_keys = state_db.get_keys('MCLAG_REMOTE_INTF_TABLE|{}'.format(domain_id))
                if (domain_id, member) in remote_interface_keys:
                    remote_entry = state_db.get_entry('MCLAG_REMOTE_INTF_TABLE', (domain_id, member))
                    remote_status = remote_entry.get('oper_status').capitalize() if remote_entry.get('oper_status') else 'Down'
                output += '\t{0: <28} {l}/{r}\n'.format(member, l=local_status, r=remote_status)
    click.echo(output)

#
# 'mclag interface' command ("show mclag interface ...")
#
@mclag.command('interface')
@click.argument('domain_id', metavar='<domain_id>', required=True, type=int)
@click.argument('portchannel_name', metavar='<portchannel_name>', required=True)
@clicommon.pass_db
def interface(db, domain_id, portchannel_name):
    """Show MCLAG interface information"""
    config_db = db.cfgdb
    app_db = db.appldb
    state_db = db.statedb
    domain_id_str = str(domain_id)

    ctx = click.get_current_context()

    domain_entry = config_db.get_entry('MCLAG_DOMAIN', domain_id_str)
    if not domain_entry:
        click.echo('Domain {} is not configured.'.format(domain_id_str))
        return

    if portchannel_name.startswith('PortChannel') is False:
        ctx.fail('Invalid portchannel name {}.'.format(portchannel_name))

    portchannel_member_keys = config_db.get_keys('MCLAG_INTERFACE|{}'.format(domain_id_str))
    if (domain_id_str, portchannel_name) not in portchannel_member_keys:
        click.echo('Domain {} member {} is not configured.'.format(domain_id_str, portchannel_name))
        return

    local_status = 'Down'
    lag_entry = app_db.get_entry('LAG_TABLE', portchannel_name)
    if lag_entry:
        local_status = lag_entry.get('oper_status').capitalize()

    remote_status = 'Down'
    remote_interface_keys = state_db.get_keys('MCLAG_REMOTE_INTF_TABLE|{}'.format(domain_id_str))
    if (domain_id_str, portchannel_name) in remote_interface_keys:
        remote_entry = state_db.get_entry('MCLAG_REMOTE_INTF_TABLE', (domain_id_str, portchannel_name))
        remote_status = remote_entry.get('oper_status').capitalize() or 'Down'

    port_isolate_peer_link_status = 'No'
    local_interface_entry = state_db.get_entry('MCLAG_LOCAL_INTF_TABLE', portchannel_name)
    if local_interface_entry and local_interface_entry.get('port_isolate_peer_link') == 'true':
        port_isolate_peer_link_status = 'Yes'

    output = ''
    output += '\t{0: <28} : {l}/{r}\n'.format('Local/Remote Status', l=local_status, r=remote_status)
    output += '\t{0: <28} : {s}\n'.format('IsolateWithPeerLink', s=port_isolate_peer_link_status)
    click.echo(output)

#
# 'mclag unique-ip' command ("show mclag unique-ip")
#
@mclag.command('unique-ip')
@clicommon.pass_db
def unique_ip(db):
    """Show MCLAG unique-ip information"""
    config_db = db.cfgdb
    output = '\t{0: <28} :'.format('Unique IP')
    unique_ip_keys = config_db.get_keys('MCLAG_UNIQUE_IP')
    for vlan_intf in natsorted(unique_ip_keys):
        output += ' {},'.format(vlan_intf)
    output = output[:-1] if len(unique_ip_keys) > 0 else output
    click.echo(output)

