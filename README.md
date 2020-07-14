# InfluxDBUploader 

Taurus plugin to stream results to InfluxDB, based on [signalfxUploader](https://github.com/doctornkz/signalfxUploader) from [@doctornkz](https://github.com/doctornkz)

## Installation

```bash
git clone https://github.com/johnnybus/influxDBUploader.git
cd influxDBUploader/
pip install .
```

## Example of configuration file

```ini
execution:
- executor: pbench
  concurrency: 100
  ramp-up: 1m
  hold-for: 10m
  iterations: 5
  throughput: 10
  scenario: simple_usage

scenarios:
  simple_usage:  
    default-address: https://example.com:443/
    requests:
    - /

reporting:
  - module: signalfx

modules:
  console:
    disable: true
  influxdbuploader:
    influxdb-address:   # influxdb address
    influxdb-port:      # influxdb port
    influxdb-user:      # influxdb username which can also be defined in envrironemnt variables INFLUXDB_USER
    influxdb-password:  # influxdb password which can also be defined in envrironemnt variables INFLUXDB_PASSWORD
    influxdb-database:  # influxdb database
    dashboard-url:      # grafana dashboard url


    project: my-test # project will be used in tags
    browser-open: none  # auto-open the report in browser, 
                         # can be "start", "end", "both", "none"
    send-interval: 10s   # send data each n-th second
    timeout: 5s  # connect and request timeout for BlazeMeter API
    custom-tags:
      in_development: true # custom tags
```

## InfluxDB Authentification

You can use:

- `INFLUXDB_USER` and `INFLUXDB_PASSWORD` environment variable to pass the credentials
- `influxdb-user` and `influxdb-password` from configuration file (see example above)

## Starting

```bash
(py36) ➜  loadtest bzt load.yaml
10:06:50 INFO: Taurus CLI Tool v1.14.2
10:06:50 INFO: Starting with configs: ['load.yaml']
10:06:50 INFO: Configuring...
10:06:50 INFO: Artifacts dir: /Users/joao.carreira/Desktop/loadtest
10:06:50 INFO: Preparing...
10:06:55 INFO: Credentials found in config file
10:06:55 INFO: Starting...
10:06:55 INFO: Waiting for results...
10:06:55 INFO: Started data feeding: 
10:07:02 INFO: Current: 2 vu	2 succ	0 fail	0.649 avg rt	/	Cumulative: 0.649 avg rt, 0% failures
10:07:03 INFO: Current: 5 vu	18 succ	0 fail	0.192 avg rt	/	Cumulative: 0.238 avg rt, 0% failures
10:07:04 INFO: Current: 7 vu	27 succ	0 fail	0.207 avg rt	/	Cumulative: 0.220 avg rt, 0% failures
10:07:05 INFO: Current: 9 vu	42 succ	0 fail	0.180 avg rt	/	Cumulative: 0.201 avg rt, 0% failures
10:07:06 INFO: Current: 10 vu	51 succ	0 fail	0.194 avg rt	/	Cumulative: 0.198 avg rt, 0% failures
10:07:07 INFO: Current: 10 vu	52 succ	0 fail	0.186 avg rt	/	Cumulative: 0.195 avg rt, 0% failures
10:07:08 INFO: Current: 10 vu	57 succ	0 fail	0.185 avg rt	/	Cumulative: 0.193 avg rt, 0% failures
10:07:09 INFO: Current: 10 vu	57 succ	0 fail	0.170 avg rt	/	Cumulative: 0.189 avg rt, 0% failures
10:07:10 INFO: Current: 10 vu	54 succ	0 fail	0.189 avg rt	/	Cumulative: 0.189 avg rt, 0% failures
10:07:11 INFO: Current: 10 vu	59 succ	0 fail	0.166 avg rt	/	Cumulative: 0.185 avg rt, 0% failures
10:07:12 INFO: Current: 10 vu	60 succ	0 fail	0.176 avg rt	/	Cumulative: 0.184 avg rt, 0% failures
10:07:13 INFO: Current: 10 vu	55 succ	0 fail	0.170 avg rt	/	Cumulative: 0.183 avg rt, 0% failures
10:07:14 INFO: Current: 10 vu	61 succ	0 fail	0.176 avg rt	/	Cumulative: 0.182 avg rt, 0% failures
10:07:15 INFO: Current: 10 vu	57 succ	0 fail	0.170 avg rt	/	Cumulative: 0.181 avg rt, 0% failures
10:07:16 INFO: Current: 10 vu	55 succ	0 fail	0.165 avg rt	/	Cumulative: 0.180 avg rt, 0% failures
10:07:17 INFO: Current: 10 vu	53 succ	0 fail	0.188 avg rt	/	Cumulative: 0.180 avg rt, 0% failures
10:07:18 INFO: Current: 10 vu	60 succ	0 fail	0.175 avg rt	/	Cumulative: 0.180 avg rt, 0% failures
10:07:19 INFO: Current: 10 vu	56 succ	0 fail	0.174 avg rt	/	Cumulative: 0.180 avg rt, 0% failures
10:07:20 INFO: Current: 6 vu	54 succ	0 fail	0.173 avg rt	/	Cumulative: 0.179 avg rt, 0% failures
10:07:20 WARNING: Please wait for graceful shutdown...
10:07:20 INFO: Shutting down...
10:07:20 INFO: Post-processing...
10:07:20 INFO: Test duration: 0:00:25
10:07:20 INFO: Samples count: 1000, 0.00% failures
10:07:20 INFO: Average times: total 0.178, latency 0.178, connect 0.029
10:07:20 INFO: Percentiles:
┌───────────────┬───────────────┐
│ Percentile, % │ Resp. Time, s │
├───────────────┼───────────────┤
│           0.0 │         0.131 │
│          50.0 │         0.146 │
│          90.0 │         0.221 │
│          95.0 │         0.458 │
│          99.0 │         0.502 │
│          99.9 │         0.574 │
│         100.0 │         0.829 │
└───────────────┴───────────────┘
10:07:20 INFO: Request label stats:
┌───────┬────────┬─────────┬────────┬───────┐
│ label │ status │    succ │ avg_rt │ error │
├───────┼────────┼─────────┼────────┼───────┤
│ Hello │   OK   │ 100.00% │  0.178 │       │
└───────┴────────┴─────────┴────────┴───────┘
10:07:20 INFO: Sending remaining KPI data to server...
10:07:21 INFO: Report link: 
10:07:21 INFO: Artifacts dir: /Users/vladimir.patato/loadtest
10:07:21 INFO: Done performing with code: 0
```

## Dashboard example

![Dashboard](/promo/dashboard_example.png)
