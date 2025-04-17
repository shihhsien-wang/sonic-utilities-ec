import configparser
import datetime
import os
import re
import subprocess
import sys
import shutil

import click
import json
import lazy_object_proxy
import netaddr

import utilities_common.bgp_util as bgp_util

from natsort import natsorted
from sonic_py_common import multi_asic
from utilities_common.db import Db
from utilities_common.general import load_db_config
from sonic_py_common.general import getstatusoutput_noshell_pipe
from sonic_py_common import device_info

VLAN_SUB_INTERFACE_SEPARATOR = '.'

pass_db = click.make_pass_decorator(Db, ensure=True)

ALIAS_COMMANDS_TABLE = {
    "portstat": {
        # show interface counters
        "title_prefix": "IFACE",
        "intf_title": "IFACE",
        "align_left": False
    },
    "intfstat": {
        # show interfaces counters rif
        "title_prefix": "IFACE",
        "intf_title": "IFACE",
        "align_left": False
    },
    "pfcstat": {
        # show pfc counters
        "title_prefix": "Port Rx",
        "intf_title": "Port Rx",
        "align_left": False
    },
    "sfputil show eeprom": {
        # show interface transceiver eeprom
        # TODO: need to fix it
        "title_prefix": "IFACE",
        "intf_title": "IFACE",
        "align_left": False
    },
    "sfputil show": {
        # show interface transceiver lpmode
        "title_prefix": "Port",
        "intf_title": "Port",
        "align_left": True
    },
    "sfpshow presence": {
        # show interface transceiver presence
        "title_prefix": "Port",
        "intf_title": "Port",
        "align_left": True
    },
    "lldpshow": {
        # show lldp table
        "title_prefix": "LocalPort",
        "intf_title": "LocalPort",
        "align_left": True,
        "exclude_args": [
            "-d" # show lldp neighbor
        ]
    },
    "queuestat": {
        # show queue counters
        "title_prefix": "Port",
        "intf_title": "Port",
        "align_left": False
    },
    "fdbshow": {
        # show mac
        "title_prefix": "No.",
        "intf_title": "Port",
        "align_left": True
    },
    "nbrshow": {
        # show arp/nd
        "title_prefix": "Address",
        "intf_title": "Iface",
        "align_left": True
    },
    "ipintutil": {
        # show ip/ipv6 interface
        "title_prefix": "Interface",
        "intf_title": "Interface",
        "align_left": True
    }
}

class AbbreviationGroup(click.Group):
    """This subclass of click.Group supports abbreviated subgroup/subcommand names
    """

    def get_command(self, ctx, cmd_name):
        # Try to get builtin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # Allow automatic abbreviation of the command.  "status" for
        # instance will match "st".  We only allow that however if
        # there is only one command.
        # If there are multiple matches and the shortest one is the common prefix of all the matches, return
        # the shortest one
        matches = []
        shortest = None
        for x in self.list_commands(ctx):
            if x.lower().startswith(cmd_name.lower()):
                matches.append(x)
                if not shortest:
                    shortest = x
                elif len(shortest) > len(x):
                    shortest = x

        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        else:
            for x in matches:
                if not x.startswith(shortest):
                    break
            else:
                return click.Group.get_command(self, ctx, shortest)

            ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))


# This is from the aliases example:
# https://github.com/pallets/click/blob/57c6f09611fc47ca80db0bd010f05998b3c0aa95/examples/aliases/aliases.py
class Config(object):
    """Object to hold CLI config"""

    def __init__(self):
        self.path = os.getcwd()
        self.aliases = {}

    def read_config(self, filename):
        parser = configparser.RawConfigParser()
        parser.read([filename])
        try:
            self.aliases.update(parser.items('aliases'))
        except configparser.NoSectionError:
            pass

# Global Config object
_config = None

