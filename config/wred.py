import click
import utilities_common.cli as clicommon
from sonic_py_common import device_info
from .utils import log
from .main import update_profile_to_interface_queue

def validate_qos_map_bind_queue(db, profile, qos_map_field):
    config_db = db.cfgdb
    ctx = click.get_current_context()

    port_qos_table = config_db.get_table('QUEUE')
    for k, v in port_qos_table.items():
        if qos_map_field in v:
            qos_map = v.get(qos_map_field, '')
            found = True if qos_map == profile else False
            if found:
                ctx.fail('The profile is binding to queue, unbind from it first.')

#
#  wred' group ('config wred ...')
#
@click.group(cls=clicommon.AbbreviationGroup)
def wred():
    """Configure ECN WRED profile"""
    pass

def convert_wred_ecn_green(ctx, wred_prof, wred_enable, ecn_enable, gmin, gmax, gdrop, ecn_gmin, ecn_gmax, ecn_gmark):
    if gmin != None and gmax != None and gdrop != None:
        if gmin > gmax:
            ctx.fail("gmin cannot be greater than gmax")
        else:
            if wred_enable:
                wred_prof['green_min_threshold'] = gmin
                wred_prof['green_max_threshold'] = gmax
                wred_prof['green_drop_probability'] = gdrop
                wred_prof['wred_green_enable'] = 'true'

            if ecn_enable:
                wred_prof['ecn_green_min_threshold'] = gmin
                wred_prof['ecn_green_max_threshold'] = gmax
                wred_prof['ecn_green_mark_probability'] = gdrop
    elif gmin != None or gmax != None or gdrop != None:
        ctx.fail("gmin/gmax/gdrop all values should be provided")

    if ecn_gmin != None and ecn_gmax != None and ecn_gmark != None:
        if not ecn_enable:
            ctx.fail("ecn must be enabled when ecn_gmin/ecn_gmax/ecn_gmark values are provided")

        if ecn_gmin > ecn_gmax:
            ctx.fail("ecn_gmin cannot be greater than ecn_gmax")

        if ecn_enable:
            wred_prof['ecn_green_min_threshold'] = ecn_gmin
            wred_prof['ecn_green_max_threshold'] = ecn_gmax
            wred_prof['ecn_green_mark_probability'] = ecn_gmark
    elif ecn_gmin != None or ecn_gmax != None or ecn_gmark != None:
        ctx.fail("ecn_gmin/ecn_gmax/ecn_gmark all values should be provided")

def convert_wred_ecn_yellow(ctx, wred_prof, wred_enable, ecn_enable, ymin, ymax, ydrop, ecn_ymin, ecn_ymax, ecn_ymark):
    if ymin != None and ymax != None and ydrop != None:
        if ymin > ymax:
            ctx.fail("ymin cannot be greater than ymax")
        else:
            if wred_enable:
                wred_prof['yellow_min_threshold'] = ymin
                wred_prof['yellow_max_threshold'] = ymax
                wred_prof['yellow_drop_probability'] = ydrop
                wred_prof['wred_yellow_enable'] = 'true'

            if ecn_enable:
                wred_prof['ecn_yellow_min_threshold'] = ymin
                wred_prof['ecn_yellow_max_threshold'] = ymax
                wred_prof['ecn_yellow_mark_probability'] = ydrop
    elif ymin != None or ymax != None or ydrop != None:
        ctx.fail("ymin/ymax/ydrop all values should be provided")

    if ecn_ymin != None and ecn_ymax != None and ecn_ymark != None:
        if not ecn_enable:
            ctx.fail("ecn must be enabled when ecn_ymin/ecn_ymax/ecn_ymark values are provided")

        if ecn_ymin > ecn_ymax:
            ctx.fail("ecn_ymin cannot be greater than ecn_ymax")

        if ecn_enable:
            wred_prof['ecn_yellow_min_threshold'] = ecn_ymin
            wred_prof['ecn_yellow_max_threshold'] = ecn_ymax
            wred_prof['ecn_yellow_mark_probability'] = ecn_ymark
    elif ecn_ymin != None or ecn_ymax != None or ecn_ymark != None:
        ctx.fail("ecn_ymin/ecn_ymax/ecn_ymark all values should be provided")

