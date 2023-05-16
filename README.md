# Call Light System for Long-Term Care Facility

The Call Light System is designed to provide an efficient and reliable way for nursing staff in a long-term care facility to receive alerts when residents require assistance. The system utilizes Raspberry Pis, Python programming, schematic and PCB design, Home Assistant, MQTT for pub/sub and wireless communications, and a secure local server. The building is wired with Ethernet cables to facilitate the communication between the buttons and lights.

## Features

- Raspberry Pis: The system utilizes Raspberry Pis as the central processing units to control the communication between buttons and lights.
- Python Programming: The system's logic and functionality are implemented using Python programming language, ensuring flexibility and easy maintenance.
- Schematic and PCB Design: The hardware components are designed and integrated using schematic and PCB design techniques, providing a streamlined and reliable system.
- Home Assistant Integration: Home Assistant is utilized to manage and control the overall system, offering a user-friendly interface for monitoring and configuration.
- MQTT for Pub/Sub and Wireless Communications: The system employs MQTT (Message Queuing Telemetry Transport) protocol for efficient publish-subscribe messaging and wireless communications between the Raspberry Pis, buttons, and lights.
- Local Secure Server: A local server is set up to ensure secure communication and data management within the facility, protecting the privacy and confidentiality of the residents.
- Wired Building with Ethernet Cables: Ethernet cables are installed throughout the building, allowing seamless and reliable communication between the buttons and lights, ensuring prompt response to residents' needs.

## Setup and Configuration

1. Hardware Setup: Follow the provided hardware documentation to set up the Raspberry Pis, buttons, and lights according to the schematic and PCB design.
2. Software Installation: Install the required software dependencies and libraries as specified in the installation instructions.
3. Configuration: Customize the system's settings, such as MQTT broker configuration, network settings, and resident-specific details, using the provided configuration file.
4. Integration with Home Assistant: Connect the system to Home Assistant by following the integration guide, enabling easy monitoring and control through the Home Assistant user interface.
5. Testing and Calibration: Conduct thorough testing and calibration of the system to ensure proper functionality and responsiveness.
6. Deployment: Deploy the system in the long-term care facility, ensuring all buttons and lights are properly installed and connected via the wired Ethernet infrastructure.
7. Ongoing Maintenance: Regularly monitor the system's performance, apply updates and patches, and address any maintenance needs to ensure the smooth operation of the call light system.

## Contributors

- [Axel De La Guardia](https://github.com/axeldelaguardia)
- [Hansin Lee](https://github.com/HannyShin)

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- [Home Assistant](https://www.home-assistant.io/) - Open-source home automation platform.
- [MQTT](https://mqtt.org/) - Lightweight messaging protocol for IoT applications.
- [Raspberry Pi](https://www.raspberrypi.org/) - Single-board computer for versatile projects.