class AliasedGroup(click.Group):
    """This subclass of click.Group supports abbreviations and
       looking up aliases in a config file with a bit of magic.
    """

    def get_command(self, ctx, cmd_name):
        global _config

        # If we haven't instantiated our global config, do it now and load current config
        if _config is None:
            _config = Config()

            # Load our config file
            cfg_file = os.path.join(os.path.dirname(__file__), 'aliases.ini')
            _config.read_config(cfg_file)

        # Try to get builtin commands as normal
        rv = click.Group.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        # No builtin found. Look up an explicit command alias in the config
        if cmd_name in _config.aliases:
            actual_cmd = _config.aliases[cmd_name]
            return click.Group.get_command(self, ctx, actual_cmd)

        # Alternative option: if we did not find an explicit alias we
        # allow automatic abbreviation of the command.  "status" for
        # instance will match "st".  We only allow that however if
        # there is only one command.
        matches = [x for x in self.list_commands(ctx)
                   if x.lower().startswith(cmd_name.lower())]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, ctx, matches[0])
        ctx.fail('Too many matches: %s' % ', '.join(sorted(matches)))

class InterfaceAliasConverter(object):
    """Class which handles conversion between interface name and alias"""

    def __init__(self, db=None):

        # Load database config files
        load_db_config()
        if db is None:
            self.port_dict = multi_asic.get_port_table()
        else:
            self.config_db = db.cfgdb
            self.port_dict = self.config_db.get_table('PORT')
        self.alias_max_length = 0


        if not self.port_dict:
            self.port_dict = {}

        self.port_dict['eth0'] = {'alias': 'eth0'}

        for port_name in self.port_dict:
            try:
                if self.alias_max_length < len(
                        self.port_dict[port_name]['alias']):
                   self.alias_max_length = len(
                        self.port_dict[port_name]['alias'])
            except KeyError:
                break

    def name_to_alias(self, interface_name):
        """Return vendor interface alias if SONiC
           interface name is given as argument
        """
        vlan_id = ''
        sub_intf_sep_idx = -1
        if interface_name is not None:
            sub_intf_sep_idx = interface_name.find(VLAN_SUB_INTERFACE_SEPARATOR)
            if sub_intf_sep_idx != -1:
                vlan_id = interface_name[sub_intf_sep_idx + 1:]
                # interface_name holds the parent port name
                interface_name = interface_name[:sub_intf_sep_idx]

            for port_name in self.port_dict:
                if interface_name == port_name:
                    return self.port_dict[port_name]['alias'] if sub_intf_sep_idx == -1 \
                            else self.port_dict[port_name]['alias'] + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

        # interface_name not in port_dict. Just return interface_name
        return interface_name if sub_intf_sep_idx == -1 else interface_name + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

    def alias_to_name(self, interface_alias):
        """Return SONiC interface name if vendor
           port alias is given as argument
        """
        vlan_id = ''
        sub_intf_sep_idx = -1
        if interface_alias is not None:
            sub_intf_sep_idx = interface_alias.find(VLAN_SUB_INTERFACE_SEPARATOR)
            if sub_intf_sep_idx != -1:
                vlan_id = interface_alias[sub_intf_sep_idx + 1:]
                # interface_alias holds the parent port alias
                interface_alias = interface_alias[:sub_intf_sep_idx]

            for port_name in self.port_dict:
                if interface_alias == self.port_dict[port_name]['alias']:
                    return port_name if sub_intf_sep_idx == -1 else port_name + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

        # interface_alias not in port_dict. Just return interface_alias
        return interface_alias if sub_intf_sep_idx == -1 else interface_alias + VLAN_SUB_INTERFACE_SEPARATOR + vlan_id

# Lazy global class instance for SONiC interface name to alias conversion
iface_alias_converter = lazy_object_proxy.Proxy(lambda: InterfaceAliasConverter())

def get_interface_naming_mode():
    mode = os.getenv('SONIC_CLI_IFACE_MODE')
    if mode is None:
        mode = "default"
    return mode

def is_ipaddress(val):
    """ Validate if an entry is a valid IP """
    import netaddr
    if not val:
        return False
    try:
        netaddr.IPAddress(str(val))
    except netaddr.core.AddrFormatError:
        return False
    return True

