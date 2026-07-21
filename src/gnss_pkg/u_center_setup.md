# gnss_pkg

`gnss_pkg`는 ROS 2 Humble 환경에서 u-blox GNSS 수신기와 NTRIP 보정 데이터를 함께 사용하기 위한 패키지 모음입니다.

일반 GNSS 수신기는 위성 신호만으로 위치를 계산하므로 주변 환경, 대기 오차, 위성 궤도 오차 등에 의해 수 m 수준의 오차가 발생할 수 있습니다. RTK(Real-Time Kinematic)를 사용하면 기준국에서 생성한 RTCM 보정 데이터를 수신기에 전달하여 더 높은 정확도의 위치를 얻을 수 있습니다. 이 패키지는 그 과정을 ROS 2 토픽으로 연결합니다.

## 전체 동작 흐름

이 패키지의 핵심 흐름은 다음과 같습니다.

```text
u-blox GNSS receiver
  -> ublox_gps node
  -> /f9p/fix or /f9r/fix
  -> fix2nmea node
  -> /ntrip_client/nmea
  -> NTRIP caster
  -> /ntrip_client/rtcm
  -> ublox_gps node
  -> u-blox GNSS receiver
```

각 단계의 의미는 아래와 같습니다.

1. `ublox_gps` 노드는 u-blox 수신기에서 현재 GNSS 위치를 읽어 ROS 2 `NavSatFix` 메시지로 publish합니다.
2. `fix2nmea` 노드는 `NavSatFix` 메시지를 NTRIP 서버가 요구하는 NMEA GGA 문장으로 변환합니다.
3. `ntrip_client` 노드는 NMEA 문장을 NTRIP caster에 보내고, caster로부터 RTCM 보정 데이터를 받아옵니다.
4. `ntrip_client`가 publish한 RTCM 메시지는 다시 `ublox_gps` 노드로 전달됩니다.
5. `ublox_gps` 노드는 RTCM 보정 데이터를 실제 u-blox 수신기에 써서 RTK 보정이 적용되도록 합니다.

즉, GNSS 수신기의 대략적인 현재 위치를 NTRIP 서버에 알려주고, NTRIP 서버가 해당 위치에 맞는 보정 데이터를 보내주면, 그 보정 데이터를 다시 GNSS 수신기에 넣어 위치 정확도를 높이는 구조입니다.

## 포함된 주요 패키지

### 1. u-blox Driver

u-blox 드라이버는 KumarRobotics의 `ublox` ROS 패키지를 기반으로 합니다.

원본 저장소: <https://github.com/KumarRobotics/ublox.git>

이 드라이버는 u-blox 수신기와 시리얼 통신을 수행하고, 수신기에서 나오는 UBX 메시지를 ROS 2 메시지로 변환합니다. 이 워크스페이스에서는 주로 ZED-F9P 또는 ZED-F9R 수신기를 rover로 사용하는 구성을 제공합니다.

주요 파일은 다음과 같습니다.

- `ublox_gps/launch/ublox_f9p_launch.py`: ZED-F9P 실행용 launch 파일
- `ublox_gps/launch/ublox_f9r_launch.py`: ZED-F9R 실행용 launch 파일
- `ublox_gps/config/zed_f9p.yaml`: ZED-F9P 파라미터 설정
- `ublox_gps/config/zed_f9r.yaml`: ZED-F9R 파라미터 설정

기본 실행 명령은 다음과 같습니다.

```bash
ros2 launch ublox_gps ublox_f9p_launch.py
```

또는 ZED-F9R을 사용할 경우:

```bash
ros2 launch ublox_gps ublox_f9r_launch.py
```

기본 시리얼 포트는 launch 파일에 다음처럼 설정되어 있습니다.

- ZED-F9P: `/dev/ttyACM1`
- ZED-F9R: `/dev/ttyACM0`

장치 포트가 다르면 launch 실행 시 직접 지정할 수 있습니다.

```bash
ros2 launch ublox_gps ublox_f9p_launch.py serial_port:=/dev/ttyACM0 baudrate:=115200
```

u-blox 노드는 RTCM 보정 데이터를 받기 위해 `/ntrip_client/rtcm` 토픽을 구독합니다. 이 토픽으로 들어온 `rtcm_msgs/msg/Message` 데이터는 `gps_->sendRtcm(...)`을 통해 실제 수신기로 전달됩니다.

