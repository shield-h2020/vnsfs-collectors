Distributed Collector
========================================================================================================================================
The role of the Distributed Collector is similar, as it processes the data before transmission. Distributed Collector tracks a directory backwards for newly created files. When a file is detected, it converts it into CSV format and stores the output in the local staging area. Following to that, reads the CSV file line-by-line and creates smaller chunks of bytes. The size of each chunk depends on the maximum request size allowed by Kafka. Finally, it serializes each chunk into an Avro-encoded format and publishes them to Kafka cluster.<br />
Due to its architecture, Distributed Collector can run **on an edge node** of the Big Data infrastructure as well as **on a remote host** (proxy server, vNSF, etc).<br />
In addition, option `--skip-conversion` has been added. When this option is enabled, Distributed Collector expects already processed files in the CSV format. Hence, when it detects one, it does not apply any transformation; just splits it into chunks and transmits to the Kafka cluster.<br />
This option is also useful, when a segment failed to transmit to the Kafka cluster. By default, Distributed Collector stores the failed segment in CSV format under the local staging area. Then, using `--skip-conversion` option could be reloaded and sent to the Kafka cluster.<br />
Distributed Collector publishes to Apache Kafka only the CSV-converted file, and not the original one. The binary file remains to the local filesystem of the current host.

## Prerequisites
Dependencies in Python:
* [avro](https://avro.apache.org/) - Data serialization system.
* [kafka-python](https://github.com/dpkp/kafka-python) - Python client for the Apache Kafka distributed stream processing system.
* [watchdog](https://pypi.python.org/pypi/watchdog) - Python API and shell utilities to monitor file system events.

Dependencies in Linux OS:
* [pip](https://pypi.org/project/pip/) - Python package manager.

In addition, for processing some pipelines, it will be needed to install the appropriate tools:
* [spot-nfdump](https://github.com/Open-Network-Insight/spot-nfdump) - Nfdump version for processing netflow.
* [tshark](https://www.wireshark.org/download.html) - A part of wireshark distribution for processing pcap files.

## Installation
Installation of the Distributed Collector requires a user with `sudo` privileges.
1. Install packages from the given requirements file:<br />
  `sudo -H pip install -r requirements.txt`

2. Install package:<br />
  `sudo python setup.py install --record install-files.txt`

To uninstall Distributed Collector, just delete installation files:<br />
  `cat install-files.txt | sudo xargs rm -rf`

If you want to avoid granting `sudo` permissions to the user (or keeping isolated the current installation from the rest of the system), use the `virtualenv` package.
1. Install `virtualenv` package as `root` user:<br />
  `sudo apt-get -y install python-virtualenv`

2. Switch to your user and create an isolated virtual environment:<br />
  `virtualenv --no-site-packages venv`

3. Activate the virtual environment and install source distribution:<br />
  `source venv/bin/activate`<br />
  `pip install -r requirements.txt`<br />
  `python setup.py install`

## Configuration
After the installation, a configuration file (in `JSON` format) will be generated under the user's home directory (`~/.d-collector.json`).
    
    {
      "kerberos": {
        "kinit": "/usr/bin/kinit",
        "principal": "user",
        "keytab": "/opt/security/user.keytab"
      },
      "pipelines": {
        "dns": {
          "file_watcher": {
            "collector_path": "/collector/path",
            "recursive": "true",
            "supported_files": [".*.pcap"]
          },
          "local_staging": "/tmp",
          "process_opts": "-E separator=, -E header=y -E occurrence=f -T fields -e frame.time -e frame.time_epoch -e frame.len -e ip.src -e ip.dst -e dns.resp.name -e dns.resp.type -e dns.resp.class -e dns.flags.rcode -e dns.a 'dns.flags.response == 1'"
        },
        "flow": {
          "file_watcher": {
            "collector_path": "/collector/path",
            "recursive": "true",
            "supported_files": ["nfcapd.*"]
          },
          "local_staging": "/tmp",
          "process_opts": ""
        },
        "proxy": {
          "file_watcher": {
            "collector_path": "/collector/path",
            "recursive": "true",
            "supported_files": [".*.log"]
          },
          "local_staging": "/tmp",
          "process_opts": ""
        }
      },
      "interval": 1,
      "processes": 4,
      "producer": {
        "bootstrap_servers": ["kafka_server:kafka_port"],
        "max_request_size": 1048576
      }
    }

* _"kerberos"_: [Kerberos](https://web.mit.edu/kerberos/) is a network authentication protocol and in this section you can define its parameters. To enable this feature, you also need to set the environment variable `KRB_AUTH`.
* _"pipelines"_: For each pipeline, you need to define the same parameters:
  * _"file_watcher"_: An observer thread that monitors the `collector_path` directory, to detect new generated files. If the filenames match any pattern from the `supported_files` RegEx list, then they will be collected. If `recursive` is ``True``, then events will be emitted for sub-directories traversed recursively.
  * _"local_staging"_: Path to the staging area of the local file system. If it is empty, it will use the default system temporary directory.
  *_"process_opts"_: Additional command options for the conversion from binary to CSV format.
* _"interval"_: time interval (in seconds) at which detected files will be divided into batches. If it is empty, the default value is 5 seconds.
* _"processes"_: Distributed Collector uses `multiprocessing` module to collect and transmit files to Kafka cluster. This parameter defines the number of the parallel processes. If it is empty, the default value is the number of host's CPUs.
* _"producer"_: This section contains configuration parameters for the `KafkaProducer`.
  * _"bootstrap_servers"_: 'host[:port]' string (or list of 'host[:port]' strings) that the producer should contact to bootstrap initial cluster metadata.
  * _"max_request_size"_: Defines the maximum size of the chunks that are sent to Kafka cluster. If it is not set, then the default value that will be used is 1MB.<br />
Configuration parameters are described in more detail at https://kafka.apache.org/0100/configuration.html#producerconfigs.

**Example of Configuration file**<br />
An example of the configuration file for `flow` is given below:

    {
      "kerberos": {
        "kinit": "/usr/bin/kinit",
        "principal": "spotuser",
        "keytab": "/opt/security/spotuser.keytab"
      },
      "pipelines": {
        "flow": {
          "file_watcher": {
            "collector_path": "/var/collector",
            "recursive": "true",
            "supported_files": ["nfcapd.[0-9]{14}", "nfcapd.*.old]
          }
        }
      },
      producer": {
        "bootstrap_servers": ["cloudera01:9092"],
        "max_request_size": 4194304
      }
    }

This example only defines mandatory configurations - all other parameters get default values.

## Start Distributed Collector

### Print Usage Message
Before you start using the Distributed Collector, you should print the usage message and check the available options.

    usage: d-collector [OPTIONS]... -t <pipeline> --topic <topic>
    
    Distributed Collector transmits to Kafka cluster already processed files in a
    comma-separated (CSV) output format.
    
    Optional Arguments:
      -h, --help                       show this help message and exit
      -c FILE, --config-file FILE      path of configuration file
      -l STRING, --log-level STRING    determine the level of the logger
      -p INTEGER, --partition INTEGER  optionally specify a partition
      -s, --skip-conversion            no transformation will be applied to the
                                       data; useful for importing CSV files
      -v, --version                    show program's version number and exit
      
    Required Arguments:
      --topic STRING                   name of topic where the messages will be
                                       published
      -t STRING, --type STRING         type of data that will be collected
      
    END

The only mandatory arguments for the Distributed Collector are the topic and the type of the pipeline (`flow`, `dns` or `proxy`). Distributed Collector _does not create a new topic_, so you have to pass _an existing one_. By default, it loads configuration parameters from the `~/.d-collector.json` file, but you can override it with `-c FILE, --config-file FILE` option.

### Run `d-collector` Command
To start Distributed Collector:<br />
  `d-collector -t "pipeline_configuration" --topic "my_topic"`

Some examples are given below:<br />
1. `d-collector -t flow --topic SPOT-INGEST-TEST-TOPIC`<br />
2. `d-collector -t flow --topic SPOT-INGEST-TEST-TOPIC --partition 2 --config-file /tmp/another_ingest_conf.json`<br />
3. `d-collector -t proxy --topic SPOT-PROXY-TOPIC --log-level DEBUG`

### Acknowledgement
The work for this contribution has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement No700199.
