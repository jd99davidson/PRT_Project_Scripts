# Explicit dependencies
from qc import Query
from math import ceil
from copy import deepcopy


class PowerTable(object):
	""" Power table custom component object. """

	COLUMN_WIDTH_RATIO = 4
	CHARACTER_MAX_DEFAULT = 50
	CHARACTER_MAX_MIN = 20
	DB_TABLE_NAME = 'PowerTable.ViewConfig'
	ADMIN_DB = 'PRT_ADMIN'
	DEFAULT_AUTO_ID = 1000

	def __init__(self, dataBase, viewConfig=None, configs=None):
		# Database attribute that can be either Database() object or string. Should be populated
		# using session.custom.activeDatabase in perspective.
		self.dataBase = util.getDatabaseObj(dataBase)
		# View config string (name of pt configurations)
		self.viewConfig = viewConfig
		# Configs attribute that store the PTConfigs object
		self._configs = (PTConfigs(configs, dataBase=self.dataBase.Name) if configs 
						else PTConfigs(self._getConfigsFromViewConfig(), dataBase=self.dataBase.Name))
		# Whether or not to paginate the PowerTable results
		self.paginate = True
	
	@property
	def Query(self):
		q = self.getQuery()
		return self._decidePagination(q)
		
	@property
	def configs(self):
		return self._configs.configs
		
	@property
	def Data(self):
		# Error handling?
		return self.Query.execute(dataBase=self.dataBase.Name)
		
	def _getConfigsFromViewConfig(self):
		# View configs are stored as strings in db, converted to a dictionary here.
		q = Query().Select(['configs']).From(self.DB_TABLE_NAME).Where(['viewConfig = ?'])
		data = q.execute([str(self.viewConfig)], dataBase=self.ADMIN_DB)
		if data.getRowCount():
			return eval(data[0]['configs'])
		# If no data, return a copy of the template
		return deepcopy(PTConfigs.CONFIGS_TEMPLATE)
		
	def _decidePagination(self, query):
		if self.paginate:
			c = self._configs
			return query.paginate(c.OrderBy, c.RowsPerPage, c.CurrentPage)
		return query
		
	def getQuery(self):
		# Constructs the query to be executed to populate Data.
		q = Query()
		c = self._configs
		# Using the columns in configs as well as their AutoID columns
		q.Select(c.getColumnsWithAutoIDs())
		q.From(c.BaseTableObj.FullName, c.BaseTable['alias'] if c.BaseTable['alias'] else c.BaseTableObj.Alias)
		# Need table to join on from config (default is From table)...
		for table in c.configs['tables']:
			if table['columnJoin']:
				q.Join(table['name'], 
					   c.BaseTableObj.FullName,
					   table['alias'],
					   c.BaseTable['alias'] if c.BaseTable['alias'] else c.BaseTableObj.Alias,
					   table['columnJoin'],
					   table['joinType'])
		# Need to add conditionals for filters
		clauses = self._getWhereClauses()
		return q.Where(clauses) if clauses else q		
	
	def _getWhereClauses(self):
		c = self._configs
		return ["{0} LIKE '%{1}%'".format(name, filter_) for name, filter_ in c.Filters.items()]
	
	def getTotalRowCount(self):
		# Total results row count.
		q = self.getQuery()
		data = q.execute(dataBase=self.dataBase.Name)
		# Expecting integer but catching if is error type.
		if isinstance(data, Error):
			return data.Value
		return data.getRowCount()
	
	def getTotalPageCount(self):
		from val import Error
		# Total results page count.
		results = self.getTotalRowCount()
		# Expecting integer but catching if is error type.
		if isinstance(results, Error):
			return results.Value
		return int(ceil(float(results)/float(self._configs.Pager['rowsPerPage'])))
	
	def getPotentialColumns(self):
		# Only showing additional fields for Base table...
		c = self._configs
		existingColumns = [col['name'].split('.')[1].strip(db.BRACKET_STRIP) 
						   for col in c.configs['columns'] if col['isDisplayed']]
		# Need to know how to alias column, so we need to know the table its coming from		
		return [{'name': '{0}.[{1}]'.format(c.BaseTable['alias'], col.Name), 
				 'characterMax': self._filterCharacterMax(col.characterMax), 
				 'dataType': 'FK' if col.IsForeignKey else col.dataType, 
				 'alias': col.Name if 'AutoID' not in col.Name else col.Name.replace('AutoID', ''), 
				 'filter_': '', 
				 'orderBy': '',
				 'referenceTable': c.BaseTable['name'].replace('[', '').replace(']', '') 
				 				   if not col.getFKReference() else col.getFKReference(),
				 'isDisplayed': 1}
				for col in c.BaseTableObj.Columns
				if col.Name not in existingColumns and not col.IsAutoID]
				
	def getAllColumns(self):
		c = self._configs
		columns = c.configs['columns']
		for col in c.BaseTableObj.Columns:
			newColName = '{0}.[{1}]'.format(c.BaseTable['alias'], col.Name)
			if not col.IsAutoID and newColName not in c.Columns:
				newColumn = {'name': newColName,
							 'characterMax': self._filterCharacterMax(col.characterMax),
							 'dataType': 'FK' if col.IsForeignKey else col.dataType,
							 'alias': col.Name if 'AutoID' not in col.Name else col.Name.replace('AutoID', ''),
							 'filter_': '',
							 'orderBy': '',
							 'referenceTable': c.BaseTable['name'].replace('[', '').replace(']', '')
							 				   if not col.getFKReference() else col.getFKReference(),
							 'isDisplayed': 0} 
				columns.append(newColumn)
		return columns
				
	def _filterCharacterMax(self, characterMax):
		# Maybe this should be in PTConfigs
		# Character max is 50 if none provided by query, 20 if less than min, or value
		if characterMax:
			return characterMax if characterMax > self.CHARACTER_MAX_MIN else self.CHARACTER_MAX_MIN
		return self.CHARACTER_MAX_DEFAULT
			
	def filterPotentialColumns(self, filter_, selections):
		# Function for the 'AddColumn' search functionality.
		potentialCols = self.getPotentialColumns()
		return [col for col in potentialCols if filter_ in col['alias']
					or col['name'] in [selection['name'] for selection in selections]]
		
	def getColumnHeaderInstances(self):
		# Retrieving the column header instances (contained in 
		# a flex repeater) from the configs.
		flxr = component.FlexRepeater()
		for i, col in enumerate(self.configs['columns']):
			if col['isDisplayed']:
				params = {'configs': self.configs,
						  'instanceID': i}
				flxr.addInstances(1, params)
		return flxr.Instances
	
	def getRowInstances(self, data):
		# Retrieving the row instances (contained in 
		# a flex repeater) from the data input param.
		flxr = component.FlexRepeater()
		for i, row in enumerate(data):
			params = {'row': [{'value': row[j],
							   'column': self.configs['columns'][j/2],
							   'cell': [i, j],
							   'AutoID': row[j+1]}
							   for j in range(len(row))
							   if j%2 == 0 and self.configs['columns'][j/2]['isDisplayed']]}
			flxr.addInstances(1, params)
		return flxr.Instances
		
	def getCellInstances(self, row):
		# Receives a row structured as is defined in the getRowInstances() 
		# method.
		vwc = component.ViewCanvas()
		width = 0
		for cell in row:
			viewPath = self._getCellViewPath(cell['column']['dataType'])
			params = {'value': cell['value'],
					  'originalValue': cell['value'],
					  'column': cell['column'],
					  'cell': cell['cell'],
					  'AutoID': cell['AutoID']}
			instance = component.VWCInstance(viewPath, params)
			instance.setPosition(0, width)
			w = cell['column']['characterMax']*self.COLUMN_WIDTH_RATIO
			instance.setDimensions('auto', w)
			width += w
			vwc.addInstance(instance)
		return vwc.Instances
		
	def _getCellViewPath(self, dataType):
		ints = [enums.DataType.INT.value, 
				enums.DataType.SMALLINT.value, 
				enums.DataType.TINYINT.value]
		# Dropdown cell view path is determined not by data type but by schema (Enums).
		# To avoid restructuring the 'row' list passed to 'getCellInstances' method,
		# we could access the schema the column comes from using the 'getTableFromAlias'
		# method on the PTConfigs object...
		if dataType == 'FK':
			return 'F3100-PowerTable/T/V440-DropdownCell'
		if dataType == enums.DataType.DATETIME.value:
			return 'F3100-PowerTable/T/V420-DateCell'
		if dataType in ints:
			return 'F3100-PowerTable/T/V430-NumericCell'
		return 'F3100-PowerTable/T/V400-TextCell'
		
	def _groupChanges(self, changes):
		# Take the PowerTable dataChanges dict and return the structured
		# groupedChanges dictionary modeled as: {table: {AutoID: {col: value}}}
		groupedChanges = {}
		for change in changes:
			AutoID = change['AutoID']
			alias, colName = change['column']['name'].split('.')
			table = self._configs.getTableFromAlias(alias)
			if table.FullName not in groupedChanges:
				groupedChanges[table.FullName] = {}
			if AutoID not in groupedChanges[table.FullName]:
				# Create a new key for the AutoID and assign the value as a dict
				groupedChanges[table.FullName][AutoID] = {colName: change['value']}
			else:
				groupedChanges[table.FullName][AutoID].update({colName: change['value']})
		return groupedChanges	
		
	def saveDataChanges(self, changes):
		# @@NEEDS_BUSINESS_LOGIC@@
		# Method to save dataChanges to the database.
		results = []
		groupedChanges = self._groupChanges(changes)
		for table in groupedChanges:
			tableObj = db.Table(table, dataBase=self.dataBase.Name)
			for AutoID in groupedChanges[table]:
				result = db.Row(tableObj, AutoID).update(groupedChanges[table][AutoID])
				results.append(result)
		# Either returns a list of rows affected (per AutoID) or val.Error obj.
		return results
		
	def updateViewConfig(self, values):
		from val import Error
		# @@NEEDS_BUSINESS_LOGIC@@
		# Accepts a dictionary with the columns of the ViewConfig table as keys
		# and the data as values.
				
		# Need validation.
		# Expecting None but catches val.Error types.
		error = self._validateCRUD(values)
		if isinstance(error, Error):
			return error.Value
			
		table = db.Table(self.DB_TABLE_NAME, dataBase=self.ADMIN_DB)
		row = db.Row(table, values[table.AutoIDColumnHeader])
		# Either returns integer of # of rows affected or val.Error obj.
		return row.update(values)
		
	def createViewConfig(self, values):
		from val import Error
		# @@NEEDS_BUSINESS_LOGIC@@
		# Accepts a dictionary with the columns of the ViewConfig table as keys
		# and the data as values.
		# Also accepts the activeDatabaseAutoID to register
		
		# Need validation.
		# Expecting None but catches val.Error types.
		error = self._validateCRUD(values)
		if isinstance(error, Error):
			return error.Value
		
		table = db.Table(self.DB_TABLE_NAME, dataBase=self.ADMIN_DB)
		row = db.Row(table)
		# Either returns integer of # of rows affected or val.Error obj.
		return row.create(values)
		
	def registerViewConfig(self, ViewConfigAutoID, databaseAutoID):
		# @@NEEDS_BUSINESS_LOGIC@@
		# Register a view configuration on a particular database.
		table = db.Table('PowerTable.ViewConfigRegisteredDatabase', dataBase=self.ADMIN_DB)
		row = db.Row(table)
		values = {'ViewConfigAutoID': ViewConfigAutoID,
				  'DatabaseAutoID': databaseAutoID}
		return row.create(values)
		
	def deleteViewConfig(self, values):
		# @@NEEDS_BUSINESS_LOGIC@@
		table = db.Table(self.DB_TABLE_NAME, dataBase=self.ADMIN_DB)
		# Either returns integer of # of rows affected or val.Error obj.
		return db.Row(table, values[table.AutoIDColumnHeader]).delete()
		
	def deregisterViewConfig(self, ViewConfigAutoID, databaseAutoID):
		# @@NEEDS_BUSINESS_LOGIC@@
		# Deregisters ViewConfig from the supplied database and deletes it from 
		# PowerTable.ViewConfig if it is only registered on the supplied db 
		table = db.Table('PowerTable.ViewConfigRegisteredDatabase', dataBase=self.ADMIN_DB)
		values = {'ViewConfigAutoID': ViewConfigAutoID,
				  'DatabaseAutoID': databaseAutoID}
		return db.Row(table, filters=values).delete()
	
	def isRegistered(self, ViewConfigAutoID):
		# Check to see if view is registered on any db
		table = db.Table('PowerTable.ViewConfigRegisteredDatabase', dataBase=self.ADMIN_DB)
		row = db.Row(table, filters={'ViewConfigAutoID': ViewConfigAutoID})
		return row.Exists
		
	def _validateCRUD(self, values):
		# TODO!
		# Check 1: viewConfig doesn't already exist
		# Check 2: check to see if viewconfigAutoID exists in registered 
		#		   before taking action
		return None
		
	def isConfigs(self, currentConfigs):
		# Checking if some configs are equal to the object configs,
		# disregarding if the page number is different.
		differences = util.deepDiff(self.configs, currentConfigs)
		if differences.keys() == ['root.pager.currentPage']:
			return True
		return not bool(differences)