### 2. NTRIP Client

NTRIP Client는 LORD-MicroStrain의 ROS 2 패키지를 기반으로 합니다.

원본 저장소: <https://github.com/LORD-MicroStrain/ntrip_client.git>

NTRIP은 인터넷을 통해 기준국 보정 데이터(RTCM)를 받아오기 위한 프로토콜입니다. 여기서 `ntrip_client` 노드는 NTRIP caster에 접속하여 RTCM 데이터를 받아오고, ROS 2 토픽으로 publish합니다.

주요 파일은 다음과 같습니다.

- `ntrip_client/launch/ntrip_client_launch.py`: NTRIP 접속 정보와 노드 실행 설정
- `ntrip_client/scripts/ntrip_ros.py`: ROS 2 노드 구현
- `ntrip_client/src/ntrip_client/ntrip_client.py`: 실제 NTRIP 서버 접속 로직

기본 실행 명령은 다음과 같습니다.

```bash
ros2 launch ntrip_client ntrip_client_launch.py
```

launch 파일에서 설정하는 주요 값은 다음과 같습니다.

- `host`: NTRIP caster 주소
- `port`: NTRIP caster 포트, 일반적으로 `2101`
- `mountpoint`: 사용할 기준국 또는 보정 스트림 이름
- `authenticate`: 계정 인증 사용 여부
- `username`: NTRIP 계정 이름
- `password`: NTRIP 계정 비밀번호
- `rtcm_message_package`: RTCM 메시지 타입 선택, 이 패키지에서는 `rtcm_msgs` 사용

현재 launch 파일은 기본값으로 `www.gnssdata.or.kr`, `2101`, `SOUL-RTCM32`를 사용하도록 되어 있습니다. 다른 기준국이나 계정을 사용하려면 launch 파일을 수정하거나 실행 시 인자로 넘기면 됩니다.

예시:

```bash
ros2 launch ntrip_client ntrip_client_launch.py \
  host:=www.gnssdata.or.kr \
  port:=2101 \
  mountpoint:=SOUL-RTCM32 \
  authenticate:=True \
  username:=YOUR_USERNAME \
  password:=YOUR_PASSWORD \
  rtcm_message_package:=rtcm_msgs
```

주의할 점은 계정 정보입니다. `username`, `password`를 소스 코드나 공개 저장소에 그대로 남기면 보안 문제가 생길 수 있으므로, 실제 프로젝트에서는 환경 변수나 별도 설정 파일로 분리하는 것이 좋습니다.

`ntrip_client` 노드의 주요 토픽은 다음과 같습니다.

- Subscribe: `/ntrip_client/nmea`
- Publish: `/ntrip_client/rtcm`

`/ntrip_client/nmea`는 NTRIP caster에 보낼 현재 위치 NMEA 문장입니다. 일부 caster는 rover의 대략적인 위치를 알아야 주변 기준국에 맞는 보정 데이터를 제공합니다. `/ntrip_client/rtcm`은 caster에서 받은 RTCM 보정 데이터이며, u-blox 드라이버가 이 토픽을 구독합니다.

### 3. /fix to /nmea Parser

`fix2nmea`는 `sensor_msgs/msg/NavSatFix` 형식의 GNSS 위치 메시지를 `nmea_msgs/msg/Sentence` 형식의 NMEA GGA 문장으로 바꾸는 작은 변환 노드입니다.

NTRIP caster가 rover 위치를 요구하는 경우, 단순히 RTCM만 받는 것이 아니라 rover의 현재 위치를 NMEA 형태로 서버에 계속 보내야 합니다. 그런데 u-blox 드라이버에서 ROS 쪽으로 나오는 대표 위치 메시지는 `/fix` 계열의 `NavSatFix` 메시지입니다. 그래서 중간에 `fix2nmea`가 필요합니다.

실행 명령은 다음과 같습니다.

```bash
ros2 run fix2nmea fix2nmea
```

현재 `fix2nmea` 구현 기준 토픽은 다음과 같습니다.

- Subscribe: `/ublox_gps_node/fix`
- Publish: `/ntrip_client/nmea`

단, 제공된 u-blox launch 파일은 `/ublox_gps_node/fix`를 아래 토픽으로 remap합니다.

- ZED-F9P launch: `/f9p/fix`
- ZED-F9R launch: `/f9r/fix`

