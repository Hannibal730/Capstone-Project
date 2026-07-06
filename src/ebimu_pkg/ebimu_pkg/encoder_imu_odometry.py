import math

import rclpy
from geometry_msgs.msg import PoseStamped
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from nav_msgs.msg import Path
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float64
from tf2_ros import TransformBroadcaster


class EncoderImuOdometry(Node):

    def __init__(self):
        super().__init__('encoder_imu_odometry')

        self.declare_parameter('odom_publish_rate_hz', 100.0)
        self.declare_parameter('path_publish_rate_hz', 5.0)
        self.declare_parameter('path_min_distance', 0.02)
        self.declare_parameter('path_max_length', 300)
        self.declare_parameter('max_dt_sec', 0.2)
        self.declare_parameter('sensor_timeout_sec', 0.2)
        self.declare_parameter('odom_frame_id', 'odom')
        self.declare_parameter('base_frame_id', 'base_link')

        self.odom_publish_period = self.period_from_rate(
            float(self.get_parameter('odom_publish_rate_hz').value)
        )
        self.path_publish_period = self.period_from_rate(
            float(self.get_parameter('path_publish_rate_hz').value)
        )
        self.path_min_distance = float(self.get_parameter('path_min_distance').value)
        self.path_max_length = int(self.get_parameter('path_max_length').value)
        self.max_dt_sec = float(self.get_parameter('max_dt_sec').value)
        self.sensor_timeout_sec = float(self.get_parameter('sensor_timeout_sec').value)
        self.odom_frame_id = self.get_parameter('odom_frame_id').value
        self.base_frame_id = self.get_parameter('base_frame_id').value

        self.yaw = 0.0
        self.position = [0.0, 0.0, 0.0]
        self.velocity = [0.0, 0.0, 0.0]
        self.last_time = None
        self.last_yaw_rate = 0.0
        self.last_speed = 0.0
        self.last_imu_time = None
        self.last_speed_time = None
        self.encoder_distance = 0.0
        self.last_path_position = None
        self.last_path_publish_time = None
        self.last_log_times = {}

        self.odom_publisher = self.create_publisher(Odometry, 'odom', 10)
        self.path_publisher = self.create_publisher(Path, 'odom_path', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        self.imu_subscription = self.create_subscription(Imu, 'imu/data', self.imu_callback, 10)
        self.speed_subscription = self.create_subscription(Float64, 'encoder/speed', self.speed_callback, 10)
        self.distance_subscription = self.create_subscription(Float64, 'encoder/distance', self.distance_callback, 10)

        self.path = Path()
        self.path.header.frame_id = self.odom_frame_id
        self.odom_timer = self.create_timer(self.odom_publish_period, self.timer_callback)

    def imu_callback(self, msg):
        self.last_yaw_rate = msg.angular_velocity.z
        self.last_imu_time = self.stamp_to_seconds(msg.header.stamp)

    def speed_callback(self, msg):
        self.last_speed = msg.data
        self.last_speed_time = self.get_clock().now().nanoseconds * 1e-9

    def distance_callback(self, msg):
        self.encoder_distance = msg.data

    def timer_callback(self):
        stamp = self.get_clock().now()
        stamp_time = stamp.nanoseconds * 1e-9

        if self.last_time is None:
            self.last_time = stamp_time
            return

        dt = stamp_time - self.last_time
        self.last_time = stamp_time
        if dt <= 0.0 or dt > self.max_dt_sec:
            self.log_throttled('dt', f'Ignoring odometry update with invalid dt={dt:.4f}', 'warn')
            return

        speed = self.value_if_fresh(self.last_speed, self.last_speed_time, stamp_time, 'encoder_speed')
        yaw_rate = self.value_if_fresh(self.last_yaw_rate, self.last_imu_time, stamp_time, 'imu_gyro_z')
        yaw_mid = self.yaw + 0.5 * yaw_rate * dt
        self.yaw = self.normalize_angle(self.yaw + yaw_rate * dt)
        self.velocity[0] = speed
        self.velocity[1] = 0.0
        self.velocity[2] = 0.0

        self.position[0] += math.cos(yaw_mid) * speed * dt
        self.position[1] += math.sin(yaw_mid) * speed * dt

        q = self.yaw_to_quaternion(self.yaw)
        self.publish_odometry(stamp, q, yaw_rate)
        self.publish_tf(stamp, q)

        if self.should_publish(stamp_time, self.last_path_publish_time, self.path_publish_period):
            self.publish_path(stamp, q)
            self.last_path_publish_time = stamp_time

    def publish_odometry(self, stamp, q, yaw_rate):
        msg = Odometry()
        msg.header.stamp = stamp.to_msg()
        msg.header.frame_id = self.odom_frame_id
        msg.child_frame_id = self.base_frame_id
        msg.pose.pose.position.x = self.position[0]
        msg.pose.pose.position.y = self.position[1]
        msg.pose.pose.position.z = 0.0
        msg.pose.pose.orientation = q
        msg.twist.twist.linear.x = self.velocity[0]
        msg.twist.twist.linear.y = self.velocity[1]
        msg.twist.twist.linear.z = self.velocity[2]
        msg.twist.twist.angular.z = yaw_rate
        self.odom_publisher.publish(msg)

    def publish_path(self, stamp, q):
        if self.last_path_position is not None:
            distance = math.hypot(
                self.position[0] - self.last_path_position[0],
                self.position[1] - self.last_path_position[1],
            )
            if distance < self.path_min_distance:
                return

        self.last_path_position = list(self.position)
        pose = PoseStamped()
        pose.header.stamp = stamp.to_msg()
        pose.header.frame_id = self.odom_frame_id
        pose.pose.position.x = self.position[0]
        pose.pose.position.y = self.position[1]
        pose.pose.position.z = 0.0
        pose.pose.orientation = q
        self.path.header.stamp = stamp.to_msg()
        self.path.poses.append(pose)
        self.path.poses = self.path.poses[-self.path_max_length:]
        self.path_publisher.publish(self.path)

    def publish_tf(self, stamp, q):
        transform = TransformStamped()
        transform.header.stamp = stamp.to_msg()
        transform.header.frame_id = self.odom_frame_id
        transform.child_frame_id = self.base_frame_id
        transform.transform.translation.x = self.position[0]
        transform.transform.translation.y = self.position[1]
        transform.transform.translation.z = 0.0
        transform.transform.rotation = q
        self.tf_broadcaster.sendTransform(transform)

    def yaw_to_quaternion(self, yaw):
        q = Imu().orientation
        q.w = math.cos(yaw * 0.5)
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(yaw * 0.5)
        return q

    def stamp_to_seconds(self, stamp):
        return stamp.sec + stamp.nanosec * 1e-9

    def value_if_fresh(self, value, sample_time, now, name):
        if sample_time is None:
            self.log_throttled(name, f'Waiting for {name} samples.', 'warn')
            return 0.0
        if now - sample_time > self.sensor_timeout_sec:
            self.log_throttled(name, f'{name} sample timed out; using 0.0.', 'warn')
            return 0.0
        return value

    def normalize_angle(self, angle):
        return math.atan2(math.sin(angle), math.cos(angle))

    def should_publish(self, stamp_time, last_time, period):
        if period <= 0.0 or last_time is None:
            return True
        return stamp_time - last_time >= period

    def period_from_rate(self, rate_hz):
        if rate_hz <= 0.0:
            return 0.0
        return 1.0 / rate_hz

    def log_throttled(self, key, message, level='info', period=1.0):
        now = self.get_clock().now().nanoseconds * 1e-9
        last = self.last_log_times.get(key)
        if last is not None and now - last < period:
            return
        self.last_log_times[key] = now
        if level == 'warn':
            self.get_logger().warn(message)
        else:
            self.get_logger().info(message)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = EncoderImuOdometry()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
