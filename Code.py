from machine import Pin, ADC, I2C
import dht
import ssd1306
import time
from umqtt.simple import MQTTClient
import network

# --- Cấu hình Wi-Fi và MQTT ---
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""
MQTT_BROKER = "test.mosquitto.org"
MQTT_PORT = 1883
MQTT_CLIENT_ID = ""
MQTT_USER = None
MQTT_PASSWORD = None
TOPIC_PUB_SENSOR = b"sensor12345/data"
TOPIC_SUB_CONTROL = b"control12345/relay"
mqtt_client = None

# --- Cấu hình phần cứng ---
# OLED
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
I2C_SDA_PIN = 21
I2C_SCL_PIN = 22
i2c = I2C(0, sda=Pin(I2C_SDA_PIN), scl=Pin(I2C_SCL_PIN))
display = ssd1306.SSD1306_I2C(SCREEN_WIDTH, SCREEN_HEIGHT, i2c, addr=0x3C)

# Cảm biến
DHT_PIN = 15
dht_sensor = dht.DHT22(Pin(DHT_PIN))

PHOTORESISTOR_PIN = 33
photoresistor = ADC(Pin(PHOTORESISTOR_PIN))
photoresistor.atten(ADC.ATTN_11DB)

TRIG_PIN = 5
ECHO_PIN = 18
trig = Pin(TRIG_PIN, Pin.OUT)
echo = Pin(ECHO_PIN, Pin.IN)

# Thiết bị điều khiển
PUMP_PIN = 16
LED_MODE_PIN = 12
pump = Pin(PUMP_PIN, Pin.OUT, value=0)
led_mode = Pin(LED_MODE_PIN, Pin.OUT, value=0)

# Nút bấm
BUTTON_TEMP_PIN = 26
BUTTON_HUMID_PIN = 27
BUTTON_LIGHT_PIN = 14
BUTTON_PUMP_PIN = 25
BUTTON_MODE_PIN = 32
button_temp = Pin(BUTTON_TEMP_PIN, Pin.IN, Pin.PULL_UP)
button_humid = Pin(BUTTON_HUMID_PIN, Pin.IN, Pin.PULL_UP)
button_light = Pin(BUTTON_LIGHT_PIN, Pin.IN, Pin.PULL_UP)
button_pump = Pin(BUTTON_PUMP_PIN, Pin.IN, Pin.PULL_UP)
button_mode = Pin(BUTTON_MODE_PIN, Pin.IN, Pin.PULL_UP)

# Relay
RELAY_TEMP_PIN = 23
RELAY_HUMID_PIN = 19
RELAY_LIGHT_PIN = 17
relay_temp = Pin(RELAY_TEMP_PIN, Pin.OUT, value=0)
relay_humid = Pin(RELAY_HUMID_PIN, Pin.OUT, value=0)
relay_light = Pin(RELAY_LIGHT_PIN, Pin.OUT, value=0)

# --- Biến trạng thái và ngưỡng ---
NGUONG_ANH_SANG = 1000
NGUONG_NUOC = 50
CHIEU_CAO_BE = 100

temp_state = False
humid_state = False
light_state = False
pump_state = False
mode_state = False  # False: Thủ công, True: Tự động

last_debounce_time_temp = 0
last_debounce_time_humid = 0
last_debounce_time_light = 0
last_debounce_time_pump = 0
last_debounce_time_mode = 0
DEBOUNCE_DELAY = 0.2  # 200ms

previous_millis_oled = 0
INTERVAL_OLED = 2.0  # 2 giây

# Biến lưu giá trị trước đó
last_temp = None
last_humid = None
last_lux = None
last_muc_nuoc = None
last_mode_state = None
last_relay_temp = None
last_relay_humid = None
last_relay_light = None
last_pump = None

