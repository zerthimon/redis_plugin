# -*- coding: utf-8 -*-
# redis collectd plugin - redis_plugin.py
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; only version 2 of the License is applicable.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#
# Author: 
#     Lior Goikhburg <goikhburg at gmail.com >
#
# Description:
#     This is a collectd plugin which runs under the Python plugin to
#     collect metrics from redis.
#
# collectd:
#     http://collectd.org
#
# Redis:
#     http://redis.io
#
# collectd-python:
#     https://collectd.org/wiki/index.php/Plugin:Python
#
# Inspired by:
#
# Michael Leinartas' Haproxy plugin:
#     https://github.com/mleinart/collectd-haproxy
#
# Garret Heaton's Redis plugin:
#     https://github.com/powdahound/redis-collectd-plugin
#
# Redis API handling and functions code parts were taken from:
# Abdelkader ALLAM's Desir:
#     https://github.com/aallamaa/desir

import collectd
import socket

NAME = 'redis'

# map of collectd data sets to lists of data sources as defined in redis_types.db
INFO_STATS_MAP = {
    'clients': ['connected_clients', 'blocked_clients'],
    'connected_slaves': ['connected_slaves'],
    'redis_connections': ['rejected_connections', 'total_connections_received'],
    'redis_keys': ['expired_keys', 'evicted_keys'],
    'keyspace': ['keyspace_misses', 'keyspace_hits'],
    'last_save': ['rdb_last_bgsave_time_sec', 'aof_last_rewrite_time_sec', 'rdb_changes_since_last_save'],
    'redis_memory': ['used_memory', 'used_memory_lua', 'used_memory_peak',
                     'used_memory_rss', 'mem_fragmentation_ratio'],
    'commands_per_sec': ['instantaneous_ops_per_sec'],
    'pubsub': ['pubsub_channels', 'pubsub_patterns'],
    'uptime_in_seconds': ['uptime_in_seconds'],
    'cpu_used': ['used_cpu_user_children', 'used_cpu_sys', 'used_cpu_sys_children', 'used_cpu_user'],
    'expires': ['expires'],
    'total': ['keys'],
    'avg_ttl': ['avg_ttl'],
    'calls': ['calls'],
    'usec_per_call': ['usec_per_call']}

METRIC_DELIM = '.'

def logger(level, message):
    if level == 'err':
        collectd.error("%s: %s" % (NAME, message))
    elif level == 'warn':
        collectd.warning("%s: %s" % (NAME, message))
    elif level == 'verb':
        if CONFIG_INSTANCES['root_config']['VERBOSE_LOGGING']:
            collectd.info("%s: %s" % (NAME, message))
    else:
        collectd.notice("%s: %s" % (NAME, message))

class RedisError(Exception):
    pass

class ServerError(Exception):
    pass

