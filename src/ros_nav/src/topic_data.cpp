#include "rclcpp/rclcpp.hpp"
#include "mavros_msgs/msg/state.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"


using std::placeholders::_1;
using namespace std;
using namespace std::chrono_literals;

class TopicSubscriber : public rclcpp::Node
{
public:
    TopicSubscriber() : Node("topic_subscriber")
    {
        // Subscribe to state
        state_sub_ = this->create_subscription<mavros_msgs::msg::State>(
            "/mavros/state", 10,
            [this](const mavros_msgs::msg::State::SharedPtr msg) {
                state_callback(msg);});
        
        // Sub to gps
        gps_sub_ = this->create_subscription<sensor_msgs::msg::NavSatFix>(
            "/mavros/global_position/global", rclcpp::SensorDataQoS(), std::bind(&TopicSubscriber::gps_callback, this, _1));
    
        gps_timer_ = this->create_wall_timer(1s, [this]() {
            gps_fake_callback();
        });

        // Subscribe to velo
        velo_sub_ = this->create_subscription<geometry_msgs::msg::TwistStamped>(
            "/mavros/local_position/velocity_body", rclcpp::SensorDataQoS(),
            [this](const geometry_msgs::msg::TwistStamped::SharedPtr msg) {
                velo_callback(msg);});

        velo_timer_ = this->create_wall_timer(1s, [this]() {
            velo_fake_callback();
        });

    }

private:
    void state_callback(const mavros_msgs::msg::State::SharedPtr msg)
    {
        RCLCPP_INFO(this->get_logger(), "--- State Update ---");
        RCLCPP_INFO(this->get_logger(), "Armed: %s", msg->armed ? "true" : "false");
        RCLCPP_INFO(this->get_logger(), "Mode: %s", msg->mode.c_str());
    }

    void gps_callback(const sensor_msgs::msg::NavSatFix::SharedPtr msg)
    {
        current_latitude_ = msg->latitude;
        current_longitude_ = msg->longitude; 
    }

    void gps_fake_callback()
    {
        RCLCPP_INFO(this->get_logger(), "--- Position Update ---");
        RCLCPP_INFO(this->get_logger(), "Latitude: %f", current_latitude_);
        RCLCPP_INFO(this->get_logger(), "Longitude: %f", current_longitude_);
        
    }    

    void velo_callback(const geometry_msgs::msg::TwistStamped::SharedPtr msg)
    {
        current_velo_x_ = msg->twist.linear.x;
        current_velo_y_ = msg->twist.linear.y;
    }

    void velo_fake_callback()
    {
        RCLCPP_INFO(this->get_logger(), "--- Velocity Update ---");
        RCLCPP_INFO(this->get_logger(), "x: %f (m/s)", current_velo_x_);
        RCLCPP_INFO(this->get_logger(), "y: %f (m/s)", current_velo_y_);
        
    }    

    double current_latitude_ = 0.0;
    double current_longitude_ = 0.0;
    double current_velo_x_ = 0.0;
    double current_velo_y_ = 0.0;

    rclcpp::TimerBase::SharedPtr gps_timer_;
    rclcpp::TimerBase::SharedPtr velo_timer_;

    rclcpp::Subscription<mavros_msgs::msg::State>::SharedPtr state_sub_;
    rclcpp::Subscription<sensor_msgs::msg::NavSatFix>::SharedPtr gps_sub_;
    rclcpp::Subscription<geometry_msgs::msg::TwistStamped>:: SharedPtr velo_sub_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<TopicSubscriber>());
    rclcpp::shutdown();
    return 0;
}