class PTConfigs(object):
	""" Power Table configurations object. """
	
	CONFIGS_TEMPLATE = 	{'columns': [{'name': '',
									  'characterMax': '',
									  'dataType': '',
									  'alias': '',
									  'filter_': '',
									  'orderBy': '',
									  'referenceTable': '',
									  'isDisplayed': ''}],
						 'pager': {'rowsPerPage': '',
						 		   'currentPage': ''},
						 'tables': [{'name': '',
									 'alias': '',
									 'columnJoin': '',
									 'joinType': ''}]}	
	
	def __init__(self, configs=None, dataBase=None):
		self.configs = configs if configs else deepcopy(PTConfigs.CONFIGS_TEMPLATE)
		self.dataBase = util.getDatabaseObj(dataBase)
	
	@property
	def Columns(self):
		return [col['name'] for col in self.configs['columns']]
		
	@property
	def ColumnOrder(self):
		return [col['alias'] for col in self.configs['columns']]
		
	@property
	def OrderBy(self):
		clauses =  ['{0} {1}'.format(col['name'], col['orderBy']) for col in self.configs['columns']
					if col['orderBy']]
		# Default the base table's AutoID column ASC
		alias = self.BaseTable['alias'] if self.BaseTable['alias'] else self.BaseTableObj.Alias
		default = ['{0}.[{1}]'.format(alias, self.BaseTableObj.AutoIDColumnHeader)]
		return default if len(clauses) == 0 else clauses
	
	@property	
	def Pager(self):
		return self.configs['pager']
		
	@property
	def CurrentPage(self):
		return self.Pager['currentPage']
		
	@property
	def RowsPerPage(self):
		return self.Pager['rowsPerPage']
			
	@property
	def Tables(self):
		return self.configs['tables']
	
	@property
	def BaseTable(self):
		return next(table for table in self.Tables if not table['columnJoin'])
			   
	@property
	def BaseTableObj(self):
		return db.Table(self.BaseTable['name'], dataBase=self.dataBase.Name)
						
	@property
	def Filters(self):
		# Dictionary with column name key and filter value.'
		filters = {}
		for col in self.configs['columns']:
			if col['filter_']:
				if col['dataType'] == 'FK':
					# How to get primaryID column header?
					table = db.Table(col['referenceTable'])
					alias = self.getAliasFromReferenceTable(col['referenceTable'])
					PrimaryIDColumnHeader = '{0}.[{1}]'.format(alias, table.PrimaryIDColumnHeader)
					filters[PrimaryIDColumnHeader] = col['filter_']
				else:
					filters[col['name']] = col['filter_']
		return filters

	def getAliasFromReferenceTable(self, referenceTable):
		for table in self.configs['tables']:
			if table['name'].replace('[', '').replace(']', '') == referenceTable.replace('[', '').replace(']', ''):
				return table['alias']
	
	def shiftColumn(self, columnName, direction):
		index = -1 if direction == enums.Direction.LEFT.value else 1
		columns = self.configs['columns']
		for i, col in enumerate(columns):
			if col['name'] == columnName:
				newPos = i + index
				# Don't allow the first column to be moved off the table (or wrapped)
				if newPos < 0:
					break
				columns.insert(newPos, columns.pop(i))
				break
		return self.configs
		
	def addColumn(self, pos, column):
		# Add column (containing all key/values defined in CONFIGS_TEMPLATE)
		# to an index of the columns list 'pos'
		if pos >= len(self.configs['columns']):
			self.configs['columns'].append(column)
		else:
			self.configs['columns'].insert(pos, column)
		return self.configs
		
	def removeColumn(self, pos):
		# Remove a column from a position in the configs attribtue
		self.configs['columns'].pop(pos)
		return self.configs
		
	def getColumnsWithAutoIDs(self):
		# Returns a list of aliased columns with aliased AutoID headers 
		# immediately adjacent to 'display' headers.
		columnList = []
		for column in self.Columns:
			alias = column.split('.')[0]
			# Match alias with table.
			table = self.getTableFromAlias(alias)
			AutoIDColumn = '{0}.[{1}]'.format(alias, table.AutoIDColumnHeader)
			columnList.extend([column, AutoIDColumn])
		return columnList
			
	def getTableFromAlias(self, alias):
		# Retrieve the table name in the configs from alias.
		# This acts as a bridge between aliased columns and their tables.
		for table in self.Tables:
			if table['alias'] == alias:
				return db.Table(table['name'], dataBase=self.dataBase.Name)
		return Error(enums.Message.HANDLED_FAILURE.value,
					 'No table found with alias {0}'.format(alias)).Value