def convert_wred_ecn_red(ctx, wred_prof, wred_enable, ecn_enable, rmin, rmax, rdrop, ecn_rmin, ecn_rmax, ecn_rmark):
    if rmin != None and rmax != None and rdrop != None:
        if rmin > rmax:
            ctx.fail("rmin cannot be greater than rmax")
        else:
            if wred_enable:
                wred_prof['red_min_threshold'] = rmin
                wred_prof['red_max_threshold'] = rmax
                wred_prof['red_drop_probability'] = rdrop
                wred_prof['wred_red_enable'] = 'true'

            if ecn_enable:
                wred_prof['ecn_red_min_threshold'] = rmin
                wred_prof['ecn_red_max_threshold'] = rmax
                wred_prof['ecn_red_mark_probability'] = rdrop
    elif rmin != None or rmax != None or rdrop != None:
        ctx.fail("rmin/rmax/rdrop all values should be provided")

    if ecn_rmin != None and ecn_rmax != None and ecn_rmark != None:
        if not ecn_enable:
            ctx.fail("ecn must be enabled when ecn_rmin/ecn_rmax/ecn_rmark values are provided")

        if ecn_rmin > ecn_rmax:
            ctx.fail("ecn_rmin cannot be greater than ecn_rmax")

        if ecn_enable:
            wred_prof['ecn_red_min_threshold'] = ecn_rmin
            wred_prof['ecn_red_max_threshold'] = ecn_rmax
            wred_prof['ecn_red_mark_probability'] = ecn_rmark
    elif ecn_rmin != None or ecn_rmax != None or ecn_rmark != None:
        ctx.fail("ecn_rmin/ecn_rmax/ecn_rmark all values should be provided")

def update_wred_ecn_values(ctx, wred_prof, mode,
                           gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
                           ecn_gmin, ecn_gmax, ecn_gmark, ecn_ymin, ecn_ymax, ecn_ymark, ecn_rmin, ecn_rmax, ecn_rmark):
    wred_enable = False
    ecn_enable = False

    if mode == None:
        if wred_prof['ecn'] != 'ecn_none':
            ecn_enable = True

        if wred_prof.get('wred_green_enable', 'false') == 'true' or \
            wred_prof.get('wred_red_enable', 'false') == 'true' or \
            wred_prof.get('wred_red_enable', 'false') == 'true':
            wred_enable = True
    elif mode == 'wred':
        wred_enable = True

        remove_wred_ecn_values(wred_prof, False, False, False, True, True, True)
    elif mode == 'ecn':
        ecn_enable = True

        remove_wred_ecn_values(wred_prof, True, True, True, False, False, False)
    elif mode == 'both':
        wred_enable = True
        ecn_enable = True
    else:
        ctx.fail("Unknown mode ({}).".format(mode))

    convert_wred_ecn_green(ctx, wred_prof, wred_enable, ecn_enable, gmin, gmax, gdrop, ecn_gmin, ecn_gmax, ecn_gmark)
    convert_wred_ecn_yellow(ctx, wred_prof, wred_enable, ecn_enable, ymin, ymax, ydrop, ecn_ymin, ecn_ymax, ecn_ymark)
    convert_wred_ecn_red(ctx, wred_prof, wred_enable, ecn_enable, rmin, rmax, rdrop, ecn_rmin, ecn_rmax, ecn_rmark)

