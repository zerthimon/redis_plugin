redis_plugin
============

This is a collectd (<http://collectd.org/>) plugin which runs under the Python plugin (<https://collectd.org/wiki/index.php/Plugin:Python>) to collect metrics from redis (<http://redis.io/>).

Requirements:
------------

*Redis*  
This plugin requires an access to Redis.
UNIX Domain socket and TCP/IP communication are supported.

*collectd*  
Collectd must have the Python plugin installed. See (<https://collectd.org/wiki/index.php/Plugin:Python>)

Options:
-------
* `Socket`  
   Path to a UNIX Domain socket of the Redis instance.  
   When specified, takes over IP and PORT configuration.  
   Default: none  
* `IP`  
   IP Address of the Redis instance.  
   Default: none  
* `Port`  
   TCP Port of the Redis instance.  
   Default: 6379  
* `Auth`  
   Password to use when connecting to Redis instance.  
   Default: none  
* `Commandstats`  
   Include Redis command statistics, from "INFO COMMANDSTATS" command.  
   Default: false  
* `Verbose`  
   Provide verbose logging of plugin operation in the Collectd's log.  
   Default: false  
* `Instance`  
   There are situations when multiple instances of Redis needs to run on the same host.  

Single-instance Plugin Config Example:
-------
    TypesDB "/usr/share/collectd/redis_types.db"

    <LoadPlugin python>
        Globals true
    </LoadPlugin>

    <Plugin python>
        # redis_plugin.py is at /usr/lib64/collectd/redis_plugin.py
        ModulePath "/usr/lib64/collectd/"

        Import "redis_plugin"

        <Module redis_plugin>
          Socket "/var/run/redis.sock"
          Commandstats true
          Verbose false
        </Module>
    </Plugin>

Multi-instance Plugin Config Example:
----------------------
    TypesDB "/usr/share/collectd/redis_types.db"`

    <LoadPlugin python>
        Globals true
    </LoadPlugin>

    <Plugin python>
        # redis_plugin.py is at /usr/lib64/collectd/redis_plugin.py
        ModulePath "/usr/lib64/collectd/"

        Import "redis_plugin"

        <Module redis_plugin>
          <Instance redis1>
              Socket "/var/run/redis1.sock"
              Commandstats false
          </Instance>
          <Instance redis2>
              IP "127.0.0.1"
              Port 6379
              Auth "foobared"
              Commandstats true
          </Instance>
          Verbose false
        </Module>
    </Plugin>

Graph Examples:
--------------
These graphs were created using Graphite (<http://graphite.wikidot.com/>)

Connected Clients:
![Connected Clients](https://github.com/zerthimon/redis_plugin/raw/master/screenshots/redis_connected_clients.png)

Redis Process RSS Memory:
![Redis Process RSS Memory](https://github.com/zerthimon/redis_plugin/raw/master/screenshots/redis_memory_used_rss.png)

Commands per Second:
![Commands per Second](https://github.com/zerthimon/redis_plugin/raw/master/screenshots/redis_total_commands_per_sec.png)

Redis GET Commands per Second:
![Redis GET Commands per Second](https://github.com/zerthimon/redis_plugin/raw/master/screenshots/redis_get_commands_per_sec.png)

Cache Hits:
![Cache Hits](https://github.com/zerthimon/redis_plugin/raw/master/screenshots/redis_cache_hits.png)

RDB Changes Since Last Save:
![RDB Changes Since Last Save](https://github.com/zerthimon/redis_plugin/raw/master/screenshots/redis_changes_since_last_rdb_save.png)

Total Keys in db0:
![Total Keys in db0](https://github.com/zerthimon/redis_plugin/raw/master/screenshots/redis_db0_keys_total.png)