class PTTreeBrowser(object):
	""" Power Table tree browser object. """
	
	# Basic structure is 'Categories' at the root with default folders
	ADMIN_DB = 'PRT_ADMIN'
	TABLE_DEFAULT = 'PowerTable.ViewConfig'
	ROOT_DEFAULT = 'Categories'
	FOLDERS_DEFAULT = ['Asset', 
					   'IO List', 
					   'Model Number', 
					   'Location', 
					   'Device Type', 
					   'Enums',
					   'Networking',
					   'Change Tracking',
					   'Reports']
	FOLDER_ICON_DEFAULT = 'material/folder'
	VIEW_ICON_DEFAULT = 'material/table_view'
	
	def __init__(self, items=None):
		self.items = items if items else self._initializeItems()
		
	def getAutoIDs(self, activeDatabase):
		# Retrieve the autoIDs of viewConfigs that are registered on the activeDatabase string
		q = (qc.Query().Select(['vc.ViewConfigAutoID'])
					   .From('PowerTable.ViewConfig', 'vc')
					   .Join('PowerTable.ViewConfigRegisteredDatabase', 'PowerTable.ViewConfig', 'rdb', 'vc', 'rdb.ViewConfigAutoID = vc.ViewConfigAutoID')
					   .Join('Enum.[Database]', 'PowerTable.ViewConfigRegisteredDatabase', 'db', 'rdb', 'db.DatabaseAutoID = rdb.DatabaseAutoID')
					   .Where(['db.[Database] = ?']))
		data = q.execute([activeDatabase], dataBase=self.ADMIN_DB)
		return [row[0] for row in data]
		
	def _initializeItems(self):
		self._initializeRoot()
		for i, folder in enumerate(self.FOLDERS_DEFAULT):
			self.addFolder(folder, '0/{0}'.format(i))
		return self.items
	
	def _initializeRoot(self):
			t = component.Tree([])
			i = component.Icon(self.FOLDER_ICON_DEFAULT)
			self.items = t.addItem(self.ROOT_DEFAULT, '0', expanded=True, icon=i)
			return self.items
		
	def addFolder(self, name, path):
		# Extendeds the Tree().addItem() functionality by specifying icon
		t = component.Tree(self.items)
		i = component.Icon(self.FOLDER_ICON_DEFAULT)
		self.items = t.addItem(name, path, icon=i)
		return self.items
		
	def addView(self, name, path, data):
		# Extendeds the Tree().addItem() functionality by specifying icon
		t = component.Tree(self.items)
		i = component.Icon(self.VIEW_ICON_DEFAULT)
		self.items = t.addItem(name, path, data=data, icon=i)
		return self.items
		
	def moveView(self, currentPath, desPath):
		# Replicates the Tree().moveItem() functionality for PTTreeBrowser objs
		# Might want to validate that user is attempting to move view not folder...
		t = component.Tree(self.items)
		self.items = t.moveItem(currentPath, desPath)
		return self.items
		
	def getItemsFromAutoIDs(self, AutoIDs):
		# Get items to populate tree from list of AutoIDs
		values = self._getValuesFromAutoIDs(AutoIDs)
		for i, val in enumerate(values):
			self.addView(val['viewConfig'], val['Path'], val['ViewConfigAutoID'])
		return self.items
	
	# Decrement?
	def _getValuesFromAutoIDs(self, AutoIDs):
		# Get column values from list of AutoIDs
		table = db.Table(self.TABLE_DEFAULT, dataBase=self.ADMIN_DB)
		return [db.Row(table, AutoID).Values for AutoID in AutoIDs]
		
	def openViewPath(self, path):
		t = component.Tree(self.items)
		self.items = t.openItemPath(path)
		return self.items
		
	def setItemsCollapsed(self):
		t = component.Tree(self.items)
		return t.setItemsCollapsed()
		
	def getReadablePath(self, path):
		t = component.Tree(self.items)
		return t.getReadablePath(path)