class RedisSocket(object):
    def __init__(self, socket_file=None, ip=None, port=None, auth=None):
        self.socket_file = socket_file
        self.ip = ip
        self.port = port
        self.auth = auth
        self._socket = None
        self._handler = None
        self.endpoint = ''

    def connect(self):
        """ Connects to redis on UNIX Domain socket or on TCP port """

        if self._handler is not None:
            return

        try:
            if self.ip:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.connect((self.ip, self.port))
                self.endpoint = "%s:%s" % (self.ip, self.port)
            elif self.socket_file:
                self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self._socket.connect(self.socket_file)
                self.endpoint = self.socket_file
            self._handler = self._socket.makefile()

        except socket.error as error:
            self.disconnect()
            if len(error.args) == 1:
                raise ServerError("Error connecting to redis on %s: %s." % (self.endpoint,
                                                                               error.args[0]))
            else:
                raise ServerError("Error %s connecting to redis on %s: %s." % (error.args[0],
                                                                                   self.endpoint, 
                                                                                   error.args[1]))
        finally:
            if self._handler is not None:
                if self.auth is not None:
                    if not self.send_command("auth %s" % (self.auth)):
                        self.disconnect()
                        raise RedisError('Redis plugin: AUTH command failed')
                # issue an "empty" command to validate connection
                self.send_command('select 0')

    def disconnect(self):
        if self._socket:
            try:
                self._socket.close()
            except socket.error:
                pass
            finally:
                self._socket = None
                self._handler = None

    def write_line(self, message):
        """ Write a single line to the socket """

        self.connect()

        try:
            self._handler.write(message + '\r\n')
            self._handler.flush()
        except socket.error as error:
            self.disconnect()
            if len(error.args) == 1:
                raise ServerError("Error sending data to redis on %s: %s" % (self.endpoint,
                                                                                 error.args[0]))
            else:
                raise ServerError("Error %s sending data to redis on %s: %s." % (error.args[0],
                                                                                     self.endpoint,
                                                                                     error.args[1]))

    def read_line(self):
        """ Read a line from redis and handle it according to message type """

        try:
            response = self._handler.readline()
        except socket.error as error:
            self.disconnect()
            if len(error.args) == 1:
                raise ServerError("Error reading data from redis on %s: %s" % (self.endpoint,
                                                                                   error.args[0]))
            else:
                raise ServerError("Error %s reading data from redis on %s: %s." % (error.args[0],
                                                                                       self.endpoint,
                                                                                       error.args[1]))

        if response[:-2] in ["$-1", "*-1"]:
            return None

        msg_type, response = response[0], response[1:]
        if msg_type == "+":
            return response[:-2]
        elif msg_type == "-":
            raise RedisError(response.strip())
        elif msg_type == "$":
            try:
                response = self._handler.read(int(response))
                self._handler.read(2)
                return response.strip()
            except socket.error as error:
                self.disconnect()
                if len(error.args) == 1:
                    raise ServerError("Error reading data from redis on %s: %s" % (self.endpoint,
                                                                                       error.args[0]))
                else:
                    raise ServerError("Error %s reading data from redis on %s: %s." % (error.args[0],
                                                                                           self.endpoint,
                                                                                           error.args[1]))
        else:
            raise RedisError("Unknown redis message type %s" % (msg_type))

    def send_command(self, command):
        self.write_line(command)
        return self.read_line()


def info2dict(info_lines):
    """ Parse response from Redis into a Dict """

    metric_dict = {}
    for line in info_lines.splitlines():
        if not line:
            continue

        # sections in INFO command stat with #
        if line.startswith('#'):
            metric_section = line.split(' ')[1]
            continue

        if ':' not in line:
            logger('warn', "Bad format for info line: %s" % (line))
            continue

        metric_name, metric_value = line.split(':')

        # Handle multi-value keys (like dbs and cmdstats).
        # db lines look like "db0:keys=10,expire=0"
        # cmdstats lines look like "cmdstat_ping:calls=1,usec=2,usec_per_call=2.00"
        if ',' in metric_value:
            new_section = METRIC_DELIM.join([metric_section, metric_name])
            if new_section.startswith('Commandstats'):
                new_section = new_section.replace('cmdstat_', '')
            if new_section not in metric_dict:
                metric_dict[new_section] = {}
            for sub_value in metric_value.split(','):
                key, _, value = sub_value.rpartition('=')
                metric_dict[new_section][key] = value
        else:
            if metric_section not in metric_dict:
                metric_dict[metric_section] = {}
            metric_dict[metric_section][metric_name] = metric_value
    return metric_dict


def get_metric(metric_dict, metric_name):
    """ find metric in dict, return it's value and section """

    found_values = []
    for section_name, section_data in metric_dict.iteritems():
        if metric_name in section_data:
            found_values.append((section_data[metric_name], section_name))
    return found_values


