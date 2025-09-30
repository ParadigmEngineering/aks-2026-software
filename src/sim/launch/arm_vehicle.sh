#!/bin/bash

MAVLINK_UDP_PORT="udp:localhost:14550"
PATH_TO_PX4_AUTOPILOT="$HOME/PX4-Autopilot"

# Start a new tmux session and run the MAVLink shell in it
tmux new-session -d -s mavlink_shell "python3 $PATH_TO_PX4_AUTOPILOT/Tools/mavlink_shell.py $MAVLINK_UDP_PORT"

# Give it a few seconds to start up
sleep 5

# Send the arm command in the tmux session
tmux send-keys -t mavlink_shell "commander arm" C-m

echo "Arm command sent to MAVLink shell in tmux session."

# sleep for 5 seconds then close
sleep 5
tmux kill-session -t mavlink_shell
echo "MAVLink shell terminated."