class Grid(object):
	""" Grid object used in dashboard and viewcanvas. """
	
	def __init__(self, rowCount, columnCount):
		# Initializing the Grid's data (list of lists)
		self.data = [[0]*columnCount for _ in range(rowCount)]
		self.rowCount = rowCount
		self.columnCount = columnCount
	
	def addRectangle(self, x, y, width, length):
		self._addRemoveRectangle(x, y, width, length, 1)
		
	def removeRectangle(self, x, y, width, length):		
		self._addRemoveRectangle(x, y, width, length, 0)
		
	def _addRemoveRectangle(self, x, y, width, length, val):
		for i in range(x, (x + length)):
			for j in range(y, (y + width)):
				self.data[i][j] = val
				
	def clear(self):
		self.data = [[0]*self.columnCount for _ in range(self.rowCount)]
	
	def placeRectangle(self, width, length):
		startCell = self._findStartCell()
		# Check to see if rectangle will fit in that location
		rowStart, columnStart = startCell
		rowEnd = rowStart + length
		columnEnd = columnStart + width
		
		if columnEnd <= self.columnCount and rowEnd <= self.rowCount:
			self.addRectangle(rowStart, columnStart, width, length)
			topLeftCorner = (rowStart, columnStart)
		else:
			self.addRectangle(rowStart + length, 1, width, length)
			topLeftCorner = (rowStart + length, 1)
		return topLeftCorner
	
	def _findStartCell(self):
		for i in range(self.rowCount):
			for j in range(self.columnCount):
				if self.data[i][j] == 0:
					startCell = (i, j)
					return startCell
					

