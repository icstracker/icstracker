#                  - OpenPLC Python SubModule (PSM) -
# 
# PSM is the bridge connecting OpenPLC core to Python programs. PSM allows
# you to directly interface OpenPLC IO using Python and even write drivers 
# for expansion boards using just regular Python.
#
# PSM API is quite simple and just has a few functions. When writing your
# own programs, avoid touching on the "__main__" function as this regulates
# how PSM works on the PLC cycle. You can write your own hardware initialization
# code on hardware_init(), and your IO handling code on update_inputs() and
# update_outputs()
#
# To manipulate IOs, just use PSM calls psm.get_var([location name]) to read
# an OpenPLC location and psm.set_var([location name], [value]) to write to
# an OpenPLC location. For example:
#     psm.get_var("QX0.0")
# will read the value of %QX0.0. Also:
#     psm.set_var("IX0.0", True)
# will set %IX0.0 to true.
#
# Below you will find a simple example that uses PSM to switch OpenPLC's
# first digital input (%IX0.0) every second. Also, if the first digital
# output (%QX0.0) is true, PSM will display "QX0.0 is true" on OpenPLC's
# dashboard. Feel free to reuse this skeleton to write whatever you want.

#import all your libraries here
import psm
import time
import RPi.GPIO as GPIO
import board
import adafruit_tcs34725

from pymodbus.client.sync import ModbusTcpClient
# Create a client instance
print("Creating a client instance: ")
client = ModbusTcpClient('10.120.39.1', port=502)
print("Client instance created...")

#GPIO Mode
GPIO.setmode(GPIO.BCM)

GPIO_FlowSensor = 4         #GPIO pin 4 connected to flow sensor's (YF-S01) data
GPIO_PumpControl = 21       #GPIO pin 21 connected to pump's relay 
GPIO_RangeEcho = 24         #GPIO pin 24 connected to range's echo pin
GPIO_RangeTrigger = 23      #GPIO pin 23 connected to range's trigger pin
GPIO_Valve = 16             #GPIO pin 16 connected to valve's relay

def hardware_init():
    #Insert your hardware initialization code in here
    psm.start()
    global i2c
    i2c = board.I2C()  # uses board.SCL and board.SDA
    global rgbSensor
    rgbSensor = adafruit_tcs34725.TCS34725(i2c)
    global startTime
    startTime = 0.000
    global pulse 
    pulse = 0  # Freqeuncy of pulse from flow sensor
    global prev_distance # Previous distance from range sensor 
    prev_distance = None
    #set GPIO direction (IN / OUT)
    GPIO.setup(GPIO_FlowSensor, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(GPIO_PumpControl, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(GPIO_RangeEcho, GPIO.IN)
    GPIO.setup(GPIO_RangeTrigger, GPIO.OUT)
    GPIO.setup(GPIO_Valve, GPIO.OUT)
    GPIO.add_event_detect(GPIO_FlowSensor, GPIO.RISING, callback=handle_flow_interrupt)

#Handle when flow sensor detects rising edge
def handle_flow_interrupt(channel):
    global pulse
    pulse += 1

def update_flow():
    global pulse
    global startTime
    currentTime = time.time()
    elapsedTime = currentTime - startTime
    if elapsedTime >= 1:  # Check if one second has passed
        flowRate = (pulse / 7.5) * 60
        #print(f"Flow Rate: {flowRate} L/Hr")
        #print(f"Pulse: {pulse}")
        psm.set_var("IW4", int(flowRate))
        pulse = 0
        startTime = currentTime  # Reset the start time      

def get_distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_RangeTrigger,True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_RangeTrigger,False)

    # Initialize start and stop times
    StartTime = time.time()
    StopTime = time.time()

     #Define timeout duration (in seconds) 
     #Should try to stay within 20 ms cycle task time
    timeout = 0.005

    # save StartTime
    start_timeout = time.time()
    while GPIO.input(GPIO_RangeEcho) == 0:
        StartTime = time.time()
        if StartTime - start_timeout > timeout:
            return None

    # save time of arrival
    stop_time = time.time()
    while GPIO.input(GPIO_RangeEcho) == 1:
        StopTime = time.time()
        if StopTime - stop_time > timeout:
            return None

    # time difference between start and arrival
    TimeElapsed = StopTime - StartTime
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    return (TimeElapsed * 34300) / 2 # Return Distance

def get_treatmentCompleted():
    global treatmentCompleted
    global underFlowT2
    treatmentCompleted = 0
    underFlowT2 = 0
    
    try:
        # Connect to the PLC
        connection = client.connect()
        if connection:
        # Read the coil at address QX0.0 (address 0 in Modbus terms)
            result = client.read_coils(0, 2)
            #print(f"Result: {result}")
            if not result.isError():
            # Print the value of the coil
                treatmentCompleted = result.bits[0]
                underFlowT2 = result.bits[1]
                #print(f"treatmentCompleted: {treatmentCompleted}")
                #print(f"UnderFlowState of Tank2: {underFlowT2}")
            else:
                print(f"Error reading %QX0.0: {result}")
        else:
            print("Failed to connect to the PLC")
            # Sleep for a short duration before polling again
            time.sleep(.05) #50ms
           
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
     #Close the connection to the PLC
        client.close()
 
def update_inputs():
    #place here your code to update inputs
    global rgbSensor
    update_flow()
    distance = get_distance()
    rgbColor = rgbSensor.color_rgb_bytes
    get_treatmentCompleted()
    if distance is not None:
        global prev_distance 
        prev_distance = distance
        print ("Measured Distance = %.1f cm" % distance)
        psm.set_var("IW3", int(round(distance)))
    else:
        if prev_distance is not None:
            print (f"Measurment Failed, using last = {prev_distance}")
            psm.set_var("IW3", int(round(prev_distance)))
        else:
            print ("Measurement Failed, no previous value")
    psm.set_var("IW0", rgbColor[1])
    psm.set_var("IW1", rgbColor[2])
    psm.set_var("IW2", rgbColor[0])
    #psm.set_var("IW3", int(round(distance)))
    psm.set_var("IX0.0", treatmentCompleted)
    psm.set_var("IX0.1", underFlowT2)

def update_outputs():
    #place here your code to work on outputs
    GPIO.output(GPIO_PumpControl , GPIO.HIGH * psm.get_var("QX0.6"))
    GPIO.output(GPIO_Valve, GPIO.HIGH * psm.get_var("QX1.0"))


if __name__ == "__main__":
    hardware_init()
    while (not psm.should_quit()):
        update_inputs()
        update_outputs()
        time.sleep(0.1) #You can adjust the psm cycle time here
    psm.stop()
