#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "mavros_msgs/srv/set_mode.hpp"
#include "ament_index_cpp/get_package_share_directory.hpp"
#include "geographic_msgs/msg/geo_pose_stamped.hpp"
#include <tf2/LinearMath/Quaternion.h> 
#include "tf2_geometry_msgs/tf2_geometry_msgs.h"
#include <fstream>
#include <vector>
#include <iostream>
#include <cmath>

using namespace std;
using namespace std::chrono_literals;
using std::placeholders::_1;

class WaypointPublisher : public rclcpp::Node
{
public:
    WaypointPublisher() : Node("waypoint_publisher")
    {
        get_coords();
        // Subscription to the kart's GPS position
        gps_subscriber_ = this->create_subscription<sensor_msgs::msg::NavSatFix>(
            "/mavros/global_position/global", rclcpp::SensorDataQoS(), std::bind(&WaypointPublisher::gps_callback, this, _1));

        // Publisher for waypoints to the MAVROS setpoint topic
        waypoint_publisher_ = this->create_publisher<geographic_msgs::msg::GeoPoseStamped>("/mavros/setpoint_position/global", 10);

        heading_subscriber_ = this->create_subscription<geographic_msgs::msg::GeoPoseStamped>(
            "/mavros/setpoint_position/global", rclcpp::SensorDataQoS(), std::bind(&WaypointPublisher::heading_callback, this, _1));

        // Create the service client to change the mode
        set_mode_client_ = this->create_client<mavros_msgs::srv::SetMode>("/mavros/set_mode");

        // Change the mode to OFFBOARD after a delay
        services_timer_ = this->create_wall_timer(3s, [this]() {
            RCLCPP_INFO(this->get_logger(), "Initiating OFFBOARD mode...");
            change_to_offboard_mode();
        });

        // Start a timer to publish dummy waypoints
        waypoint_timer_ = this->create_wall_timer(200ms, [this]() { publish_waypoint(); });
    }

private:
    void gps_callback(const sensor_msgs::msg::NavSatFix::SharedPtr msg)
    {
        if (isfinite(msg->latitude) && isfinite(msg->longitude)) {
            last_kart_latitude = current_latitude_;
            last_kart_longitude = current_longitude_;
            current_latitude_ = msg->latitude;
            current_longitude_ = msg->longitude;

        } else {
            RCLCPP_WARN(this->get_logger(), "Invalid GPS data received. Waiting for valid GPS signal...");
        }
    }

    void heading_callback(const geographic_msgs::msg::GeoPoseStamped::SharedPtr msg)
    {
        const auto& orientation = msg->pose.orientation;
        
        // Convert quaternion to RPY angles
        tf2::Quaternion tf_quat;
        tf2::fromMsg(orientation, tf_quat);
        
        double roll, pitch, yaw;
        tf2::Matrix3x3(tf_quat).getRPY(roll, pitch, yaw);
        current_heading_ = yaw;
    }

    void change_to_offboard_mode()
    {
        if (!set_mode_client_->wait_for_service(5s)) {
            RCLCPP_ERROR(this->get_logger(), "SetMode service not available");
            return;
        }

        auto request = std::make_shared<mavros_msgs::srv::SetMode::Request>();
        request->base_mode = 0; // No change to base_mode
        request->custom_mode = "OFFBOARD";

        std::thread([this, request]() {
            auto result = set_mode_client_->async_send_request(request);
            try {
                if (result.wait_for(5s) == std::future_status::ready) {
                    auto response = result.get();
                    if (response->mode_sent) {
                        RCLCPP_INFO(this->get_logger(), "Successfully changed to OFFBOARD mode");
                        waypoint_timer_->cancel(); // Stop publishing dummy waypoints
                        waypoint_timer_ = this->create_wall_timer(1s, [this]() { publish_waypoint(); }); // Publish real waypoints
                    } else {
                        RCLCPP_ERROR(this->get_logger(), "Failed to change to OFFBOARD mode");
                    }
                } else {
                    RCLCPP_ERROR(this->get_logger(), "Timeout while changing to OFFBOARD mode");
                }
            } catch (const std::exception &e) {
                RCLCPP_ERROR(this->get_logger(), "Exception in setting mode: %s", e.what());
            }
        }).detach(); // Detach the thread
    }