class SearchTextField(object):
	""" Search Text Field component object. """    
    
	def __init__(self, text, searchView, dataBase=None):		
		self.text = text 
		self.dataBase = util.getDatabaseObj(dataBase)
		self.searchView = db.Table(searchView, dataBase=self.dataBase.Name)
		self._isColumnSearch = False
		self._Column = None
		self._SearchText = None
		
		self._checkForColumnSearch()
    
	def getSearchIDs(self):
		from val import Error
		if self._isColumnSearch == True:
			self._Column, self._SearchText = self.getColumnAndText()
			if (self._Column != None) and (self._SearchText != None):
				whereClause = ["{0} = '{1}' AND {2} LIKE '{3}'".format(self.searchView.Columns[2].Name,
																	   self._Column,
																	   self.searchView.Columns[1].Name, 
												  					   _WildcardHandler(self._SearchText).getSQLString())]
			else:
				whereClause = ["{0} = '{1}'".format(self.searchView.Columns[2].Name, 
													self._Column)]
		
		else:
			whereClause = ["{0} LIKE '{1}'".format(self.searchView.Columns[1].Name, 
												   _WildcardHandler(self.text).getSQLString())]
		
		q = (Query()
			.Select([self.searchView.Columns[0].Name], distinct=True)
			.From(self.searchView.FullName)
			.Where(whereClause))
		results = q.execute(dataBase=self.dataBase.Name)
		if isinstance(results, Error):
			return results.Value
		return [result[0] for result in results]
	
	def _checkForColumnSearch(self):
		text = self.text
		if text.find("[column]:") == -1:
			self._isColumnSearch = False
		else:
			self._isColumnSearch = True
	
	def getColumnAndText(self):
		text = self.text.remove("[column]:")
		text = text.lstrip()
		splitText = text.split(" ", 1)
		if len(splitText) == 2:
			return splitText[0].lower(), splitText[1]
		elif len(splitText) == 1:
			return splitText[0].lower(), ""
		else:
			return None, None