# --- Hàm kết nối Wi-Fi ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    max_attempts = 10
    attempt = 0
    
    while not wlan.isconnected() and attempt < max_attempts:
        print(f"Attempting to connect to Wi-Fi ({attempt + 1}/{max_attempts})...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(10):  # Chờ 10 giây
            if wlan.isconnected():
                break
            time.sleep(1)
        attempt += 1
    
    if wlan.isconnected():
        print("Wi-Fi connected. IP:", wlan.ifconfig()[0])
        return True
    else:
        print("Failed to connect to Wi-Fi")
        return False

# --- Hàm kết nối MQTT ---
def connect_mqtt():
    global mqtt_client
    try:
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASSWORD)
        mqtt_client.set_callback(mqtt_callback)
        mqtt_client.connect()
        mqtt_client.subscribe(TOPIC_SUB_CONTROL)
        print("Connected to MQTT Broker")
        return True
    except Exception as e:
        print(f"Failed to connect to MQTT: {e}")
        mqtt_client = None
        return False

# --- Hàm reconnect MQTT ---
def reconnect_mqtt():
    global mqtt_client
    wlan = network.WLAN(network.STA_IF)
    
    if not wlan.isconnected():
        print("Wi-Fi disconnected, attempting to reconnect...")
        if not connect_wifi():
            return False
    
    if mqtt_client is None or not wlan.isconnected():
        print("MQTT disconnected, attempting to reconnect...")
        return connect_mqtt()
    
    return True

# --- Hàm callback MQTT ---
def mqtt_callback(topic, msg):
    global mode_state
    print(f"Received message on topic {topic}: {msg}")
    try:
        if topic == TOPIC_SUB_CONTROL:
            message = msg.decode()
            if not mode_state:  # Chỉ điều khiển thủ công
                if message == "TEMP_ON":
                    control_relay_local("temp", True)
                elif message == "TEMP_OFF":
                    control_relay_local("temp", False)
                elif message == "HUMID_ON":
                    control_relay_local("humid", True)
                elif message == "HUMID_OFF":
                    control_relay_local("humid", False)
                elif message == "LIGH_ON":
                    control_relay_local("light", True)
                elif message == "LIGH_OFF":
                    control_relay_local("light", False)
                elif message == "PUMP_ON":
                    control_relay_local("pump", True)
                elif message == "PUMP_OFF":
                    control_relay_local("pump", False)
            if message == "MODE_AUTO":
                mode_state = True
                led_mode.value(1)
            elif message == "MODE_THUCONG":
                mode_state = False
                led_mode.value(0)
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# --- Hàm điều khiển relay/pump ---
def control_relay_local(control, state):
    global temp_state, humid_state, light_state, pump_state
    if control == "temp":
        temp_state = state
        relay_temp.value(state)
    elif control == "humid":
        humid_state = state
        relay_humid.value(state)
    elif control == "light":
        light_state = state
        relay_light.value(state)
    elif control == "pump":
        pump_state = state
        pump.value(state)

# --- Ngắt nút bấm ---
def button_temp_interrupt(pin):
    global last_debounce_time_temp, mode_state
    current_time = time.ticks_ms() / 1000
    if (current_time - last_debounce_time_temp) > DEBOUNCE_DELAY and not mode_state:
        control_relay_local("temp", not relay_temp.value())
        last_debounce_time_temp = current_time

def button_humid_interrupt(pin):
    global last_debounce_time_humid, mode_state
    current_time = time.ticks_ms() / 1000
    if (current_time - last_debounce_time_humid) > DEBOUNCE_DELAY and not mode_state:
        control_relay_local("humid", not relay_humid.value())
        last_debounce_time_humid = current_time

def button_light_interrupt(pin):
    global last_debounce_time_light, mode_state
    current_time = time.ticks_ms() / 1000
    if (current_time - last_debounce_time_light) > DEBOUNCE_DELAY and not mode_state:
        control_relay_local("light", not relay_light.value())
        last_debounce_time_light = current_time

def button_pump_interrupt(pin):
    global last_debounce_time_pump, mode_state
    current_time = time.ticks_ms() / 1000
    if (current_time - last_debounce_time_pump) > DEBOUNCE_DELAY and not mode_state:
        control_relay_local("pump", not pump.value())
        last_debounce_time_pump = current_time

