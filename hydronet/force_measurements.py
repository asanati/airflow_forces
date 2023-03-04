from force_sensor import ForceGauge
from Logger import Logger,t_step
import zmq
import detection_msg_pb2
import time

force_logger = Logger(name="force_measurements", use_csv=True, use_tensorboard=False)

fg = ForceGauge()

context = zmq.Context()
socket_quad = context.socket(zmq.REP)
socket_obj = context.socket(zmq.REP)

socket_quad.connect('tcp://localhost:2222')
socket_obj.connect('tcp://localhost:4444')

t = 0
while True:
    quad_pose_serial = socket_quad.recv()
    quad_pose = detection_msg_pb2.Detection()
    quad_pose.ParseFromString(quad_pose_serial)

    box_pose_serial = socket_obj.recv()
    box_pose = detection_msg_pb2.Detection()
    box_pose.ParseFromString(box_pose_serial)

    force, unit, _ = fg.read_gauge()
    force_logger.log("measured_force", (force, unit), t)
    force_logger.log("quad_pose", quad_pose, t)
    force_logger.log("box_pose", box_pose, t)

    print("Quad pose:")
    print(quad_pose)
    print("Box pose:")
    print(box_pose)
    print("Force:")
    print(force, unit)

    msg = detection_msg_pb2.Detection()
    msg.x = 0.0
    msg.y = 0.0
    msg.z = 0.0
    msg.label = 'Nothing'
    msg.confidence = 0.0
    serial_msg = msg.SerializeToString()
    socket_quad.send(serial_msg)
    socket_obj.send(serial_msg)

    time.sleep(0.01)
    t += 0.01