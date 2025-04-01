import click
import utilities_common.cli as clicommon
from natsort import natsorted
from sonic_py_common import device_info
from tabulate import tabulate

#
# 'buffer' command ("show interfaces buffer ...")
#
@click.group()
def buffer():
    '''Show details of the buffer'''
    pass

def get_all_interfaces(key):
    intfs, pgs = key.split('|')
    return intfs.split(',') if ',' in intfs else [intfs]

def get_all_cosq(key):
    intfs, cosq_range = key.split('|')

    if '-' in cosq_range:
        cosq_min, cosq_max = cosq_range.split('-')
        cosqs = list(range(int(cosq_min), int(cosq_max)+1))
    else:
        cosqs = [int(cosq_range)]

    return cosqs

@buffer.command('priority-group')
@click.argument('interface_name', required=False)
@clicommon.pass_db
def priority_group(db, interface_name):
    """Show Interfaces buffer priority-group"""
    header = ['Interface', 'PG', 'Profile']
    body = []

    table_entry = db.cfgdb.get_table('BUFFER_PG')
    for k,v in table_entry.items():
        key = '{}|{}'.format(k[0], k[1])
        intfs = get_all_interfaces(key)
        pgs = get_all_cosq(key)

        for if_name in intfs:
            for pg in pgs:
                if if_name == interface_name or interface_name == None:
                    if 'profile' in v and v['profile'] != "NULL":
                        body.append([if_name, pg, v['profile']])

    if len(body) != 0:
        click.echo(tabulate(natsorted(body), header, stralign='left'))

@buffer.command('queue')
@click.argument('interface_name', required=False)
@clicommon.pass_db
def queue(db, interface_name):
    """Show Interfaces buffer queue"""
    header = ['Interface', 'Queue', 'Profile']
    body = []

    table_entry = db.cfgdb.get_table('BUFFER_QUEUE')
    for k,v in table_entry.items():
        key = '{}|{}'.format(k[0], k[1])
        intfs = get_all_interfaces(key)
        queues = get_all_cosq(key)

        for if_name in intfs:
            for queue in queues:
                if if_name == interface_name or interface_name == None:
                    if 'profile' in v and v['profile'] != "NULL":
                        body.append([if_name, queue, v['profile']])

    if len(body) != 0:
        click.echo(tabulate(natsorted(body), header, stralign='left'))

def is_not_supported_device():
    devices = [
        # HR4
        'Accton-AS4625-54T',
        'Accton-AS4625-54P',
    ]

    hwsku = device_info.get_hwsku()
    if hwsku:
        for device in devices:
            if hwsku.startswith(device):
                return True
    return False

def add_command(interfaces):
    if is_not_supported_device() == False:
        interfaces.add_command(buffer)