def update_ecn_mode(wred_prof):
    ecn_green = False
    ecn_yellow = False
    ecn_red = False

    if 'ecn_green_mark_probability' in wred_prof:
        ecn_green = True
    if 'ecn_yellow_mark_probability' in wred_prof:
        ecn_yellow = True
    if 'ecn_red_mark_probability' in wred_prof:
        ecn_red = True

    if ecn_green and ecn_yellow and ecn_red:
        wred_prof['ecn'] = 'ecn_all'
    elif ecn_green and ecn_yellow:
        wred_prof['ecn'] = 'ecn_green_yellow'
    elif ecn_green and ecn_red:
        wred_prof['ecn'] = 'ecn_green_red'
    elif ecn_yellow and ecn_red:
        wred_prof['ecn'] = 'ecn_yellow_red'
    elif ecn_green:
        wred_prof['ecn'] = 'ecn_green'
    elif ecn_yellow:
        wred_prof['ecn'] = 'ecn_yellow'
    elif ecn_red:
        wred_prof['ecn'] = 'ecn_red'
    else:
        wred_prof['ecn'] = 'ecn_none'

def remove_wred_ecn_values(wred_prof, no_green, no_yellow, no_red, no_ecn_green, no_ecn_yellow, no_ecn_red):
    if no_green:
        if 'green_min_threshold' in wred_prof:
            del wred_prof['green_min_threshold']
        if 'green_max_threshold' in wred_prof:
            del wred_prof['green_max_threshold']
        if 'green_drop_probability' in wred_prof:
            del wred_prof['green_drop_probability']
        if 'wred_green_enable' in wred_prof:
            del wred_prof['wred_green_enable']

    if no_yellow:
        if 'yellow_min_threshold' in wred_prof:
            del wred_prof['yellow_min_threshold']
        if 'yellow_max_threshold' in wred_prof:
            del wred_prof['yellow_max_threshold']
        if 'yellow_drop_probability' in wred_prof:
            del wred_prof['yellow_drop_probability']
        if 'wred_yellow_enable' in wred_prof:
            del wred_prof['wred_yellow_enable']

    if no_red:
        if 'red_min_threshold' in wred_prof:
            del wred_prof['red_min_threshold']
        if 'red_max_threshold' in wred_prof:
            del wred_prof['red_max_threshold']
        if 'red_drop_probability' in wred_prof:
            del wred_prof['red_drop_probability']
        if 'wred_red_enable' in wred_prof:
            del wred_prof['wred_red_enable']

    if no_ecn_green:
        if 'ecn_green_min_threshold' in wred_prof:
            del wred_prof['ecn_green_min_threshold']
        if 'ecn_green_max_threshold' in wred_prof:
            del wred_prof['ecn_green_max_threshold']
        if 'ecn_green_mark_probability' in wred_prof:
            del wred_prof['ecn_green_mark_probability']

    if no_ecn_yellow:
        if 'ecn_yellow_min_threshold' in wred_prof:
            del wred_prof['ecn_yellow_min_threshold']
        if 'ecn_yellow_max_threshold' in wred_prof:
            del wred_prof['ecn_yellow_max_threshold']
        if 'ecn_yellow_mark_probability' in wred_prof:
            del wred_prof['ecn_yellow_mark_probability']

    if no_ecn_red:
        if 'ecn_red_min_threshold' in wred_prof:
            del wred_prof['ecn_red_min_threshold']
        if 'ecn_red_max_threshold' in wred_prof:
            del wred_prof['ecn_red_max_threshold']
        if 'ecn_red_mark_probability' in wred_prof:
            del wred_prof['ecn_red_mark_probability']

_wred_hwsku = None
_wred_max_threshold = None

def get_wred_max_threshold():
    global _wred_hwsku
    global _wred_max_threshold

    if _wred_max_threshold:
        return _wred_max_threshold

    if not _wred_hwsku:
        _wred_hwsku = device_info.get_hwsku()

    data = {
        # TD2+
        'Accton-AS5812-': 0x1ffff * 208,
        # HX5
        'Accton-AS4630-': 0x3ffff * 256,
        # MV2
        'Accton-AS5835-': 0x3ffff * 256,
        # TD3
        'Accton-AS7326-': 0x3ffff * 256,
        'Accton-AS7726-': 0x3ffff * 256,
        # TD4
        'Accton-AS9726-': 0xfffff * 254,
        # TH
        'Accton-AS7712-': 0xffff * 208,
        # TH2
        'Accton-AS7816-': 0xffff * 208,
        # TH3
        'Accton-AS9716-': 0x7ffff * 254,
        'Accton-MINIPACK': 0x7ffff * 254,
        # TH4
        'Accton-AS9736-': 0x7ffff * 254,
        'Accton-AS9737-': 0x7ffff * 254,
        # TH5
        'Accton-AS9817-': 0xfffff * 254,
        # TF
        'mavericks': 0x7ffff * 80,
        'montara': 0x7ffff * 80,
        # TF2
        'newport': 0x7ffff * 176
    }

    if _wred_hwsku:
        for device, threshold in data.items():
            if _wred_hwsku.startswith(device):
                _wred_max_threshold = threshold
                return threshold

    return 0xffff * 208 # Default use the minimum value of all device

