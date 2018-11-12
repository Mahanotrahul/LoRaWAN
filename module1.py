import time
import inspect
import sys
import datetime
import RPi.GPIO as GPIO
from hx711 import HX711
import base64
import serial
import requests
import ast


try:
    GPIO.cleanup()
    GPIO.setwarnings(False)
finally:
    print("###.....System Ready to start.....###")


def cleanAndExit():
    print("Cleaning...")
    GPIO.cleanup()
    print("Bye!")
    sys.exit()



    

##    GLOBAL  VARIABLES
CONSUMER_ID = 2000000000009
RETAILER_ID = 2000000000000
devEUI = "9c65f9fffe218a69"
AppKey = "112233445566778899aabbccddeeff00"
current_class = "A"
Class = "A" 
host = "168.87.87.213:8080"
message_type = {"confirmed" : "conf",
                "unconfirmed" : "ucnf"}
print_delay = 0.5

# State Variables
use_weight = 0      ## Maximum weight allowed to use until next recharge
weight_used = 0     ## Weight used after Recharge and before 'weight_used' becomes equal to 'use_weight'
weight_at_recharge = 0      ## Weight of the Cylinder when Recharge is done and the corresponding amount of gas is starting to come in to use
gas_detect_state = 0        ## Gas detect state 0: No Gas detected  1: Gas detected
gas_detect_threshold = 400      ## Threshold value for gas detection. Used in case for analog values
valve_state = 0                 ## gas-Flow Control valve state. 0: Shuf-OFF state, 1: Shut-ON State
retry_idx = 4                   ## Retry x-times to send data or to process something else

##   Pin Definitations
relay_pin = 19
gas_pin= 26
above_led = 2
below_led = 3
DT = 22
SCK = 27


# Initialize HX711
hx = HX711(DT, SCK)

#hx.set_reading_format("LSB", "MSB")
# hx711 configuration
zero_reading=(int)(abs(hx.read_average(5)))
def read_weight():      # function to read weight
     val = (int)(0.0419354839*(abs(hx.read_average(3)-zero_reading)/3))
     
     return val*3 ## returns current weight

weight_at_recharge = read_weight()

 

def lineno():
    ##   Returns the current line number of the line calling this function....###
    return inspect.currentframe().f_back.f_lineno


###  Setting up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_pin, GPIO.OUT)   # Set our input pin "relay_pin" to be an input
GPIO.setup(gas_pin, GPIO.IN)      # Set our input pin "gas_pin" to be an input
GPIO.setup(above_led, GPIO.OUT)      # Set our input pin "gas_pin" to be an input
GPIO.setup(below_led, GPIO.OUT)      # Set our input pin "gas_pin" to be an input


#  GPIO.LOW means switch on the valve
#  GPIO.HIGH means switch off the valve
GPIO.output(relay_pin,GPIO.LOW)
time.sleep(2)
GPIO.output(relay_pin,GPIO.HIGH)
time.sleep(2)



## Setting up Serial Communication with LoRa Module
ser = serial.Serial('/dev/ttyUSB0',baudrate = 115200,
                    parity = serial.PARITY_NONE,
                    stopbits = serial.STOPBITS_ONE,
                    bytesize = serial.EIGHTBITS)
print(ser.name)


# Variables for LoRa Node
should_try_joining = 1
join_status = 0

def get_current_class():
    global current_class
    try:
        ser.write(b"mac get_class".encode("utf-8"))
        connect_send = time.time()
        while (int((time.time() - connect_send))%60) < 10:
            if(ser.inWaiting()>0):
                data = ser.readline()
                if(data.replace('\n', '') is not ""):
                    output = data.replace(">> ",'').replace('\n','').replace('\r', '')
                    print(output)
                    current_class = output
                    break
    except Exception as e:
        print(e)
        print("Error Occurred in getting Current Class")

def get_join_status():
    global join_status
    global should_try_joining
    try:
        ser.write(b"mac get_join_status".encode("utf-8"))
        connect_send = time.time()
        while (int((time.time() - connect_send))%60) < 2:
            #ser.write("mac get_join_status")
            if(ser.inWaiting()>0):
                data = ser.readline()
                if(data.replace('\n', '') is not ""):
                    output = data.replace(">> ",'').replace('\n','').replace('\r', '')
                    print(output)
                    if(output == "unjoined"):
                        command_sent = 1
                        join_status = 0
                    elif(output == "joined"):
                        command_sent = 1
                        join_status = 1
                        return join_status
                        break
    except Exception as e:
        print(e)
        print("Error Occurred")

def join_network():
    global join_status
    try:
        if(join_status == 1):
            return
        else:
            ser.write(b"mac join otaa".encode("utf-8"))
            print("Join Command sent")
            connect_start = time.time()
            while (int((time.time() - connect_start))%60) < 10:
                #ser.write("mac get_join_status")
                if ser.inWaiting()>0:
                    data = ser.readline()
                    if(data.replace('\n', '') is not ""):
                        output = data.replace(">> ",'').replace('\n','').replace('\r', '')
                        print(output)
                        if(output == "busy"):
                            command_sent = 1
                            join_status = 0
                        elif(output == "Ok"):
                            command_sent = 1
                            join_status = 0
                        elif(output == "accepted"):
                            command_sent = 1
                            join_status = 1
                            print("Joining Complete")
                            break
                        elif(output == "unsuccess"):
                            command_sent = 1
                            join_status = 0
                            print("Joining InComplete")
                            break
    
        if(join_status == 0):
            print("Unable to Join the LoRa Network now.\n")
    except Exception as e:
        print(e)
        print("Error Occurred")