따라서 제공된 launch 파일을 그대로 사용하면 `fix2nmea`가 `/ublox_gps_node/fix`를 기다리지만 실제 위치는 `/f9p/fix` 또는 `/f9r/fix`로 나올 수 있습니다. 이 경우 `fix2nmea` 실행 시 remap을 추가해야 합니다.

ZED-F9P 예시:

```bash
ros2 run fix2nmea fix2nmea --ros-args -r /ublox_gps_node/fix:=/f9p/fix
```

ZED-F9R 예시:

```bash
ros2 run fix2nmea fix2nmea --ros-args -r /ublox_gps_node/fix:=/f9r/fix
```

## 권장 실행 순서

각 노드는 계속 실행되어야 하므로 보통 터미널을 3개 열어 실행합니다. 모든 터미널에서 먼저 워크스페이스 환경을 source해야 합니다.

```bash
cd ~/Mando2026_ws
source install/setup.bash
```

터미널 1: u-blox 수신기 실행

```bash
ros2 launch ublox_gps ublox_f9p_launch.py
```

터미널 2: `/fix`를 NMEA로 변환

```bash
ros2 run fix2nmea fix2nmea --ros-args -r /ublox_gps_node/fix:=/f9p/fix
```

터미널 3: NTRIP client 실행

```bash
ros2 launch ntrip_client ntrip_client_launch.py
```

ZED-F9R을 사용할 경우 위 명령에서 `ublox_f9p_launch.py`를 `ublox_f9r_launch.py`로 바꾸고, `/f9p/fix`를 `/f9r/fix`로 바꾸면 됩니다.

## 빌드 방법

처음 사용하거나 코드를 수정한 뒤에는 워크스페이스 루트에서 빌드합니다.

```bash
cd ~/Mando2026_ws
colcon build
source install/setup.bash
```

특정 패키지만 다시 빌드하고 싶다면 다음처럼 실행할 수 있습니다.

```bash
colcon build --packages-select fix2nmea
source install/setup.bash
```

## 토픽 확인 방법

노드가 제대로 연결되었는지 확인하려면 아래 명령을 사용할 수 있습니다.

전체 토픽 목록:

```bash
ros2 topic list
```

u-blox 위치 출력 확인:

```bash
ros2 topic echo /f9p/fix
```

NMEA 변환 결과 확인:

```bash
ros2 topic echo /ntrip_client/nmea
```

RTCM 보정 데이터 수신 확인:

```bash
ros2 topic echo /ntrip_client/rtcm
```

토픽 연결 관계를 확인하려면 다음 명령이 유용합니다.

```bash
ros2 node info /ublox_gps_node
ros2 node info /fix2nmea
ros2 node info /ntrip_client/ntrip_client
```

## 자주 확인해야 할 설정

### 시리얼 포트

u-blox 수신기가 어떤 포트로 잡혔는지 확인해야 합니다.

```bash
ls /dev/ttyACM*
```

launch 파일의 기본값과 실제 장치 포트가 다르면 `serial_port:=...` 인자로 맞춰야 합니다.

### baudrate

현재 launch 파일과 yaml 설정은 기본적으로 `115200` bps를 사용합니다. 수신기 설정이 다르면 통신이 되지 않으므로 수신기의 실제 baudrate와 맞춰야 합니다.

### dynamic_model

`zed_f9p.yaml`, `zed_f9r.yaml`에는 `dynamic_model: automotive`가 설정되어 있습니다. 차량 환경에서는 적절하지만, 고정 기준국처럼 움직이지 않는 장비라면 `stationary`가 더 적절할 수 있습니다.

### NTRIP mountpoint

`mountpoint`는 어떤 기준국 또는 보정 스트림을 사용할지 결정합니다. 잘못된 mountpoint를 사용하면 접속은 되더라도 RTCM이 오지 않거나, 현재 위치와 맞지 않는 보정 데이터가 들어올 수 있습니다.

## 문제 해결

### `/ntrip_client/rtcm`이 나오지 않는 경우

- NTRIP `host`, `port`, `mountpoint`가 맞는지 확인합니다.
- 인증이 필요한 caster라면 `authenticate`, `username`, `password`를 확인합니다.
- `/ntrip_client/nmea`가 publish되고 있는지 확인합니다.
- 인터넷 연결과 방화벽 설정을 확인합니다.

