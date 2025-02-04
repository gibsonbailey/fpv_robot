set -x
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1

sudo systemctl stop ModemManager
sudo systemctl stop NetworkManager

sudo ip link set wwan0 down
echo 'Y' | sudo tee /sys/class/net/wwan0/qmi/raw_ip
sudo ip link set wwan0 up

sudo qmicli -p -d /dev/cdc-wdm0   --device-open-net='net-raw-ip|net-no-qos-header'   --wds-start-network="apn='vzwinternet',ip-type=4"   --client-no-release-cid

sudo udhcpc -q -f -i wwan0

sudo ip route

sudo systemctl start NetworkManager

# sudo ip route del default via 192.168.0.1 dev wlan0

sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1

set +x