def get_wred_help_msg(field):
    max_th = get_wred_max_threshold()
    messages = {
        'mode': 'ECN or WRED mode.',
        'gmin': 'Minimum threshold in bytes to start WRED dropping or ECN marking for green packet. [0-{}]'.format(max_th),
        'gmax': 'Maximum threshold in bytes for WRED dropping or ECN marking for green packet. [0-{}]'.format(max_th),
        'gdrop': 'Maximum dropping or marking probability for green packet. [0-100]',
        'ymin': 'Minimum threshold in bytes to start WRED dropping or ECN marking for yellow packet. [0-{}]'.format(max_th),
        'ymax': 'Maximum threshold in bytes for WRED dropping or ECN marking for yellow packet. [0-{}]'.format(max_th),
        'ydrop': 'Maximum dropping or marking probability for yellow packet. [0-100]',
        'rmin': 'Minimum threshold in bytes to start WRED dropping or ECN marking for red packet. [0-{}]'.format(max_th),
        'rmax': 'Maximum threshold in bytes for WRED dropping or ECN marking for red packet. [0-{}]'.format(max_th),
        'rdrop': 'Maximum dropping or marking probability for red packet. [0-100]',
        'ecn-gmin': 'Minimum threshold in bytes to start ECN marking for green packet. [0-{}]'.format(max_th),
        'ecn-gmax': 'Maximum threshold in bytes for ECN marking for green packet. [0-{}]'.format(max_th),
        'ecn-gmark': 'Maximum marking probability for green packet. [0-100]',
        'ecn-ymin': 'Minimum threshold in bytes to start ECN marking for yellow packet. [0-{}]'.format(max_th),
        'ecn-ymax': 'Maximum threshold in bytes for ECN marking for yellow packet. [0-{}]'.format(max_th),
        'ecn-ymark': 'Maximum marking probability for yellow packet. [0-100]',
        'ecn-rmin': 'Minimum threshold in bytes to start ECN marking for red packet. [0-{}]'.format(max_th),
        'ecn-rmax': 'Maximum threshold in bytes for ECN marking for red packet. [0-{}]'.format(max_th),
        'ecn-rmark': 'Maximum marking probability for red packet. [0-100]',
        'no-green': 'Remove the green setting from the profile.',
        'no-yellow': 'Remove the yellow setting from the profile.',
        'no-red': 'Remove the red setting from the profile.',
        'no-ecn-green': 'Remove the green setting from the profile.',
        'no-ecn-yellow': 'Remove the yellow setting from the profile.',
        'no-ecn-red': 'Remove the red setting from the profile.',
    }

    return messages.get(field)

