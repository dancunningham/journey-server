import os
import boto3
import urllib
from urllib import urlopen
import json
import datetime
import numpy as np
import pandas as pd
from time import sleep
import helpers as h

print('Loading function')
s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ['ACCESS_KEY'],
    aws_secret_access_key=os.environ['SECRET_KEY'],
)

def handler(event, context):

    print("Received event: " + json.dumps(event, indent=2))
    runlocal = False
    if ('input-file' in event):
        download_path = event['input-file'].encode('utf8')
        runlocal = True
    else:
        # Get the object from the event and show its content type
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))
        print("bucket: " + bucket)
        print("key: " + key)
        print("downloading object ...")
        try:
            download_path = '/tmp/{}'.format(key)
            s3.download_file(bucket, key, download_path)
            #print("CONTENT TYPE: " + response['ContentType'])
            #print("Content-Length: ", response['ContentLength'])
            #print("getting data ...")
        except Exception as e:
            print(e)
            print('Error getting object {} from bucket {}.'.format(key, bucket))
            print ('Make sure they exist and your bucket is in the same region as this function.')
            raise e

    f = open(download_path, 'r')
    s = ""
    count=0
    degrees_to_radians = np.pi/180.0
    phi_prev = None
    theta_prev = None
    timestamp_prev = None
    data = []

    print ("parsing file  ...")
    for line in f:
        # found a new object => generate json or end of file -> parse last record
        if line == '  }, {\n' or line == '  } ]\n':
            s += '}'
            raw = json.loads(s) #json.loads(response['Body'].read()))
            
            # remove all points with accuracy < 1000
            if (raw['accuracy'] < 1000) : 
                # check if this is a flight
                count += 1
                if (timestamp_prev):
                    # Compute distance between two GPS points on a unit sphere
                    latitude = raw['latitudeE7']/float(1e7)
                    longitude = raw['longitudeE7']/float(1e7)
                    phi = (90.0 - latitude) * degrees_to_radians
                    theta = longitude * degrees_to_radians
                    timestamp = float(raw['timestampMs'])/1000
                    dt = datetime.datetime.fromtimestamp(timestamp)
                    distance = np.arccos(np.sin(phi)*np.sin(phi_prev) * np.cos(theta - theta_prev) +
                        np.cos(phi)*np.cos(phi_prev)) * 6378.100 # radius of earth in km
                    speed = distance/(float(timestamp_prev) - float(timestamp))*3600  #km/hr 3600/1000 to get min
                    
                    if ((speed > 40) and (distance > 80)):
                        count += 1
                        d = {
                                'index':count_prev,
                                'startlat':latitude,
                                'startlon':longitude,
                                'startdatetime':dt,
                                'endlat':latitude_prev,
                                'endlon':longitude_prev,
                                'enddatetime':dt_prev,
                                'distance':distance,
                                'speed':speed,
                            }
                        data.append(d)

                    latitude_prev = latitude
                    longitude_prev = longitude
                    phi_prev = phi
                    theta_prev = theta
                    timestamp_prev = timestamp
                    dt_prev = dt
                    count_prev = count

                #add the first
                else:
                    count += 1
                    latitude_prev = raw['latitudeE7']/float(1e7)
                    longitude_prev = raw['longitudeE7']/float(1e7)
                    phi_prev = (90.0 - latitude_prev) * degrees_to_radians
                    theta_prev = longitude_prev * degrees_to_radians
                    timestamp_prev = float(raw['timestampMs'])/1000
                    dt_prev = datetime.datetime.fromtimestamp(timestamp_prev)
            s = '{'
            del raw
        # ignore locations array
        elif line != '  "locations" : [ {\n' and line != '  } ]\n' :
            s += line.rstrip('\n')

    f.close()
    if not runlocal:
        os.remove(download_path)
    
    print (count)
    #print (data)
    flights = pd.DataFrame(data)
    print ('#flights: ' + str(len(flights)))

    # Combine instances of flight that are directly adjacent
    # Find the indices of flights that are directly adjacent
    _f = flights[flights['index'].diff() == 1]
    adjacent_flight_groups = np.split(_f, (_f['index'].diff() > 1).nonzero()[0])
    print ('#adj.flights: ' + str(len(adjacent_flight_groups)))

    # Now iterate through the groups of adjacent flights and merge their data into
    # one flight entry
    if (len(adjacent_flight_groups)>1):
        for flight_group in adjacent_flight_groups:
            idx = flight_group.index[0] - 1 #the index of flight termination
            flights.ix[idx, ['startlat', 'startlon', 'startdatetime']] = [flight_group.iloc[-1].startlat,
                                                             flight_group.iloc[-1].startlon,
                                                             flight_group.iloc[-1].startdatetime]
            # Recompute total distance of flight
            flights.ix[idx, 'distance'] = h.distance_on_unit_sphere(flights.ix[idx].startlat,
                                                               flights.ix[idx].startlon,
                                                               flights.ix[idx].endlat,
                                                               flights.ix[idx].endlon)*6378.1

        # Now remove the "flight" entries we don't need anymore.
        flights = flights.drop(_f.index).reset_index(drop=True)

    # Finally, we can be confident that we've removed instances of flights broken up by
    # GPS data points during flight. We can now be more liberal in our constraints for what
    # constitutes flight. Let's remove any instances below 200km as a final measure.

    print ('#flights (final): ' + str(len(flights)))
    print (flights)
    flights = flights[flights.distance > 200].reset_index(drop=True)


    #add city names & airports
    cached_locs = {}
    cached_apts = {}
    startlocations=list(zip(flights.startlat, flights.startlon))
    startcities = list(map(lambda x: h.getplace(x[0], x[1], cached_locs), startlocations))
    flights['startcity']=startcities
    startairports = list(map(lambda x: h.getairport(x[0], x[1], cached_apts), startlocations))
    flights['startairport']=startairports
    endlocations = list(zip(flights.endlat, flights.endlon))
    endcities = list(map(lambda x: h.getplace(x[0], x[1], cached_locs), endlocations))
    flights['endcity']=endcities
    endairports = list(map(lambda x: h.getairport(x[0], x[1], cached_apts), endlocations))
    flights['endairport']=endairports
    #print (flights)
    #print (cached_locs)

    #add CO2 consumption
    co2 = list(map(lambda x: h.getCO2(x), flights.distance))
    flights['co2']=co2


    print ('#flights (final): ' + str(len(flights)))
    print (flights)

    if ('output-folder' in event):
        flights.to_csv(event['output-folder'].encode('utf8')+"flights.csv")
        flights.to_json(event['output-folder'].encode('utf8')+"flights.json")
    else:
        try:
            print("storing ...")
            s3.put_object(
                Bucket='journey-results', 
                Key=key, 
                Body=(bytes(flights.to_json(orient='split').encode('UTF-8')))
                #Body=(bytes(json.dumps(flights, indent=2).encode('UTF-8')))
            )
            s3.put_object_acl(
                Bucket='journey-results', 
                Key=key, 
                ACL='public-read'
            )
            print("done.")
            return ("done.")
        except Exception as e:
            print(e)
            print('Error storing object {} from bucket {}.'.format(key, bucket))
            raise e
	