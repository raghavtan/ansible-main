#
# (c) 2015 Peter Sprygada, <psprygada@ansible.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

NET_COMMON_ARGS = dict(
    host=dict(required=True),
    port=dict(default=22, type='int'),
    username=dict(required=True),
    password=dict(no_log=True),
    provider=dict()
)

def to_list(val):
    if isinstance(val, (list, tuple)):
        return list(val)
    elif val is not None:
        return [val]
    else:
        return list()

class Cli(object):

    def __init__(self, module):
        self.module = module
        self.shell = None

    def connect(self, **kwargs):
        host = self.module.params['host']
        port = self.module.params['port'] or 22

        username = self.module.params['username']
        password = self.module.params['password']

        self.shell = Shell()

        try:
            self.shell.open(host, port=port, username=username, password=password)
        except Exception, exc:
            msg = 'failed to connecto to %s:%s - %s' % (host, port, str(exc))
            self.module.fail_json(msg=msg)

    def send(self, commands):
        return self.shell.send(commands)


class NetworkModule(AnsibleModule):

    def __init__(self, *args, **kwargs):
        super(NetworkModule, self).__init__(*args, **kwargs)
        self.connection = None
        self._config = None

    @property
    def config(self):
        if not self._config:
            self._config = self.get_config()
        return self._config

    def _load_params(self):
        params = super(NetworkModule, self)._load_params()
        provider = params.get('provider') or dict()
        for key, value in provider.items():
            if key in NET_COMMON_ARGS.keys():
                params[key] = value
        return params

    def connect(self):
        self.connection = Cli(self)
        self.connection.connect()
        if self.connection.shell._matched_prompt.strip().endswith('%'):
            self.execute('cli')
        self.execute('set cli screen-length 0')

    def configure(self, commands):
        commands = to_list(commands)
        commands.insert(0, 'configure')
        commands.append('commit and-quit')
        responses = self.execute(commands)
        responses.pop(0)
        responses.pop()
        return responses

    def execute(self, commands, **kwargs):
        return self.connection.send(commands)

    def disconnect(self):
        self.connection.close()

    def parse_config(self, cfg):
        return parse(cfg, indent=4)

    def get_config(self):
        cmd = 'show configuration'
        return self.execute(cmd)[0]

def get_module(**kwargs):
    """Return instance of NetworkModule
    """
    argument_spec = NET_COMMON_ARGS.copy()
    if kwargs.get('argument_spec'):
        argument_spec.update(kwargs['argument_spec'])
    kwargs['argument_spec'] = argument_spec
    kwargs['check_invalid_arguments'] = False

    module = NetworkModule(**kwargs)

    # HAS_PARAMIKO is set by module_utils/shell.py
    if not HAS_PARAMIKO:
        module.fail_json(msg='paramiko is required but does not appear to be installed')

    module.connect()
    return module

