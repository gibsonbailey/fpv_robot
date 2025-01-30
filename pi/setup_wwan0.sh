sudo systemctl stop ModemManager
sudo systemctl stop NetworkManager

sudo ip link set wwan0 down
echo 'Y' | sudo tee /sys/class/net/wwan0/qmi/raw_ip
sudo ip link set wwan0 up

sudo qmicli -p -d /dev/cdc-wdm0   --device-open-net='net-raw-ip|net-no-qos-header'   --wds-start-network="apn='vzwinternet',ip-type=4"   --client-no-release-cid

sudo udhcpc -q -f -i wwan0

sudo systemctl start NetworkManager