def remove_not_supported_attr(wred_prof):
    if 'ecn_green_min_threshold' in wred_prof:
        wred_prof['green_min_threshold'] = wred_prof['ecn_green_min_threshold']
        wred_prof['wred_green_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_green_min_threshold']

    if 'ecn_green_max_threshold' in wred_prof:
        wred_prof['green_max_threshold'] = wred_prof['ecn_green_max_threshold']
        wred_prof['wred_green_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_green_max_threshold']

    if 'ecn_green_mark_probability' in wred_prof:
        wred_prof['green_drop_probability'] = wred_prof['ecn_green_mark_probability']
        wred_prof['wred_green_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_green_mark_probability']

    if 'ecn_yellow_min_threshold' in wred_prof:
        wred_prof['yellow_min_threshold'] = wred_prof['ecn_yellow_min_threshold']
        wred_prof['wred_yellow_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_yellow_min_threshold']

    if 'ecn_yellow_max_threshold' in wred_prof:
        wred_prof['yellow_max_threshold'] = wred_prof['ecn_yellow_max_threshold']
        wred_prof['wred_yellow_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_yellow_max_threshold']

    if 'ecn_yellow_mark_probability' in wred_prof:
        wred_prof['yellow_drop_probability'] = wred_prof['ecn_yellow_mark_probability']
        wred_prof['wred_yellow_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_yellow_mark_probability']

    if 'ecn_red_min_threshold' in wred_prof:
        wred_prof['red_min_threshold'] = wred_prof['ecn_red_min_threshold']
        wred_prof['wred_red_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_red_min_threshold']

    if 'ecn_red_max_threshold' in wred_prof:
        wred_prof['red_max_threshold'] = wred_prof['ecn_red_max_threshold']
        wred_prof['wred_red_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_red_max_threshold']

    if 'ecn_red_mark_probability' in wred_prof:
        wred_prof['red_drop_probability'] = wred_prof['ecn_red_mark_probability']
        wred_prof['wred_red_enable'] = 'true'
        wred_prof['ecn'] = 'ecn_all'

        del wred_prof['ecn_red_mark_probability']

@click.command('add')
@click.argument('profile', metavar='<profile>', required=True)
@click.option('--mode', required=True, type=click.Choice(['ecn', 'wred', 'both']), help=get_wred_help_msg('mode'))
@click.option('--gmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('gmin'))
@click.option('--gmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('gmax'))
@click.option('--gdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('gdrop'))
@click.option('--ymin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymin'))
@click.option('--ymax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymax'))
@click.option('--ydrop', type=click.IntRange(0, 100), help=get_wred_help_msg('ydrop'))
@click.option('--rmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmin'))
@click.option('--rmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmax'))
@click.option('--rdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('rdrop'))
@click.option('--ecn-gmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-gmin'))
@click.option('--ecn-gmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-gmax'))
@click.option('--ecn-gmark', type=click.IntRange(0, 100), help=get_wred_help_msg('ecn-gmark'))
@click.option('--ecn-ymin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-ymin'))
@click.option('--ecn-ymax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-ymax'))
@click.option('--ecn-ymark', type=click.IntRange(0, 100), help=get_wred_help_msg('ecn-ymark'))
@click.option('--ecn-rmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-rmin'))
@click.option('--ecn-rmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-rmax'))
@click.option('--ecn-rmark', type=click.IntRange(0, 100), help=get_wred_help_msg('ecn-rmark'))
@clicommon.pass_db
def add_brcm(db, profile, mode, gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
        ecn_gmin, ecn_gmax, ecn_gmark, ecn_ymin, ecn_ymax, ecn_ymark, ecn_rmin, ecn_rmax, ecn_rmark):
    """Add ECN WRED profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    entry = config_db.get_entry('WRED_PROFILE', profile)
    if len(entry) != 0:
        ctx.fail("Profile '{}' already exists use update command.".format(profile))

    wred_prof = {}

    update_wred_ecn_values(ctx, wred_prof, mode,
                           gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
                           ecn_gmin, ecn_gmax, ecn_gmark, ecn_ymin, ecn_ymax, ecn_ymark, ecn_rmin, ecn_rmax, ecn_rmark)
    update_ecn_mode(wred_prof)

    config_db.set_entry('WRED_PROFILE', profile, wred_prof)

@click.command('add')
@click.argument('profile', metavar='<profile>', required=True)
@click.option('--mode', required=True, type=click.Choice(['ecn', 'wred']), help=get_wred_help_msg('mode'))
@click.option('--gmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('gmin'))
@click.option('--gmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('gmax'))
@click.option('--gdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('gdrop'))
@click.option('--ymin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymin'))
@click.option('--ymax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymax'))
@click.option('--ydrop', type=click.IntRange(0, 100), help=get_wred_help_msg('ydrop'))
@click.option('--rmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmin'))
@click.option('--rmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmax'))
@click.option('--rdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('rdrop'))
@clicommon.pass_db
def add_bfn(db, profile, mode, gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop):
    """Add ECN WRED profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    entry = config_db.get_entry('WRED_PROFILE', profile)
    if len(entry) != 0:
        ctx.fail("Profile '{}' already exists use update command.".format(profile))

    wred_prof = {}

    update_wred_ecn_values(ctx, wred_prof, mode,
                           gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
                           None, None, None, None, None, None, None, None, None)
    update_ecn_mode(wred_prof)

    remove_not_supported_attr(wred_prof)

    config_db.set_entry('WRED_PROFILE', profile, wred_prof)

