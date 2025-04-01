import click
from swsscommon.swsscommon import ConfigDBConnector
import utilities_common.cli as clicommon
from sonic_py_common import device_info
from .main import interface_name_is_valid, VLAN_SUB_INTERFACE_SEPARATOR

# #
# # 'buffer' group ('config buffer ...')
# #
# @click.group(cls=clicommon.AbbreviationGroup)
# @click.pass_context
# def buffer(ctx):
#     """buffer-related configuration tasks"""
#     pass

#
# 'buffer pool' group ('config buffer pool ...')
#
@click.group('pool')
def pool():
    """Configure buffer pool"""
    pass

def validate_buffer_pool_change(db, profile):
    config_db = db.cfgdb
    ctx = click.get_current_context()

    buff_prof_table = config_db.get_table('BUFFER_PROFILE')
    for k, v in buff_prof_table.items():
        if 'pool' in v:
            pool_name = v.get('pool','')
            found = True if pool_name == profile else False
            if found:
                ctx.fail("Buffer profile '{}' is bound to this pool, remove the profile first.".format(k))

@pool.command('add')
@click.argument('profile', metavar='<profile>', required=True)
@click.option('--type', type=click.Choice(['ingress', 'egress']), required=True, \
        help="Ingress/egress pool type")
@click.option('--size', type=int, required=True, help="Buffer pool size in bytes")
@click.option('--xoff-size', type=int, help="Headroom pool size in bytes for ingress lossless pool")
@clicommon.pass_db
def add(db, profile, type, size, xoff_size):
    """Add buffer pool."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    validate_buffer_pool_change(db, profile)

    if xoff_size != None and not(type == 'ingress'):
        ctx.fail("xoff-size is valid only for ingress lossless pool.")

    config_db = ConfigDBConnector()
    config_db.connect()
    buff_pool = {}

    buff_pool['type'] = type
    buff_pool['size'] = size * clicommon.get_traffic_manage_itm()
    buff_pool['mode'] = 'dynamic'
    if xoff_size != None:
        xoff_size = xoff_size * clicommon.get_traffic_manage_itm()
        buff_pool['xoff'] = xoff_size

    config_db.set_entry('BUFFER_POOL', profile, buff_pool)

@pool.command('del')
@click.argument('profile', metavar='<profile>', required=True)
@clicommon.pass_db
def delete(db, profile):
    """Delete buffer pool."""
    config_db = db.cfgdb
    ctx = click.get_current_context()

    entry = config_db.get_entry('BUFFER_POOL', profile)
    if len(entry) == 0:
        ctx.fail("Buffer pool '{}' not found.".format(profile))

    validate_buffer_pool_change(db, profile)

    config_db.set_entry('BUFFER_POOL', profile, None)

# #
# # 'buffer profile' group ('config buffer profile ...')
# #
# @buffer.group('profile')
# def profile():
#     """Configure buffer profile"""
#     pass

def validate_buffer_profile_binded(db, profile_name):
    ctx = click.get_current_context()
    config_db = db.cfgdb

    buff_pg_table = config_db.get_table('BUFFER_PG')
    for k, v in buff_pg_table.items():
        if 'profile' in v:
            profile_data = v.get('profile','')
            if profile_data == profile_name:
                ctx.fail("Buffer profile is bound to an interface priority group, unbind the profile first.")

    buff_queue_table = config_db.get_table('BUFFER_QUEUE')
    for k, v in buff_queue_table.items():
        if 'profile' in v:
            profile_data = v.get('profile','')
            if profile_data == profile_name:
                ctx.fail("Buffer profile is bound to an interface queue, unbind the profile first.")

def validate_buffer_profile_change(db, profile_name, pool=None, size=None, shared_static=None, shared_dynamic_alpha=None,
    xon=None, xoff=None, xon_offset=None):
    config_db = db.cfgdb
    ctx = click.get_current_context()
    hwsku = device_info.get_hwsku()

    if shared_static != None and shared_dynamic_alpha != None:
        ctx.fail("Either shared-size or shared-percent can be configured not both.")
    elif shared_static == None and shared_dynamic_alpha == None:
        ctx.fail("One of shared-size and shared-percent should be provided!")

    version_info = device_info.get_sonic_version_info()
    asic_type = version_info.get('asic_type')

    if xoff != None or xon != None or xon_offset != None:
        if pool and pool['type'] == 'egress':
            ctx.fail("xon/xoff/xon-offset can be configured only for ingress pool profile.")

        if pool:
            pool_xoff = pool.get('xoff', '0')
            pool_xoff = int(pool_xoff)
            pool_size = pool.get('size', '0')
            pool_size = int(pool_size)

            itm = clicommon.get_traffic_manage_itm()
            pool_xoff = pool_xoff / itm
            pool_size = pool_size / itm

        if xoff == None:
            ctx.fail("xoff should be provided.")
        else:
            profile_xoff = int(xoff)
            if hwsku != None and "AS5812" in hwsku:
                if size and profile_xoff > int(size):
                    ctx.fail("xoff shall not greater than the size ({}).".format(size))
            elif pool:
                if profile_xoff > pool_xoff:
                    ctx.fail("xoff shall not greater than the xoff in pool ({}).".format(pool_xoff))

        if xon == None:
            ctx.fail("xon should be provided.")
        else:
            if shared_static:
                if int(xon) > int(shared_static):
                    ctx.fail("xon shall not greater than the shared size ({}).".format(shared_static))
                else:
                    if pool and int(xon) > pool_size:
                        ctx.fail("xon shall not greater than the size in pool ({}).".format(pool_size))

        if xon_offset == None:
            if asic_type == 'broadcom':
                ctx.fail("xon-offset should be provided.")
        else:
            if asic_type == 'barefoot':
                ctx.fail("xon-offset can not be configured on Intel platform.")

            if shared_static:
                if int(xon_offset) > int(shared_static):
                    ctx.fail("xon-offset shall not greater than the shared size ({}).".format(shared_static))
                else:
                    if pool and int(xon_offset) > pool_size:
                        ctx.fail("xon-offset shall not greater than the size in pool ({}).".format(pool_size))

    validate_buffer_profile_binded(db, profile_name)

def _validate_dynamic_percent(ctx, param, value):
    if value == None:
        return None

    version_info = device_info.get_sonic_version_info()
    if (version_info and version_info['asic_type'] == 'barefoot'):
        valid_values = ('1.5', '3', '6', '11', '20', '33', '50', '66', '80')

        if value not in valid_values:
            raise click.BadParameter('Shared percent should be one of {}.'.format(valid_values))

    return value

def _convert_shared_dynamic_percent_to_alpha(percent):
    version_info = device_info.get_sonic_version_info()

    if (version_info and version_info.get('asic_type') == 'barefoot'):
        alpha_map = {
            '1.5': 0,
            '3': 1,
            '6': 2,
            '11': 3,
            '20': 4,
            '33': 5,
            '50': 6,
            '66': 7,
            '80': 8
        }
    else:
        alpha_map = {
            '0.78': -7,
            '1.5': -6,
            '3': -5,
            '6': -4,
            '11': -3,
            '20': -2,
            '33': -1,
            '50': 0,
            '66': 1,
            '80': 2,
            '89': 3
        }

    return alpha_map.get(percent)

@click.command('add')
@click.argument('profile', metavar='<profile>', required=True)
@click.option('--pool', type=click.STRING, required=True, help="Ingress or egress pool name")
@click.option('--size', type=int, required=True, help="Buffer profile size in bytes")
@click.option('--shared-size', type=int, help="Shared size in bytes")
@click.option('--shared-percent', required=False, type=click.Choice(['0.78', '1.5', '3', '6', '11', '20', '33', '50', '66', '80', '89']),
    callback=_validate_dynamic_percent, help="Share percent(%), the 0.78% and 89% are only available on Broadcom platform")
@click.option('--xoff', type=int, help="xoff size in bytes for ingress profile")
@click.option('--xon', type=int, help="xon size in bytes for ingress profile")
@click.option('--xon-offset', type=int, help="xon-offset size in bytes for ingress profile")
@clicommon.pass_db
def buffer_profile_add(db, profile, pool, size, shared_size, shared_percent, xoff, xon, xon_offset):
    """Add buffer profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    buff_profile = {}
    buff_pool = config_db.get_entry('BUFFER_POOL', pool)
    if len(buff_pool) == 0:
        ctx.fail("Buffer pool '{}' doesn't exist.".format(pool))

    shared_dynamic_alpha = _convert_shared_dynamic_percent_to_alpha(shared_percent)

    validate_buffer_profile_change(db, profile, buff_pool, size, shared_size, shared_dynamic_alpha, xon, xoff, xon_offset)

    buff_profile = config_db.get_entry('BUFFER_PROFILE', profile)
    buff_profile['pool'] = '{}'.format(pool)
    buff_profile['size'] = size

    if shared_dynamic_alpha != None:
        buff_profile['dynamic_th'] = shared_dynamic_alpha
    elif 'dynamic_th' in buff_profile:
        del buff_profile['dynamic_th']

    if shared_size != None:
        buff_profile['static_th'] = shared_size * clicommon.get_traffic_manage_itm()
    elif 'static_th' in buff_profile:
        del buff_profile['static_th']

    if xoff != None:
        buff_profile['xoff'] = xoff
    if xon != None:
        buff_profile['xon'] = xon
    if xon_offset != None:
        buff_profile['xon_offset'] = xon_offset

    config_db.set_entry('BUFFER_PROFILE', profile, buff_profile)