### `/ntrip_client/nmea`가 나오지 않는 경우

- `fix2nmea` 노드가 실행 중인지 확인합니다.
- u-blox 위치 토픽(`/f9p/fix` 또는 `/f9r/fix`)이 실제로 publish되는지 확인합니다.
- `fix2nmea` 실행 시 `/ublox_gps_node/fix` remap을 올바르게 줬는지 확인합니다.

### u-blox 위치 토픽이 나오지 않는 경우

- 수신기가 USB 또는 시리얼로 연결되어 있는지 확인합니다.
- launch 파일의 `serial_port`가 실제 포트와 일치하는지 확인합니다.
- 현재 사용자에게 시리얼 포트 접근 권한이 있는지 확인합니다.
- 안테나가 하늘이 보이는 위치에 있는지 확인합니다.

### RTK 상태가 되지 않는 경우

- `/ntrip_client/rtcm`에 데이터가 계속 들어오는지 확인합니다.
- u-blox 노드가 `/ntrip_client/rtcm`을 구독하고 있는지 확인합니다.
- NTRIP mountpoint가 현재 지역과 맞는지 확인합니다.
- 수신기와 안테나가 RTK를 지원하는 모델인지 확인합니다.
- 하늘 시야가 좋지 않거나 multipath가 심한 환경에서는 RTK fix가 늦거나 불안정할 수 있습니다.

## 핵심 요약

- `ublox_gps`: u-blox 수신기와 통신하고 GNSS 위치를 ROS 토픽으로 publish합니다.
- `fix2nmea`: ROS `NavSatFix` 위치를 NTRIP 서버용 NMEA GGA 문장으로 변환합니다.
- `ntrip_client`: NTRIP caster에서 RTCM 보정 데이터를 받아 `/ntrip_client/rtcm`으로 publish합니다.
- `/ntrip_client/rtcm`: u-blox 수신기에 들어가는 RTK 보정 데이터입니다.
- `/ntrip_client/nmea`: NTRIP caster에 rover의 현재 위치를 알려주기 위한 NMEA 문장입니다.

## ZED-F9R u-center 초기 설정 메모

이 내용은 ZED-F9R을 펌웨어 업데이트한 뒤, 센서의 USB-C 포트와 노트북을 직접 연결해서 ROS 2 `ublox_gps` 노드와 NTRIP/RTK 보정을 사용하는 경우를 기준으로 합니다.

### USB 포트 설정

USB-C 케이블로 노트북에 연결하는 경우 u-center의 `UBX-CFG-PRT` 또는 Generation 9 Advanced Configuration View에서 `UART1`이 아니라 `USB` target을 확인해야 합니다.

추천 설정은 다음과 같습니다.

```text
USB Protocol in:  UBX + NMEA + RTCM3
USB Protocol out: UBX
```

`Protocol in`은 노트북 또는 외부 장치에서 F9R로 들어오는 데이터 종류입니다.

- `UBX`: u-center와 ROS 드라이버가 수신기에 설정 명령을 보내는 데 필요합니다.
- `NMEA`: 표준 GNSS 문장 입력용입니다. 필수는 아니지만 켜 두어도 보통 문제 없습니다.
- `RTCM3`: NTRIP caster에서 받은 RTK 보정 데이터를 F9R에 넣기 위해 필요합니다.

`Protocol out`은 F9R에서 노트북으로 나가는 데이터 종류입니다.

- `UBX`: ROS `ublox_gps` 드라이버가 위치, 속도, RTK 상태, ESF/IMU 상태 등을 읽는 주 프로토콜입니다.
- `NMEA`: 사람이 보기 쉬운 `$GNGGA`, `$GNRMC` 같은 텍스트 문장입니다. ROS 운용 기준에서는 필수는 아니며, 출력 부하를 줄이기 위해 보통 끕니다.
- `RTCM3`: rover로 쓰는 F9R에서는 보통 출력할 필요가 없습니다. RTCM3는 기준국/NTRIP에서 받아 F9R에 넣는 보정 데이터입니다.

u-center 표기에서 숫자는 다음 의미로 보면 됩니다.

```text
0 = UBX
1 = NMEA
5 = RTCM3
```

따라서 다음처럼 해석합니다.

```text
0+1   = UBX + NMEA
0+1+5 = UBX + NMEA + RTCM3
```