    void publish_waypoint()
    {
        // RCLCPP_INFO(this->get_logger(), "waypoint_latidtude: %.6f, waypoint_longitude: %.6f", waypoint_latitude, waypoint_longitude);
        
        get_next_waypoint();
        // Convert GPS (latitude, longitude) to a local coordinate system
        // double waypoint_x = (waypoint_latitude - origin_latitude_) * meters_per_degree_;
        // double waypoint_y = (waypoint_longitude - origin_longitude_) * meters_per_degree_;

        // Calculate heading
        double heading = calculate_waypoints_angle();

        // Convert heading to quaternion
        tf2::Quaternion quaternion;
        quaternion.setRPY(0, 0, heading); // Roll and pitch are 0; yaw is the heading

        // Set message values
        auto waypoint_msg = geographic_msgs::msg::GeoPoseStamped();
        waypoint_msg.header.stamp = this->get_clock()->now();
        waypoint_msg.header.frame_id = "global"; // Replace with your local frame if needed
        waypoint_msg.pose.position.latitude = waypoint_latitude;
        waypoint_msg.pose.position.longitude = waypoint_longitude;
        waypoint_msg.pose.position.altitude = 0.0; // Assuming ground-level operation
        waypoint_msg.pose.orientation.x = quaternion.x();
        waypoint_msg.pose.orientation.y = quaternion.y();
        waypoint_msg.pose.orientation.z = quaternion.z();
        waypoint_msg.pose.orientation.w = quaternion.w();

        RCLCPP_INFO(this->get_logger(), "Publishing Waypoint: latitude: %.2f, longitude: %.2f, current counter = %d", waypoint_latitude, waypoint_longitude, counter);
        RCLCPP_INFO(this->get_logger(), "Heading: %.2f", heading);
        waypoint_publisher_->publish(waypoint_msg);
    }

    double normalize_angle(double angle){
        if (angle < - M_PI) {
            angle += 2 * M_PI;
        }
        else if (angle >= M_PI){
            angle -= 2 * M_PI;
        }
        return angle;
    }


    double calculate_waypoints_angle()
    {

        // Algo 1 - probably not the best when hyperparameters of 2 are good - Jason

        // double way_vec_lon = (next_waypoint_longitude - waypoint_longitude);
        // double way_vec_lat = (next_waypoint_latitude - waypoint_latitude);

        // double kart_vec_lon = (current_longitude_ - last_kart_longitude);
        // double kart_vec_lat = (current_latitude_ - last_kart_latitude);

        // double wayCrossKart_norm = abs((way_vec_lon*kart_vec_lat) - (way_vec_lat*kart_vec_lon));

        // // cos (theta) = (a dot b)/(|a|*|b|)
        // // sin (theta) = (|a x b|)/(|a|*|b|)
        // double heading = atan2(wayCrossKart_norm, (way_vec_lon*kart_vec_lon + way_vec_lat*kart_vec_lat));

        // // Normalize the heading to [-pi, pi)
        // heading = normalize_angle(heading);

        // if (heading < -M_PI/7){
        //     heading = -M_PI/7;
        // }
        // else if (heading >= M_PI/7){
        //     heading = M_PI/7;
        // }

        // if ((waypoint_latitude >  current_latitude_  && waypoint_longitude < current_longitude_)||(waypoint_latitude <  current_latitude_  && waypoint_longitude > current_longitude_)){
        //     heading = -heading;
        // }

        //----------------------------------

        //Algo 2: Probably the better once good hyperparameters - Jason
        
        double alpha = atan2(waypoint_longitude - current_longitude_, waypoint_latitude - current_latitude_) - current_heading_;
        alpha = normalize_angle(alpha);
        
        double beta = atan2(next2_waypoint_longitude - next_waypoint_longitude, next2_waypoint_latitude - next_waypoint_latitude) - (current_heading_ + alpha);
        beta = normalize_angle(beta);
        
        // Tune these, beta < 0, aplha > 0
        double K_alpha = 1.0;
        double K_beta = -1.0;
        
        double heading = ((K_alpha * alpha) + (K_beta * beta));
        
        if (heading < -M_PI/7){
            heading = -M_PI/7;
        }
        else if (heading >= M_PI/7){
            heading = M_PI/7;
        }

        return heading;
    }