def button_mode_interrupt(pin):
    global mode_state, last_debounce_time_mode
    current_time = time.ticks_ms() / 1000
    if (current_time - last_debounce_time_mode) > DEBOUNCE_DELAY:
        mode_state = not mode_state
        led_mode.value(mode_state)
        last_debounce_time_mode = current_time

# --- Khởi tạo ---
def setup():
    print("Setup started...")
    if not connect_wifi():
        print("Initial Wi-Fi connection failed, continuing without network...")
    else:
        connect_mqtt()

    display.fill(0)
    display.text("Smart Garden", 0, 0)
    display.show()

    button_temp.irq(trigger=Pin.IRQ_FALLING, handler=button_temp_interrupt)
    button_humid.irq(trigger=Pin.IRQ_FALLING, handler=button_humid_interrupt)
    button_light.irq(trigger=Pin.IRQ_FALLING, handler=button_light_interrupt)
    button_pump.irq(trigger=Pin.IRQ_FALLING, handler=button_pump_interrupt)
    button_mode.irq(trigger=Pin.IRQ_FALLING, handler=button_mode_interrupt)

    print("Setup complete.")

# --- Đọc nhiệt độ và độ ẩm ---
def read_temperature_and_control_led():
    global temp_state, humid_state, mode_state
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humid = dht_sensor.humidity()
        if temp is None or humid is None:
            print("Failed to read DHT sensor")
            return None, None
        print(f"Nhiet do: {temp:.2f} °C")
        print(f"Do am: {humid:.2f} %")

        if mode_state:
            relay_temp.value(1 if temp < 12 or temp > 35 else 0)
            relay_humid.value(1 if humid < 40 or humid > 70 else 0)
        return temp, humid
    except Exception as e:
        print(f"Error reading DHT sensor: {e}")
        return None, None

# --- Đọc ánh sáng ---
def read_light_and_control_led():
    global light_state, mode_state
    try:
        light_intensity = photoresistor.read()
        voltage = light_intensity / 4095.0 * 3.3
        resistance = 2000 * voltage / (1 - voltage / 3.3) if voltage < 3.3 else float('inf')
        lux = pow(33 * 1e3 * pow(10, 0.7) / resistance, (1 / 0.7)) if resistance > 0 else 0
        print(f"Cuong do anh sang: {lux:.2f} lux")

        if mode_state:
            relay_light.value(1 if lux < NGUONG_ANH_SANG else 0)
        return lux
    except Exception as e:
        print(f"Error reading light sensor: {e}")
        return None

# --- Đọc mực nước ---
def read_distance_and_control_pump():
    global pump_state, mode_state
    try:
        trig.value(0)
        time.sleep_us(2)
        trig.value(1)
        time.sleep_us(10)
        trig.value(0)

        timeout_us = 500000
        start_time = time.ticks_us()
        while echo.value() == 0:
            if time.ticks_diff(time.ticks_us(), start_time) > timeout_us:
                print("Echo pulse not received (start)")
                return None

        pulse_start = time.ticks_us()
        while echo.value() == 1:
            if time.ticks_diff(time.ticks_us(), pulse_start) > timeout_us:
                print("Echo pulse not received (end)")
                return None

        pulse_end = time.ticks_us()
        duration = time.ticks_diff(pulse_end, pulse_start)
        distance_cm = duration * 0.0343 / 2
        muc_nuoc = 0 if distance_cm > CHIEU_CAO_BE else CHIEU_CAO_BE - distance_cm
        print(f"Muc nuoc: {muc_nuoc:.2f} cm")

        if mode_state:
            pump.value(1 if distance_cm > NGUONG_NUOC else 0 if distance_cm < 20 else pump.value())
        return muc_nuoc
    except Exception as e:
        print(f"Error reading distance sensor: {e}")
        return None