RTK/NTRIP을 사용할 때는 USB `Protocol in`에 반드시 `0+1+5`, 즉 `UBX + NMEA + RTCM3`가 포함되어야 합니다. USB `Protocol out`은 ROS 기준으로 `0`, 즉 `UBX only`를 추천합니다.

### UART1 설정

USB-C 연결만 사용할 경우 `UART1` baudrate와 protocol 설정은 ROS 통신에 직접 영향을 주지 않습니다. `UART1`은 F9R 보드의 TX/RX 핀을 MCU나 USB-TTL 컨버터에 연결할 때 필요한 설정입니다.

나중에 UART1을 사용할 계획이 있다면 다음처럼 맞춰 두면 됩니다.

```text
UART1 Protocol in:  UBX + NMEA + RTCM3
UART1 Protocol out: UBX
UART1 Baudrate:     115200
Databits:           8
Stopbits:           1
Parity:             None
```

### Dynamic model

차량에 장착해서 사용하는 F9R은 dynamic model을 `Automotive`로 설정하는 것을 추천합니다.

u-center Generation 9 Advanced Configuration View에서 다음 항목을 찾습니다.

```text
CFG-NAVSPG-DYNMODEL
```

기본값이 다음처럼 보일 수 있습니다.

```text
0 - PORT (Portable)
```

차량용 설정은 다음 값입니다.

```text
4 - AUTOMOTIVE
```

이 워크스페이스의 `zed_f9r.yaml`도 `dynamic_model: automotive`를 사용합니다. u-center에서 다른 값으로 저장해도 ROS `ublox_gps` 실행 시 YAML 설정이 다시 적용될 수 있으므로, u-center 설정과 ROS 설정을 같은 방향으로 맞추는 것이 좋습니다.

### TMODE3

F9R을 차량 rover로 사용할 때는 base station 또는 survey-in 모드가 아니어야 합니다.

확인할 항목은 다음과 같습니다.

```text
CFG-TMODE-MODE
```

추천값은 다음과 같습니다.

```text
Disabled
```

`Survey-in` 또는 `Fixed mode`는 기준국/base로 사용할 때 필요한 설정입니다.

### IMU auto-alignment

F9R의 dead reckoning과 sensor fusion을 사용하려면 보드가 차량에 어떤 방향으로 장착되어 있는지 정렬되어야 합니다. 차량에 F9R을 단단히 고정한 뒤 자동 IMU mount alignment를 켜는 것을 추천합니다.

확인할 항목은 다음과 같습니다.

```text
CFG-SFIMU-AUTO_MNTALG_ENA
```

추천값은 다음과 같습니다.

```text
Enabled
```

설정 후에는 하늘이 잘 보이는 곳에서 직진, 좌회전, 우회전이 포함된 주행을 몇 분간 수행해야 합니다. 중간에 30초 정도 정지하는 구간을 몇 번 포함하면 IMU calibration에 도움이 됩니다.

정렬 상태는 `UBX-ESF-ALG.status`로 확인합니다.

```text
1: roll/pitch alignment 진행 중
2: yaw alignment 진행 중
3: coarse calibration, sensor fusion 사용 가능
4: fine calibration, 더 안정적인 상태
```

목표는 `UBX-ESF-ALG.status >= 3`입니다.

### NMEA high precision mode

ROS `ublox_gps` 드라이버를 UBX output 중심으로 사용할 경우 NMEA high precision mode는 필수 설정이 아닙니다.

추천값은 다음과 같습니다.

```text
NMEA high precision mode: OFF
```

이 모드는 F9R이 NMEA 문장을 직접 출력하고, 다른 프로그램이 그 NMEA 문장을 읽어야 할 때만 고려합니다. 이 워크스페이스에서는 NTRIP 서버에 보낼 GGA 문장을 F9R의 NMEA output에서 직접 가져오지 않고, `/f9r/fix`를 받은 `fix2nmea` 노드가 `/ntrip_client/nmea`로 만들어 보냅니다.

### Navigation rate

현재 F9R YAML 설정은 `rate: 15.0`을 사용합니다. u-center에서 수동으로 맞출 경우 다음과 같은 방향입니다.

```text
CFG-RATE-MEAS: 약 66 또는 67 ms
CFG-RATE-NAV:  1
```

