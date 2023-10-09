# plug2mqtt

Publish smart plug state to MQTT. Specifically and currently this works for P110 only.

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

Opionally, the config can be extended with abitrary dictionary, like so:

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