class _WildcardHandler(object):
	""" Wildcard Handler for SearchTextField class. """    
	
	# Placeholders
	LITERAL_TILDE = "__TILDE__"    
	LITERAL_ASTERISK = "__ASTERISK__"    
	LITERAL_QUESTIONMARK = "__QUESTIONMARK__"    
	
	def __init__(self, text):
		self.text = text
			
	def getSQLString(self):
		text = self.text
		if text.endswith("~") and not text.endswith("~~"):
			text = text[0:text.rindex("~")]
		if text.find("~") == text.find("*") == text.find("?"):
			return '%{0}%'.format(text)
		else:
			text = self._transformTilde(text)
			text = self._transformAsterisk(text)
			text = self._transformQuestionMark(text)
			text = self._transformLiteral(text)
		return text
	
	def _transformTilde(self, text):
		while text.find("~") != -1:
			escapedCharacter = text[text.find("~") + 1]
			if escapedCharacter == "~":
				text = text.replace("~~", _WildcardHandler.LITERAL_TILDE)
			elif escapedCharacter == "*":
				text = text.replace("~*", _WildcardHandler.LITERAL_ASTERISK)
			elif escapedCharacter == "?":
				text = text.replace("~?", _WildcardHandler.LITERAL_QUESTIONMARK)
			else:
				text = text.replace("~{0}".format(escapedCharacter), "[{0}]".format(escapedCharacter))
		return text
		
	def _transformAsterisk(self, text):
		return text.replace("*", "%")
	
	def _transformQuestionMark(self, text):
		return text.replace("?", "_")
	
	def _transformLiteral(self, text):
		text = text.replace(_WildcardHandler.LITERAL_TILDE, "[~]")
		text = text.replace(_WildcardHandler.LITERAL_ASTERISK, "[*]")
		text = text.replace(_WildcardHandler.LITERAL_QUESTIONMARK, "[?]")
		return text
		
