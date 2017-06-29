import serial
#import thread
import math
import numpy
import re
import time
import datetime
from Pysolar import solar
#from posix import lstat
#from cgi import logfile
#import sys
#import select
#import os
#import msvcrt

startMarker = 60 # this is '<'
endMarker = 62 # and this is '>'
globalIrradiation = numpy.empty([32, 5, 9])
# Anzahl der Messbereiche
# Ele = 0 -> 32
# Ele = 9 -> 32...
allEle = [0, 9, 18, 27, 36, 45, 54,  63,  72, 81, 90]
allAMB = [32, 32, 30, 29, 26, 23, 19, 15, 10, 5, 2]


def recvFromArduino():
    global startMarker, endMarker
    
    ck = ""
    x = "z" # any value that is not an end- or startMarker
    byteCount = -1 # to allow for the fact that the last increment will be one too many
  
    # wait for the start character
    while  ord(x) != startMarker:
        x = ser.read()
  
    # save data until the end marker is found
    while ord(x) != endMarker:
        if ord(x) != startMarker:
            ck = ck + x
            byteCount += 1
        x = ser.read()
  
    print("RX: " + ck)
    return(ck)

def measureGlobalIrrad():
    global irradiationMatrix, allEle, allAMB
    global logfileGlobal
    
    # save date/time to file
    datetimeStr = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    print(datetimeStr)
    logfileGlobal.write(datetimeStr + "\n")
    
    
    # Find Zero
    ser.write("<f>")
    msg = ""
    while msg.find("F0") == -1:
        msg = recvFromArduino()
    
#     for i in range(9, 11):
    arrayLength = len(allAMB)
    for i in range(arrayLength):
        actEle = allEle[i]
        actAMB = allAMB[i]
        
        # No idea what I'm doing...
        r = math.cos(actEle*math.pi/180)
        # first = 11.25*math.pi/180 aka 0.2
        #stepcount_raw = r*2*math.pi/0.2
        stepcountRaw = 10*math.pi*r
        stepcount = math.ceil(stepcountRaw)
        stepwidth = (2*math.pi*r)/stepcount
        motorsteps = int(round((stepwidth * (180 / math.pi)) / ((1.8 / 8) * r)))
        
        ser.write("<m>")
        while msg.find("W4P") == -1:
            msg = recvFromArduino()
            
        strTmp = "<" + str(motorsteps) + "," + str(actEle) + "," + str(actAMB) + ">"
        ser.write(strTmp)
        
        msg = ""
        i=0
        while msg.find("MDone") == -1:
            msg = recvFromArduino()
            if msg.find("MDone") == -1:
                parts = re.split('\s|(?<!\d)[,.](?!\d)', msg)
            
                aziArd = float(parts[0])
                eleArd = float(parts[1])
                rVal = float(parts[2])
                gVal = float(parts[3])
                bVal = float(parts[4])
                xpin = float(parts[5])
                
                logfileGlobal.write(str(aziArd) + "," + str(eleArd) + "," + str(rVal) + "," + str(gVal) + "," + str(bVal) + "," + str(xpin)  + "\n")
                
                print("The position of the arduino is: Azimuth = " + str(aziArd) + ", Altitude = " + str(eleArd))
                print("The irradiaton values are: RED = " + str(rVal) + ", GREEN = " + str(gVal) + ", BLUE = " + str(bVal))
                print("---------------------------------")
        time.sleep(1)
    ser.write("<e>")

def measureDirectIrrad():
    global logfileDirect
    
    latitudePB = 51.7
    longitudePB = 8.7
    elevationPB = 170;
    date = datetime.datetime.utcnow()
    #date = datetime.datetime(2017, 5, 31, 7, 0, 0, 0)
    
    sunAlt = solar.GetAltitude(latitudePB, longitudePB, date, elevation = elevationPB)    
    sunAzi = solar.GetAzimuth(latitudePB, longitudePB, date, elevation = elevationPB)
    sunAziCor = (-sunAzi+180)%360
    
    strAlt = "{:.2f}".format(sunAlt)
    strAzi = "{:.2f}".format(sunAziCor)
    print("Sun is at " + strAlt + " degree altitude and " + strAzi + " degree azimuth")
    
    ser.write("<f>")
    msg = ""
    while msg.find("F0") == -1:
        msg = recvFromArduino()
    
    ser.write("<d>")
    msg = ""
    while msg.find("W4P") == -1:
        msg = recvFromArduino()
        
    steps = int(sunAziCor/0.225)
          
    ser.write("<" + str(steps) + "," + str(sunAlt) + ">")
    
    msg = ""
    while msg.find("MDone") == -1:
            msg = recvFromArduino()
            if msg.find("MDone") == -1:
                parts = re.split('\s|(?<!\d)[,.](?!\d)', msg)
                aziArd = float(parts[0])
                eleArd = float(parts[1])
                rVal = float(parts[2])
                gVal = float(parts[3])
                bVal = float(parts[4])
                xpin = float(parts[5])
                
                datetimeStr = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                logfileDirect.write(datetimeStr + ",")
                logfileDirect.write(str(aziArd) + "," + str(eleArd) + "," + str(rVal) + "," + str(gVal) + "," + str(bVal) + "," + str(xpin))
                logfileDirect.write("\n")
                
                print("The position of the arduino is: Altitude = " + str(eleArd) + ", Azimuth = " + str(aziArd))
                print("The irradiaton values are: RED = " + str(rVal) + ", GREEN = " + str(gVal) + ", BLUE = " + str(bVal))
                print("---------------------------------")