# --- Hiển thị OLED ---
def display_data(temp, humid, lux, muc_nuoc):
    display.fill(0)
    display.text(f"Temp: {temp:.1f} C", 0, 0)
    display.text(f"Humid: {humid:.1f} %", 0, 10)
    display.text(f"Light: {lux:.0f} lux", 0, 20)
    display.text(f"Water: {muc_nuoc:.1f} cm", 0, 30)
    display.text(f"Mode: {'Auto' if mode_state else 'Manual'}", 0, 40)
    display.text(f"T:{'ON' if relay_temp.value() else 'OFF'} H:{'ON' if relay_humid.value() else 'OFF'} L:{'ON' if relay_light.value() else 'OFF'} P:{'ON' if pump.value() else 'OFF'}", 0, 50)
    display.show()

# --- Vòng lặp chính ---
def loop():
    global previous_millis_oled, mqtt_client, last_temp, last_humid, last_lux, last_muc_nuoc
    global last_mode_state, last_relay_temp, last_relay_humid, last_relay_light, last_pump

    while True:
        current_millis = time.ticks_ms() / 1000
        if current_millis - previous_millis_oled >= INTERVAL_OLED:
            previous_millis_oled = current_millis

            temp, humid = read_temperature_and_control_led()
            lux = read_light_and_control_led()
            muc_nuoc = read_distance_and_control_pump()

            if temp is None or humid is None or lux is None or muc_nuoc is None:
                time.sleep(0.1)  # Tránh lặp nhanh khi cảm biến lỗi
                continue

            # Trạng thái hiện tại
            current_mode_state = mode_state
            current_relay_temp = relay_temp.value()
            current_relay_humid = relay_humid.value()
            current_relay_light = relay_light.value()
            current_pump = pump.value()

            # Kiểm tra thay đổi với ngưỡng
            data_changed = (
                (last_temp is None or abs(last_temp - temp) >= 0.5) or
                (last_humid is None or abs(last_humid - humid) >= 2.0) or
                (last_lux is None or abs(last_lux - lux) >= 50.0) or
                (last_muc_nuoc is None or abs(last_muc_nuoc - muc_nuoc) >= 5.0) or
                (last_mode_state is None or last_mode_state != current_mode_state) or
                (last_relay_temp is None or last_relay_temp != current_relay_temp) or
                (last_relay_humid is None or last_relay_humid != current_relay_humid) or
                (last_relay_light is None or last_relay_light != current_relay_light) or
                (last_pump is None or last_pump != current_pump)
            )

            if data_changed:
                display_data(temp, humid, lux, muc_nuoc)
                if mqtt_client is not None and network.WLAN(network.STA_IF).isconnected():
                    try:
                        sensor_data = (
                            "Temperature: {:.1f} C, ".format(temp) +
                            "Humidity: {:.1f} %, ".format(humid) +
                            "Light: {:.0f} lux, ".format(lux) +
                            "Water: {:.1f} cm, ".format(muc_nuoc) +
                            "Mode: {}, ".format("Auto" if mode_state else "Manual") +
                            "Relay_T: {}, ".format("ON" if relay_temp.value() else "OFF") +
                            "Relay_H: {}, ".format("ON" if relay_humid.value() else "OFF") +
                            "Relay_L: {}, ".format("ON" if relay_light.value() else "OFF") +
                            "Pump: {}".format("ON" if pump.value() else "OFF")
                        )
                        mqtt_client.publish(TOPIC_PUB_SENSOR, sensor_data.encode())
                        print(f"Published to {TOPIC_PUB_SENSOR}: {sensor_data}")
                    except Exception as e:
                        print(f"Error publishing to MQTT: {e}")
                        reconnect_mqtt()

                # Cập nhật giá trị trước đó
                last_temp = temp
                last_humid = humid
                last_lux = lux
                last_muc_nuoc = muc_nuoc
                last_mode_state = current_mode_state
                last_relay_temp = current_relay_temp
                last_relay_humid = current_relay_humid
                last_relay_light = current_relay_light
                last_pump = current_pump

        if mqtt_client is not None:
            try:
                mqtt_client.check_msg()
            except Exception as e:
                print(f"Error checking MQTT messages: {e}")
                reconnect_mqtt()
        else:
            reconnect_mqtt()

        time.sleep(0.01)

# --- Chạy chương trình ---
if __name__ == "__main__":
    setup()
    loop()