class UserDirectory(object):
	""" User directory custom component object. """
	# IN THE WORKS
	
	ROLE_TABLE_NAME = 'User.Role'
	USER_TABLE_NAME = 'User.User'
	USER_ROLE_TABLE_NAME = 'User.UserRole'
	ADMIN_DB = 'PRT_ADMIN'
	
	def __init__(self, instances):
		self._instances = instances
		self._userData = None
		self._userRoles = None
		
	@property
	def Instances(self):
		return self._instances if instances else self._getInstances()
		
	@property
	def Roles(self):
		table = db.Table(self.ROLE_TABLE_NAME)
		return [{'RoleAutoID': row[0],
			     'Role': row[1],
			     'Enabled': False}
			     for row in table.getAllRows()]
			     
	def _getInstances(self):
		# NEEDS WORK #
		query = """SELECT u.UserAutoID, u.Username, u.FirstName, u.LastName, u.Comment, u.Email, u.Phone, u.isDisabled, r.RoleAutoID, r.[Role] 
				   FROM [User].[UserRole] AS ur
				   LEFT JOIN [User].[User] AS u ON u.UserAutoID = ur.UserAutoID
				   LEFT JOIN [User].[Role] AS r ON r.RoleAutoID = ur.RoleAutoID"""
		data = system.db.runPrepQuery(query, [])
		
		# Need a way to set enabled to true if userAutoID has that role
		userParams = []
		userAutoIDs = []
		for i, row in enumerate(data):
			enabled = False if row['isDisabled'] else True 
			params = {'DisplayMode': '',
				      'InstanceID': 0,
				      'AutoID': row['UserAutoID'],
				      'Visible': enabled,
				      'Enabled': enabled,
				      'Text': {'Comment': row['Comment'],
				   			   'Email': row['Email'],
				   			   'Phone': row['Phone'],
				   			   'Username': row['Username'],
				   			   'FirstName': row['FirstName'],
				   			   'LastName': row['LastName']},
		   			  'Roles': roles}
		   	
		   	if row['UserAutoID'] in userAutoIDs:
		   		pass
		   	else:
		   		userAutoIDs.append(row['UserAutoID'])
		   		userParams.append(params)
		  
		