초기 테스트에서는 5 Hz 또는 10 Hz로 낮춰 확인해도 됩니다. 중요한 것은 수신기 설정과 ROS YAML 설정이 서로 다른 값을 반복해서 덮어쓰지 않도록 맞추는 것입니다.

### 모니터링용 UBX 메시지

u-center에서 상태를 확인하려면 USB output에 다음 UBX 메시지를 켜 두면 유용합니다.

```text
UBX-NAV-PVT      위치, fix type, RTK 상태
UBX-NAV-SAT      위성 상태
UBX-RXM-RTCM     RTCM 보정 수신 상태
UBX-ESF-STATUS   IMU/센서 fusion calibration 상태
UBX-ESF-ALG      IMU auto-alignment 상태
UBX-NAV-ATT      roll, pitch, yaw attitude
```

Generation 9 Advanced Configuration View에서는 보통 다음과 같은 key 이름으로 보입니다.

```text
CFG-MSGOUT-UBX_NAV_PVT_USB
CFG-MSGOUT-UBX_NAV_SAT_USB
CFG-MSGOUT-UBX_RXM_RTCM_USB
CFG-MSGOUT-UBX_ESF_STATUS_USB
CFG-MSGOUT-UBX_ESF_ALG_USB
CFG-MSGOUT-UBX_NAV_ATT_USB
```

값을 `1`로 설정하면 일반적으로 매 navigation epoch마다 출력됩니다.

### 설정 저장

u-center에서 변경한 설정은 RAM에만 적용하면 전원 재인가 또는 reset 후 사라질 수 있습니다. 설정 후 다음 layer에 저장합니다.

```text
RAM
BBR
Flash
```

Generation 9 Advanced Configuration View에서는 값을 바꾼 뒤 다음 버튼을 사용합니다.

```text
Set in RAM
Set in BBR
Set in Flash
Send configuration
```

적용 후 각 항목 아래 layer 값이 원하는 값으로 보이는지 확인합니다.

### 최종 추천값 요약

```text
USB Protocol in:         UBX + NMEA + RTCM3
USB Protocol out:        UBX
Dynamic model:           Automotive
TMODE3:                  Disabled
IMU auto-alignment:      Enabled
NMEA high precision:     OFF
Navigation rate:         10-15 Hz
Save layers:             RAM + BBR + Flash
```

## ZED-F9R + ROS 2 + NTRIP 전체 데이터 흐름

이 구성에서는 ZED-F9R이 GNSS/IMU/RTCM 보정을 이용해 위치를 계산하고, 노트북의 ROS 2 노드들이 NTRIP 서버와 통신해 RTCM 보정 데이터를 다시 F9R에 넣습니다.

전체 흐름은 다음과 같습니다.

```text
ZED-F9R
  USB out: UBX
    |
    v
ublox_gps node
  UBX binary 메시지 해석
  /f9r/fix publish
    |
    v
fix2nmea node
  /f9r/fix -> NMEA GGA 변환
  /ntrip_client/nmea publish
    |
    v
ntrip_client node
  NMEA GGA를 NTRIP 서버로 전송
  RTCM 보정 데이터 수신
    |
    v
/ntrip_client/rtcm
    |
    v
ublox_gps node
  RTCM binary를 F9R로 write
    |
    v
ZED-F9R
  USB in: RTCM3
  RTK 보정 적용
  더 정확한 위치 계산
```

### 1. F9R에서 노트북으로 나가는 데이터

F9R은 USB-C를 통해 노트북에 연결되고, `USB Protocol out = UBX` 설정으로 UBX 메시지를 노트북에 보냅니다.

대표적으로 다음 메시지들이 사용됩니다.

```text
UBX-NAV-PVT      위치, fix type, RTK 상태
UBX-NAV-SAT      위성 상태
UBX-RXM-RTCM     RTCM 수신 상태
UBX-ESF-STATUS   sensor fusion calibration 상태
UBX-ESF-ALG      IMU auto-alignment 상태
UBX-NAV-ATT      roll, pitch, yaw
```

UBX는 u-blox 전용 binary protocol이며, ROS `ublox_gps` 드라이버가 읽기 좋고 NMEA보다 더 많은 상태 정보를 제공합니다.

### 2. `ublox_gps` 노드가 UBX를 ROS 토픽으로 변환

노트북에서 실행되는 `ublox_gps` 노드는 F9R이 연결된 USB serial device를 엽니다.