def trackSunPosition():
    global logfileDirect
    ser.write("<t>")
    latitudePB = 51.7
    longitudePB = 8.7
    elevationPB = 170;
    try:
        while True:
            date = datetime.datetime.utcnow()
            sunAlt = solar.GetAltitude(latitudePB, longitudePB, date, elevation = elevationPB)    
            sunAzi = solar.GetAzimuth(latitudePB, longitudePB, date, elevation = elevationPB)
            sunAziCor = (-sunAzi+180)%360
            
            strAlt = "{:.2f}".format(sunAlt)
            strAzi = "{:.2f}".format(sunAziCor)
            steps = int(sunAziCor/0.225)
            print("Sun is at " + strAlt + " degree altitude and " + strAzi + " degree azimuth")
            
            msg = ""
            while msg.find("W4P") == -1:
                msg = recvFromArduino()
                
            ser.write("<" + str(steps) + "," + str(sunAlt) + ">")
            
            msg = ""
            while msg.find("MDone") == -1:
                    msg = recvFromArduino()
                    if msg.find("MDone") == -1:
                        parts = re.split('\s|(?<!\d)[,.](?!\d)', msg)
                        aziArd = float(parts[0])
                        eleArd = float(parts[1])
                        rVal = float(parts[2])
                        gVal = float(parts[3])
                        bVal = float(parts[4])
                        xpin = float(parts[5])
                        
                        datetimeStr = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                        logfileDirect.write(datetimeStr + ",")
                        logfileDirect.write(str(aziArd) + "," + str(eleArd) + "," + str(rVal) + "," + str(gVal) + "," + str(bVal) + "," + str(xpin))
                        logfileDirect.write("\n")
                        
                        print("The position of the arduino is: Altitude = " + str(eleArd) + ", Azimuth = " + str(aziArd))
                        print("The irradiaton values are: RED = " + str(rVal) + ", GREEN = " + str(gVal) + ", BLUE = " + str(bVal))
                        print("---------------------------------")
            time.sleep(10) 
    except KeyboardInterrupt:
        ser.write("<e>")
    

def main():
    global ser
    global logfileDirect, logfileGlobal
    
    port = "/dev/ttyACM3"
    baudRate = 9600
    ser = serial.Serial(port, baudRate,timeout=None)
    logfileDirect = open("logfileDirect.csv","a")
    logfileGlobal = open("logfileGlobal.txt","a")
    
    if (ser.isOpen() == 1):
        
        msg = ""
        while msg.find("ArduinoReady") == -1:
            msg = recvFromArduino()


        exitBool = False
        print("Serial Port is open - Please select:")
        print("1 - Global Irradiation Measurement")
        print("2 - Direct Irradiation Measurement")
        print("3 - Sun Tracking")
        print("4 - Irradiation Measurement (Loop) - not implemented!")
        print("E - Exit")
        
        selection = raw_input(">> ")
        
        while not(exitBool):
            if selection in ['E', 'e', 'exit']:
                exitBool = True
            elif int(selection) == 1:
                measureGlobalIrrad()
                print("Global Irradiation Measurement finished - Please select next step")
                selection = raw_input(">> ")
            elif int(selection) == 2:
                measureDirectIrrad()
                print("Direct Irradiation Measurement finished - Please select next step")
                selection = raw_input(">> ")
            elif int(selection) == 3:
                trackSunPosition()
                print("Measurement finished - Please select next step")
                selection = raw_input(">> ")
            else:
                print("Error - Command not recognized - Please re-enter")
                selection = raw_input(">> ")
        ser.close()
        logfileDirect.close()
        logfileGlobal.close()            
    else:
        print("Error - Can't open Port")
    
    
    

if __name__=="__main__":
    main();