    void get_next_waypoint()
    {
        // Ensure counter does not exceed vector size
        if (counter >= (int) latitude_vec.size()) {
            RCLCPP_INFO(this->get_logger(), "All waypoints have been processed.");
            waypoint_latitude = 0.0;
            waypoint_longitude = 0.0;
            return;
        }
        double latitude_differential = abs(waypoint_latitude - current_latitude_);
        double longitude_differential = abs(waypoint_longitude - current_longitude_);
        RCLCPP_INFO(this->get_logger(), "latitude_differential = %.6f, longitude_differential = %.6f", latitude_differential, longitude_differential);
        // If this is the first waypoint or we have reached the current waypoint
        if ((waypoint_latitude == 0.0 && waypoint_longitude == 0.0) || (latitude_differential < offset_latitude && longitude_differential < offset_longitude)) {
            waypoint_latitude = latitude_vec[counter];
            waypoint_longitude = longitude_vec[counter];
            next_waypoint_latitude = latitude_vec[counter+1];
            next_waypoint_longitude = longitude_vec[counter+2];
            next2_waypoint_latitude = latitude_vec[counter+2];
            next2_waypoint_longitude = longitude_vec[counter+1];
            last_waypoint_latitude = latitude_vec[counter-1];
            last_waypoint_longitude = longitude_vec[counter-1];
            RCLCPP_INFO(this->get_logger(), "Updating to next waypoint: Latitude: %.6f, Longitude: %.6f",
                        waypoint_latitude, waypoint_longitude);
            counter++;
            counter %= latitude_vec.size();
        }
    }

    void get_coords()
    {
        // Get the path to the package's share directory
        std::string package_share_path = ament_index_cpp::get_package_share_directory("ros_nav");
        std::string latitude_file_path = package_share_path + "/data/latitudes_minimal.txt";
        std::string longitude_file_path = package_share_path + "/data/longitudes_minimal.txt";
        std::string spline_lat_file_path = package_share_path + "/data/latitudes_spline.txt";
        std::string spline_lon_file_path = package_share_path + "/data/longitudes_spline.txt";

        // Read latitudes from file
        ifstream read_latitude(latitude_file_path);
        if (!read_latitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", latitude_file_path.c_str());
            return;
        }
        double value;
        while (read_latitude >> value) {
            latitude_vec.push_back(value);
        }
        read_latitude.close();

        // Read longitudes from file
        ifstream read_longitude(longitude_file_path);
        if (!read_longitude.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", longitude_file_path.c_str());
            return;
        }
        while (read_longitude >> value) {
            longitude_vec.push_back(value);
        }
        read_longitude.close();

        // Read spline latitudes from file
        ifstream read_spline_lat(spline_lat_file_path);
        if (!read_spline_lat.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", spline_lat_file_path.c_str());
            return;
        }
        while (read_spline_lat >> value) {
            spline_lat_vec.push_back(value);
        }
        read_spline_lat.close();

        // Read spline longitudes from file
        ifstream read_spline_lon(spline_lon_file_path);
        if (!read_spline_lon.is_open()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Unable to open %s", spline_lon_file_path.c_str());
            return;
        }

        while (read_spline_lon >> value) {
            spline_lon_vec.push_back(value);
        }
        read_spline_lon.close();

        // Check if latitude and longitude vectors are the same size
        if (latitude_vec.size() != longitude_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Latitude and Longitude vectors are not of equal size.");
            return;
        }

        // Check if latitude and longitude vectors are the same size
        if (spline_lat_vec.size() != spline_lon_vec.size()) {
            RCLCPP_ERROR(this->get_logger(), "Error: Spline Latitude and Longitude vectors are not of equal size.");
            return;
        }
    }

    rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr gps_subscriber_;
    rclcpp::Publisher<geographic_msgs::msg::GeoPoseStamped>::SharedPtr waypoint_publisher_;
    rclcpp::Subscription<geographic_msgs::msg::GeoPoseStamped>::SharedPtr heading_subscriber_;
    rclcpp::Client<mavros_msgs::srv::SetMode>::SharedPtr set_mode_client_;
    rclcpp::TimerBase::SharedPtr waypoint_timer_;
    rclcpp::TimerBase::SharedPtr services_timer_;

    double current_latitude_ = 0.0;
    double current_longitude_ = 0.0;

    double last_kart_latitude = 0.0;
    double last_kart_longitude = 0.0;

    double waypoint_latitude = 0.0;
    double waypoint_longitude = 0.0;

    double next_waypoint_latitude = 0.0;
    double next_waypoint_longitude = 0.0;

    double next2_waypoint_latitude = 0.0;
    double next2_waypoint_longitude = 0.0;

    double last_waypoint_latitude = 0.0;
    double last_waypoint_longitude = 0.0;

    double current_heading_ = 0.0;

    const double origin_latitude_ = 40.437688;
    const double origin_longitude_ = -86.944469;

    const double meters_per_degree_ = 111000.0;

    const double offset_latitude = 0.00004;
    const double offset_longitude = 0.00004;


    vector<double> longitude_vec;  // Vector to store longitudes
    vector<double> latitude_vec;  // Vector to store latitudes
    vector<double> spline_lon_vec;
    vector<double> spline_lat_vec;

    int counter = 0;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<WaypointPublisher>());
    rclcpp::shutdown();
    return 0;
}
