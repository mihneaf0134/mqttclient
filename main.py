import os
from MQTTClient import MQTTClient
import signal
import psutil
import tkinter as tk
from tkinter import messagebox, ttk
import re
import time
from threading import Thread

class MQTTClientUI:
    def __init__(self, root):
        self.root = root
        self.root.title('MQTT Client Configuration')

        self.is_connected = False

        self.create_broker_config_frame()
        self.create_client_id_frame()
        self.create_last_will_frame()
        self.create_qos_frame()
        self.create_username_password_frame()
        self.create_pub_sub_frame()

    def create_broker_config_frame(self):
        frame = tk.LabelFrame(self.root, text='Broker Configuration')
        frame.pack(pady=10, padx=10)

        tk.Label(frame, text='Broker IP:').grid(row=0, column=0)
        self.broker_ip_entry = tk.Entry(frame)
        self.broker_ip_entry.grid(row=0, column=1)

        tk.Label(frame, text='Port: 1883 (fixed)').grid(row=1, column=0, columnspan=2)

        tk.Button(frame, text='Save', command=self.save_broker_config).grid(row=2, columnspan=2)

    def create_client_id_frame(self):
        frame = tk.LabelFrame(self.root, text='Client ID Configuration')
        frame.pack(pady=10, padx=10)

        tk.Label(frame, text='Client ID:').grid(row=0, column=0)
        self.client_id_entry = tk.Entry(frame)
        self.client_id_entry.grid(row=0, column=1)

        tk.Button(frame, text='Generate', command=self.generate_client_id).grid(row=0, column=2)

    def create_last_will_frame(self):
        frame = tk.LabelFrame(self.root, text='Last Will Configuration')
        frame.pack(pady=10, padx=10)

        tk.Label(frame, text='Message:').grid(row=1, column=0)
        self.will_message_entry = tk.Entry(frame)
        self.will_message_entry.grid(row=1, column=1)

    def create_qos_frame(self):
        frame = tk.LabelFrame(self.root, text='QoS Configuration')
        frame.pack(pady=10, padx=10)

        tk.Label(frame, text='QoS:').grid(row=0, column=0)
        self.qos_var = tk.StringVar(value='0')
        self.qos_dropdown = ttk.Combobox(frame, textvariable=self.qos_var, values=['0', '1', '2'])
        self.qos_dropdown.grid(row=0, column=1)

    def create_username_password_frame(self):
        frame = tk.LabelFrame(self.root, text='Username and Password')
        frame.pack(pady=10, padx=10)

        tk.Label(frame, text='Username:').grid(row=0, column=0)
        self.username_entry = tk.Entry(frame)
        self.username_entry.grid(row=0, column=1)

        tk.Label(frame, text='Password:').grid(row=1, column=0)
        self.password_entry = tk.Entry(frame, show='*')
        self.password_entry.grid(row=1, column=1)

    def create_pub_sub_frame(self):
        frame = tk.LabelFrame(self.root, text='Publish/Subscribe Options')
        frame.pack(pady=10, padx=10)

        self.pub_sub_var = tk.StringVar(value='publish')
        tk.Radiobutton(frame, text='Publish', variable=self.pub_sub_var, value='publish').grid(row=0, column=0)
        tk.Radiobutton(frame, text='Subscribe', variable=self.pub_sub_var, value='subscribe').grid(row=0, column=1)

        self.start_button = tk.Button(frame, text='Start', command=self.toggle_connection, state=tk.DISABLED)
        self.start_button.grid(row=1, column=0)

        self.stop_button = tk.Button(frame, text='Stop', command=self.stop_connection, state=tk.DISABLED)
        self.stop_button.grid(row=1, column=1)

    def validate_ip(self, ip):
        pattern = re.compile('^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$')
        return pattern.match(ip)

    def save_broker_config(self):
        ip = self.broker_ip_entry.get()
        if not self.validate_ip(ip):
            messagebox.showerror('Invalid IP', 'Please enter a valid IP address.')
            return
        self.start_button.config(state=tk.NORMAL)
        messagebox.showinfo('Success', 'Broker configuration saved.')

    def generate_client_id(self):
        generated_id = 'client_' + str(int(time.time()))
        self.client_id_entry.delete(0, tk.END)
        self.client_id_entry.insert(0, generated_id)
        messagebox.showinfo('Client ID', f'Generated Client ID: {generated_id}')

    def toggle_connection(self):
        ip = self.broker_ip_entry.get()
        if not self.validate_ip(ip):
            messagebox.showerror('Invalid IP', 'Please enter a valid IP address before starting.')
            return

        if self.is_connected:
            self.stop_connection()
            self.connectionThread.join()
        else:
            self.connectionThread = Thread(target=self.start_connection)
            self.connectionThread.start()

    def start_connection(self):
        self.is_connected = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        mode = self.pub_sub_var.get()
        messagebox.showinfo('Connection', f'Started {mode} mode.')

        self.mqttClient = MQTTClient(
            ip=self.broker_ip_entry.get(),
            port=1883,
            client_id=self.client_id_entry.get(),
            last_will=self.will_message_entry.get(),
            qos=int(self.qos_var.get()),
            will_qos=int(self.qos_var.get()),
            username=self.username_entry.get(),
            password=self.password_entry.get(),
            will_topic='computer/status',
            keep_alive=2
        )

        self.mqttClient.connect_to_broker()
        self.mqttClient.connect()

        if mode == 'publish':
            try:
                while self.is_connected:
                    self.mqttClient.set_publish_topic('computer/cpuUsage')
                    self.mqttClient.set_publish_message(str(psutil.cpu_percent()))
                    self.mqttClient.publish()
                    self.mqttClient.set_publish_topic('computer/cpuTemp')
                    cpu_temp = None
                    if hasattr(psutil, "sensors_temperatures"):
                        temp = psutil.sensors_temperatures()
                        if temp and 'coretemp' in temp:
                            cpu_temp = temp['coretemp'][0].current
                    self.mqttClient.set_publish_message(str(cpu_temp))
                    self.mqttClient.publish()
                    self.mqttClient.set_publish_topic('computer/ramUsage')
                    self.mqttClient.set_publish_message(str(psutil.virtual_memory().percent))
                    self.mqttClient.publish()
                    time.sleep(3)
            except KeyboardInterrupt:
                pass
        else:
            try:
                self.mqttClient.set_subscribe_topic('computer/+')
                self.mqttClient.subscribe()
                while self.is_connected:
                    continue
            except KeyboardInterrupt:
                pass

    def stop_connection(self):
        self.is_connected = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showinfo('Connection', 'Connection stopped.')

        if self.pub_sub_var.get() == 'publish':
            try:
                self.mqttClient.disconnect(0)
            except KeyboardInterrupt:
                pass
            finally:
                self.mqttClient.close_connection()
        else:
            try:
                self.mqttClient.unsubscribe()
                self.mqttClient.disconnect(0)
            except KeyboardInterrupt:
                pass
            finally:
                self.mqttClient.close_connection()

def signal_handler(signum, frame):
    root.quit()
    os._exit(os.EX_OK)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTSTP, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        root = tk.Tk()
        app = MQTTClientUI(root)
        root.mainloop()
    except KeyboardInterrupt:
        pass
