import pytest

from device import *
from zigbee import *

def do_zigbee_request(device, zigbee, request_topic, payload, response_topic, expected_response):
    # Prepare for waiting a zigbee2mqtt response
    zigbee.subscribe(response_topic)

    # Publish the request
    zigbee.publish(request_topic, payload)

    # Verify that the device has received the request, and properly process it
    device.wait_str(expected_response)

    # Wait the response from zigbee2mqtt
    return zigbee.wait_msg(response_topic)


def send_bind_request(bridge, clusters, src, dst):
    # clusters attribute must be a list
    if isinstance(clusters, str):
        clusters = [clusters]

    # Send the bind request
    payload = {"clusters": clusters, "from": src, "to": dst, "skip_disable_reporting": "true"}
    bridge.request('device/bind', payload)


def send_unbind_request(bridge, clusters, src, dst):
    # clusters attribute must be a list
    if isinstance(clusters, str):
        clusters = [clusters]

    # Send the bind request
    payload = {"clusters": clusters, "from": src, "to": dst, "skip_disable_reporting": "true"}
    bridge.request('device/unbind', payload)


class SmartSwitch:
    """ 
    Smart Switch Test Harness

    This is a helper object that simplifies operating with the device via both UART and MQTT, performs routine checks,
    and moves communication burden from the test to the test harness.
    """

    def __init__(self, device, zigbee, ep, ep_name, z2m_name):
        # Remember parameters for further use
        self.device = device
        self.zigbee = zigbee
        self.ep = ep
        self.button = ep-1
        self.ep_name = ep_name
        self.z2m_name = z2m_name

        # Most of the tests will require device state MQTT messages. Subscribe for them
        self.zigbee.subscribe(self.z2m_name)

        # Make sure the device is fresh and ready to operate
        self.reset()


    def reset(self):
        self.device.reset()
        self.wait_button_state('IDLE')


    def get_full_name(self):
        return f"{self.z2m_name}/{self.ep}"
    

    def get_action_name(self, action):
        return action + '_' + self.ep_name


    def do_set_request(self, attribute, value, expected_response):
        # Send payload like {"state_button_3", "ON"} to the <device>/set topic
        # Wait for the new device state response
        payload = {attribute: value}
        response = do_zigbee_request(self.device, self.zigbee, self.z2m_name + '/set', payload, self.z2m_name, expected_response)
        return response[attribute]


    def do_get_request(self, attribute, expected_response):
        # Send payload like {"state_button_3", ""} to the <device>/get topic
        # Wait for the new device state response
        payload = {attribute: ""}
        response = do_zigbee_request(self.device, self.zigbee, self.z2m_name + '/get', payload, self.z2m_name, expected_response)
        return response[attribute]


    def get_state_change_msg(self, expected_state):
        state = "1" if expected_state == "ON" else ("0" if expected_state == "OFF" else "") 
        return f"SwitchEndpoint EP={self.ep}: do state change {state}"


    def switch(self, cmd, expected_state = None):
        # Calculate expected state. Toggle command may not be fully checked, but this ok as it simplifies the test
        if expected_state == None and cmd != "TOGGLE": 
            expected_state = cmd   

        # Send the On/Off/Toggle command, verify device log has the state change message
        msg = self.get_state_change_msg(expected_state)
        self.do_set_request('state_'+self.ep_name, cmd, msg)

        # Device will respond with On/Off state report
        state = self.wait_zigbee_state_change()

        # Verify response from Z2M if possible
        if expected_state != None:
            assert state == expected_state

        return state


    def get_state(self):
        msg = f"ZCL Read Attribute: EP={self.ep} Cluster=0006 Command=00 Attr=0000"
        return self.do_get_request('state_'+self.ep_name, msg)


    def wait_device_state_change(self, expected_state):
        msg = self.get_state_change_msg(expected_state)
        self.device.wait_str(msg)


    def get_attr_id_by_name(self, attr):
        match attr:
            case 'switch_mode':
                return 'ff00'
            case 'switch_actions':
                return '0010'
            case 'relay_mode':
                return 'ff01'
            case 'max_pause':
                return 'ff02'
            case 'min_long_press':
                return 'ff03'
            case 'long_press_mode':
                return 'ff04'
            case 'operation_mode':
                return 'ff05'
            case _:
                raise RuntimeError("Unknown attribute name")


    def set_attribute(self, attr, value):
        msg = f"ZCL Write Attribute: Cluster 0007 Attrib {self.get_attr_id_by_name(attr)}"
        assert self.do_set_request(attr + '_' + self.ep_name, value, msg) == value
        self.wait_button_state('IDLE')


    def get_attribute(self, attr):
        msg = f"ZCL Read Attribute: EP={self.ep} Cluster=0007 Command=00 Attr={self.get_attr_id_by_name(attr)}"
        return self.do_get_request(attr + '_' + self.ep_name, msg)
    

    def press_button(self):
        cmd = f"BTN{self.button}_PRESS"
        self.device.send_str(cmd)


    def release_button(self):
        cmd = f"BTN{self.button}_RELEASE"
        self.device.send_str(cmd)


    def wait_button_state(self, state):
        state_str = f"Switching button {self.ep} state to {state}"
        self.device.wait_str(state_str)


    def wait_report_multistate(self, value):
        state_str = f"Reporting multistate action EP={self.ep} value={value}... status: 00"
        self.device.wait_str(state_str)


    def wait_report_level_ctrl(self, cmd):
        state_str = f"Sending Level Control {cmd} command status: 00"
        self.device.wait_str(state_str)


    def wait_zigbee_msg(self):
        return self.zigbee.wait_msg(self.z2m_name)
    

    def wait_zigbee_state_change(self):
        return self.zigbee.wait_msg(self.z2m_name)['state_' + self.ep_name]


    def wait_zigbee_attribute_change(self, attribute):
        return self.zigbee.wait_msg(self.z2m_name)[attribute + '_' + self.ep_name]


    def wait_zigbee_action(self):
        return self.zigbee.wait_msg(self.z2m_name)['action']
