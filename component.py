# This script is intended to standardize on scripts that surround and extend the
# functionality of Ignition built in components. 

from qc import Query
from copy import deepcopy
from val import Error

class FlexRepeater(object):
	""" Flex Repeater object. """
	
	def __init__(self):
		self._instances = []
		
	@property
	def Instances(self):	
		return self._instances
		
	def addInstances(self, num, params):
		# Add any number of instances to the flex repeater object
		# with the appropriate embedded view parameters.
		for i in range(num):
			self._instances.append(FLXRInstance(params).Value)
		return self.Instances
		
	def removeInstance(self, index):
		# Remove a flex repeater instance from the object at
		# any index in the list.
		self._instances.pop(index)
		return self.Instances
		
		
class FLXRInstance(object):
	""" A Flex Repeater instance object. """
	
	INSTANCE_TEMPLATE = {'instanceStyle': {'classes': ''},
						 'instancePosition': {}}
	
	def __init__(self, parameters=None):
		self.parameters = parameters if parameters else {}
		
	@property
	def Value(self):
		# The IGN compatible structured dictionary to instantiate a 
		# flex repeater instance with defined parameters.
		instance = deepcopy(FLXRInstance.INSTANCE_TEMPLATE)
		instance.update(self.parameters)
		return instance


class ViewCanvas(object):
	""" View Canvas object. """
	
	def __init__(self):
		self._instances = []
		
	@property
	def Instances(self):	
		return self._instances
		
	def addInstance(self, VWCInstance):
		self._instances.append(VWCInstance.instance)
				
	def removeInstances(self, num):
		if self._instances>=num:
			for i in range(num):
				self._instances.pop()
		return self.Instances
	
	
class VWCInstance(object):
	""" View Canvas Instance object. """
	
	INSTANCE_TEMPLATE = {'position': 'absolute',
						 'top': '0px',
						 'left': '0px',
						 'bottom': 'auto',
						 'right': 'auto',
						 'zIndex': 'auto',
						 'width': 'auto',
						 'height': 'auto',
						 'viewPath': '',
						 'viewParams': {},
						 'style': {'classes': ''}}
						 
	def __init__(self, viewPath, parameters=None):
		self.viewPath = viewPath
		self.parameters = parameters if parameters else {}
		self.instance = self._configureInstance()
		
	@property
	def Value(self):
		return self.instance
		
	def _configureInstance(self):
		inst = deepcopy(VWCInstance.INSTANCE_TEMPLATE)
		inst['viewParams'] = self.parameters 
		inst['viewPath'] = self.viewPath
		return inst
		
	def setPosition(self, top, left):
		self.instance['top'] = 'auto' if top == 'auto' else '{0}px'.format(top)
		self.instance['left'] = 'auto' if left == 'auto' else '{0}px'.format(left)
	
	def setDimensions(self, height, width):
		self.instance['height'] = 'auto' if height == 'auto' else '{0}px'.format(height)
		self.instance['width'] = 'auto' if width == 'auto' else '{0}px'.format(width)


