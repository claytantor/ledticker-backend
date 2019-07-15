# ledticker-backend
making a flashlex backend to send messages to the led device

## installing python3

```
python3 -m venv venv --system-site-packages
source venv/bin/activate
python3 -m pip install --user --upgrade pip
pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3
import ssl
print (ssl.OPENSSL_VERSION)
OpenSSL 1.1.0j  20 Nov 2018
```

## creating the systemd service
Instructions for setting up your service can be found at https://www.raspberrypi-spy.co.uk/2015/10/how-to-autorun-a-python-script-on-boot-using-systemd/

```
sudo cp ledtickerbe.service /lib/systemd/system/ledtickerbe.service
sudo chmod 644 /lib/systemd/system/ledtickerbe.service
sudo systemctl daemon-reload
sudo systemctl enable ledtickerbe.service
```

## add logging to syslog

Then, assuming your distribution is using rsyslog to manage syslogs, create a file in /etc/rsyslog.d/<new_file>.conf with the following content:

```
if $programname == '<your program identifier>' then /path/to/log/file.log
& stop
```

restart rsyslog (sudo systemctl restart rsyslog) and enjoy! Your program stdout/stderr will still be available through journalctl  `(sudo journalctl -u <your program identifier>)` but they will also be available in your file of choice.

We have included a conf file that makes this easier. Use the 
instructions below to enable rsyslog for ledtickerbe.

```
sudo cp ledtickerbe.conf /etc/rsyslog.d/ledtickerbe.conf
sudo systemctl daemon-reload
sudo systemctl restart ledtickerbe.service
sudo systemctl restart rsyslog
```

## check the status of the service
```
sudo systemctl status ledtickerbe.service
```

## rotating logs
you will want to rotate logs so your disk doesnt fill up with logs. your conf file for logrotation looks like this in `/etc/logrotate.conf`:

```
/var/log/ledtickerbe.log {
    daily
    missingok
    rotate 7
    maxage 7
    dateext
    dateyesterday
}
```

make a crontab that executes logrotate daily

```
/usr/sbin/logrotate /etc/logrotate.conf
```