def ipaddress_type(val):
    """ Return the IP address type """
    if not val:
        return None

    try:
        ip_version = netaddr.IPAddress(str(val))
    except netaddr.core.AddrFormatError:
        return None

    return ip_version.version

def is_ip_prefix_in_key(key):
    '''
    Function to check if IP address is present in the key. If it
    is present, then the key would be a tuple or else, it shall be
    be string
    '''
    return (isinstance(key, tuple))

def is_valid_port(config_db, port):
    """Check if port is in PORT table"""

    port_table = config_db.get_table('PORT')
    if port in port_table:
        return True

    return False

def is_valid_portchannel(config_db, port):
    """Check if port is in PORT_CHANNEL table"""

    pc_table = config_db.get_table('PORTCHANNEL')
    if port in pc_table:
        return True

    return False

def is_vlanid_in_range(vid):
    """Check if vlan id is valid or not"""

    if vid >= 1 and vid <= 4094:
        return True

    return False

def check_if_vlanid_exist(config_db, vlan, table_name='VLAN'):
    """Check if vlan id exits in the config db or ot"""

    if len(config_db.get_entry(table_name, vlan)) != 0:
        return True

    return False

def has_vlan_member(config_db, vlan):
    vlan_ports_data = config_db.get_table('VLAN_MEMBER')
    for key in vlan_ports_data:
        if key[0] == vlan:
            return True
    return False

def is_port_vlan_member(config_db, port, vlan):
    """Check if port is a member of vlan"""

    vlan_ports_data = config_db.get_table('VLAN_MEMBER')
    for key in vlan_ports_data:
        if key[0] == vlan and key[1] == port:
            return True

    return False

def interface_is_in_vlan(vlan_member_table, interface_name):
    """ Check if an interface is in a vlan """
    for _,intf in vlan_member_table:
        if intf == interface_name:
            return True

    return False

def is_valid_vlan_interface(config_db, interface):
    """ Check an interface is a valid VLAN interface """
    return interface in config_db.get_table("VLAN_INTERFACE")

def interface_is_in_portchannel(portchannel_member_table, interface_name):
    """ Check if an interface is part of portchannel """
    for _,intf in portchannel_member_table:
        if intf == interface_name:
            return True

    return False

def is_port_router_interface(config_db, port):
    """Check if port is a router interface"""

    interface_table = config_db.get_table('INTERFACE')
    for intf in interface_table:
        if port == intf:
            return True

    return False

def is_pc_router_interface(config_db, pc):
    """Check if portchannel is a router interface"""

    pc_interface_table = config_db.get_table('PORTCHANNEL_INTERFACE')
    for intf in pc_interface_table:
        if pc == intf:
            return True

    return False

def is_port_mirror_dst_port(config_db, port):
    """Check if port is already configured as mirror destination port """
    mirror_table = config_db.get_table('MIRROR_SESSION')
    for _,v in mirror_table.items():
        if 'dst_port' in v and v['dst_port'] == port:
            return True

    return False

def vni_id_is_valid(vni):
    """Check if the vni id is in acceptable range (between 1 and 2^24)
    """

    if (vni < 1) or (vni > 16777215):
        return False

    return True

def is_vni_vrf_mapped(db, vni):
    """Check if the vni is mapped to vrf
    """

    found = 0
    vrf_table = db.cfgdb.get_table('VRF')
    vrf_keys = vrf_table.keys()
    if vrf_keys is not None:
      for vrf_key in vrf_keys:
        if ('vni' in vrf_table[vrf_key] and vrf_table[vrf_key]['vni'] == vni):
           found = 1
           break

    if (found == 1):
        print("VNI {} mapped to Vrf {}, Please remove VRF VNI mapping".format(vni, vrf_key))
        return False

    return True