@click.command('update')
@click.argument('profile', metavar='<profile>', required=True)
@click.option('--shared-percent', required=False, help="Share percent(%), the 0.78% and 89% are only available on Broadcom platform",
    type=click.Choice(['0.78', '1.5', '3', '6', '11', '20', '33', '50', '66', '80', '89']),
    callback=_validate_dynamic_percent)
@click.option('--xon', type=int, help="xon size in bytes for ingress profile")
@clicommon.pass_db
def buffer_profile_update(db, profile, shared_percent, xon):
    """Update buffer profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    buff_profile = config_db.get_entry('BUFFER_PROFILE', profile)
    if len(buff_profile) == 0:
        ctx.fail("Buffer profile '{}' doesn't exist.".format(profile))

    if shared_percent and buff_profile.get('dynamic_th') == None:
        ctx.fail("Can not change the shared mode.")

    if xon and buff_profile.get('xon') == None:
        ctx.fail("Can not specify a xon value to a lossy buffer profile.")

    shared_static = None
    shared_dynamic_alpha = None
    if shared_percent:
        shared_dynamic_alpha = _convert_shared_dynamic_percent_to_alpha(shared_percent)

    if shared_dynamic_alpha == None:
        shared_static = buff_profile.get('static_th')
        shared_dynamic_alpha = buff_profile.get('dynamic_th')

    pool = buff_profile['pool']
    buff_pool = config_db.get_entry('BUFFER_POOL', pool)

    size = buff_profile.get('size')
    xon = xon if xon else buff_profile.get('xon')
    xoff = buff_profile.get('xoff')
    xon_offset = buff_profile.get('xon_offset')

    validate_buffer_profile_change(db, profile, buff_pool, size, shared_static, shared_dynamic_alpha, xon, xoff, xon_offset)

    if shared_dynamic_alpha != None:
        buff_profile['dynamic_th'] = shared_dynamic_alpha
        if 'static_th' in buff_profile:
            del buff_profile['static_th']
    elif 'dynamic_th' in buff_profile:
        del buff_profile['dynamic_th']

    if xon != None:
        buff_profile['xon'] = xon

    config_db.set_entry('BUFFER_PROFILE', profile, buff_profile)

@click.command('del')
@click.argument('profile', metavar='<profile>', required=True)
@clicommon.pass_db
def buffer_profile_delete(db, profile):
    """Delete buffer profile."""
    config_db = db.cfgdb
    ctx = click.get_current_context()
    entry = config_db.get_entry('BUFFER_PROFILE', profile)
    if len(entry) == 0:
        ctx.fail("buffer profile '{}' not found.".format(profile))

    validate_buffer_profile_binded(db, profile)

    config_db.set_entry('BUFFER_PROFILE', profile, None)

#
# 'buffer' subgroup ('config interface buffer ...')
#
class BufferProfileHelper:
    def __init__(self, config_db):
        self.config_db = config_db

    def get_interface_list_from_string(self, key):
        intfs, pgs = key.split('|')
        return intfs.split(',') if ',' in intfs else [intfs]

    def get_cosq_list_from_string(self, key):
        intfs, cosq_range = key.split('|')

        return self.expand_range_from_string(cosq_range)

    def expand_range_from_string(self, cosq_range):
        if '-' in cosq_range:
            cosq_min, cosq_max = cosq_range.split('-')
            cosqs = list(range(int(cosq_min), int(cosq_max)+1))
        else:
            cosqs = [int(cosq_range)]

        return cosqs

    def is_bind(self, key, interface, cosq_list):
        intfs = self.get_interface_list_from_string(key)
        cosqs = self.get_cosq_list_from_string(key)

        if type(cosq_list) is int:
            cosq_list = [cosq_list]

        if interface in intfs:
            for _cosq in cosq_list:
                if _cosq in cosqs:
                    return True

        return False

    def validate_cosq_range(self, is_pg, input_val):
        """
        Tool function to check whether input_val is legal.
        For broadcom TD3 series:
            pgs in range [0-7]
            queue in range [0-9]
        For brodcom other:
            pgs in range [0-7]
            queue in range [0-7]
        For Intel:
            pgs in range [1-5]
            queue in range [0-7]
        """
        ctx = click.get_current_context()

        hwsku = device_info.get_hwsku()
        version_info = device_info.get_sonic_version_info()
        asic_type = version_info.get('asic_type')

        if asic_type == 'barefoot':
            pg_min = 1
            pg_max = 5
            queue_min = 0
            queue_max = 7
        elif 'AS7326' in hwsku or 'AS7726' in hwsku or 'AS4630' in hwsku or 'AS5835' in hwsku:
            pg_min = queue_min = 0
            pg_max = 7
            queue_max = 9
        else:
            pg_min = queue_min = 0
            pg_max = queue_max = 7

        min = pg_min if is_pg else queue_min
        max = pg_max if is_pg else queue_max

        try:
            if '-' in input_val:
                cosq_min, cosq_max = input_val.split('-')
                lower = int(cosq_min)
                upper = int(cosq_max)
            else:
                lower = upper = int(input_val)

            if upper < lower or lower < min or upper > max:
                ctx.fail("{} {} is not valid.".format('PG' if is_pg == True else 'QUEUE', input_val))
        except Exception:
            ctx.fail("{} {} is not valid.".format('PG' if is_pg == True else 'QUEUE', input_val))

    def bind_buffer_profile(self, is_pg, interface, cosq, profile_name):
        table_name = 'BUFFER_PG' if is_pg else 'BUFFER_QUEUE'

        data = self.config_db.get_table(table_name)
        for k, v in data.items():
            k = '{}|{}'.format(k[0], k[1])
            if self.is_bind(k, interface, cosq):
                if profile_name == v.get('profile'):
                    return

                self.config_db.set_entry(table_name, k, None)

                for intf in self.get_interface_list_from_string(k):
                    for _cosq in self.get_cosq_list_from_string(k):
                        if intf == interface and _cosq == cosq:
                            continue

                        self.config_db.set_entry(table_name, (intf, str(_cosq)), v)

                break

        self.config_db.set_entry(table_name, (interface, str(cosq)), {
            'profile': profile_name
        })

    def unbind_buffer_profile(self, is_pg, interface, cosqs):
        table_name = 'BUFFER_PG' if is_pg else 'BUFFER_QUEUE'

        data = self.config_db.get_table(table_name)
        for k, v in data.items():
            k = '{}|{}'.format(k[0], k[1])
            if self.is_bind(k, interface, cosqs):
                self.config_db.set_entry(table_name, k, None)

                for intf in self.get_interface_list_from_string(k):
                    for _cosq in self.get_cosq_list_from_string(k):
                        if intf == interface and _cosq in cosqs:
                            continue

                        self.config_db.set_entry(table_name, (intf, str(_cosq)), v)

# @click.command('buffer')
# @click.argument('op', metavar='{bind|unbind}', type=click.Choice(['bind', 'unbind']), required=True)
# @click.argument('pg_queue', metavar='{priority-group|queue}', type=click.Choice(['priority-group', 'queue']), required=True)
# @click.argument('interface_name', metavar='{<interface_name>|all}', required=True)
# @click.argument('pg_queue_range', metavar='{<pg>|<queue>}', required=True)
# @click.argument('profile', metavar='<profile>', required=False)
# @clicommon.pass_db
# def buffer_interface(db, op, pg_queue, interface_name, pg_queue_range, profile):
#     """Set interface PG/queue buffer-profile configuration"""
#     config_db = db.cfgdb
#     ctx = click.get_current_context()

#     profile_helper = BufferProfileHelper(config_db)

#     if interface_name.lower() == "all":
#         interface_name = interface_name.lower()
#     elif (not interface_name.startswith("Ethernet") or
#             not interface_name_is_valid(config_db, interface_name) or
#             VLAN_SUB_INTERFACE_SEPARATOR in interface_name):
#         ctx.fail("Interface name is invalid. Please enter a valid interface name!!")

#     if op == 'bind':
#         entry = config_db.get_entry('BUFFER_PROFILE', profile)

#         if len(entry) == 0:
#             ctx.fail("Buffer profile '{}' not found.".format(profile))

#         pool_name = entry['pool']
#         buff_pool = config_db.get_entry('BUFFER_POOL', pool_name)

#         if len(buff_pool) == 0:
#             ctx.fail("Buffer pool '{}' not found.".format(pool_name))

#         if pg_queue == 'priority-group':
#             if buff_pool['type'] != 'ingress':
#                 ctx.fail("Cannot associate an egress buffer profile in ingress direction.")
#         else:
#             if buff_pool['type'] != 'egress':
#                 ctx.fail("Cannot associate an ingress buffer profile in egress direction.")

#     is_pg = True if pg_queue == 'priority-group' else False
#     cosqs = profile_helper.expand_range_from_string(pg_queue_range)

#     interfaces = set()
#     if interface_name == "all":
#         port_table = config_db.get_table('PORT')
#         interfaces = set(port_table.keys())
#     else:
#         interfaces.add(interface_name)

#     if op == 'bind':
#         profile_helper.validate_cosq_range(is_pg, pg_queue_range)

#         for intf in interfaces:
#             for cosq in cosqs:
#                 profile_helper.bind_buffer_profile(is_pg, intf, cosq, profile)
#     else:
#         for intf in interfaces:
#             profile_helper.unbind_buffer_profile(is_pg, intf, cosqs)

@click.command('bind')
@click.argument('pg_queue', metavar='{priority-group|queue}', type=click.Choice(['priority-group', 'queue']), required=True)
@click.argument('interface_name', metavar='{<interface_name>|all}', required=True)
@click.argument('pg_queue_range', metavar='{<pg>|<queue>}', required=True)
@click.argument('profile', metavar='<profile>', required=False)
@clicommon.pass_db
def buffer_interface_bind(db, pg_queue, interface_name, pg_queue_range, profile):
    """Set interface PG/queue buffer-profile configuration"""
    config_db = db.cfgdb
    ctx = click.get_current_context()

    profile_helper = BufferProfileHelper(config_db)

    if interface_name.lower() == "all":
        interface_name = interface_name.lower()
    elif (not interface_name.startswith("Ethernet") or
            not interface_name_is_valid(config_db, interface_name) or
            VLAN_SUB_INTERFACE_SEPARATOR in interface_name):
        ctx.fail("Interface name is invalid. Please enter a valid interface name!!")

    entry = config_db.get_entry('BUFFER_PROFILE', profile)

    if len(entry) == 0:
        ctx.fail("Buffer profile '{}' not found.".format(profile))

    pool_name = entry['pool']
    buff_pool = config_db.get_entry('BUFFER_POOL', pool_name)

    if len(buff_pool) == 0:
        ctx.fail("Buffer pool '{}' not found.".format(pool_name))

    if pg_queue == 'priority-group':
        if buff_pool['type'] != 'ingress':
            ctx.fail("Cannot associate an egress buffer profile in ingress direction.")
    else:
        if buff_pool['type'] != 'egress':
            ctx.fail("Cannot associate an ingress buffer profile in egress direction.")

    is_pg = True if pg_queue == 'priority-group' else False
    cosqs = profile_helper.expand_range_from_string(pg_queue_range)

    interfaces = set()
    if interface_name == "all":
        port_table = config_db.get_table('PORT')
        interfaces = set(port_table.keys())
    else:
        interfaces.add(interface_name)

    profile_helper.validate_cosq_range(is_pg, pg_queue_range)

    for intf in interfaces:
        for cosq in cosqs:
            profile_helper.bind_buffer_profile(is_pg, intf, cosq, profile)

@click.command('unbind')
@click.argument('pg_queue', metavar='{priority-group|queue}', type=click.Choice(['priority-group', 'queue']), required=True)
@click.argument('interface_name', metavar='{<interface_name>|all}', required=True)
@click.argument('pg_queue_range', metavar='{<pg>|<queue>}', required=True)
@click.argument('profile', metavar='<profile>', required=False)
@clicommon.pass_db
def buffer_interface_unbind(db, pg_queue, interface_name, pg_queue_range, profile):
    """Set interface PG/queue buffer-profile configuration"""
    config_db = db.cfgdb
    ctx = click.get_current_context()

    profile_helper = BufferProfileHelper(config_db)

    if interface_name.lower() == "all":
        interface_name = interface_name.lower()
    elif (not interface_name.startswith("Ethernet") or
            not interface_name_is_valid(config_db, interface_name) or
            VLAN_SUB_INTERFACE_SEPARATOR in interface_name):
        ctx.fail("Interface name is invalid. Please enter a valid interface name!!")

    is_pg = True if pg_queue == 'priority-group' else False
    cosqs = profile_helper.expand_range_from_string(pg_queue_range)

    interfaces = set()
    if interface_name == "all":
        port_table = config_db.get_table('PORT')
        interfaces = set(port_table.keys())
    else:
        interfaces.add(interface_name)

    for intf in interfaces:
        profile_helper.unbind_buffer_profile(is_pg, intf, cosqs)

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

def add_command(buffer, buffer_profile, interface_buffer):
    if is_not_supported_device() == False:
        buffer.add_command(pool)
        buffer_profile.add_command(buffer_profile_add)
        buffer_profile.add_command(buffer_profile_update)
        buffer_profile.add_command(buffer_profile_delete)
        interface_buffer.add_command(buffer_interface_bind)
        interface_buffer.add_command(buffer_interface_unbind)
