import enums
from qc import Query


# Default settings
DATABASE_DEFAULT = 'PRT_DB'
SCHEMA_DEFAULT = 'dbo'
BRACKET_STRIP = '[]"\''


class Database(object):
	""" MSSQL Database object. """ 

	def __init__(self, dataBase=DATABASE_DEFAULT):
		self._dataBase = dataBase

	@property
	def Name(self):
		return self._dataBase


class Schema(object):
	""" Database Schema object. """

	def __init__(self, schema=SCHEMA_DEFAULT, dataBase=Database()):
		self._schema = schema
		self.dataBase = util.getDatabaseObj(dataBase)

	@property
	def Name(self):
		return self._schema


class Table(object):
	"""	Database Table object. """

	def __init__(self, table, dataBase=Database()):
		# Format string input
		if '.' in table:
			schema,_,table = table.partition('.')
			self.schema = Schema(schema.strip('[]"\''))
		self._table = table.strip('[]"\'')
		self.dataBase = util.getDatabaseObj(dataBase)
		# Validation, maybe run a few validation checks on intializing the table
		self.error = self._validate()
		# Cache
		self._columns = None
	
	@property
	def Name(self):
		return self._table

	@property
	def FullName(self):
		return '[{0}].[{1}]'.format(self.schema.Name, self.Name)

	@property
	def Alias(self):
		# Make smarter???
		return '[{0}]'.format(self.Name[0].lower())
	
	@property
	def Columns(self):
		# Cache column objects on instance.
		if not self._columns:
			self._columns = self._getColumns()
		return self._columns
		
	@property
	def ColumnHeaders(self):
		return [col.Name for col in self.Columns]
		
	@property
	def NonNullColumnHeaders(self):
		return [col.Name for col in self.Columns if col.isNonNull]
		
	@property
	def ExtendedProperties(self):
		return self._getExtendedProperties()
	
	@property
	def AutoIDColumnHeader(self):
		return next(col.Name for col in self.Columns 
					if col.IsAutoID)
					
	@property
	def UniqueIndices(self):
		# The unique indices configured on a table structured like this:
		# {'uniqueIndexName': [colObj1, colObj2, ...], ...}
		q = (Query().Select(['i.[name] AS [Index]', "STRING_AGG(c.[name], ', ') AS [Column]"])
					.From('sys.schemas', 's')
					.Join('sys.tables', childAlias='t', ON='t.schema_id = s.schema_id')
					.Join('sys.columns', 'sys.tables', 'c', 't', 'c.object_id = t.object_id')
					.Join('sys.indexes', 'sys.tables', 'i', 't', 'i.object_id = t.object_id AND i.is_primary_key = 0 AND i.is_unique = 1')
					.Join('sys.index_columns', 'sys.tables', 'ic', 't', 'ic.object_id = t.object_id AND ic.column_id = c.column_id')
					.Where(['s.[name] = ?', 't.[name] = ?'])
					.GroupBy(['i.[name]']))
		data = q.execute([self.schema.Name, self.Name], dataBase=self.dataBase.Name)
		return {row['Index']: [Column(self, col) for col in row['Column'].split(', ')] for row in data}
	
	@property
	def PrimaryIDColumnHeader(self):
		# 'Primary ID' is the 'most important' column in a table that best 
		# represents the data a row in the table is contributing. This is an
		# extended property configured on the column in SSMS.
		return next(col.Name for col in self.Columns
					if enums.ExtProps.IsPrimaryID.value in col.ExtendedProperties)
					
	@property
	def ComputedIDColumnHeader(self):
		for col in self.Columns:
			if col.IsComputedID:
				return col.Name
		return None
	
	@property
	def IsOneToMany(self):
		# Extended property configured on a table in SSMS to describe if the
		# parent table can have repeated auto IDs in this child table.
		return enums.ExtProps.IsOneToMany.value in self.ExtendedProperties
		
	def _validate(self):
		# Check 1: Table exists in active db
		return None
		
	def _getColumns(self):
		from val import Error
		# Query to retrieve the columns configured on a table.
		q = (Query().Select(['COLUMN_NAME'])
			        .From('INFORMATION_SCHEMA.COLUMNS')
				    .Where(['TABLE_NAME = ?', 'TABLE_SCHEMA = ?']))
		data = q.execute([self.Name, self.schema.Name], dataBase=self.dataBase.Name)
		print(data)
		# Expecting PyDataset but catches val.Error type.
		if isinstance(data, Error):
			return data
		return [Column(self, row[0]) for row in data]
	    
	def _getExtendedProperties(self):
		from val import Error
		# Query to retrieve the extended properties configured on the table.
		q = (Query().Select()
			  		.From('dbo.vTableExtendedProperties')
			  		.Where(['TableSchema = ?', 'TableName = ?']))
		data = q.execute([self.schema.Name, self.Name], dataBase=self.dataBase.Name)
		# Expecting PyDataset but catches val.Error type.
		if isinstance(data, Error):
			return data
		return {row['ExtendedPropertyName']: row['ExtendedPropertyValue'] 
				for row in data}
	
	def getAllRows(self):
		# Query to return all rows and all columns from the table.
		q = Query().Select().From(self.FullName)
		return q.execute(dataBase=self.dataBase.Name)
		
	def getRowCount(self):
		from val import Error
		# Get the number of rows a table currently has.
		q = Query().Select(['COUNT(*)']).From(self.FullName)
		data = q.execute(dataBase=self.dataBase.Name)
		# Expecting PyDataset but catches val.Error type
		if isinstance(data, Error):
			return data.Value
		return data[0][0]
		
	def getRow(self, autoID):
		# Get the row object of a table given an AutoID
		return Row(self, autoID)
		
	def getRows(self, filters):
		q = (Query().Select([self.AutoIDColumnHeader])
					.From(self.FullName)
					.Where(filters=filters))
		data = q.execute(dataBase=self.dataBase.Name)
		return [Row(self, row[self.AutoIDColumnHeader]) for row in data]
	
	def getPrimaryIDForAutoID(self, autoID):
		# Get the primary ID of a single row from it's AutoID
		return Row(self, autoID).PrimaryID
		
	def getChildren(self):
		# NOT WORKING QUITE RIGHT...
		
		# Query to retrieve the children tables of the table object.
		# Should be contructed using 'qc' library eventually...
		query = 'EXEC sp_fkeys @pktable_name = ?, @pktable_owner = ?'
		data = system.db.runPrepQuery(query, [self.Name, self.schema.Name], self.dataBase.Name)
		if data.getRowCount() <= 0:
			return []
		return ['{0}.{1}'.format(row['FKTABLE_OWNER'], row['FKTABLE_NAME'])
				for row in data if row['FKTABLE_OWNER'] == self.schema.Name]
				
	def getParents(self):
		# NOT WORKING QUITE RIGHT...
		
		# Query to retrieve the parent tables of the table object.
		# Should be contructed using 'qc' library eventually...
		query = 'EXEC sp_fkeys @fktable_name = ?, @fktable_owner = ?'
		data = system.db.runPrepQuery(query, [self.Name, self.schema.Name], self.dataBase.Name)
		
		if data.getRowCount() <= 0:
			return []
		
		return ['{0}.{1}'.format(row['PKTABLE_OWNER'], row['PKTABLE_NAME'])
				for row in data if row['PKTABLE_OWNER'] == self.schema.Name] 
	
	# Status of these? Decrement?