def interface_has_mirror_config(mirror_table, interface_name):
    """Check if port is already configured with mirror config """
    for _,v in mirror_table.items():
        if 'src_port' in v and v['src_port'] == interface_name:
            return True
        if 'dst_port' in v and v['dst_port'] == interface_name:
            return True

    return False

# expect all columns are algin to the same direction, return column_start, column_width for further processing
def print_output_title_header(output, match_field, align_left):
    # some match field might have space in it, need to replace it instead of just split space
    replace = False
    replace_char = '|'
    if ' ' in match_field:
        replace = True
        start = output.find(match_field)
        end = start + len(match_field)
        match_field = match_field.replace(' ', replace_char)
        output = output[:start] + match_field + output[end:]

    columns = output.split()
    idx = columns.index(match_field)
    left = 0
    right = len(output)
    spaces = 0
    column_start = 0
    if align_left:
        # align left, add diff space to the right
        left = output.find(columns[idx]) + len(match_field)
        if idx < len(columns):
            right = output.find(columns[idx+1])
            spaces = right - left - 2
        else:
            right = len(output)
            spaces = right - left
        column_start = left - len(match_field)
    else:
        # align right, add diff space to the left
        right = output.find(columns[idx])
        if idx:
            left = output.find(columns[idx-1]) + len(match_field)
            spaces = right - left - 2
        else:
            left = 0
            spaces = right - left
        column_start = right - spaces

    # calculate the original width, the space between columns is fixed to 2 spaces
    column_width = spaces + len(match_field)

    # adjust the match field with the alias max length
    space_diff = iface_alias_converter.alias_max_length - column_width
    if space_diff:
        output = output[:right] + ' '*space_diff + output[right:]

    # replace back for the match field with space
    if replace:
        start = output.find(match_field)
        end = start + len(match_field)
        match_field = match_field.replace(replace_char, ' ')
        output = output[:start] + match_field + output[end:]

    click.echo(output.rstrip('\n'))
    return column_start, column_width


def print_output_in_alias_mode(output, return_cmd, column_start=0, column_width=0, align_left=True):
    """Convert and print all instances of SONiC interface
       name to vendor-sepecific interface aliases.
    """

    alias_name = ""
    interface_name = ""

    # Adjust tabulation width to length of alias name
    if output.startswith("---"):
        diff = iface_alias_converter.alias_max_length - column_width
        if diff:
            insert_idx = column_start
            if align_left:
                insert_idx += column_width
            output = output[:insert_idx] + '-'*diff + output[insert_idx:]
        click.echo(output.rstrip('\n'))
        return

    if output.startswith("Total"):
        click.echo(output.rstrip('\n'))
        return

    # get the interface name by column start and width
    column_end = column_start + column_width
    interface_name = output[column_start:column_end].strip()
    for port_name in iface_alias_converter.port_dict.keys():
        if interface_name == port_name:
            alias_name = iface_alias_converter.port_dict[port_name]['alias']

    # replace interface name by vendor alias name if it's existed
    max_width = max(column_width, iface_alias_converter.alias_max_length)
    replace_name = alias_name if alias_name else interface_name
    output_intf_name = replace_name.ljust(max_width) if align_left else replace_name.rjust(max_width)
    output = output[:column_start] + output_intf_name + output[column_end:]

    if return_cmd:
        return output
    else:
        click.echo(output.rstrip('\n'))