class Dashboard(object):
	""" Dashboard component object. """
	
	ROW_COUNT_DEFAULT = 100
  	COLUMN_COUNT_DEFAULT = 66
  	WIDGET_LENGTH_DEFAULT = 15
  	WIDGET_WIDTH_DEFAULT = 20
  	
  	def __init__(self, rowCount=None, columnCount=None):
  		# Row and column count default to class defaults if unprovided
  		self.rowCount = rowCount if rowCount else Dashboard.ROW_COUNT_DEFAULT
  		self.columnCount = columnCount if columnCount else Dashboard.COLUMN_COUNT_DEFAULT
  		# Grid and Widget objects
  		self.grid = cc.Grid(self.rowCount, self.columnCount)
  		self.widgets = []
  		
  	def clearGrid(self):
  		self.grid.clear()
  		
  	def placeWidget(self, width=None, length=None):
  		width = width if width else Dashboard.WIDGET_WIDTH_DEFAULT
  		length = length if length else Dashboard.WIDGET_LENGTH_DEFAULT
  		topLeftCorner = self.grid.placeRectangle(width, length)
  		pos = {'rowStart': topLeftCorner[0] + 1, 'rowEnd': topLeftCorner[0] + width,
  			   'columnStart': topLeftCorner[1] + 1, 'columnEnd': topLeftCorner[1] + length}
  		self.widgets.append(DASHWidget(position=pos))
  		
  		
  	def addWidget(self, pos):
  		width, length = self._getDimensionsFromPos(pos)
  		self.grid.addRectangle(pos['rowStart'] - 1,
  							   pos['columnStart'] - 1,
  							   width,
  							   length)
  	
  	def removeWidget(self, pos):
  		width, length = self._getDimensionsFromPos(pos)
		self.grid.removeRectangle(pos['rowStart'] - 1,
							  	  pos['columnStart'] - 1,
							   	  width,
							   	  length)
  	
  	def _getDimensionsFromPos(self, pos):	
  		return (pos['columnEnd'] - pos['columnStart']),\
  			   (pos['rowEnd'] - pos['rowStart'])
		
		
class DASHWidget(object):
	""" Dashboard Widget object. """
	
	WIDGET_TEMPLATE = {'name': '',
					   'viewPath': '',
					   'viewParams': {},
					   'isConfigurable': False,
					   'header': {'enabled': True, 
					   			  'title': '', 
					   			  'style': {'classes': ''}},
					   	'body': {'style': {'classes': ''}},
					   	'minSize': {'columnSpan': 1,
					   				'rowSpan': 1},
					   	'position': {'rowStart': 1,
					   				 'rowEnd': 2,
					   				 'columnStart': 1,
					   				 'columnEnd': 2},
		   				'style': {'classes': ''}}

	def __init__(self, **kwargs):
		self._kwargs = kwargs
		self.data = self._getData()
		
	def _getData(self):
		data = deepcopy(DASHWidget.WIDGET_TEMPLATE)
		for arg in self._kwargs:
			if arg in data:
				data[arg] = self._kwargs[arg]
		return data
		
	def setPosition(self, rowStart, rowEnd, columnStart, columnEnd):
		pass

class Dropdown(object):
	""" Dropdown component object. """
	def __init__(self):
		self.value = None
		self.options = []
	
	def getPrimaryIDOptions(self, table):
		# Query to retrieve a pyDataSet containing the AutoID with their 
		# corresponding primary ID's
		q = (Query().Select(['{0} AS AutoID'.format(table.AutoIDColumnHeader), 
							 '{0} AS ID'.format(table.PrimaryIDColumnHeader)])
					.From(table.FullName))
		data = q.execute(dataBase=table.dataBase.Name)
		# Expecting PyDataset but catches val.Error types.
		if isinstance(data, Error):
			return data.Value
		self.options = [DDLOption(row['AutoID'], row['ID']).Value for row in data]
		return self.options
		
	def addOption(self, value, label):
		self.option.append(DDLOption(value, label).Value)
		return self.options


class DDLOption(object):
	""" Dropdown list option property object. """
	
	OPTION_TEMPLATE = {'value': '',
					   'label': ''}
					   
	def __init__(self, value, label):
		self.value = value if value else ''
		self.label = label if label else ''
	
	@property
	def Value(self):
		option = self.OPTION_TEMPLATE.copy()
		option['value'] = self.value
		option['label'] = self.label
		return option