################################################################################			
	def getCascadingChildData(self, autoID):
		# Stored procedure that retrieves the table, select query, and rows affected for a child 
		# table if a row from the parent table (autoID) was to be deleted.
		call = system.db.createSProcCall('spCascadingChildren')
		call.registerInParam('ParentTable', system.db.NVARCHAR, self.FullName)
		call.registerInParam('ParentAutoIDColumnHeader', system.db.NVARCHAR, self.AutoIDColumnHeader)
		call.registerInParam('Criteria', system.db.NVARCHAR, '={0}'.format(autoID))
		system.db.execSProcCall(call)
		ds = call.getResultSet()
		data = system.dataset.toPyDataSet(ds)
		
		# Filtering out the 1 parent row affected and children tables with 
		# no rows affected
		return [[data[i]['FullTableName'], data[i]['SelectQuery'], data[i]['RowsAffected']]
				for i in range(data.getRowCount())
				if data[i]['FullTableName'] != self.FullName and data[i]['RowsAffected'] != 0]
		
	def getDeleteRowAffectedTables(self, autoID, items, rowsAffected):
		# Recursive algorithim to find all the tables and rows affected if a parent 
		# table row were to be deleted and cascading delete was on.
		
		data = self.getCascadingChildData(autoID)
		if len(data) == 0:
			return items, rowsAffected
		else:
			for i in range(len(data)):
				newItem = {"label": "{0} ({1} rows)".format(data[i][0], data[i][2]),
							"expanded": True,
							"data":{},
							"items":[]}
				items.append(newItem)
				rowsAffected += int(data[i][2])
				childTable = db.Table(data[i][0])
				query = data[i][1]
				childData = system.db.runPrepQuery(query, [], self.db.Name)
				for j in range(childData.getRowCount()):
					# Passing in the children AutoIDs
					_, rowsAffected = childTable.getDeleteRowAffectedTables(childData[j][0], items[i]["items"], rowsAffected)
			return items, rowsAffected
		
	def searchChildren(self, autoID):
		# Using the spCascadingChildren stored procedure to see the children 
		# table's that have parent AutoID present
		childAutoIDs = {}
		data = self.getCascadingChildData(autoID)
		for i in range(len(data)):
			# Access the Select Query returned from the stored procedure
			query = data[i][1]
			results = system.db.runPrepQuery(query, [], self.db.Name)
			# Format to fit childAutoIDs' return format
			child = db.Table(data[i][0])
			# Format fullTableName to not have brackets
			fullTableName = "{0}.{1}".format(child.schema.Name, child.Name)
			childAutoIDs[fullTableName] = [results[j][child.AutoIDColumnHeader] 
											for j in range(results.getRowCount())]
		return childAutoIDs