def run_command_in_alias_mode(command, display_cmd=False, ignore_error=False, return_cmd=False, interactive_mode=False, shell=False):
    """Run command and replace all instances of SONiC interface names
       in output with vendor-sepecific interface aliases.
    """
    if not shell:
        command_str = ' '.join(command)
    else:
        command_str = command
    process = subprocess.Popen(command, text=True, shell=shell, stdout=subprocess.PIPE)
    is_title = False
    is_alias_command = False
    column_width = 0

    # check if command is alias command needed to be converted
    exclude = False
    for cmd_prefix, data in ALIAS_COMMANDS_TABLE.items():
        if cmd_prefix in command_str:
            if "exclude_args" in data:
                if any(arg in command_str for arg in data["exclude_args"]):
                    exclude = True
                    break

            if exclude:
                break

            is_alias_command = True
            align_left = data['align_left']
            title_prefix = data['title_prefix']
            intf_title = data['intf_title']
            break

    converted_output = ''
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break

        if output:
            raw_output = output
            if is_alias_command:
                if output.lstrip().startswith(title_prefix):
                    is_title = True
                    column_start, column_width = print_output_title_header(output, intf_title, align_left)
                else:
                    if is_title:
                        print_output_in_alias_mode(output, return_cmd, column_start, column_width, align_left)
                    else:
                        click.echo(output.rstrip('\n'))

            else:
                """
                Default command conversion
                Search for port names either at the start of a line or preceded immediately by
                whitespace and followed immediately by either the end of a line or whitespace
                or a comma followed by whitespace
                """
                converted_output = raw_output
                for port_name in iface_alias_converter.port_dict:
                    converted_output = re.sub(r"(^|\s){}($|,{{0,1}}\s)".format(port_name),
                            r"\1{}\2".format(iface_alias_converter.name_to_alias(port_name)),
                            converted_output)
                if return_cmd:
                    pass
                else:
                    click.echo(converted_output.rstrip('\n'))

    rc = process.poll()
    return converted_output.rstrip('\n'), rc


def run_command(command, display_cmd=False, ignore_error=False, return_cmd=False, interactive_mode=False, force_none_alias=False, shell=False):
    """
    Run bash command. Default behavior is to print output to stdout. If the command returns a non-zero
    return code, the function will exit with that return code.

    Args:
        display_cmd: Boolean; If True, will print the command being run to stdout before executing the command
        ignore_error: Boolean; If true, do not exit if command returns a non-zero return code
        return_cmd: Boolean; If true, the function will return the output, ignoring any non-zero return code
        interactive_mode: Boolean; If true, it will treat the process as a long-running process which may generate
                          multiple lines of output over time
        shell: Boolean; If true, the command will be run in a shell
    """
    if not shell:
        command_str = ' '.join(command)
    else:
        command_str = command
    if display_cmd == True:
        click.echo(click.style("Running command: ", fg='cyan') + click.style(command_str, fg='green'))

    # No conversion needed for intfutil commands as it already displays
    # both SONiC interface name and alias name for all interfaces.
    # IP route table cannot be handled in function run_command_in_alias_mode since it is in JSON format
    # with a list for next hops
    if not force_none_alias and get_interface_naming_mode() == "alias" and not command_str.startswith("intfutil") and not bgp_util.is_vtysh_cmd(command_str):
        output, rc = run_command_in_alias_mode(command, display_cmd=display_cmd, ignore_error=ignore_error, return_cmd=return_cmd, interactive_mode=interactive_mode, shell=shell)
        if return_cmd:
            return output, rc
        else:
            if rc != 0:
                sys.exit(rc)
            else:
                return

    proc = subprocess.Popen(command, shell=shell, text=True, stdout=subprocess.PIPE)

    if return_cmd:
        output = proc.communicate()[0]
        return output, proc.returncode

    if not interactive_mode:
        (out, err) = proc.communicate()

        if len(out) > 0:
            click.echo(out.rstrip('\n'))

        if proc.returncode != 0 and not ignore_error:
            sys.exit(proc.returncode)

        return

    # interactive mode
    while True:
        output = proc.stdout.readline()
        if output == "" and proc.poll() is not None:
            break
        if output:
            click.echo(output.rstrip('\n'))

    rc = proc.poll()
    if rc != 0:
        sys.exit(rc)


