import socket
from db import Database

def datasetToDict(dataset):
	"""
	| Converts dataset to dictionary
	| Parameters: dataset (dataset)
	| Returns: dictionary (dictionary)
	"""
	data = system.dataset.toPyDataSet(dataset)
	columnHeaders = system.dataset.getColumnHeaders(dataset) 
	
	dictionary = {}
	rowNum = 0 #assume only a single row is given and always return the first row
	i = 0
	for column in columnHeaders:
		dictionary[column] = data[rowNum][i]
		i+=1
	return dictionary
	
def findAllSubViews(folder='SV'):
	"""
	| Find all the sub view names in a given folder.
	| Parameters: folder name, default is 'SV' (string)
	| Returns: subViews (list)
	"""
	meta = system.perspective.getProjectInfo()
	views = meta["views"]
	subViews = []
	for i in range(len(views)):
		if folder in views[i]["path"]:
			subViews.append(views[i]["path"])	
	return subViews
	
def isNullValue(value):
    """ Test if field value is NULL. """
    return (value in [None, ''] or str(value).upper() == 'NULL' or len(str(value)) == 0)
   
def areEqualDicts(d1, d2):
	""" Compare if two dictionaries are equivalent. """
	return not(bool(deepDiff(d1, d2)))

def deepDiff(d1, d2, differences=None, level='root'):
	""" Recursive algorithim to compare two dictionaries and their contents. """
	# Initializing differences dictionary for first level of recursion.
	differences = differences if differences else {}
	# If current layer is dictionary, check if keys are equal
	if isinstance(d1, dict) and isinstance(d2, dict):
		# If keys aren't equal store them sets to find the difference between them
		if d1.keys() != d2.keys():
			s1 = set(d1.keys())
			s2 = set(d2.keys())
			# Append the level as a key if differences dict with the set differences as the value
			differences[level] = 'Key Difference: {0} - {1}'.format(s1-s2, s2-s1)
			# Store shared keys
			commonKeys = s1 & s2
		else:
			commonKeys = set(d1.keys())
		# Iterate through the shared keys and send back through function
		for key in commonKeys:
			differences = deepDiff(d1[key], d2[key], differences, level='{}.{}'.format(level, key))
		return differences
	# If current layer is a list, check the lengths
	elif isinstance(d1, list) and isinstance(d2, list):
		# If lengths differ, store the level as a key to differences dict with length difference string as value
		if len(d1) != len(d2):
			differences[level] = 'List Length Difference: len({0}1) = {1} while len({2}2) = {3}'.format(level, len(d1), level, len(d2))
		# Store common length as integer
		commonLength = min(len(d1), len(d2))
		# Iterate through length and pass each list item back through function
		for i in range(commonLength):
			differences = deepDiff(d1[i], d2[i], differences, level='{0}[{1}]'.format(level, i))
		return differences
	# If current layer is not a list or dictionary, check the values
	else:
		if d1 != d2:
			differences[level] = 'Value Difference: {0} != {1}'.format(d1, d2)
		return differences
		
def getReadableDiff(diff):
	""" Return a readable string from a deepDiff() dictionary. """
	messages = []
	for key, val in diff.items():
		if 'Key Difference' in val:
			initialKeys = val.split("set([")[1].split("])")[0].split(',')
			newKeys = val.split("set([")[2].split("])")[0].split(',')
			for i, initialKey in enumerate(initialKeys):
				messages.append('Change {0} to {1} at {2}.'.format(initialKey, newKeys[i], key.split('.')[-1]))
		if 'List Length Difference' in val:
			initialLen = val.split(' = ')[1].split(' while')[0]
			newLen = val.split(' = ')[2]
			difference = int(newLen) - int(initialLen)
			if difference > 0:
				messages.append('Add {0} to {1}.'.format(abs(difference), key.split('.')[-1]))
			else:
				messages.append('Remove {0} from {1}.'.format(abs(difference), key.split('.')[-1]))
		if 'Value Difference' in val:
			values = val.replace('Value Difference: ', '').split(' != ')
			initialVal, newVal = values
			messages.append('Change {0} from {1} to {2}.'.format(key.split('.')[-1], initialVal, newVal))
	return messages

def getDictionary(obj):
	# Get a PyDict from IGN native data structures like 
	# PropertyTreeScriptWrapper or DotReferenceJythonMap.
	json = system.util.jsonEncode(obj)
	return system.util.jsonDecode(json)
	
def getDatabaseObj(dataBase):
	return dataBase if isinstance(dataBase, Database) else Database(dataBase)

#https://forum.inductiveautomation.com/t/getting-host-name-in-perspective/40472
def getHostName(ipaddr,stripdomain = False):
	#Get a hostname from an IP Address
	# Used to determine hostname when saving audit log to database
	if validateIp(ipaddr):
		hostname = socket.gethostbyaddr(ipaddr)[0]
		#Verify that we actually got a host name
		if not validateIp(hostname):
			if stripdomain:
				return hostname[:hostname.find('.')]
			else:
				return hostname
		else:
			#If the hostname can't be found then this will just return the ip address
			return hostname
	else:
		#Just return the ipaddr because it's probably the host name
		return ipaddr

def validateIp(ipaddr):
	try:
		socket.inet_aton(ipaddr)
		return True
	except socket.error:
		return False
		
