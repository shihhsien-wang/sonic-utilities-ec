"""
Module holding IP/VRF mock data for config CLI command of the syslog_test.py
"""

VRF_LIST = '''
[
    {
        "name": "mgmt"
    },
    {
        "name": "Vrf-Data"
    }
]
'''

VRF_MGMT_MEMBERS = '''
[
    {
        "ifname": "eth0"
    }
]
'''

VRF_DATA_MEMBERS = '''
[
    {
        "ifname": "Ethernet0"
    }
]
'''

IP_ADDR_LIST = '''
[
    {
        "ifname": "Ethernet0",
        "addr_info": [
            {
                "local": "1111::1111"
            }
        ]
    },
    {
        "ifname": "Loopback0",
        "addr_info": [
            {
                "local": "1.1.1.1"
            }
        ]
    },
    {
        "ifname": "eth0",
        "addr_info": [
            {
                "local": "3.3.3.3"
            }
        ]
    }
]
'''

def exec_cmd_mock(cmd):
    if cmd == 'ip --json vrf show':
        return VRF_LIST
    elif cmd == 'ip --json link show vrf mgmt':
        return VRF_MGMT_MEMBERS
    elif cmd == 'ip --json link show vrf Vrf-Data':
        return VRF_DATA_MEMBERS
    elif cmd == 'ip --json address show':
        return IP_ADDR_LIST
    raise Exception("{}: unknown command: {}".format(__name__, cmd))


DEFAULT_VRF_IP_NOT_FOUND_IP_ADDR_LIST = '''
[
    {
        "ifname": "Ethernet4",
        "addr_info": [
            {
                "local": "10.0.0.1"
            }
        ]
    },
    {
        "ifname": "Loopback0",
        "addr_info": [
            {
                "local": "1.1.1.1"
            }
        ]
    },
    {
        "ifname": "eth0",
        "addr_info": [
            {
                "local": "3.3.3.3"
            }
        ]
    }
]
'''

# Mock for test_config_syslog_source_ip_not_in_default_vrf
# Simulates '10.0.0.100' not being an IP in default VRF.
# Default VRF interfaces are those not part of any other VRF.
# Here, Ethernet4 and Loopback0 are in default VRF. eth0 is in mgmt.
def exec_cmd_mock_default_vrf_ip_not_found(cmd):
    if cmd == 'ip --json vrf show':
        return VRF_LIST # mgmt, Vrf-Data
    elif cmd == 'ip --json link show vrf mgmt':
        # eth0 is part of mgmt VRF
        return '''
[
    {
        "ifname": "eth0"
    }
]
'''
    elif cmd == 'ip --json link show vrf Vrf-Data':
        # No interfaces in Vrf-Data for this specific mock if not needed,
        # or some other interfaces. The key is that 10.0.0.100 is not on
        # Ethernet4 or Loopback0 based on IP_ADDR_LIST below.
        return '''
[
    {
        "ifname": "Ethernet0"
    }
]
'''
    elif cmd == 'ip --json address show':
        # 10.0.0.100 is NOT in this list on Ethernet4 or Loopback0
        return DEFAULT_VRF_IP_NOT_FOUND_IP_ADDR_LIST
    raise Exception("{}: unknown command in exec_cmd_mock_default_vrf_ip_not_found: {}".format(__name__, cmd))


SPECIFIED_VRF_IP_NOT_FOUND_IP_ADDR_LIST = '''
[
    {
        "ifname": "Ethernet0",
        "addr_info": [
            {
                "local": "20.0.0.1"
            }
        ]
    },
    {
        "ifname": "Ethernet8",
        "addr_info": [
            {
                "local": "20.0.0.200"
            }
        ]
    },
    {
        "ifname": "Loopback0",
        "addr_info": [
            {
                "local": "1.1.1.1"
            }
        ]
    },
    {
        "ifname": "eth0",
        "addr_info": [
            {
                "local": "3.3.3.3"
            }
        ]
    }
]
'''

# Mock for test_config_syslog_source_ip_not_in_specified_vrf
# Simulates '20.0.0.200' not being an IP in 'Vrf-Data'.
# Vrf-Data has Ethernet0 as a member. 20.0.0.200 is on Ethernet8 (not in Vrf-Data).
def exec_cmd_mock_specified_vrf_ip_not_found(cmd):
    if cmd == 'ip --json vrf show':
        return VRF_LIST # mgmt, Vrf-Data
    elif cmd == 'ip --json link show vrf mgmt':
        return VRF_MGMT_MEMBERS
    elif cmd == 'ip --json link show vrf Vrf-Data':
        # Vrf-Data has Ethernet0.
        return '''
[
    {
        "ifname": "Ethernet0"
    }
]
'''
    elif cmd == 'ip --json address show':
        # 20.0.0.200 is on Ethernet8, which is not in Vrf-Data
        return SPECIFIED_VRF_IP_NOT_FOUND_IP_ADDR_LIST
    raise Exception("{}: unknown command in exec_cmd_mock_specified_vrf_ip_not_found: {}".format(__name__, cmd))