################################################################################


class Column(object):
	"""	Table Column object. """
	
	DEFAULT_CHARACTER_MAX = 50
	
	def __init__(self, table, column):
		# Column object attributes
		self._column = column
		self.table = table
		# Make more lightweight???
		self.dataType, self.characterMax, self.isNonNull = self._getColumnType()
	
	@property 
	def Name(self):
		return self._column
		
	@property
	def ExtendedProperties(self):
		from val import Error
		# Query to retrieve the extended properties configured on the column.
		q = (Query().Select()
			 		.From('dbo.vColumnExtendedProperties')
			 		.Where(['TableSchema = ?', 'TableName = ?', 'ColumnName = ?']))
		data = q.execute([self.table.schema.Name, self.table.Name, self.Name], self.table.dataBase.Name)
		# Expecting PyDataset but cathces val.Error type.
		if isinstance(data, Error):
			return data.Value
		return {data[i]['ExtendedPropertyName']: data[i]['ExtendedPropertyValue'] 
				for i in range(data.getRowCount())}
		
	@property
	def IsForeignKey(self):
		from val import Error
		result = self.getFKReference()
		return result.Value if isinstance(result, Error) else bool(result)

	@property
	def IsAutoID(self):
		return enums.ExtProps.IsAutoID.value in self.ExtendedProperties
		
	@property
	def IsComputedID(self):
		q = Query().Select(["COLUMNPROPERTY(OBJECT_ID('{0}'), '{1}', 'IsComputed') AS [Computed]".format(self.table.FullName, self.Name)])
		data = q.execute(dataBase = self.table.dataBase.Name)
		return bool(data[0]['Computed'])
		
		
	def getFKReference(self):
		from val import Error
		# Returns the referenced table if is a FK column.
		q = (Query().Select(['sch2.[name] AS [referenced_schema]', 'tbl2.[name] AS [referenced_table]'])
					.From('sys.foreign_key_columns', 'fkc')
					.Join('sys.objects', 'sys.foreign_key_columns', 'obj', 'fkc', 'obj.object_id = fkc.constraint_object_id')
					.Join('sys.tables', 'sys.foreign_key_columns', 'tbl1', 'fkc', 'tbl1.object_id = fkc.parent_object_id')
					.Join('sys.schemas', 'sys.tables', 'sch1', 'tbl1', 'sch1.schema_id = tbl1.schema_id')
					.Join('sys.columns', 'sys.tables', 'col1', 'tbl1', 'col1.column_id = parent_column_id AND col1.object_id = tbl1.object_id')
					.Join('sys.tables', 'sys.foreign_key_columns', 'tbl2', 'fkc', 'tbl2.object_id = fkc.referenced_object_id')
					.Join('sys.schemas', 'sys.tables', 'sch2', 'tbl2', 'sch2.schema_id = tbl2.schema_id')
					.Join('sys.columns', 'sys.tables', 'col2', 'tbl2', 'col2.column_id = referenced_column_id AND col2.object_id = tbl2.object_id')
					.Where(['sch1.[name] = ?', 'tbl1.[name] = ?', 'col1.[name] = ?']))
		data = q.execute([self.table.schema.Name, self.table.Name, self.Name], self.table.dataBase.Name)
		if isinstance(data, Error):
			return data.Value
		return '{0}.{1}'.format(data[0]['referenced_schema'], data[0]['referenced_table']) if data else None
	
	def _getColumnType(self):
		from val import Error
		# Query to retrieve the data type stored in the column, the max 
		# character lengh of entries, and whether the column is nullable.
		q = (Query().Select(['DATA_TYPE', 'CHARACTER_MAXIMUM_LENGTH', 'IS_NULLABLE'])
			 		.From('INFORMATION_SCHEMA.COLUMNS')
				 	.Where(['TABLE_SCHEMA = ?', 'TABLE_NAME = ?', 'COLUMN_NAME = ?']))
		data = q.execute([self.table.schema.Name, self.table.Name, self.Name], self.table.dataBase.Name)
		# Expecting PyDataset but cathces val.Error type.
		if isinstance(data, Error):
			return data.Value
		return (data[0]['DATA_TYPE'], 
			    self.DEFAULT_CHARACTER_MAX if data[0]['CHARACTER_MAXIMUM_LENGTH'] == -1 
			    						   else data[0]['CHARACTER_MAXIMUM_LENGTH'], 
			    False if data[0]['IS_NULLABLE'] == 'YES' else True)