def get_stats(config_data):
    """ sends commands to redis and returns a dict of results to callback read function """

    redis = RedisSocket(socket_file=config_data['REDIS_SOCKET'],
                        ip=config_data['REDIS_IP'],
                        port=config_data['REDIS_PORT'],
                        auth=config_data['REDIS_AUTH'])

    data = ''
    collectd_stats = {}
    try:
        redis.connect()
    except Exception as error:
        logger('err', "Could not connect to redis: %s" % (error.message))
        return collectd_stats
    logger('verb', "Connected to redis on %s" % (redis.endpoint))

    logger('verb', "Sending 'INFO' command")
    try:
        data += redis.send_command('info')
    except Exception as error:
        logger('err', "Error while sending 'INFO' command: %s" % (error.message))

    if config_data['COMMANDSTATS']:
        logger('verb', "Sending 'INFO COMMANDSTATS' command")
        try:
            data += "\n" + redis.send_command('info commandstats')
        except Exception as error:
            logger('err', "Error while sending 'INFO COMMANDSTATS' command: %s" % (error.message))

    metric_dict = info2dict(data)

    for data_set, data_sources in INFO_STATS_MAP.iteritems():
        for data_source in data_sources:
            metric_data = get_metric(metric_dict, data_source)
            if metric_data is not None:
                for metric_value, section_name in metric_data:
                    if section_name not in collectd_stats:
                        collectd_stats[section_name] = {}
                    if data_set not in collectd_stats[section_name]:
                        collectd_stats[section_name][data_set] = []
                    collectd_stats[section_name][data_set].append(float(metric_value))

    return collectd_stats


def get_instance_config(config_child):
    """ builds per-instance config dict from collectd config data """

    instance_config = {
        'REDIS_SOCKET': None,
        'REDIS_IP': '127.0.0.1',
        'REDIS_PORT': 6379,
        'REDIS_AUTH': None,
        'COMMANDSTATS': False,
        'VERBOSE_LOGGING': False}

    for node in config_child.children:
        if node.key == "Socket":
            instance_config['REDIS_SOCKET'] = node.values[0]
            instance_config['REDIS_IP'] = None
            instance_config['REDIS_PORT'] = None
        elif node.key == "IP":
            instance_config['REDIS_IP'] = node.values[0]
            instance_config['REDIS_SOCKET'] = None
        elif node.key == "Port":
            instance_config['REDIS_PORT'] = int(node.values[0])
            instance_config['REDIS_SOCKET'] = None
        elif node.key == "Auth":
            instance_config['REDIS_AUTH'] = node.values[0]
        elif node.key == "Commandstats":
            instance_config['COMMANDSTATS'] = bool(node.values[0])
        elif node.key == "Verbose":
            instance_config['VERBOSE_LOGGING'] = bool(node.values[0])
        elif node.key == "Instance":
            continue
        else:
            logger('warn', "Unknown config key: %s" % (node.key))
    return instance_config


def configure_callback(conf):
    """
    process config provided by collectd config callback, handles instances
    and root configs
    """

    global CONFIG_INSTANCES
    CONFIG_INSTANCES = {}

    for node in conf.children:
        if node.children:
            # instance config
            if node.key == 'Instance':
                instance_name = node.values[0]
            else:
                instance_name = node.key
            CONFIG_INSTANCES[instance_name] = get_instance_config(node)
        else:
            # root config
            CONFIG_INSTANCES['root_config'] = get_instance_config(conf)


def read_callback():
    """ read callback gathers data and dispatches values to collectd """

    logger('verb', "beginning read_callback")

    collectd_stats = {}
    for instance_name, instance_config in CONFIG_INSTANCES.iteritems():
        if instance_name == 'root_config':
            if len(CONFIG_INSTANCES) == 1:
                collectd_stats['root'] = get_stats(instance_config)
                if not collectd_stats['instance']:
                    logger('err', 'No data received from Redis')
        else:
            collectd_stats[instance_name] = get_stats(instance_config)
            if not collectd_stats[instance_name]:
                logger('warn', "No data received from redis instance %s" % (instance_name))

    for instance_name, instance_data in collectd_stats.iteritems():
        for section_name, data_sets in instance_data.iteritems():
            for data_set, values in data_sets.iteritems():
                metric_prefix = NAME
                if instance_name != 'root':
                    metric_prefix = METRIC_DELIM.join([metric_prefix, instance_name])
                metric_prefix = METRIC_DELIM.join([metric_prefix, section_name]) 

                logger('verb', "dispatching values - plugin_name: %s, type: %s, values: %s" % (
                    metric_prefix, data_set, ", ".join([str(i) for i in values])))

                val = collectd.Values(plugin=metric_prefix.lower(), type=data_set)
                val.values = values
                val.dispatch()

# register collectd plugins
collectd.register_config(configure_callback)
collectd.register_read(read_callback)
