import click
import subprocess
import utilities_common.cli as clicommon
from swsscommon.swsscommon import ConfigDBConnector
from sonic_py_common import device_info
from tabulate import tabulate

def fill_wred_data(data):
    ret = {}

    ret['green_min_threshold'] = str(data.get('green_min_threshold', '-'))
    ret['green_max_threshold'] = str(data.get('green_max_threshold', '-'))
    ret['green_drop_probability'] = str(data.get('green_drop_probability', '-'))

    ret['yellow_min_threshold'] = str(data.get('yellow_min_threshold', '-'))
    ret['yellow_max_threshold'] = str(data.get('yellow_max_threshold', '-'))
    ret['yellow_drop_probability'] = str(data.get('yellow_drop_probability', '-'))

    ret['red_min_threshold'] = str(data.get('red_min_threshold', '-'))
    ret['red_max_threshold'] = str(data.get('red_max_threshold', '-'))
    ret['red_drop_probability'] = str(data.get('red_drop_probability', '-'))

    ret['ecn_green_min_threshold'] = str(data.get('ecn_green_min_threshold', '-'))
    ret['ecn_green_max_threshold'] = str(data.get('ecn_green_max_threshold', '-'))
    ret['ecn_green_mark_probability'] = str(data.get('ecn_green_mark_probability', '-'))

    ret['ecn_yellow_min_threshold'] = str(data.get('ecn_yellow_min_threshold', '-'))
    ret['ecn_yellow_max_threshold'] = str(data.get('ecn_yellow_max_threshold', '-'))
    ret['ecn_yellow_mark_probability'] = str(data.get('ecn_yellow_mark_probability', '-'))

    ret['ecn_red_min_threshold'] = str(data.get('ecn_red_min_threshold', '-'))
    ret['ecn_red_max_threshold'] = str(data.get('ecn_red_max_threshold', '-'))
    ret['ecn_red_mark_probability'] = str(data.get('ecn_red_mark_probability', '-'))

    return ret

def show_wred_profile(config_db, profile):
    table_entry = config_db.get_table('WRED_PROFILE')

    for k,v in table_entry.items():
        if profile != None and profile != k:
            continue

        wred_enable = False
        ecn_enable = False

        if v.get('wred_green_enable', 'false') == 'true' or \
            v.get('wred_red_enable', 'false') == 'true' or \
            v.get('wred_red_enable', 'false') == 'true':
            wred_enable = True

        if v.get('ecn', 'ecn_none') != 'ecn_none':
            ecn_enable = True

        click.echo('Profile: {}'.format(k))

        body = []

        data = fill_wred_data(v)

        if wred_enable == True:
            if ecn_enable == True:
                click.echo('Mode: both')

                header = ['Color',
                          'Non-ECT Min Threshold (Byte)\nECN/CE Min Threshold (Byte)',
                          'Non-ECT Max Threshold (Byte)\nECN/CE Max Threshold (Byte)',
                          'Non-ECT Drop Probability (%)\nECN/CE Mark Probability (%)']

                body.append([
                    'Green',
                    '{}\n{}'.format(data['green_min_threshold'], data['ecn_green_min_threshold']),
                    '{}\n{}'.format(data['green_max_threshold'], data['ecn_green_max_threshold']),
                    '{}\n{}'.format(data['green_drop_probability'], data['ecn_green_mark_probability']),
                    ])
                body.append([
                    'Yellow',
                    '{}\n{}'.format(data['yellow_min_threshold'], data['ecn_yellow_min_threshold']),
                    '{}\n{}'.format(data['yellow_max_threshold'], data['ecn_yellow_max_threshold']),
                    '{}\n{}'.format(data['yellow_drop_probability'], data['ecn_yellow_mark_probability']),
                    ])
                body.append([
                    'Red',
                    '{}\n{}'.format(data['red_min_threshold'], data['ecn_red_min_threshold']),
                    '{}\n{}'.format(data['red_max_threshold'], data['ecn_red_max_threshold']),
                    '{}\n{}'.format(data['red_drop_probability'], data['ecn_red_mark_probability']),
                    ])
            else:
                click.echo('Mode: WRED')

                header = ['Color', 'Min Threshold (Byte)', 'Max Threshold (Byte)', 'Drop Probability (%)']

                body.append([
                    'Green',
                    '{}'.format(data['green_min_threshold']),
                    '{}'.format(data['green_max_threshold']),
                    '{}'.format(data['green_drop_probability']),
                    ])
                body.append([
                    'Yellow',
                    '{}'.format(data['yellow_min_threshold']),
                    '{}'.format(data['yellow_max_threshold']),
                    '{}'.format(data['yellow_drop_probability']),
                    ])
                body.append([
                    'Red',
                    '{}'.format(data['red_min_threshold']),
                    '{}'.format(data['red_max_threshold']),
                    '{}'.format(data['red_drop_probability']),
                    ])
        elif ecn_enable == True:
            click.echo('Mode: ECN')

            header = ['Color', 'Min Threshold (Byte)', 'Max Threshold (Byte)', 'Mark Probability (%)']

            body.append([
                'Green',
                '{}'.format(data['ecn_green_min_threshold']),
                '{}'.format(data['ecn_green_max_threshold']),
                '{}'.format(data['ecn_green_mark_probability']),
                ])
            body.append([
                'Yellow',
                '{}'.format(data['ecn_yellow_min_threshold']),
                '{}'.format(data['ecn_yellow_max_threshold']),
                '{}'.format(data['ecn_yellow_mark_probability']),
                ])
            body.append([
                'Red',
                '{}'.format(data['ecn_red_min_threshold']),
                '{}'.format(data['ecn_red_max_threshold']),
                '{}'.format(data['ecn_red_mark_probability']),
                ])

        click.echo('')

        print_data = tabulate(body, header, stralign='left')
        click.echo(print_data)

        click.echo('')

#
# 'wred' command ("show qos wred")
#
@click.command('wred')
@click.argument('profile', required=False)
def wred(profile):
    """Show ECN WRED configuration"""
    config_db = ConfigDBConnector()
    config_db.connect()

    show_wred_profile(config_db, profile)


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
        show.add_command(wred)