class UDInstance(object):
	""" User directory instance object. """
	
	PARAMS_TEMPLATE = {'DisplayMode': '',
					   'InstanceID': 0,
					   'AutoID': 0,
					   'Visible': True,
					   'Enabled': True,
					   'Text': {'Comment': '',
					   			'Email': '',
					   			'Phone': '',
					   			'Username': '',
					   			'FirstName': '',
					   			'LastName': ''},
			   			'Roles': [{'Role': '',
			   					   'RoleAutoID': 0,
			   					   'Enabled': True}]}
	
	def __init__(self, parameters=None):
		self.parameters = parameters if parameters else deepcopy(UDInstance.PARAMS_TEMPLATE)
	
	@property
	def Value(self):
		return FLXRInstance(self.parameters).Value


class AssetExplorer(object):
	""" Asset Explorer custom component object. """
	
	
	WIDGET_OBJS = [widget.AssetWidget, 
				   widget.TagsWidget, 
				   widget.AssetStatusWidget, 
				   widget.SystemWidget,
				   widget.UserFieldWidget,
				   widget.ProcurementWidget]
	
	def __init__(self, dataBase):
		self.dataBase = util.getDatabaseObj(dataBase)
		
	def getUserPins(self, username):
		from val import Error
		# Retrieve a user's pinned asset flxr instances
		q = qc.Query().Select(['AssetAutoID']).From('Asset.UserPin').Where(['Username = ?'])
		data = q.execute([username], dataBase=self.dataBase.Name)
		if isinstance(data, Error):
			return data.Value
		
		flxr = component.FlexRepeater()
		for row in data:
			params = {'AutoID': row['AssetAutoID']}
			flxr.addInstances(1, params)
		return flxr.Instances
		
	def getSearchItems(self, search):
		from val import Error
		# Get all search item instances from a search term
		q = (Query().Select(['agi.AutoID', 'agi.Title', 'agi.SubTitle'], distinct=True)
					.From('Asset.vAssetGalleryInstance', 'agi')
					.Join('dbo.vSearchKeywordsAsset', 'Asset.vAssetGalleryInstance', 'ask', 'agi', 'ask.SearchID = agi.AutoID')
					.Where(["ask.Keywords LIKE '%{0}%'".format(search)])
					.OrderBy(['agi.Title']))
		data = q.execute(dataBase=self.dataBase.Name)
		if isinstance(data, Error):
			return data.Value
		
		flxr = component.FlexRepeater()
		for row in data:
			params = {'AutoID': row['AutoID']}
			flxr.addInstances(1, params)
		return flxr.Instances
		
	def initializeInstances(self, AutoID):
		vwc = component.ViewCanvas()
		params = {'AssetAutoID': AutoID}
		for obj in self.WIDGET_OBJS:
			inst = component.VWCInstance(obj.VIEW_PATH, params)
			inst.setDimensions(obj.SUBVIEW_HEIGHT, obj.SUBVIEW_WIDTH)
			inst.setPosition(obj.SUBVIEW_TOP, obj.SUBVIEW_LEFT)
			vwc.addInstance(inst)
		return vwc.Instances
