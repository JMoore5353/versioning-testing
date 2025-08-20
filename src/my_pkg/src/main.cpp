#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

class MyNode : public rclcpp::Node {
public:
  MyNode() : rclcpp::Node("my_node") {
    my_pub_ = this->create_publisher<std_msgs::msg::String>("my_data", 10);
  }

private:
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr my_pub_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<MyNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
