# 기본 준비
```
cd /home/thislifewon/dev/Mando2026_ws
colcon build
source install/setup.bash
sudo chmod 666 /dev/tty*
```
# Publisher
## `/encoder/*`
```
ros2 run ebimu_pkg encoder_publisher --ros-args -p serial_port:=/dev/ttyACM0
```

## `/imu/*`
```
ros2 run ebimu_pkg ebimu_publisher --ros-args -p serial_port:=/dev/ttyUSB0 -p baudrate:=115200
```

## `/odom`, `/odom_path`, `/tf`
```
ros2 run ebimu_pkg encoder_imu_odometry --ros-args --params-file src/ebimu_pkg/config/imu_only_params.yaml
```

## `/f9p/*`, `/ublox_gps_node/*`
```
ros2 launch ublox_gps ublox_f9p_launch.py serial_port:=/dev/ttyUSB0 baudrate:=115200
```

## `/f9r/*`, `/ublox_gps_node/*`
```
ros2 launch ublox_gps ublox_f9r_launch.py serial_port:=/dev/ttyUSB1 baudrate:=115200
```


# RVIZ
## RVIZ만 실행
```
rviz2 -d install/ebimu_pkg/share/ebimu_pkg/config/imu_odometry.rviz
```
## `/encoder/*`, `/imu/*`, `/odom`도 같이 실행
```
ros2 launch ebimu_pkg encoder_imu_rviz.launch.py
```

---
udev 작업 필요