@click.command('update')
@click.argument('profile', metavar='<profile>', required=True)
@click.option('--mode', type=click.Choice(['ecn', 'wred', 'both']), help=get_wred_help_msg('mode'))
@click.option('--gmin', type=click.IntRange(0, get_wred_max_threshold()),  help=get_wred_help_msg('gmin'))
@click.option('--gmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('gmax'))
@click.option('--gdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('gdrop'))
@click.option('--ymin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymin'))
@click.option('--ymax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymax'))
@click.option('--ydrop', type=click.IntRange(0, 100), help=get_wred_help_msg('ydrop'))
@click.option('--rmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmin'))
@click.option('--rmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmax'))
@click.option('--rdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('rdrop'))
@click.option('--ecn-gmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-gmin'))
@click.option('--ecn-gmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-gmax'))
@click.option('--ecn-gmark', type=click.IntRange(0, 100), help=get_wred_help_msg('ecn-gmark'))
@click.option('--ecn-ymin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-ymin'))
@click.option('--ecn-ymax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-ymax'))
@click.option('--ecn-ymark', type=click.IntRange(0, 100), help=get_wred_help_msg('ecn-ymark'))
@click.option('--ecn-rmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-rmin'))
@click.option('--ecn-rmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ecn-rmax'))
@click.option('--ecn-rmark', type=click.IntRange(0, 100), help=get_wred_help_msg('ecn-rmark'))
@click.option('--no-green', default=False, is_flag=True, help=get_wred_help_msg('no-green'))
@click.option('--no-yellow', default=False, is_flag=True, help=get_wred_help_msg('no-yellow'))
@click.option('--no-red', default=False, is_flag=True, help=get_wred_help_msg('no-red'))
@click.option('--no-ecn-green', default=False, is_flag=True, help=get_wred_help_msg('no-ecn-green'))
@click.option('--no-ecn-yellow', default=False, is_flag=True, help=get_wred_help_msg('no-ecn-yellow'))
@click.option('--no-ecn-red', default=False, is_flag=True, help=get_wred_help_msg('no-ecn-red'))
@clicommon.pass_db
def update_brcm(db, profile, mode, gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
           ecn_gmin, ecn_gmax, ecn_gmark, ecn_ymin, ecn_ymax, ecn_ymark, ecn_rmin, ecn_rmax, ecn_rmark,
           no_green, no_yellow, no_red, no_ecn_green, no_ecn_yellow, no_ecn_red):
    """Update ECN WRED profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    wred_prof = config_db.get_entry('WRED_PROFILE', profile)
    if len(wred_prof) == 0:
        ctx.fail("Profile '{}' not found.".format(profile))

    validate_qos_map_bind_queue(db, profile, 'wred_profile')

    update_wred_ecn_values(ctx, wred_prof, mode,
                           gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
                           ecn_gmin, ecn_gmax, ecn_gmark, ecn_ymin, ecn_ymax, ecn_ymark, ecn_rmin, ecn_rmax, ecn_rmark)
    remove_wred_ecn_values(wred_prof, no_green, no_yellow, no_red, no_ecn_green, no_ecn_yellow, no_ecn_red)
    update_ecn_mode(wred_prof)

    config_db.set_entry('WRED_PROFILE', profile, None)
    config_db.set_entry('WRED_PROFILE', profile, wred_prof)

@click.command('update')
@click.argument('profile', metavar='<profile>', required=True)
@click.option('--mode', type=click.Choice(['ecn', 'wred']), help=get_wred_help_msg('mode'))
@click.option('--gmin', type=click.IntRange(0, get_wred_max_threshold()),  help=get_wred_help_msg('gmin'))
@click.option('--gmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('gmax'))
@click.option('--gdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('gdrop'))
@click.option('--ymin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymin'))
@click.option('--ymax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('ymax'))
@click.option('--ydrop', type=click.IntRange(0, 100), help=get_wred_help_msg('ydrop'))
@click.option('--rmin', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmin'))
@click.option('--rmax', type=click.IntRange(0, get_wred_max_threshold()), help=get_wred_help_msg('rmax'))
@click.option('--rdrop', type=click.IntRange(0, 100), help=get_wred_help_msg('rdrop'))
@click.option('--no-green', default=False, is_flag=True, help=get_wred_help_msg('no-green'))
@click.option('--no-yellow', default=False, is_flag=True, help=get_wred_help_msg('no-yellow'))
@click.option('--no-red', default=False, is_flag=True, help=get_wred_help_msg('no-red'))
@clicommon.pass_db
def update_bfn(db, profile, mode, gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
           no_green, no_yellow, no_red):
    """Update ECN WRED profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    wred_prof = config_db.get_entry('WRED_PROFILE', profile)
    if len(wred_prof) == 0:
        ctx.fail("Profile '{}' not found.".format(profile))

    validate_qos_map_bind_queue(db, profile, 'wred_profile')

    update_wred_ecn_values(ctx, wred_prof, mode,
                           gmin, gmax, gdrop, ymin, ymax, ydrop, rmin, rmax, rdrop,
                           None, None, None, None, None, None, None, None, None)
    remove_wred_ecn_values(wred_prof, no_green, no_yellow, no_red, None, None, None)
    update_ecn_mode(wred_prof)

    remove_not_supported_attr(wred_prof)

    config_db.set_entry('WRED_PROFILE', profile, None)
    config_db.set_entry('WRED_PROFILE', profile, wred_prof)

