import os
import urllib
from urllib import urlopen
import json
import datetime
import numpy as np
from time import sleep


googleplaces_api_key=os.environ['GOOGLEPLACES_API_KEY']
googlemaps_api_key=os.environ['GOOGLEMAPS_API_KEY']

def distance_on_unit_sphere(lat1, long1, lat2, long2):
	# http://www.johndcook.com/python_longitude_latitude.html
	# Convert latitude and longitude to spherical coordinates in radians.
	degrees_to_radians = np.pi/180.0
	# phi = 90 - latitude
	phi1 = (90.0 - lat1)*degrees_to_radians
	phi2 = (90.0 - lat2)*degrees_to_radians
	# theta = longitude
	theta1 = long1*degrees_to_radians
	theta2 = long2*degrees_to_radians

	cos = (np.sin(phi1)*np.sin(phi2)*np.cos(theta1 - theta2) +
		   np.cos(phi1)*np.cos(phi2))
	arc = np.arccos( cos )
	# Remember to multiply arc by the radius of the earth
	# in your favorite set of units to get length.
	return arc

def key_for(lat,lon):
	return str(round(lat,3))+'#'+str(round(lon,3))

def getplace(lat, lon, cached_locs):
	country = town = None

	tc = cached_locs.get(key_for(lat, lon))
	#print (tc)
	if tc:
		print ("using cache for %s, %s" % (tc[0], tc[1]))
		return tc[0], tc[1]

	url = "https://maps.googleapis.com/maps/api/geocode/json?"
	url += "latlng=%s,%s&sensor=false&key=%s" % (lat, lon, googlemaps_api_key)
	v = urlopen(url).read()
	j = json.loads(v)
	#print (j)
	#print (json.dumps(j, indent=2, sort_keys=True))

	tries = 3
	timedelta = .3
	for i in range(tries):
		try:
			components = j['results'][0]['address_components']
			#print (j['results'][0]['formatted_address'].replace(',','.'))
			for c in components:
				if "country" in c['types']:
					country = c['long_name']
				if "locality" in c['types']:
					town = c['long_name']
		except Exception as e:
			if i < tries - 1: # i is zero indexed
				sleep(timedelta)
				timedelta += timedelta
				print('Could not resolve country and town from json. Retrying.')
				error = ''
				if ('status' in j):
					error = j['status']
				if ('error_message' in j):
					error += ": " + j['error_message']
				print (error)
				continue
			else:
				print('Could not resolve country and town from json.')
				print (j)
				print(e)
		break

	cached_locs[key_for(lat,lon)]=(town, country)
	#if ((country == None) or (town == None)):
	#    print (json.dumps(j, indent=2, sort_keys=True))
	return town, country


def getairport(lat, lon, cached_locs):
	country = town = None

	airport = cached_locs.get(key_for(lat, lon))
	#print (tc)
	if airport:
		print ("using cache for %s" % airport)
		return airport

	url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
	url += "location=%s,%s&radius=50000&type=airport&&key=%s" % (lat, lon, googleplaces_api_key)
	#print (url)
	v = urlopen(url).read()
	j = json.loads(v)
	#print (j)
	#print (json.dumps(j, indent=2, sort_keys=True))

	try:
		components = j['results'][0]#['address_components']
		c = components
		#print (components)
		#print ("%s, %s" % (c['types'], c['icon']))
		if "airport" in c['types'] and c['icon'] == "https://maps.gstatic.com/mapfiles/place_api/icons/airport-71.png":
			airport = c['name']
	except Exception as e:
		print('Could not resolve airport from json. Retrying.')
		print (j)
		print(e)

	cached_locs[key_for(lat,lon)]=airport
	#if ((country == None) or (town == None)):
	#    print (json.dumps(j, indent=2, sort_keys=True))
	return airport


def getCO2(x):
	#### Hybrid short-haul + Generic short-haul ###
	if (x<1500):
		p = {
			# Average seat number
			'S' : 158.44,
			# Passenger load factor
			'PLF' : 0.77,
			# Detour constant
			'DC' : 50,
			#1- Cargo factor
			'CF' : 0.049,
			# Economy class weight
			'ECW' : 0.960,
			# Business class weight
			'BCW' :  1.26,
			# First class weight
			'FCW' : 2.40,
			# Emission factor
			'EF' : 3.150,
			# Preproduction
			'P' : 0.51,
			# Multiplier
			'M' : 2,
			#a
			'a' : 0.0000387871,
			#b
			'b' : 2.9866,
			#c
			'c' : 1263.42
			}

	#### Hybrid long-haul + Generic long-haul ###
	elif (x>2500):
		p = {
			# Average seat number
			'S' : 280.39,
			# Passenger load factor
			'PLF' : 0.77,
			# Detour constant
			'DC' : 125,
			#1- Cargo factor
			'CF' : 0.049,
			# Economy class weight
			'ECW' : 0.800,
			# Business class weight
			'BCW' :  1.54,
			# First class weight
			'FCW' : 2.40,
			# Emission factor
			'EF' : 3.150,
			# Preproduction
			'P' : 0.51,
			# Multiplier
			'M' : 2,
			#a
			'a' : 0.000134576,
			#b
			'b' : 6.1798,
			#c
			'c' : 3446.20
			}
	# interpolate inbetween, TODO: using middle values for now
	else :
		p = {
			# Average seat number
			'S' : 219.415,
			# Passenger load factor
			'PLF' : 0.77,
			# Detour constant
			'DC' : 87.5,
			#1- Cargo factor
			'CF' : 0.049,
			# Economy class weight
			'ECW' : 0.880,
			# Business class weight
			'BCW' :  1.4,
			# First class weight
			'FCW' : 2.40,
			# Emission factor
			'EF' : 3.150,
			# Preproduction
			'P' : 0.51,
			# Multiplier
			'M' : 2,
			#a
			'a' : 0.00008668155,
			#b
			'b' : 4.5832,
			#c
			'c' : 2354.81
			}
	# Add Distance Correction for detours and holding patterns, and inefficiencies in the air traffic control systems [km]
	distance = x + p['DC'];
	
	#TODO: using economy only for now
	E = ((p['a']*distance**2) + (p['b']*distance) + p['c']) / (p['S'] * p['PLF']) 
	E = E * (1 - p['CF']) * p['ECW'] * (p['EF'] * p['M'] + p['P'])
	return E;


	