예시는 다음과 같습니다.

```text
/dev/ttyACM0
/dev/ttyACM1
```

이 노드는 F9R의 UBX 메시지를 읽고 ROS 토픽으로 변환합니다.

대표 토픽은 다음과 같습니다.

```text
/f9r/fix
/f9r/fix_velocity
```

`/f9r/fix`는 `sensor_msgs/msg/NavSatFix` 타입이며, F9R이 계산한 위도, 경도, 고도, covariance, fix 상태를 포함합니다.

### 3. `fix2nmea` 노드가 `/f9r/fix`를 NMEA GGA로 변환

NTRIP 서버는 rover의 현재 위치를 알아야 현재 위치에 맞는 기준국 또는 VRS 보정 데이터를 보낼 수 있습니다. 이때 서버가 요구하는 위치 형식은 보통 ROS `NavSatFix`가 아니라 NMEA GGA 문장입니다.

따라서 `fix2nmea` 노드가 다음 변환을 수행합니다.

```text
/f9r/fix
  -> fix2nmea
  -> /ntrip_client/nmea
```

`/ntrip_client/nmea`는 `nmea_msgs/msg/Sentence` 타입이며, 내부에는 `$GPGGA` 또는 `$GNGGA` 형태의 문장이 들어갑니다.

예시 형태는 다음과 같습니다.

```text
$GNGGA,time,lat,N,lon,E,fix_quality,num_sat,hdop,alt,M,...
```

이 문장의 핵심 역할은 NTRIP 서버에 rover의 대략적인 현재 위치를 알려주는 것입니다.

### 4. `ntrip_client` 노드가 NMEA를 서버로 보내고 RTCM을 수신

`ntrip_client` 노드는 `/ntrip_client/nmea`를 subscribe하고, 그 GGA 문장을 NTRIP caster 서버로 보냅니다.

동시에 NTRIP 서버에서 RTCM 보정 데이터를 받아 ROS 토픽으로 publish합니다.

```text
NTRIP server
  -> RTCM correction data
  -> ntrip_client
  -> /ntrip_client/rtcm
```

`/ntrip_client/rtcm`은 `rtcm_msgs/msg/Message` 타입이며, 내부에는 RTCM binary correction data가 들어 있습니다.

### 5. `ublox_gps` 노드가 RTCM을 F9R로 다시 전달

`ublox_gps` 노드는 `/ntrip_client/rtcm`을 subscribe합니다. NTRIP 서버에서 받은 RTCM 보정 데이터는 이 노드를 통해 실제 F9R USB 포트로 write됩니다.

이때 F9R USB 설정에서 가장 중요한 부분은 다음입니다.

```text
USB Protocol in = UBX + NMEA + RTCM3
```

특히 `RTCM3 input`이 활성화되어 있어야 F9R이 보정 데이터를 받아 RTK 계산에 사용할 수 있습니다.

### 6. F9R 내부에서 RTK 보정 적용

F9R은 노트북에서 들어온 RTCM3 보정 데이터를 사용해 GNSS 위치 계산을 개선합니다.

일반적인 상태 변화는 다음과 같습니다.

```text
Single GNSS
  -> DGNSS
  -> RTK Float
  -> RTK Fixed
```

RTK Fixed가 되면 cm급 위치 정확도에 가까워집니다. 실제 도달 시간과 안정성은 하늘 시야, multipath, 안테나, 기준국 거리, NTRIP mountpoint, RTCM 수신 상태에 영향을 받습니다.

### 7. F9R sensor fusion / IMU 흐름

F9R은 GNSS뿐 아니라 내부 IMU도 함께 사용합니다. 차량 장착 기준으로 다음 설정이 중요합니다.

```text
Dynamic model = Automotive
IMU auto-alignment = Enabled
```

`Dynamic model = Automotive`는 F9R이 차량 움직임에 맞는 sensor fusion 가정을 사용하도록 합니다. `IMU auto-alignment`는 F9R 보드가 차량에 어떤 방향으로 장착되어 있는지 자동으로 추정합니다.

초기 주행 중에는 alignment 상태가 다음처럼 보일 수 있습니다.

```text
UBX-ESF-ALG.status = 1 또는 2
```

충분한 직진, 좌회전, 우회전 주행 후에는 다음 상태를 목표로 합니다.

```text
UBX-ESF-ALG.status >= 3
```

