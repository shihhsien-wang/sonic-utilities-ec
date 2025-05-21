#!/usr/bin/env python

import sys
import click
import logging
from show.main import cli as show_main_cli
from config.main import config
from clear.main import cli as clear_main_cli

logger = logging.getLogger('sonic-cli-list')
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def get_command_group_name(cli_command_group):
    if hasattr(cli_command_group, 'name') and cli_command_group.name:
        return cli_command_group.name
    elif hasattr(cli_command_group, '__name__'):
        return cli_command_group.__name__
    elif hasattr(cli_command_group, '__class__'):
        return cli_command_group.__class__.__name__
    else:
        return "unknown commands"

def extract_click_commands_info(group, parent_name=''):
    commands_info = {}
    command_group_name = get_command_group_name(group)
    for name, command in group.commands.items():
        if parent_name is not None:
            full_name = f"{parent_name} {name}".strip()
        else:
            full_name = f"{parent_name} {name}".strip()
        commands_info[full_name] = {
            'arguments': [],
            'options': []
        }

        for param in command.params:
            if isinstance(param, click.Argument):
                arg_info = {
                    'name': param.name,
                    'choices': None
                }
                if isinstance(param.type, click.Choice):
                    arg_info['choices'] = param.type.choices
                commands_info[full_name]['arguments'].append(arg_info)

            elif isinstance(param, click.Option):
                opt_info = {
                    'opts': param.opts,
                    'choices': None
                }
                if isinstance(param.type, click.Choice):
                    opt_info['choices'] = param.type.choices
                commands_info[full_name]['options'].append(opt_info)

        if isinstance(command, click.core.Group):
            commands_info.update(extract_click_commands_info(command, full_name))

    return commands_info

def print_commands_info(commands_info, title, print_type="all"):
    sorted_commands = sorted(commands_info.items(), key=lambda x: x[0])

    for command, info in sorted_commands:
        command_str = f"{title} {command}"

        arg_strs = []
        for arg in info['arguments']:
            arg_desc = f"argument: {arg['name']}"
            if arg['choices']:
                arg_desc += f" (Choices: {', '.join(arg['choices'])})"
            arg_strs.append(arg_desc)
        arg_str = " ".join(arg_strs) if arg_strs else "argument: None"

        opt_strs = []
        for opt in info['options']:
            opt_desc = f"option: {', '.join(opt['opts'])}"
            if opt['choices']:
                opt_desc += f" (Choices: {', '.join(opt['choices'])})"
            opt_strs.append(opt_desc)
        opt_str = " ".join(opt_strs) if opt_strs else "option: None"

        if print_type == "all":
            print(f"{command_str} [{arg_str}] [{opt_str}]")
        elif print_type == "argument":
            print(f"{command_str} [{arg_str}]")
        else:
            print(f"{command_str} [{opt_str}]")

@click.group()
@click.pass_context
def cli(ctx):
    pass

@cli.command()
@click.argument('print_type', default='all', type=click.Choice(['argument', 'option', 'all'], case_sensitive=False))
@click.pass_context
def show(ctx, print_type):
    show_main_commands_info = extract_click_commands_info(show_main_cli)
    print("Show Main Commands Info:")
    print_commands_info(show_main_commands_info, "show", print_type)

    config_main_commands_info = extract_click_commands_info(config)
    print("\nConfig Main Commands Info:")
    print_commands_info(config_main_commands_info, "config", print_type)

    clear_main_commands_info = extract_click_commands_info(clear_main_cli)
    print("\nClear Main Commands Info:")
    print_commands_info(clear_main_commands_info, "clear", print_type)


if __name__ == '__main__':
    cli()
