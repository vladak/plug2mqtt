# plug2mqtt

Publish smart plug state to MQTT. Specifically and currently this works with Tapo P110 only.

## Install

- clone the repository to `/srv/plug2mqtt`
- create Python environment
```
  cd /srv/plug2mqtt
  python3 -m venv venv
```
- install requirements
```
  . ./venv/bin/activate
  python3 -m pip install -r requirements.txt
```
- install the service
```
  sudo cp /srv/plug2mqtt/plug2mqtt.service /etc/systemd/system/
  sudo systemctl enable plug2mqtt
  sudo systemctl daemon-reload
  sudo systemctl start plug2mqtt
  systemctl status plug2mqtt
```

## Prometheus

If the metrics published are to be available in Prometheus, the MQTT exporter configuration
in `/etc/prometheus/mqtt-exporter.yaml` needs to be augmented with:
```yaml
matrics:
  -
    # The name of the metric in prometheus
    prom_name: power
    # The name of the metric in a MQTT JSON message
    mqtt_name: current_power
    # The prometheus help text for this metric
    help: power in Watts
    # The prometheus type for this metric. Valid values are: "gauge" and "counter"
    type: gauge
  -
    # The name of the metric in prometheus
    prom_name: today_energy
    # The name of the metric in a MQTT JSON message
    mqtt_name: today_energy
    # The prometheus help text for this metric
    help: energy for one day in Wh
    # The prometheus type for this metric. Valid values are: "gauge" and "counter"
    type: counter
```

## Setup

The `plugs.json` configuration file should look like this:
```json
[
  {
    "topic": "devices/plug/kitchen",
    "username": "foo@bar",
    "password": "Changeme",
    "hostname": "foo.iot"
  },
  {
    "topic": "devices/plug/cellar",
    "username": "foo@bar",
    "password": "Changeme",
    "hostname": "bar.iot"
  },
]
```

Opionally, the config can be extended with abitrary dictionary (as long as it does not contain reserved keys: `on` or `current_power`), like so:

```json
[
  {
    "topic": "devices/plug/kitchen",
    "username": "foo@bar",
    "password": "Changeme",
    "hostname": "foo.iot",
    "data": {"foo", "bar"}
  }
]
```
