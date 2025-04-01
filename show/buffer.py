import click
import utilities_common.cli as clicommon
from natsort import natsorted
from sonic_py_common import device_info
from tabulate import tabulate
from .main import run_command

#
# 'buffer' command ("show buffer")
#
# @click.group(cls=clicommon.AliasedGroup)
# def buffer():
#     """Show details of the buffer"""
#     pass

def convert_bytes_to_display_string(value):
    if value < 1024 or value % 1024:
        return '{} Bytes'.format(format(value, ',d'))

    value = value // 1024
    if value % 1024:
        return '{} KiB'.format(format(value, ',d'))

    value = value // 1024
    if value % 1024:
        return '{} MiB'.format(format(value, ',d'))

    value = value // 1024
    return '{} GiB'.format(format(value, ',d'))

@click.command('pool')
@click.argument('profile', required=False)
@clicommon.pass_db
def pool(db, profile):
    '''Show buffer pool configuration'''
    config_db = db.cfgdb
    ctx = click.get_current_context()
    buf_pools = config_db.get_table('BUFFER_POOL')
    if buf_pools:
        header = ['Pool', 'Type', 'Size', 'Xoff']
        body = []

        if profile == None:
            pool_keys = natsorted(buf_pools.keys())
            for k in pool_keys:
                size = int(buf_pools[k].get('size'))
                size = size // clicommon.get_traffic_manage_itm()
                size = convert_bytes_to_display_string(size)

                xoff = buf_pools[k].get('xoff')
                if xoff:
                    xoff = int(xoff) // clicommon.get_traffic_manage_itm()
                    xoff = convert_bytes_to_display_string(xoff)

                body.append([k, buf_pools[k].get('type'), size, xoff])
        else:
            data = config_db.get_entry('BUFFER_POOL', profile)
            if len(data) != 0:
                size = int(data['size'])
                size = size // clicommon.get_traffic_manage_itm()
                size = convert_bytes_to_display_string(size)

                xoff = data.get('xoff')
                if xoff:
                    xoff = int(xoff) // clicommon.get_traffic_manage_itm()
                    xoff = convert_bytes_to_display_string(xoff)

                body.append([profile, data.get('type'), size, xoff])
            else:
                ctx.fail("Buffer pool {} not found".format(profile))

        click.echo(tabulate(body, header, stralign='left'))
    else:
        click.echo("No buffer pool information available")

def _convert_shared_dynamic_alpha_to_percent(percent):
    version_info = device_info.get_sonic_version_info()

    if (version_info and version_info.get('asic_type') == 'barefoot'):
        percent_map = {
            '0': '1.5',
            '1': '3',
            '2': '6',
            '3': '11',
            '4': '20',
            '5': '33',
            '6': '50',
            '7': '66',
            '8': '80'
        }
    else:
        percent_map = {
            '-7': '0.78',
            '-6': '1.5',
            '-5': '3',
            '-4': '6',
            '-3': '11',
            '-2': '20',
            '-1': '33',
            '0': '50',
            '1': '66',
            '2': '80',
            '3': '89'
        }

    return percent_map.get(percent)

@click.command('profile')
@click.argument('profile', required=False)
@clicommon.pass_db
def profile(db, profile):
    '''Show buffer profile configuration'''
    config_db = db.cfgdb
    ctx = click.get_current_context()

    buf_profs = config_db.get_table('BUFFER_PROFILE')
    if buf_profs:
        header = ['Profile', 'Pool', 'Size', 'Shared Mode', 'Shared Size', 'Xoff', 'Xon', 'Xon-offset']
        body = []

        if profile == None:
            pool_keys = natsorted(buf_profs.keys())
            for k in pool_keys:
                shared_mode = 'dynamic' if buf_profs[k].get('dynamic_th') else 'static'
                shared_size = buf_profs[k].get('dynamic_th') if buf_profs[k].get('dynamic_th') else buf_profs[k].get('static_th')
                if shared_mode == 'dynamic':
                    shared_size = '{}%'.format(_convert_shared_dynamic_alpha_to_percent(shared_size))
                else:
                    shared_size = int(shared_size) // clicommon.get_traffic_manage_itm()
                    shared_size = convert_bytes_to_display_string(shared_size)

                size = buf_profs[k].get('size')
                if size:
                    size = convert_bytes_to_display_string(int(size))

                xoff = buf_profs[k].get('xoff')
                if xoff:
                    xoff = convert_bytes_to_display_string(int(xoff))

                xon = buf_profs[k].get('xon')
                if xon:
                    xon = convert_bytes_to_display_string(int(xon))

                xon_offset = buf_profs[k].get('xon_offset')
                if xon_offset:
                    xon_offset = convert_bytes_to_display_string(int(xon_offset))

                body.append([k, buf_profs[k].get('pool'), size
                              , shared_mode, shared_size, xoff
                              , xon, xon_offset])
        else:
            data = config_db.get_entry('BUFFER_PROFILE', profile)
            if len(data) != 0:
                shared_mode = 'dynamic' if data.get('dynamic_th') else 'static'
                shared_size = data.get('dynamic_th') if data.get('dynamic_th') else data.get('static_th')
                if shared_mode == 'dynamic':
                    shared_size = '{}%'.format(_convert_shared_dynamic_alpha_to_percent(shared_size))
                else:
                    shared_size = int(shared_size) // clicommon.get_traffic_manage_itm()
                    shared_size = convert_bytes_to_display_string(shared_size)

                size = data.get('size')
                if size:
                    size = convert_bytes_to_display_string(int(size))

                xoff = data.get('xoff')
                if xoff:
                    xoff = convert_bytes_to_display_string(int(xoff))

                xon = data.get('xon')
                if xon:
                    xon = convert_bytes_to_display_string(int(xon))

                xon_offset = data.get('xon_offset')
                if xon_offset:
                    xon_offset = convert_bytes_to_display_string(int(xon_offset))

                body.append([profile, data.get('pool'), size
                              , shared_mode, shared_size, xoff
                              , xon, xon_offset])
            else:
                ctx.fail("Buffer profile {} not found".format(profile))

        click.echo(tabulate(body, header, stralign='left'))
    else:
        click.echo("No buffer profile information available")

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

def add_command(show):
    if is_not_supported_device() == False:
        show.add_command(pool)
        show.add_command(profile)
