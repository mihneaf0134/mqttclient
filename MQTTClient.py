import socket
import time
import select
import os
from threading import Thread, Event


class MQTTClient:
    def __init__(self,
                 # IP, PORT, flags for CONNECT and PUBLISH, last will, username, password, keep alive and qos
                 ip, port, client_id, clean_start=True, will_retain=False, retain=False, last_will='', username='',
                 password='', keep_alive=60, qos=0, will_qos=0,

                 # CONNECT packet variable header fields
                 session_expiry_interval_connect=-1, receive_maximum_connect=0, maximum_packet_size_connect=0,
                 topic_alias_maximum_connect=0,
                 request_response_information_connect=False, request_problem_information_connect=True,
                 user_property_connect='', will_delay_interval=0, payload_format_indicator_will=-1,
                 message_expiry_interval_will=0,
                 content_type_will='', response_topic_will='', correlation_data_will='', user_property_will='',
                 will_topic='',

                 # PUBLISH packet variable header fields and payload
                 publish_topic='', publish_message='', payload_format_indicator_publish=-1,
                 message_expiry_interval_publish=0, topic_alias_publish=0,
                 response_topic_publish='', correlation_data_publish='', user_property_publish='',
                 content_type_publish='',

                 # SUBSCRIBE properites
                 user_property_subscribe='', subscribe_topic='',

                 # UNSUBSCRIBE properites
                 user_property_unsubscribe=''):
        self.ip = ip
        self.port = port
        self.client_id = client_id
        self.clean_start = clean_start
        self.last_will = last_will
        self.username = username
        self.password = password
        self.keep_alive = keep_alive
        self.will_retain = will_retain
        self.dup = 0
        self.retain = retain

        self.session_expiry_interval_connect = session_expiry_interval_connect
        self.receive_maximum_connect = receive_maximum_connect
        self.maximum_packet_size_connect = maximum_packet_size_connect
        self.topic_alias_maximum_connect = topic_alias_maximum_connect
        self.request_response_information_connect = request_response_information_connect
        self.request_problem_information_connect = request_problem_information_connect
        self.user_property_connect = user_property_connect

        self.will_delay_interval = will_delay_interval
        self.payload_format_indicator_will = payload_format_indicator_will
        self.message_expiry_interval_will = message_expiry_interval_will
        self.content_type_will = content_type_will
        self.response_topic_will = response_topic_will
        self.correlation_data_will = correlation_data_will
        self.user_property_will = user_property_will

        self.payload_format_indicator_publish = payload_format_indicator_publish
        self.message_expiry_interval_publish = message_expiry_interval_publish
        self.topic_alias_publish = topic_alias_publish
        self.response_topic_publish = response_topic_publish
        self.correlation_data_publish = correlation_data_publish
        self.user_property_publish = user_property_publish
        self.content_type_publish = content_type_publish

        self.user_property_subscribe = user_property_subscribe

        self.user_property_unsubscribe = user_property_unsubscribe

        self.next_ping_time = time.time() + self.keep_alive
        self.qos = qos
        self.will_qos = will_qos
        self.qosSupported = 0
        self.s = None
        self.subscribe_identifier = 1
        self.running = True
        self.recieved_data = b''
        self.response_event = Event()
        self.response_thread = None

        self.packet_identifier = 1
        self.will_topic = will_topic.encode('utf-8')
        self.publish_topic = publish_topic.encode('utf-8')
        self.message_mqtt = publish_message.encode('utf-8')
        self.subscribe_topic = subscribe_topic.encode('utf-8')

    def set_publish_message(self, message):
        self.message_mqtt = message.encode('utf-8')

    def set_publish_topic(self, topic):
        self.publish_topic = topic.encode('utf-8')

    def set_will_topic(self, topic):
        self.will_topic = topic.encode('utf-8')

    def set_subscribe_topic(self, topic):
        self.subscribe_topic = topic.encode('utf-8')

    def __print_and_quit(self, message):
        print(message)
        os._exit(os.EX_PROTOCOL)

    def connect_to_broker(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(3)
        try:
            self.s.connect((self.ip, self.port))
        except socket.timeout:
            print('Connection timed out')
            os._exit(os.EX_IOERR)
        self.response_thread = Thread(target=self.__response_handler)
        self.response_thread.start()
        print(f'Connected to {self.ip}:{self.port}')

    def connect(self):
        clean_start = 0x02 if self.clean_start else 0x00
        will_flag = 0x04 if self.last_will else 0x00
        will_qos = self.will_qos << 3 if self.last_will else 0x00
        will_retain = 0x01 if self.will_retain else 0x00
        username_flag = 0x80 if self.username else 0x00
        password_flag = 0x40 if self.password else 0x00

        connect_flags = (
                clean_start | will_flag | will_qos | will_retain | username_flag | password_flag
        )
        keep_alive = self.keep_alive.to_bytes(2, byteorder='big')
        client_id_encoded = self.client_id.encode('utf-8')
        client_id_len = len(client_id_encoded).to_bytes(2, byteorder='big')
        payload = client_id_len + client_id_encoded

        if self.last_will:
            will_topic_len = len(self.will_topic).to_bytes(2, byteorder='big')
            will_message = self.last_will.encode('utf-8')
            will_message_len = len(will_message).to_bytes(2, byteorder='big')

            will_properties = b''
            if self.will_delay_interval != 0:
                will_properties += b'\x18' + self.will_delay_interval.to_bytes(4, byteorder='big')

            if self.payload_format_indicator_will != -1:
                will_properties += b'\x01' + self.payload_format_indicator_will.to_bytes(1, byteorder='big')

            if self.message_expiry_interval_will != 0:
                will_properties += b'\x02' + self.message_expiry_interval_will.to_bytes(4, byteorder='big')

            if self.content_type_will != '':
                content_type_will_encoded = self.content_type_will.encode('utf-8')
                will_properties += b'\x03' + len(content_type_will_encoded).to_bytes(2,
                                                                                     byteorder='big') + content_type_will_encoded

            if self.response_topic_will != '':
                response_topic_will_encoded = self.response_topic_will.encode('utf-8')
                will_properties += b'\x08' + len(response_topic_will_encoded).to_bytes(2,
                                                                                       byteorder='big') + response_topic_will_encoded

            if self.correlation_data_will != '':
                correlation_data_will_encoded = self.correlation_data_will.encode('utf-8')
                will_properties += b'\x09' + len(correlation_data_will_encoded).to_bytes(2,
                                                                                         byteorder='big') + correlation_data_will_encoded

            if self.user_property_will != '':
                user_properties = self.user_property_will.split('|')
                for user_property in user_properties:
                    name, value = user_property.split(':')
                    name_bytes = name.encode('utf-8')
                    value_bytes = value.encode('utf-8')
                    will_properties += b'\x26' + len(name_bytes).to_bytes(2, byteorder='big') + name_bytes + len(
                        value_bytes).to_bytes(2, byteorder='big') + value_bytes

            will_properties_len = len(will_properties).to_bytes(1, byteorder='big')
            payload += will_properties_len + will_properties + will_topic_len + self.will_topic + will_message_len + will_message

        if self.username:
            username_encoded = self.username.encode('utf-8')
            username_len = len(username_encoded).to_bytes(2, byteorder='big')
            payload += username_len + username_encoded

        if self.password:
            password_encoded = self.password.encode('utf-8')
            password_len = len(password_encoded).to_bytes(2, byteorder='big')
            payload += password_len + password_encoded

        variable_header = (
                b'\x00\x04' + b'MQTT' + b'\x05' + bytes([connect_flags]) + keep_alive
        )

        properties = b''

        if self.session_expiry_interval_connect != -1 and clean_start == 0x00:
            session_expiry = b'\x11' + self.session_expiry_interval_connect.to_bytes(4, byteorder='big')
            properties += session_expiry

        if self.receive_maximum_connect != 0:
            receive_maximum_connect = b'\x21' + self.receive_maximum_connect.to_bytes(2, byteorder='big')
            properties += receive_maximum_connect

        if self.maximum_packet_size_connect != 0:
            maximum_packet_size_connect = b'\x27' + self.maximum_packet_size_connect.to_bytes(4, byteorder='big')
            properties += maximum_packet_size_connect

        if self.topic_alias_maximum_connect != 0:
            topic_alias_maximum_connect = b'\x22' + self.topic_alias_maximum_connect.to_bytes(2, byteorder='big')
            properties += topic_alias_maximum_connect

        if self.request_response_information_connect:
            request_response_information_connect = b'\x19' + (1).to_bytes(1, byteorder='big')
            properties += request_response_information_connect

        if not self.request_problem_information_connect:
            request_problem_information_connect = b'\x17' + (0).to_bytes(1, byteorder='big')
            properties += request_problem_information_connect

        if self.user_property_connect != '':
            user_properties = self.user_property_connect.split('|')
            for user_property in user_properties:
                name, value = user_property.split(':')
                name_bytes = name.encode('utf-8')
                value_bytes = value.encode('utf-8')
                user_property_bytes = b'\x26' + len(name_bytes).to_bytes(2, byteorder='big') + name_bytes + len(
                    value_bytes).to_bytes(2, byteorder='big') + value_bytes
                properties += user_property_bytes

        variable_header += len(properties).to_bytes(1, byteorder='big') + properties

        remaining_length = len(variable_header) + len(payload)
        fixed_header = b'\x10' + remaining_length.to_bytes(1, byteorder='big')
        connect_packet = fixed_header + variable_header + payload

        if self.s.fileno() != -1:
            self.s.sendall(connect_packet)
            self.__reset_keep_alive()
            self.response_event.wait()
            self.response_event.clear()

    def subscribe(self):
        variable_header = self.packet_identifier.to_bytes(2, byteorder='big')
        self.packet_identifier += 1

        s_id_size = 0
        if 0 < self.subscribe_identifier < 127:
            s_id_size = 1
        if 128 < self.subscribe_identifier < 16383:
            s_id_size = 2
        if 16384 < self.subscribe_identifier < 2097151:
            s_id_size = 3
        if 2097152 < self.subscribe_identifier < 268435455:
            s_id_size = 4

        properties = b'\x0B' + self.subscribe_identifier.to_bytes(s_id_size, byteorder='big')

        if self.user_property_subscribe != '':
            user_properties = self.user_property_subscribe.split('|')
            for user_property in user_properties:
                name, value = user_property.split(':')
                name_bytes = name.encode('utf-8')
                value_bytes = value.encode('utf-8')
                user_property_bytes = b'\x26' + len(name_bytes).to_bytes(2, byteorder='big') + name_bytes + len(
                    value_bytes).to_bytes(2, byteorder='big') + value_bytes
                properties += user_property_bytes

        variable_header += len(properties).to_bytes(1, byteorder='big') + properties
        payload = len(self.subscribe_topic).to_bytes(2, byteorder='big') + self.subscribe_topic + self.qos.to_bytes(1,
                                                                                                                byteorder='big')
        remaining_length = len(variable_header) + len(payload)
        fixed_header = b'\x82' + remaining_length.to_bytes(1, byteorder='big')
        subscribe_packet = fixed_header + variable_header + payload

        if self.s.fileno() != -1:
            self.s.sendall(subscribe_packet)
            self.__reset_keep_alive()
            self.response_event.wait()
            self.response_event.clear()

    def publish(self):
        variable_header = len(self.publish_topic).to_bytes(2, byteorder='big') + self.publish_topic
        if self.qos > 0:
            variable_header += self.packet_identifier.to_bytes(2, byteorder='big')
            self.packet_identifier += 1

        s_id_size = 0
        if 0 < self.subscribe_identifier < 127:
            s_id_size = 1
        if 128 < self.subscribe_identifier < 16383:
            s_id_size = 2
        if 16384 < self.subscribe_identifier < 2097151:
            s_id_size = 3
        if 2097152 < self.subscribe_identifier < 268435455:
            s_id_size = 4

        properties = b'\x0B' + self.subscribe_identifier.to_bytes(s_id_size, byteorder='big')

        if self.payload_format_indicator_publish != -1:
            properties += b'\x01' + self.payload_format_indicator_publish.to_bytes(1, byteorder='big')

        if self.message_expiry_interval_publish != 0:
            properties += b'\x02' + self.message_expiry_interval_publish.to_bytes(4, byteorder='big')

        if self.content_type_publish != '':
            content_type_publish_encoded = self.content_type_publish.encode('utf-8')
            properties += b'\x03' + len(content_type_publish_encoded).to_bytes(2,
                                                                               byteorder='big') + content_type_publish_encoded

        if self.topic_alias_publish != 0:
            properties += b'\x23' + self.topic_alias_publish.to_bytes(2, byteorder='big')

        if self.response_topic_publish != '':
            response_topic_publish_encoded = self.response_topic_publish.encode('utf-8')
            properties += b'\x08' + len(response_topic_publish_encoded).to_bytes(2,
                                                                                 byteorder='big') + response_topic_publish_encoded

        if self.correlation_data_publish != '':
            correlation_data_publish_encoded = self.correlation_data_publish.encode('utf-8')
            properties += b'\x09' + len(correlation_data_publish_encoded).to_bytes(2,
                                                                                   byteorder='big') + correlation_data_publish_encoded

        if self.user_property_publish != '':
            user_properties = self.user_property_publish.split('|')
            for user_property in user_properties:
                name, value = user_property.split(':')
                name_bytes = name.encode('utf-8')
                value_bytes = value.encode('utf-8')
                properties += b'\x26' + len(name_bytes).to_bytes(2, byteorder='big') + name_bytes + len(
                    value_bytes).to_bytes(2, byteorder='big') + value_bytes

        properties_len = len(properties).to_bytes(1, byteorder='big')
        variable_header += properties_len + properties

        payload = len(self.message_mqtt).to_bytes(2, byteorder='big') + self.message_mqtt
        remaining_length = len(variable_header) + len(payload)
        fixed_header = (0x30 | (self.dup << 3) | (self.qos << 1) | int(self.retain)).to_bytes(1,
                                                                                              byteorder='big') + remaining_length.to_bytes(
            1, byteorder='big')
        publish_packet = fixed_header + variable_header + payload
        if len(publish_packet) > self.maximum_packet_size_connect > 0:
            print('PUBLISH packet too large.')
        else:
            if self.s.fileno() != -1:
                self.s.sendall(publish_packet)
                self.__reset_keep_alive()
                if self.qos != 0:
                    self.response_event.wait()
                    self.response_event.clear()

    def handle_qos2_send_PUBREL(self, packet):
        variable_header = packet[2:4]
        remaining_length = len(variable_header)
        fixed_header = b'\x62' + remaining_length.to_bytes(1, byteorder='big')
        pubrel_packet = fixed_header + variable_header
        self.recieved_data = b''
        if self.s.fileno() != -1:
            self.s.sendall(pubrel_packet)
            self.__reset_keep_alive()

    def handle_qos_1(self, packet):
        topic_length = int.from_bytes(packet[2:4], byteorder='big')
        variable_header = packet[4 + topic_length: 6 + topic_length]
        remaining_length = len(variable_header)
        fixed_header = b'\x40' + remaining_length.to_bytes(1, byteorder='big')
        puback_packet = fixed_header + variable_header

        self.recieved_data = b''
        if self.s.fileno() != -1:
            self.s.sendall(puback_packet)
            self.__reset_keep_alive()

    def handle_qos_2_PUBREC(self, packet_identifier):
        variable_header = packet_identifier.to_bytes(2, byteorder='big')
        remaining_length = len(variable_header)
        fixed_header = b'\x50' + remaining_length.to_bytes(1, byteorder='big')
        pubrec_packet = fixed_header + variable_header

        self.recieved_data = b''
        if self.s.fileno() != -1:
            self.s.sendall(pubrec_packet)
            self.__reset_keep_alive()

    def handle_qos_2_PUBCOMP(self, packet):
        variable_header = packet[2:4]
        remaining_length = len(variable_header)
        fixed_header = b'\x70' + remaining_length.to_bytes(1, byteorder='big')
        pubcomp_packet = fixed_header + variable_header

        self.recieved_data = b''
        if self.s.fileno() != -1:
            self.s.sendall(pubcomp_packet)
            self.__reset_keep_alive()

    def unsubscribe(self):
        variable_header = self.subscribe_identifier.to_bytes(2, byteorder='big')

        properties = b''

        if self.user_property_unsubscribe != '':
            user_properties = self.user_property_unsubscribe.split('|')
            for user_property in user_properties:
                name, value = user_property.split(':')
                name_bytes = name.encode('utf-8')
                value_bytes = value.encode('utf-8')
                user_property_bytes = b'\x26' + len(name_bytes).to_bytes(2, byteorder='big') + name_bytes + len(
                    value_bytes).to_bytes(2, byteorder='big') + value_bytes
                properties += user_property_bytes

        variable_header += len(properties).to_bytes(1, byteorder='big') + properties

        payload = len(self.subscribe_topic).to_bytes(2, byteorder='big') + self.subscribe_topic
        remaining_length = len(variable_header) + len(payload)
        fixed_header = b'\xA2' + remaining_length.to_bytes(1, byteorder='big')
        unsubscribe_packet = fixed_header + variable_header + payload

        if self.s.fileno() != -1:
            self.s.sendall(unsubscribe_packet)
            self.__reset_keep_alive()
            self.response_event.wait()
            self.response_event.clear()

    def ping(self):
        pingreq_packet = b'\xC0\x00'
        if self.s.fileno() != -1:
            self.s.sendall(pingreq_packet)
            self.__reset_keep_alive()

    def disconnect(self, reason_code):
        fixed_header = b'\xE0'
        if reason_code == 0:
            variable_header = b''
            fixed_header += b'\x00'
        else:
            variable_header = reason_code.to_bytes(1, byteorder='big') + b'\x00\x00'
            fixed_header += len(variable_header).to_bytes(1, byteorder='big')
        disconnect_packet = fixed_header + variable_header

        self.running = False
        if self.s.fileno() != -1:
            self.s.sendall(disconnect_packet)
        print('Disconnected.')
        self.response_thread.join()

    def close_connection(self):
        self.running = False
        self.s.shutdown(socket.SHUT_RDWR)
        self.s.close()
        print('Connection closed.')

    def __handle_CONNACK(self, packet):
        if packet[0] != len(packet[1:]):
            self.__print_and_quit('Bad remaining length for CONNACK.')

        if packet[1] > 1:
            self.__print_and_quit('Bad connect CONNACK flags.')

        if self.clean_start is True and packet[1] == 1:
            self.__print_and_quit('The server says that there is another state while there isn\'t one.')

        if packet[1] == 0 and packet[2] != 0:
            self.__print_and_quit('There is an error but it says there is a session present.')

        match packet[2]:
            case 0x00:
                print('Successfully connected.')
            case 0x80:
                self.__print_and_quit('Unspecified error.')
            case 0x81:
                self.__print_and_quit('Malformed packet.')
            case 0x82:
                self.__print_and_quit('Protocol error.')
            case 0x83:
                self.__print_and_quit('CONNECT is valid but the server is doesn\'t accept it')
            case 0x84:
                self.__print_and_quit('Unsupported protocol version.')
            case 0x85:
                self.__print_and_quit('Client identifier not valid.')
            case 0x86:
                self.__print_and_quit('Bad user name or password.')
            case 0x87:
                self.__print_and_quit('Not authorized.')
            case 0x88:
                self.__print_and_quit('Server unavailable')
            case 0x89:
                self.__print_and_quit('Server busy.')
            case 0x8A:
                self.__print_and_quit('Banned.')
            case 0x8C:
                self.__print_and_quit('Bad authentification method.')
            case 0x90:
                self.__print_and_quit('Topic name invalid.')
            case 0x95:
                self.__print_and_quit('Packet too large.')
            case 0x97:
                self.__print_and_quit('Quota exceeded')
            case 0x99:
                self.__print_and_quit('Payload format invalid.')
            case 0x9A:
                self.__print_and_quit('Retain not supported.')
            case 0x9B:
                self.__print_and_quit('QoS not supported.')
            case 0x9C:
                self.__print_and_quit('Use another server.')
            case 0x9D:
                self.__print_and_quit('Server moved.')
            case 0x9F:
                self.__print_and_quit('Connection rate exceeded.')

        if packet[3] != len(packet[4:]):
            self.__print_and_quit('Bad property length for CONNACK.')

        identifiers = {
            17: 0,
            33: 0,
            36: 0,
            37: 0,
            39: 0,
            18: 0,
            34: 0,
            31: 0,
            38: 0,
            40: 0,
            41: 0,
            42: 0,
            19: 0,
            26: 0,
            28: 0,
            21: 0,
            22: 0
        }

        i = 0
        while i < packet[3]:
            if identifiers[packet[4 + i]] == 1:
                print('An identifier appears multiple times.')
                self.disconnect(0x82)
            identifiers[packet[4 + i]] += 1
            match packet[4 + i]:
                case 17:
                    self.session_expiry_interval_connect = int.from_bytes(packet[5 + i: 9 + i], byteorder='big')
                    print('Session expiry interval changed to ', self.session_expiry_interval_connect)
                    i += 5
                case 33:
                    self.recieve_maximum = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    if self.recieve_maximum == 0:
                        print('Recieve maximum cannot be zero.')
                        self.disconnect(0x82)
                    print('Recieve maximum changed to ', self.recieve_maximum)
                    i += 3
                case 36:
                    self.qosSupported = packet[5 + i]
                    if self.qosSupported != 0 and self.qosSupported != 1:
                        print('QoS cannot be adifferent value other than 0 or 1.')
                        self.disconnect(0x82)
                    if self.qosSupported != self.qos:
                        self.qos = self.qosSupported
                        print('Maximum QoS changed to ', self.qosSupported)
                    i += 2
                case 37:
                    self.retain = packet[5 + i]
                    if self.retain != 0 and self.retain != 1:
                        print('Retain cannot be adifferent value other than 0 or 1.')
                        self.disconnect(0x82)
                    print('Retain changed to ', self.retain)
                    i += 2
                case 39:
                    self.maximum_packet_size_connect = int.from_bytes(packet[5 + i: 9 + i], byteorder='big')
                    if self.maximum_packet_size_connect == 0:
                        print('Maximum packet size cannot be zero.')
                        self.disconnect(0x82)
                    print('Maximum packet changed to ', self.maximum_packet_size_connect)
                    i += 5
                case 18:
                    client_id_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    if self.client_id == '' and client_id_length == 0:
                        self.__print_and_quit('Client ID is not given and yet the server doesn\'t give one.')
                    if self.client_id != '' and client_id_length != 0:
                        self.__print_and_quit('Client ID is given and yet the server gives one too.')

                    self.client_id = packet[7 + i: 7 + client_id_length + i]
                    print('Client ID changed to ', self.client_id.decode('utf-8'))
                    i += 3 + client_id_length
                case 34:
                    self.topic_alias_maximum_connect = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    if self.topic_alias_publish > self.topic_alias_maximum_connect:
                        self.__print_and_quit(f'Topic alias is too big, the maximim is {self.topic_alias_maximum_connect}.')
                    i += 3
                case 31:
                    reason_string_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print(f'Reason string is {packet[7 + i: 7 + i + reason_string_length]}.')
                    i += 3 + reason_string_length
                case 38:
                    # It will be ignored
                    user_property_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    i += 3 + user_property_length
                case 40:
                    wildcard_subscription_available = packet[5 + i]
                    if wildcard_subscription_available != 0 and wildcard_subscription_available != 1:
                        print('Wildcard subscription available cannot have a value other than 0 or 1.')
                        self.disconnect(0x82)
                    i += 2
                case 41:
                    subscription_identifiers_available = packet[5 + i]
                    if subscription_identifiers_available != 0 and subscription_identifiers_available != 1:
                        print('Subscription identifiers available cannot have a value other than 0 or 1.')
                        self.disconnect(0x82)
                    i += 2
                case 42:
                    shared_subscription_available = packet[5 + i]
                    if shared_subscription_available != 0 and shared_subscription_available != 1:
                        print('Shared subscription available cannot have a value other than 0 or 1.')
                        self.disconnect(0x82)
                    i += 2
                case 19:
                    self.keep_alive = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print('Keep alive set to ', self.keep_alive)
                    i += 3
                case 26:
                    # Not defined for this specification, so it will only be printed
                    response_information_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print(f'Response information is {packet[7 + i: 7 + i + response_information_length]}.')
                    i += 3 + response_information_length
                case 28:
                    # Not defined for this specification, so it will only be printed
                    server_reference_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print(f'Server reference is {packet[7 + i: 7 + i + server_reference_length]}.')
                    i += 3 + server_reference_length
                case 21:
                    authentification_method_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print(f'Authentication method is {packet[7 + i: 7 + i + authentification_method_length]}.')
                    i += 3 + authentification_method_length
                case 22:
                    authentification_data_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print(f'Authentication data is {packet[7 + i: 7 + i + authentification_data_length]}.')
                    i += 3 + authentification_data_length
                case _:
                    print('Unknown property.')
                    self.disconnect(0x82)

        if identifiers[34] == 0 or self.topic_alias_maximum_connect == 0:
            self.topic_alias_publish = ''

    def __handle_PUBACK_and_PUBREC(self, packet):
        if packet[1] != len(packet[2:]):
            self.__print_and_quit(f'Bad remaining length for {"PUBACK" if packet[0] == 0x40 else "PUBREC"}.')

        if packet[1] == 2:
            return

        match packet[4]:
            case 0x00:
                pass
            case 0x10:
                print('No matching subscribers.')
            case 0x80:
                self.__print_and_quit('Unspecified error.')
            case 0x83:
                self.__print_and_quit('Implementation specific error.')
            case 0x87:
                self.__print_and_quit('Not authorized.')
            case 0x90:
                self.__print_and_quit('Topic name invalid.')
            case 0x91:
                self.__print_and_quit('Packet identifier in use.')
            case 0x97:
                self.__print_and_quit('Quota exceeded.')
            case 0x99:
                self.__print_and_quit('Payload format invalid.')

        try:
            if packet[5] != len(packet[6:]):
                self.__print_and_quit(f'Bad property length for {"PUBACK" if packet[0] == 0x40 else "PUBREC"}.')

            identifiers = {
                31: 0,
                38: 0,
            }

            i = 0
            while i < packet[5]:
                if identifiers[packet[6 + i]] == 1:
                    print('An identifier appears multiple times.')
                    self.disconnect(0x82)
                identifiers[packet[6 + i]] += 1
                match packet[6 + i]:
                    case 31:
                        reason_string_length = int.from_bytes(packet[7 + i: 9 + i], byteorder='big')
                        print(f'Reason string is {packet[9 + i: 9 + i + reason_string_length]}.')
                        i += 3 + reason_string_length
                    case 38:
                        # It will be ignored
                        user_property_length = int.from_bytes(packet[7 + i: 9 + i], byteorder='big')
                        i += 3 + user_property_length
        except IndexError:
            pass

    def __handle_PUBREL(self, packet):
        if packet[0] != len(packet[1:]):
            self.__print_and_quit(f'Bad remaining length for PUBREL.')

        if packet[0] == 2:
            return

        match packet[3]:
            case 0x00:
                pass
            case 0x92:
                self.__print_and_quit('Packet identifier not found.')
        try:
            if packet[4] != len(packet[5:]):
                self.__print_and_quit(f'Bad property length for PUBREL.')

            identifiers = {
                31: 0,
                38: 0,
            }

            i = 0
            while i < packet[4]:
                if identifiers[packet[5 + i]] == 1:
                    print('An identifier appears multiple times.')
                    self.disconnect(0x82)
                identifiers[packet[5 + i]] += 1
                match packet[5 + i]:
                    case 31:
                        reason_string_length = int.from_bytes(packet[6 + i: 8 + i], byteorder='big')
                        print(f'Reason string is {packet[8 + i: 8 + i + reason_string_length]}.')
                        i += 3 + reason_string_length
                    case 38:
                        # It will be ignored
                        user_property_length = int.from_bytes(packet[6 + i: 8 + i], byteorder='big')
                        i += 3 + user_property_length
        except IndexError:
            pass

    def __handle_PUBCOMP(self, packet):
        if packet[0] != len(packet[1:]):
            self.__print_and_quit(f'Bad remaining length for PUBCOMP.')

        if packet[0] == 2:
            return

        match packet[3]:
            case 0x00:
                pass
            case 0x92:
                self.__print_and_quit('Packet identifier not found.')

        try:
            if packet[4] != len(packet[5:]):
                self.__print_and_quit(f'Bad property length for PUBCOMP.')

            identifiers = {
                31: 0,
                38: 0,
            }

            i = 0
            while i < packet[4]:
                if identifiers[packet[5 + i]] == 1:
                    print('An identifier appears multiple times.')
                    self.disconnect(0x82)
                identifiers[packet[5 + i]] += 1
                match packet[5 + i]:
                    case 31:
                        reason_string_length = int.from_bytes(packet[6 + i: 8 + i], byteorder='big')
                        print(f'Reason string is {packet[8 + i: 8 + i + reason_string_length]}.')
                        i += 3 + reason_string_length
                    case 38:
                        # It will be ignored
                        user_property_length = int.from_bytes(packet[6 + i: 8 + i], byteorder='big')
                        i += 3 + user_property_length
        except IndexError:
            pass

    def __handle_SUBACK(self, packet):
        if packet[0] != len(packet[1:]):
            self.__print_and_quit(f'Bad remaining length for SUBACK.')

        if packet[3] != len(packet[4:-1]):
            self.__print_and_quit(f'Bad property length for SUBACK.')

        identifiers = {
            31: 0,
            38: 0,
        }

        i = 0
        while i < packet[3]:
            if identifiers[packet[4 + i]] == 1:
                print('An identifier appears multiple times.')
                self.disconnect(0x82)
            identifiers[packet[4 + i]] += 1
            match packet[4 + i]:
                case 31:
                    reason_string_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print(f'Reason string is {packet[7 + i: 7 + i + reason_string_length]}.')
                    i += 3 + reason_string_length
                case 38:
                    # It will be ignored
                    user_property_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    i += 3 + user_property_length

        match packet[-1]:
            case 0x00, 0x01, 0x02:
                pass
            case 0x80:
                self.__print_and_quit('Unspecified error.')
            case 0x83:
                self.__print_and_quit('Implementation specific error.')
            case 0x87:
                self.__print_and_quit('Not authorized.')
            case 0x8F:
                self.__print_and_quit('Topic filter invalid.')
            case 0x91:
                self.__print_and_quit('Packet identifier in use.')
            case 0x97:
                self.__print_and_quit('Quota exceeded.')
            case 0x9E:
                self.__print_and_quit('Shared subscriptions not supported.')
            case 0xA1:
                self.__print_and_quit('Subscription identifiers not supported.')
            case 0xA2:
                self.__print_and_quit('Wildcard subscriptions not supported.')

    def __handle_UNSUBACK(self, packet):
        if packet[0] != len(packet[1:]):
            self.__print_and_quit(f'Bad remaining length for UNSUBACK.')

        if packet[3] != len(packet[4:-1]):
            self.__print_and_quit(f'Bad property length for UNSUBACK.')

        identifiers = {
            31: 0,
            38: 0,
        }

        i = 0
        while i < packet[3]:
            if identifiers[packet[4 + i]] == 1:
                print('An identifier appears multiple times.')
                self.disconnect(0x82)
            identifiers[packet[4 + i]] += 1
            match packet[4 + i]:
                case 31:
                    reason_string_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    print(f'Reason string is {packet[7 + i: 7 + i + reason_string_length]}.')
                    i += 3 + reason_string_length
                case 38:
                    # It will be ignored
                    user_property_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                    i += 3 + user_property_length

        match packet[-1]:
            case 0x00:
                print(f'Unsubscribed from \'{self.subscribe_topic.decode("utf-8")}\'')
            case 0x11:
                self.__print_and_quit('No subscription existed.')
            case 0x80:
                self.__print_and_quit('Unspecified error.')
            case 0x83:
                self.__print_and_quit('Implementation specific error.')
            case 0x87:
                self.__print_and_quit('Not authorized.')
            case 0x8F:
                self.__print_and_quit('Topic filter invalid.')
            case 0x91:
                self.__print_and_quit('Packet identifier in use.')

    def __handle_DISCONNECT(self, packet):
        if packet[0] != len(packet[1:]):
            self.__print_and_quit(f'Bad remaining length for DISCONNECT.')

        try:
            if packet[3] != len(packet[4:]):
                self.__print_and_quit(f'Bad property length for DISCONNECT.')

            match packet[2]:
                case 0x00:
                    print('Disconnected from server.')
                case 0x80:
                    self.__print_and_quit('Unspecified error.')
                case 0x81:
                    self.__print_and_quit('Malformed packet.')
                case 0x82:
                    self.__print_and_quit('Protocol error.')
                case 0x83:
                    self.__print_and_quit('Implementation specific error.')
                case 0x87:
                    self.__print_and_quit('Not authorized.')
                case 0x89:
                    self.__print_and_quit('Server busy.')
                case 0x8B:
                    self.__print_and_quit('Server shutting down.')
                case 0x8D:
                    self.__print_and_quit('Keep alive timeout.')
                case 0x8E:
                    self.__print_and_quit('Session take over.')
                case 0x8F:
                    self.__print_and_quit('Topic filter invalid.')
                case 0x90:
                    self.__print_and_quit('Topic name invalid.')
                case 0x93:
                    self.__print_and_quit('Recieve maximum exceeded.')
                case 0x94:
                    self.__print_and_quit('Topic alias invalid.')
                case 0x95:
                    self.__print_and_quit('Packet too large.')
                case 0x96:
                    self.__print_and_quit('Message rate too high.')
                case 0x97:
                    self.__print_and_quit('Quota exceeded.')
                case 0x98:
                    self.__print_and_quit('Administrative action.')
                case 0x99:
                    self.__print_and_quit('Payload format invalid.')
                case 0x9A:
                    self.__print_and_quit('Retain not supported.')
                case 0x9B:
                    self.__print_and_quit('QoS not supported.')
                case 0x9C:
                    self.__print_and_quit('Use another server.')
                case 0x9D:
                    self.__print_and_quit('Server moved.')
                case 0x9E:
                    self.__print_and_quit('Shared subscriptions not supported.')
                case 0x9F:
                    self.__print_and_quit('Connection rate exceeded.')
                case 0xA0:
                    self.__print_and_quit('Maximum connect time.')
                case 0xA1:
                    self.__print_and_quit('Subscription identifiers not supported.')
                case 0xA2:
                    self.__print_and_quit('Wildcard subscriptions not supported.')

            identifiers = {
                17: 0,
                31: 0,
                38: 0,
                28: 0
            }

            i = 0
            while i < packet[3]:
                if identifiers[packet[4 + i]] == 1:
                    print('An identifier appears multiple times.')
                    self.disconnect(0x82)
                identifiers[packet[4 + i]] += 1
                match packet[4 + i]:
                    case 17:
                        session_expiry_interval = int.from_bytes(packet[5 + i: 9 + i], byteorder='big')
                        print(f'Session expiry interval is {session_expiry_interval}.')
                        i += 8
                    case 31:
                        reason_string_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                        print(f'Reason string is {packet[7 + i: 7 + i + reason_string_length]}.')
                        i += 3 + reason_string_length
                    case 38:
                        # It will be ignored
                        user_property_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                        i += 3 + user_property_length
                    case 28:
                        server_reference_length = int.from_bytes(packet[5 + i: 7 + i], byteorder='big')
                        print(f'Reason string is {packet[7 + i: 7 + i + server_reference_length]}.')
                        i += 3 + server_reference_length
        except IndexError:
            pass

    def __handle_PUBLISH(self, packet):
        topic_name_length = int.from_bytes(packet[2:4], byteorder='big')
        topic_name = packet[4:4 + topic_name_length].decode('utf-8')
        if self.qos != 0:
            if packet[0] in [0x32, 0x33, 0x3A, 0x3B]:
                self.handle_qos_1(packet)

            self.packet_identifier = int.from_bytes(packet[4 + topic_name_length:6 + topic_name_length],
                                                    byteorder='big')
            if packet[0] in [0x34, 0x35, 0x3C, 0x3D]:
                self.handle_qos_2_PUBREC(self.packet_identifier)

            property_length = packet[6 + topic_name_length]
            if int.from_bytes(packet[7 + topic_name_length + property_length: 9 + topic_name_length + property_length], byteorder='big') != \
                len(packet[9 + topic_name_length + property_length:]):
                index = 7
            else:
                index = 9

            payload = packet[index + topic_name_length + property_length:].decode('utf-8')
            print(topic_name, ':', payload)
        else:
            property_length = packet[4 + topic_name_length]
            payload = packet[8 + topic_name_length + property_length:].decode('utf-8')
            print(topic_name, ':', payload)

    def __handle_packet(self, packet):
        if packet[0] in [0x30, 0x31,
                         0x32, 0x33, 0x3A, 0x3B,
                         0x34, 0x35, 0x3C, 0x3D]:
            self.__handle_PUBLISH(packet)
        else:
            if packet:
                match packet[0]:
                    case 0x20:
                        self.__handle_CONNACK(packet[1:])
                    case 0x40:
                        self.__handle_PUBACK_and_PUBREC(packet)
                    case 0x50:
                        self.__handle_PUBACK_and_PUBREC(packet)
                        self.handle_qos2_send_PUBREL(packet)
                    case 0x62:
                        self.__handle_PUBREL(packet[1:])
                        self.handle_qos_2_PUBCOMP(packet)
                    case 0x70:
                        self.__handle_PUBCOMP(packet[1:])
                    case 0x90:
                        self.__handle_SUBACK(packet[1:])
                    case 0xB0:
                        self.__handle_UNSUBACK(packet[1:])
                    case 0xE0:
                        self.__handle_DISCONNECT(packet[1:])
                    case 0xD0:
                        pass
                    case _:
                        self.__print_and_quit('MQTT packet not recognized.')

    def __reset_keep_alive(self):
        self.next_ping_time = time.time() + self.keep_alive

    def __response_handler(self):
        response_messages = {
            b'\x20': 'CONNACK',
            b'\x40': 'PUBACK',
            b'\x50': 'PUBREC',
            b'\x62': 'PUBREL',
            b'\x30': 'PUBLISH',
            b'\x31': 'PUBLISH',
            b'\x32': 'PUBLISH',
            b'\x33': 'PUBLISH',
            b'\x34': 'PUBLISH',
            b'\x35': 'PUBLISH',
            b'\x38': 'PUBLISH',
            b'\x39': 'PUBLISH',
            b'\x3A': 'PUBLISH',
            b'\x3B': 'PUBLISH',
            b'\x3C': 'PUBLISH',
            b'\x3D': 'PUBLISH',
            b'\x90': 'SUBACK',
            b'\xB0': 'UNSUBACK',
            b'\x70': 'PUBCOMP',
            b'\xD0': 'PINGRESP',
            b'\xE0': 'DISCONNECT'
        }

        while self.running:
            if time.time() >= self.next_ping_time:
                self.ping()
            try:
                if self.s.fileno() != -1:
                    r, _, _ = select.select([self.s], [], [], 2)
                    if r:
                        data = self.s.recv(8192)
                        if data:
                            self.recieved_data += data
                            while len(self.recieved_data) >= 2:
                                remaining_length = self.recieved_data[1]
                                total_packet_length = 2 + remaining_length

                                if len(self.recieved_data) < total_packet_length:
                                    break

                                packet = self.recieved_data[:total_packet_length]
                                self.recieved_data = self.recieved_data[total_packet_length:]

                                print(f'{response_messages.get(packet[:1])} response: {packet.hex()}')
                                self.__handle_packet(packet)
                                if packet[:1] != b'\xE0' or self.qos != 0:
                                    self.response_event.set()
                                else:
                                    if packet[:1] == b'\xE0':
                                        self.close_connection()
                                        os._exit(os.EX_OK)
            except socket.timeout:
                print('Socket timeout')
                os._exit(os.EX_OK)
            except KeyboardInterrupt:
                if self.s.fileno() != -1:
                    self.close_connection()
                self.running = False
                os._exit(os.EX_OK)
            except Exception as e:
                if self.running:
                    print(e)
                os._exit(os.EX_OK)