@wred.command('del')
@click.argument('profile', metavar='<profile>', required=True)
@clicommon.pass_db
def delete(db, profile):
    """Delete ECN WRED map profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    entry = config_db.get_entry('WRED_PROFILE', profile)
    if len(entry) == 0:
        ctx.fail("Profile '{}' not found.".format(profile))

    validate_qos_map_bind_queue(db, profile, 'wred_profile')

    config_db.set_entry('WRED_PROFILE', profile, None)

@click.command('wred')
@click.argument('op', metavar='{bind|unbind}', type=click.Choice(['bind', 'unbind']), required=True)
@click.argument('queue', metavar='queue', type=click.Choice(['queue']), required=True)
@click.argument('interface_name', metavar='<interface_name>', required=True)
@click.argument('queue_range', metavar='<queue>', required=True, type=click.IntRange(0, 7))
@click.argument('wred_profile_name', metavar='<profile_name>', required=False)
@clicommon.pass_db
def wred_interface(db, op, queue, interface_name, queue_range, wred_profile_name):
    """Set interface ECN WRED configuration"""
    if op == 'bind':
        ctx = click.get_current_context()
        if wred_profile_name == None:
            ctx.fail("Cannot find WRED profile")
        else:
            wred_prof = db.cfgdb.get_entry('WRED_PROFILE', wred_profile_name)
            if len(wred_prof) == 0:
                ctx.fail("Profile '{}' not found.".format(wred_profile_name))

    update_profile_to_interface_queue(db, op, interface_name, wred_profile_name, queue_range, 'wred_profile')

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

def add_command(config, interface):
    if is_not_supported_device() == False:
        config.add_command(wred)

        version_info = device_info.get_sonic_version_info()
        if version_info and version_info.get('asic_type', '') == 'barefoot':
            wred.add_command(add_bfn)
            wred.add_command(update_bfn)
        else:
            wred.add_command(add_brcm)
            wred.add_command(update_brcm)

        interface.add_command(wred_interface)
