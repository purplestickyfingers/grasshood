from picozero import pico_led
from time import sleep, localtime
from machine import Pin, I2C, ADC
import os
import gc
import network
from math import sin
from umqtt.simple import MQTTClient
import secrets #to read Wifi and Adafruit details

pico_led.off()


# Get the local time as a tuple(collection of numbers that you can put together and index)
local_time = localtime()
print(f"Date: {local_time[0]}-{local_time[1]}-{local_time[2]}")
print(f"Time: {local_time[3]}:{local_time[4]:02}:{local_time[5]:02}")

#wifi details, store in secrets.py
wifi_ssid = secrets.wifi_ssid
wifi_password = secrets.wifi_password

#Connnect to WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(wifi_ssid, wifi_password)
if wlan.isconnected() == False:
    print ("Waiting for WiFi Network connection...")
    sleep(5)
if wlan.isconnected():
    print ("Connected to WiFi Network.")
    pico_led.on()
    sleep(0.5)
    pico_led.off()
    sleep(0.5)
    pico_led.on()
    print ("Logging to MQTT Server.")

else:
    print ("Not Connected to WiFi Network.")
    print ("Not Logging to MQTT Server.")

#Adafruit IO Authenticication Details and MQTT Topic Details
mqtt_host                 = "io.adafruit.com"
mqtt_username             = secrets.mqtt_username
mqtt_password             = secrets.mqtt_password
mqtt_publish_temp_h_topic = mqtt_username + "/feeds/temperature-test-h"
mqtt_publish_rh_h_topic   = mqtt_username + "/feeds/relative-humidity-test-h"
mqtt_publish_sm_h_topic   = mqtt_username + "/feeds/soil-moisture-test-h"
mqtt_publish_temp_o_topic = mqtt_username + "/feeds/open-open-o.temperature-test-o"
mqtt_publish_rh_o_topic   = mqtt_username + "/feeds/open-open-o.relative-humidity-test-o"
mqtt_publish_sm_o_topic   = mqtt_username + "/feeds/open-open-o.soil-moisture-test-o"
mqtt_client_id            = secrets.mqtt_client_id

mqtt_client = MQTTClient(
    client_id =mqtt_client_id,
    server    =mqtt_host,
    user      =mqtt_username,
    password  =mqtt_password)

log_file= "data.csv"

file=open(log_file,"a")

#Opening and creating new new file w? headdings
if file.read():
    print ("file already existis")
else:
    print ("file not found creating new file (w/ headings)")
    file.write("Date, Time, H Temperature, H Relative Humidity, H Soil Moisture, O Temperature, O Relative Humidity, O Soil Moisture\n")

#Debugging Line
file.write("Rebooted\n")
print ("Rebooted")

file.close()

i2c_interface  = 0
sdapin         = Pin(16)
sclpin         = Pin(17)
soil           = ADC(Pin(28))

i2c_interface2 = 1
sdapin2        = Pin(14)
sclpin2        = Pin(15)
soil2          = ADC(Pin(27))

i2c  = I2C(i2c_interface, scl=sclpin, sda=sdapin, freq=100000)

i2c2 = I2C(i2c_interface2, scl=sclpin2, sda=sdapin2, freq=100000)

devices  = i2c.scan()
print(f"i2c  {devices}")
devices2 = i2c2.scan()
print(f"i2c2 {devices}")
addrDecimal = 64

def calcTemp(binary):
    int_val = int.from_bytes(binary, "big")
    tempCalc = int_val / 65535 * 165 - 40 #65535 = 2**16 - 1
    return tempCalc


def calcRh(binary) :
    int_val = int.from_bytes(binary, "big")
    rhCalc = int_val / 65535 * 100
    return rhCalc

while True:
    # Test H [Temperature]
    i2c.writeto(addrDecimal, '\x00') #request temp reading
    sleep(0.3) # delay to alow tep reading
    tempBinary = i2c.readfrom(addrDecimal, 2)
    
    #Test O [Temperature]
    i2c2.writeto(addrDecimal, '\x00') #request temp reading
    sleep(0.3) # delay to alow tep reading
    tempBinary2 = i2c2.readfrom(addrDecimal, 2)
    
    #Test H [Relative Humidity]
    i2c.writeto(addrDecimal, '\x01') #request humidity reading
    sleep (0.3)
    rhBinary = i2c.readfrom(addrDecimal, 2) 
    rh       = calcRh(rhBinary)
    
    #Test O [Relative Humidity]
    i2c2.writeto(addrDecimal, '\x01') #request humidity reading
    sleep (0.3)
    rhBinary2 = i2c2.readfrom(addrDecimal, 2) 
    rh2       = calcRh(rhBinary2)
    
    #Test H [Soil Moisture]
    moisture   = soil.read_u16()
    
    #Test O [Soil Moisture]
    moisture2   = soil2.read_u16()
    
    #telemetry code for debugging uncoment the next four lines for use
    #print all data
    #displaying data rounded tho the nearest hundredth
    #print ( f"Test H: {calcTemp(tempBinary):.2f} °C, {rh:.2f} %, {moisture/  1000}") 
    #print ( f"Test O: {calcTemp(tempBinary2):.2f} °C, {rh2:.2f} %, {moisture2/  1000}") 
    local_time = localtime()
    
    pico_led.on()
    #thony plotter logging comment line below if using 'telemetry code for debugging'
    print ( f"{calcTemp(tempBinary):.2f} °Ch, {rh:.2f} %h, {moisture/  1000} sh, {calcTemp(tempBinary2):.2f} °Co, {rh2:.2f} %o, {moisture2/  1000} so") 

    #write to file
    file=open(log_file,"a")
    file.write( f"{local_time[0]}-{local_time[1]}-{local_time[2]},{local_time[3]}:{local_time[4]:02}:{local_time[5]:02},{calcTemp(tempBinary):.2f},{rh:.2f},{moisture/1000},{calcTemp(tempBinary2):.2f},{rh2:.2f},{moisture2/1000}\n")
    file.close()
    #print ("all data written to 'data' file")
    pico_led.off()
     
    if wlan.isconnected():
        try:
            pico_led.on()
            mqtt_client.connect()
            #log to MQTT Adafruit
            mqtt_client.publish(mqtt_publish_temp_h_topic, str(calcTemp(tempBinary)))
            #print ("logged temperature Test H")
            
            mqtt_client.publish(mqtt_publish_temp_o_topic, str(calcTemp(tempBinary2)))
            #print ("logged temperature Test O")
            
            mqtt_client.publish(mqtt_publish_rh_h_topic, str(rh))
            #print ("logged rh Test H")
             
            mqtt_client.publish(mqtt_publish_rh_o_topic, str(rh2))
            #print ("logged rh Test O")
            
            mqtt_client.publish(mqtt_publish_sm_h_topic, str(moisture))
            #print ("logged soil Moisture Test H")
            
            mqtt_client.publish(mqtt_publish_sm_o_topic, str(moisture2))
            #print ("logged soil Moisture Test O")
            sleep(5)
           
            #disconet from MQTT server
            mqtt_client.disconnect()
        except Exception as e:
            print(f"MQTT error: {e}")
            file=open(log_file,"a")
            file.write( f"MQTT error: {e}")
            file.close()
            
    for i in range(300):
        if wlan.isconnected():
            pico_led.on()
        else:
            pico_led.off()
            
        sleep(0.1)
        pico_led.on()
        sleep(0.1)
    gc.collect()    
    
    