def json_serial(obj):
    """JSON serializer for objects not serializable by default"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def json_dump(data):
    """
    Dump data in JSON format
    """
    return json.dumps(
        data, sort_keys=True, indent=2, ensure_ascii=False, default=json_serial
    )


def interface_is_untagged_member(db, interface_name):
    """ Check if interface is already untagged member"""
    vlan_member_table = db.get_table('VLAN_MEMBER')

    for key,val in vlan_member_table.items():
        if(key[1] == interface_name):
            if (val['tagging_mode'] == 'untagged'):
                return True
    return False

def is_interface_in_config_db(config_db, interface_name):
    """ Check if an interface is in CONFIG DB """
    if (not interface_name in config_db.get_keys('VLAN_INTERFACE') and
        not interface_name in config_db.get_keys('INTERFACE') and
        not interface_name in config_db.get_keys('PORTCHANNEL_INTERFACE') and
        not interface_name in config_db.get_keys('VLAN_SUB_INTERFACE') and
        not interface_name == 'null'):
            return False

    return True

def get_traffic_manage_itm():
    hwsku = device_info.get_hwsku()
    if hwsku:
        if hwsku.startswith('Accton-AS9736') or hwsku.startswith('Accton-AS9737') or hwsku.startswith('Accton-AS9817'):
            return 2

        if hwsku.startswith('Accton-MINIPACK') or hwsku.startswith('Accton-AS9716-32D') or hwsku.startswith('Accton-AS9726-32D'):
            return 2

        if hwsku.startswith('Accton-AS7816') or hwsku.startswith('Accton-AS7712'):
            return 4

    return 1

class MutuallyExclusiveOption(click.Option):
    """
    This option type is extended with `mutually_exclusive` parameter which make
    CLI to ensure the other options specified in `mutually_exclusive` are not used.
    """

    def __init__(self, *args, **kwargs):
        self.mutually_exclusive = set(kwargs.pop('mutually_exclusive', []))
        super(MutuallyExclusiveOption, self).__init__(*args, **kwargs)

    def get_help_record(self, ctx):
        """Return help string with mutually_exclusive list added."""
        help_record = list(super(MutuallyExclusiveOption, self).get_help_record(ctx))
        if self.mutually_exclusive:
            mutually_exclusive_str = 'NOTE: this argument is mutually exclusive with arguments: %s' % ', '.join(self.mutually_exclusive)
            if help_record[-1]:
                help_record[-1] += ' ' + mutually_exclusive_str
            else:
                help_record[-1] = mutually_exclusive_str
        return tuple(help_record)

    def handle_parse_result(self, ctx, opts, args):
        if self.name in opts and opts[self.name] is not None:
            for opt_name in self.mutually_exclusive:
                if opt_name in opts and opts[opt_name] is not None:
                    raise click.UsageError(
                        "Illegal usage: %s is mutually exclusive with arguments %s" % (self.name, ', '.join(self.mutually_exclusive))
                        )
        return super(MutuallyExclusiveOption, self).handle_parse_result(ctx, opts, args)


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower().strip()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


class UserCache:
    """ General purpose cache directory created per user """

    CACHE_DIR = "/tmp/cache/"

    def __init__(self, app_name=None, tag=None):
        """ Initialize UserCache and create a cache directory if it does not exist.

        Args:
            tag (str): Tag the user cache. Different tags correspond to different cache directories even for the same user.
        """
        self.uid = os.getuid()
        self.app_name = os.path.basename(sys.argv[0]) if app_name is None else app_name
        self.cache_directory_suffix = str(self.uid) if tag is None else f"{self.uid}-{tag}"
        self.cache_directory_app = os.path.join(self.CACHE_DIR, self.app_name)

        prev_umask = os.umask(0)
        try:
            os.makedirs(self.cache_directory_app, exist_ok=True)
        finally:
            os.umask(prev_umask)

        self.cache_directory = os.path.join(self.cache_directory_app, self.cache_directory_suffix)
        os.makedirs(self.cache_directory, exist_ok=True)

    def get_directory(self):
        """ Return the cache directory path """
        return self.cache_directory

    def remove(self):
        """ Remove the content of the cache directory """
        shutil.rmtree(self.cache_directory)

    def remove_all(self):
        """ Remove the content of the cache for all users """
        shutil.rmtree(self.cache_directory_app)