def send_data(data, msg_type = "ucnf", port_num = 15):
    global join_status
    try:
        if(join_status == 0):
            join_network()
        if(join_status == 1):
            command = "mac tx " + str(msg_type) + " " + str(port_num) + " " + data
            print("Command :" + str(command))
            ser.write(command.encode("utf-8"))
            print("Send-Data Command Sent")
            connect_start = time.time()
            while (int((time.time() - connect_start))%60) < 10:
                if ser.inWaiting()>0:
                    data = ser.readline()
                    if(data.replace('\n', '') is not ""):
                        output = data.replace(">> ",'').replace('\n','').replace('\r', '')
                        print(output)
                        if(output == "busy" or output == "not joined" or output == "Ok"):
                            command_sent = 1
                            send_status = 0
                        elif(output == "tx_ok"):
                            command_sent = 1
                            send_status = 1
                            print("Data Uploaded")
                            break
                        elif(output[0:7] == "mac rx "):
                            output = output.split(" ")
                            rx_port_num = output[2]
                            use_weight += ast.literal_eval(output[3].decode("hex"))["Recharge_Gas_Equivalent"]
                            new_weight_at_recharge = read_weight()
                            use_weight = use_weight - (weight_at_recharge - new_weight_at_recharge)
                            weight_at_recharge = new_weight_at_recharge
                            print("Recharge done. New Allowed Gas Usage after this Recharge is : " + str(use_weight))
    
        if(send_status == 0):
            print("Unable to Send the Data at this moment.\n")
    except Exception as e:
        print(e)
        print("Error Occurred")


try:
    get_join_status()
    join_network()
    get_current_class()
                    
except KeyboardInterrupt:
    print("KeyboardInterrupt Detected. Exiting Program")
except Exception as e:
    print(e)
    print("Error Occurred")


# GAS SENSOR CONFIGURATION
def gas_detect(channel):
    global gas_detect_state
    if GPIO.input(gas_pin):
        gas_detect_state = 0
        
    else:
        print("##...ALERT!!...##\n##....GAS DETECTED\n....##")
        gas_detect_state = 1
        #######..........SHUT OFF VALVE...........######
        GPIO.output(relay_pin, GPIO.HIGH)

GPIO.add_event_detect(gas_pin, GPIO.BOTH, callback=gas_detect, bouncetime=200)



def encode_command(iter,current_weight):

        print("Iteration : " + str(iter))
        global use_weight
        global weight_at_recharge

        command = str(current_weight)
        print("Weight = " + str(command))
        send_data(command.encode("hex"))


        
        

    

for i in range(1000):

    #print("Gas_detect_state :" + str(gas_detect_state))
    #if GPIO.input(gas_pin):
    #    gas_detect_state = 0
    #else:
    #    gas_detect_state = 1
    #    GPIO.output(relay_pin, GPIO.HIGH)

        
    #print("Use Weight : " + str(use_weight) + " g")

    current_weight = read_weight()
    print(" Current weight : " + str(current_weight) + " gram")
    weight_used = weight_at_recharge - current_weight


    if(use_weight > 0 and current_class == "C"):
        command = "mac set_class A"
        print("Command : " + str(command))
        ser.write(command.encode("utf-8"))
        print("Class Change Command Sent")
        connect_start = time.time()
        while (int((time.time() - connect_start))%60) < 2:
            if ser.inWaiting()>0:
                data = ser.readline()
                if(data.replace('\n', '') is not ""):
                        output = data.replace(">> ",'').replace('\n','').replace('\r', '')
                        print(output)
                        if(output == "Ok"):
                            current_class = "A"
                            print("Class Changed to 'A'")
                            break

    #if gas_detect_state == 0:
    if use_weight > 0 and weight_used < use_weight:
        #######..........SHUT ON VALVE...........######
        GPIO.output(relay_pin, GPIO.LOW)
        print(str(weight_used) + "relay should be on")
        valve_state = 1
    elif use_weight > 0 and weight_used >= use_weight:
        use_weight = 0
        #######..........SHUT OFF VALVE...........######
        GPIO.output(relay_pin, GPIO.HIGH)
        valve_state = 0
    elif use_weight == 0 :
        #######..........SHUT OFF VALVE...........######
        GPIO.output(relay_pin, GPIO.HIGH)
        valve_state = 0

        
    else:
        ###  Switch off Valve"
        GPIO.output(relay_pin, GPIO.HIGH)

    if(current_class == "C"):
        connect_start = time.time()
        while (int((time.time() - connect_start))%60) < 10:
            if ser.inWaiting()>0:
                data = ser.readline()
                if(data.replace('\n', '') is not ""):
                    output = data.replace(">> ",'').replace('\n','').replace('\r', '')
                    print(output)
                    if(output[0:7] == "mac rx "):
                            output = output.split(" ")
                            rx_port_num = output[2]
                            use_weight += ast.literal_eval(output[3].decode("hex"))["Recharge_Gas_Equivalent"]
                            new_weight_at_recharge = read_weight()
                            use_weight = use_weight - (weight_at_recharge - new_weight_at_recharge)
                            weight_at_recharge = new_weight_at_recharge
                            print("Recharge done. New Allowed Gas Usage after this Recharge is : " + str(use_weight))

    encode_command(i, current_weight)

    time.sleep(10)



    #print("\nGas_detect_state :" + str(gas_detect_state))
    #print("Valve State :" + str(valve_state))
    #if gas_detect_state == 1 or valve_state == 0:
    #    #######..........SHUT OFF VALVE...........######
    #   GPIO.output(relay_pin,GPIO.HIGH)
    #else:
    #    #######..........SHUT ON VALVE...........######
    #    GPIO.output(relay_pin,GPIO.LOW)

GPIO.cleanup()
sys.exit()

