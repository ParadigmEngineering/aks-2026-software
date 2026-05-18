#!/bin/bash
source ~/Code/GitHub/aks-2026-software/install/setup.bash
echo "⚠️  ARMING PIXHAWK ⚠️  "
ros2 service call /mavros/cmd/arming mavros_msgs/srv/CommandBool "{value: True}"

