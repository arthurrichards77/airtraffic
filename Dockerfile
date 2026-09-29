FROM ros:humble-ros-base

WORKDIR /ros_ws/src

RUN apt-get update \
    && apt-get install -y python3-pip ros-humble-foxglove-msgs

# ought to be able to specify Python dependencies through rosdep, but can't get it to work
RUN python3 -m pip install requests geopandas

COPY . /ros_ws/src/airtraffic

# Install dependencies
WORKDIR /ros_ws

RUN . /opt/ros/${ROS_DISTRO}/setup.sh \
    && apt-get update \
    && rosdep install --from-paths src \
    && rm -rf /var/lib/apt/lists/

# Build the package
RUN . /opt/ros/${ROS_DISTRO}/setup.sh \
    && colcon build
#RUN . /ros_ws/install/setup.sh

RUN echo '#!/bin/bash' > /my_entrypoint.sh \
    && echo 'set -e' >> /my_entrypoint.sh \
    && echo 'source "/ros_ws/install/setup.bash" --' >> /my_entrypoint.sh \
    && echo 'exec "$@"' >> /my_entrypoint.sh \
    && chmod +x /my_entrypoint.sh

ENTRYPOINT ["/my_entrypoint.sh"]

CMD [ "ros2", "launch", "airtraffic", "bristol.launch.xml" ]