class Row(object):
	""" Table Row object. """
	
	RETURN_BOOL_COLUMNS = ['IsDisabled']
	
	def __init__(self, table, autoID=None, filters=None):
		# Table object the row is a part of
		self.table = table
		# Option to find the desired row using {column: value} filters
		self._filters = filters
		# AutoID to specify which row to access in the table
		self._autoID = autoID if autoID else self._getAutoIDFromFilters()
		
	@property 
	def AutoID(self):
		return self._autoID
	
	@property
	def Values(self):
		# A dictionary with the column headers as keys and the data as the 
		# values.
		if self._autoID or self._filters:
			return self._getValues()
		return self.EmptyDict
	
	@property
	def Exists(self):
		return bool(self._autoID)
	
	@property
	def PrimaryIDColumnHeader(self):
		return self.table.PrimaryIDColumnHeader
		
	@property
	def PrimaryID(self):
		return self.Values[self.PrimaryIDColumnHeader]
				
	@property
	def Columns(self):
		return self.table.Columns
		
	@property
	def ColumnHeaders(self):
		return self.table.ColumnHeaders
		
	@property
	def EmptyList(self):
		return ['' for i in range(len(self.Columns))]
	
	@property	
	def EmptyDict(self):
		return {col.Name: '' for col in self.Columns}
		
	@property
	def EmptyPyDataSet(self):
		data = system.dataset.toDataSet(self.ColumnHeaders, [self.EmptyList])
		return system.dataset.toPyDataSet(data)
	
	def _getValues(self):
		from val import Error
		# Query to retieve the data for the row.
		q = (Query().Select()
					.From(self.table.FullName)
					.Where(['{0} = ?'.format(self.table.AutoIDColumnHeader)]))
		data = q.execute([self.AutoID], self.table.dataBase.Name)
		
		# Expecting PyDataset but cathces val.Error type.
		if isinstance(data, Error):
			return data.Value
		if data:
			return {col.Name: (data[0][i] if data[0][i] or col.Name in self.RETURN_BOOL_COLUMNS else '') 
					for i, col in enumerate(self.Columns)}
		return self.EmptyDict
		
	def _getAutoIDFromFilters(self):
		from val import Error
		if self._filters:
			q = (Query().Select()
						.From(self.table.FullName)
						.Where(['[{0}] = ?'.format(col) for col in self._filters]))
			data = q.execute([value for value in self._filters.values()], self.table.dataBase.Name)
			if isinstance(data, Error):
				return data.Value
			return data[0][self.table.AutoIDColumnHeader] if data else None
		return None
	
	def _validateCRUD(self, values):
		# Database create, update, and delete validation method. This method 
		# parses the values attempting to be pushed to the db for errors and 
		# warnings.

		# Handled Failure 1: See if values has any empty NonNull fields
		emptyNonNullFields = [field for field in values.keys() 
		                      if (not values[field]
		                          and field in self.table.NonNullColumnHeaders
		                          and field not in [self.table.AutoIDColumnHeader,
		                          					'DateCreated',
		                          					'isBaseTable',
		                          					'isDisabled'])]
		if emptyNonNullFields:
			emptyFields = ', '.join(emptyNonNullFields)
			# Might want to return error object rather than dict...
			return Error(enums.Message.HANDLED_FAILURE.value, 
						 'Table {0} requires values for {1}'.format(self.table.FullName, 
							 										emptyFields))
		                             
	   
		# Potential check 2 (warning): See if there is no change to 'values' 
		return None
	
	def _filterValues(self, values):
		# Filter out the auto-populating fields for CRUD events.
		return {col: value for col, value in values.items()
				if col not in [self.table.AutoIDColumnHeader, 
							   self.table.ComputedIDColumnHeader, 
							   'isBaseTable', 'DateCreated']}
	
	def create(self, values):
		from val import Error
		# @@NEEDS_BUSINESS_LOGIC@@
		# Create a new row in the parent table. This method also return the 
		# auto ID it just created.

		# Validation checks.
		if self.AutoID:
			return 'Row already exsits in {0}'.format(self.table.FullName)
		error = self._validateCRUD(values)
		if isinstance(error, Error):
			return error.Value
			
		# Step 1: Query to insert the values into the database.
		inserts = self._filterValues(values)	
		q = (Query().Insert(self.table.FullName, 
							inserts))
		args = [value for value in inserts.values() 
				if not util.isNullValue(value)]
		result = q.execute(args, self.table.dataBase.Name)
		# Expecting PyDataset but cathces val.Error type.
		if isinstance(result, Error):
			return result.Value
			
		# Step 2: Get the AutoID of the row just inserted using a select statement.
		q = (Query().Select([self.table.AutoIDColumnHeader])
					.From(self.table.FullName)
					.Where(filters=inserts))
		data = q.execute(dataBase=self.table.dataBase.Name)
		# Expecting PyDataset but cathces val.Error type.
		if isinstance(result, Error):
			return result.Value
		
		system.perspective.print(data)
		self.autoID = data[0][self.table.AutoIDColumnHeader]
			
		return self.autoID
		
	def update(self, values):
		# @@NEEDS_BUSINESS_LOGIC@@
		# Make modifications to existing data in a row.

		# Validation checks.
		error = self._validateCRUD(values)
		if error:
			return error
		# Query to update the row in the database.
		updates = self._filterValues(values)	  
		q = (Query().Update(self.table.FullName)
					.Set(updates)
					.Where(['[{0}] = ?'.format(self.table.AutoIDColumnHeader)]))
		args = [value for value in updates.values() 
		        if not util.isNullValue(value)]
		args.append(self.AutoID)
		return q.execute(args, self.table.dataBase.Name)			  
		
	def delete(self):
		# @@NEEDS_BUSINESS_LOGIC@@
		# Delete a row from a table in the database.
		q = (Query().Delete(self.table.FullName)
					.Where(['{0} = ?'.format(self.table.AutoIDColumnHeader)]))
		return q.execute([self.AutoID], self.table.dataBase.Name)