### 역할 정리

ZED-F9R의 역할은 다음과 같습니다.

```text
위성 수신
IMU 측정
RTCM 보정 적용
RTK/DR 위치 계산
UBX로 결과 출력
```

노트북 ROS 2의 역할은 다음과 같습니다.

```text
UBX 읽기
ROS 토픽으로 변환
/f9r/fix를 NMEA GGA로 변환
NTRIP 서버와 통신
RTCM 보정 데이터를 F9R에 다시 전달
```

최종 데이터 왕복은 다음처럼 요약할 수 있습니다.

```text
F9R -> 노트북:
  UBX 위치/상태 메시지

노트북 -> NTRIP 서버:
  NMEA GGA 현재 위치 문장

NTRIP 서버 -> 노트북:
  RTCM 보정 데이터

노트북 -> F9R:
  RTCM3 보정 데이터
```

핵심 설정은 다음 두 줄입니다.

```text
F9R USB Protocol out:
  UBX

F9R USB Protocol in:
  UBX + NMEA + RTCM3
```

`Protocol out`은 F9R이 노트북으로 말하는 형식이고, `Protocol in`은 노트북이 F9R에 넣어줄 수 있는 형식입니다.

## ZED-F9R IMU / Sensor Fusion 끄기

u-center에서 F9R의 IMU 기반 sensor fusion 사용을 끌 수 있습니다. 다만 이것은 IMU 센서를 물리적으로 완전히 끄는 것이라기보다, F9R의 위치 계산에 IMU/HPS sensor fusion을 사용하지 않도록 하는 설정입니다.

확인할 항목은 다음과 같습니다.

```text
CFG-SFCORE-USE_SF
```

이 항목은 u-center의 legacy `Messages > UBX-CFG` 트리에서는 보이지 않을 수 있습니다. 다음 화면에서 찾습니다.

```text
View
  -> Generation 9 Advanced Configuration View
  -> Advanced Configuration
```

검색창에는 `SFCORE`보다 먼저 다음 문자열로 검색하는 것이 찾기 쉽습니다.

```text
USE_SF
```

정상적으로 보이면 항목 이름은 다음과 같습니다.

```text
CFG-SFCORE-USE_SF
```

값은 boolean 형태입니다.

```text
1 / true / enabled    = sensor fusion 사용
0 / false / disabled  = GNSS-only
```

이 값을 끄면 F9R은 GNSS-only solution을 출력합니다.

```text
CFG-SFCORE-USE_SF = 0
```

반대로 F9R의 dead reckoning과 sensor fusion을 사용할 경우에는 다음처럼 둡니다.

```text
CFG-SFCORE-USE_SF = 1
```

주의할 점은 `CFG-SFIMU-AUTO_MNTALG_ENA`와 혼동하지 않는 것입니다.

```text
CFG-SFCORE-USE_SF:
  IMU/HPS sensor fusion 전체 사용 여부

CFG-SFIMU-AUTO_MNTALG_ENA:
  IMU mount auto-alignment 사용 여부
```

즉 `CFG-SFIMU-AUTO_MNTALG_ENA = 0`으로 설정해도 sensor fusion 전체가 꺼지는 것은 아닙니다. 자동 장착각 추정만 꺼집니다.

상황별 정리는 다음과 같습니다.

```text
IMU/sensor fusion 전체 끄기:
  CFG-SFCORE-USE_SF = 0

IMU/sensor fusion 사용:
  CFG-SFCORE-USE_SF = 1

IMU auto-alignment만 끄기:
  CFG-SFIMU-AUTO_MNTALG_ENA = 0

IMU 관련 UBX 출력 메시지만 끄기:
  CFG-MSGOUT-UBX_ESF_*_USB = 0
```

차량용 F9R로 dead reckoning까지 사용할 목적이면 보통 다음 설정을 추천합니다.

```text
CFG-SFCORE-USE_SF = 1
CFG-SFIMU-AUTO_MNTALG_ENA = 1
CFG-NAVSPG-DYNMODEL = 4 - AUTOMOTIVE
```

F9R을 일시적으로 F9P처럼 GNSS/RTK receiver로만 테스트하거나, IMU calibration이 꼬인 상태를 분리해서 확인하고 싶을 때는 `CFG-SFCORE-USE_SF = 0`으로 GNSS-only 상태를 만들 수 있습니다.