class Tree(object):
	""" Tree component object. """
		
	def __init__(self, items=None):
		# Items property is all I'm concerned with right now.
		self.items = items if items else []
		
	def addItem(self, label, path, expanded=False, data=None, items=None, icon=None):
		# Add item to items and return the new items list
		newItem = TreeItem(label, path, expanded, data, items, icon).Value
		parentItem, index = self._getParentItem(path)
		parentItem.insert(index, newItem)
		return self.items

	def removeItem(self, path):
		# Remove item and returns deleted item
		parentItem, index = self._getParentItem(path)
		return parentItem.pop(index)
		
	def replaceItem(self, label, path, expanded=False, data=None, items=None, icon=None):
		# Replace an item and return the new items list
		newItem = TreeItem(label, path, expanded, data, items, icon).Value
		parentItem, index = self._getParentItem(path)
		parentItem[index] = newItem
		return self.items
		
	def moveItem(self, currentPath, desPath):
		# Move a tree item from one path to another, returns new items list
		item = self.removeItem(currentPath)
		return self.addItem(item['label'], desPath, 
							item['expanded'], item['data'], 
							item['items'], item['icon'])
		
	def _getParentItem(self, path):
		indices = self._getIndices(path)
		if len(indices) == 1:
			return self.items, indices[0]
		parentItem = self.items[indices[0]]
		for index in indices[1:-1]:
			parentItem = parentItem['items'][index]
		return parentItem['items'], indices[-1]
		
	def _getIndices(self, path):
		return list(map(int, path.split('/')))
		
	def getReadablePath(self, path):
		# Iterate through items and construct a readable path
		# ie '0/0/1' might translate to 'Categories/Asset/Basic Asset'
		indices = self._getIndices(path)
		if len(indices) == 1:
			return self.items[indices[0]]['label']
		# Get root label to start path string.
		item = self.items[indices[0]]
		pathStr = item['label']
		for index in indices[1:]:
			item = item['items'][index]
			pathStr = '{0}/{1}'.format(pathStr, item['label'])
		return pathStr
		
	def openItemPath(self, path):
		# Changes the item parameter 'expanded' to true for each
		# item along the 'path' except the item itself.
		# First collapse all items.
		self.setItemsCollapsed()
		indices = self._getIndices(path)
		if len(indices) == 1:
			self.items[indices[0]]['expanded'] = True
			return self.items
		item = self.items[indices[0]]
		item['expanded'] = True
		for index in indices[1:]:
			item = item['items'][index]
			item['expanded'] = True
		return self.items
		
	def _collapseItems(self, items):	
		for item in items:
			item['expanded'] = False
			if 'items' in item:
				self._collapseItems(item['items'])
		return items
		
	def setItemsCollapsed(self):
		self.items = self._collapseItems(self.items)
		return self.items
		
	def getNumSiblings(self, path):
		parentItem, index = self._getParentItem(path)
		return len(parentItem)
		
	def getNumChildren(self, path):
		if not path:
			return None
		parentItem, index = self._getParentItem(path)
		return len(parentItem[index]['items'])
			
		
class TreeItem(object):
	""" Tree component item property. """
	
	ITEM_TEMPLATE = {'label': '',
					 'expanded': False,
					 'data': '',
					 'items': [],
					 'icon': {}}
					 
	def __init__(self, label, path, expanded=False, data=None, items=None, icon=None):
		self.label = label
		self.path = path
		self.expanded = expanded
		self.data = data if data else ''
		self.items = items if items else []
		self.icon = icon if icon else {}
		
	@property
	def Value(self):
		val = deepcopy(self.ITEM_TEMPLATE)
		val['label'] = self.label
		val['expanded'] = self.expanded
		val['data'] = self.data
		val['items'] = self.items
		val['icon'] = self.icon
		# Check to see if icon object was supplied rather than value
		if isinstance(self.icon, Icon):
			val['icon'] = self.icon.Value
		return val


class Icon(object):
	""" Icon property. """
	
	ICON_TEMPLATE = {'path': '',
					 'color': '',
					 'style': {}}
	
	def __init__(self, path, color=None, style=None):
		self.path = path
		self.color = color if color else ''
		self.style = style if style else {}
		
	@property
	def Value(self):
		val = deepcopy(self.ICON_TEMPLATE)
		val['path'] = self.path
		val['color'] = self.color
		val['style'] = self.style
		return val
