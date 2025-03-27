import click
import utilities_common.cli as clicommon
from natsort import natsorted
from sonic_py_common import device_info
from tabulate import tabulate
from ..wred import show_wred_profile

@click.command('wred')
@click.argument('interface_name', required=False)
@clicommon.pass_db
def wred(db, interface_name):
    """Show Interface ECN WRED information"""
    config_db = db.cfgdb

    data = config_db.get_table('QUEUE')
    for key in natsorted(list(data.keys())):
        port_name, q = key
        if interface_name == None or interface_name == port_name:
            qos_data = data[key]
            wred_profile = qos_data.get('wred_profile')

            if wred_profile == None:
                continue

            click.echo(port_name)
            click.echo('Queue: {}'.format(q))

            show_wred_profile(config_db, wred_profile)

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
        interfaces.add_command(wred)
