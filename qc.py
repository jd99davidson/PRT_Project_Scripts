# Explicit dependencies
import enums
from val import Error


class Statement(object):
	""" Parent class for all Query statement objects. """
	
	def __init__(self):
		# Expecting None but catches Error obj
		self._error = self._validate()		
		
	@property
	def Statement(self):
		# If there is an error return that, 
		# else call getStatement() method.
		if isinstance(self._error, Error):
			return self._error
		return self._getStatement()
	
	def _getStatement(self):
		# Placeholder overridden by subclasses. 
		# This only runs if class that inherits from Statement
		# doesn't have a _getStatement() method.
		return 'No subclass statement provided.'
		
	def _validate(self):
		# Placeholder overridden by subclasses. 
		# This only runs if class that inherits from Statement
		# doesn't have a _validate() method.
		return None


class Delete(Statement):
	""" Delete statement object. """
	
	def __init__(self, table):
		# Class table object, don't need to define dataBase bc its not used
		self.table = db.Table(table)
		# Inherit from statement class	
		super(Delete, self).__init__()		
	
	def _getStatement(self):
		return 'DELETE FROM {0}'.format(self.table.FullName)
	
	def _validate(self):
		return None


class Insert(Statement):
	""" Insert statement object. """
	
	def __init__(self, table, values, output=None):
		# Class table object
		self.table = db.Table(table)
		# Values dictionary {columns: values}	
		self.values = values
		# Column string to return on execute()		
		self.output = output
		# Inherit from statement class		
		super(Insert, self).__init__()
	
	def _getStatement(self):
		# Format and concatenate the clauses in the Insert statement
		return ('INSERT INTO {0} ({1}){2} VALUES ({3})'
				.format(self.table.FullName, 
				   		self._getColumnString(self.values.keys()), 
				   		self._getOutputInsertedString(), 
				   		self._getValuesString()))
				 	
	def _validate(self):
		return None
				   		
	def _getColumnString(self, columns):
		# Format the column string with brackets and comma sepearation
		return ', '.join('[{0}]'.format(col.strip(db.BRACKET_STRIP)) for col in columns)
		
	def _getValuesString(self):
		# Format the values from the dictionary parameter, catching
		# NULL values. The '?' is a wildcard parameter used in runPrepQuery().
		return ', '.join('NULL' 
						 if util.isNullValue(value)
						 else '?'
				 		 for value in self.values.values())
				 		 
	def _getOutputInsertedString(self):
		# The 'OUTPUT INSERTED' clause allows for the user to specify a column
		# to be returned from the updated table being inserted into. 
		if self.output:
			return ' OUTPUT INSERTED.{0}'.format(self._getColumnString(self.output))
		return ''


class Update(Statement):
	""" Update statement object. """
	
	def __init__(self, table):
		# Class table object
		self.table = db.Table(table)
		# Inherit from statement class
		super(Update, self).__init__()
	
	def _getStatement(self):
		return 'UPDATE {0}'.format(self.table.FullName)
	
	def _validate(self):
		return None


class Set(Statement):
	""" Set statement object. """
	
	def __init__(self, values):
		# Values dictionary {column: values}
		self.values = values
		# Inherit from statement class
		super(Set, self).__init__()
	
	def _getStatement(self):
		return 'SET {0}'.format(self._getSetString())
		
	def _getSetString(self):
		# Format the SET clause, catching NULL values and using
		# the runPrepQuery() dynamic argument wildcard '?'. 
		# Also strippinging the columns of brackets incase values
		# parameter has columns with brackets.
		return ', '.join('[{0}] = NULL'.format(col.strip(db.BRACKET_STRIP))
						 if util.isNullValue(value)
						 else '[{0}] = ?'.format(col.strip(db.BRACKET_STRIP))
						 for col, value in self.values.items())
	
	def _validate(self):
		return None


class Select(Statement):
	""" Select statement object. """
	
	def __init__(self, columns=None, distinct=False, top=None):  
		# List of columns (must be aliased if to be used alongside Join obj)  
	    self.columns = columns
	    # Boolean to tell if 'DISTICNT' key word ought be included.
	    self.distinct = distinct
		# Integer to be included in 'TOP' clause to retrieve first # of rows
	    self.top = top
	    # Inherit from Statement class
	    super(Select, self).__init__()
	        
	def _getStatement(self):
		# Format and concatenate each clause
		return 'SELECT{0}{1}{2}'.format(
					self._getDistinctString(), 
					self._getTopString(), 
					' {0}'.format(self._getFieldsString()))
		
	def _validate(self):
	    """Validate column inputs."""
	    # Check 1: Check to see if columns are aliased
	    aliased = False
	    for column in self.columns:	
	    	if '.' in column:
	    		aliased = True
	    	if aliased and '.' not in column:
	    		return Error(enums.Message.HANDLED_FAILURE.value, 
	    					 'All columns must be aliased.')
	    		
	    # Potential Check 2: Make sure columns exist
	    return None
	
	def _getFieldsString(self):
		# Returning the columns to display, default is all ('*')
	    return ', '.join(self.columns) if self.columns else '*'
	
	def _getTopString(self):
		# Returning the TOP clause to retrieve a restricted number
		# of results.
		return ' TOP {0}'.format(self.top) if self.top else ''
		
	def _getDistinctString(self):
		# Returning the DISTINCT clause to return only records whose
		# column values (when considered together) are all unique.
		return ' DISTINCT' if self.distinct else ''


class From(Statement):	
	""" From statement object. """
	
	def __init__(self, table, alias=None):
		# Instatiate a table object and inherit from Statement
		self.table = db.Table(table)
		# Store optional alias parameter
		self.alias = alias
		# Inherit from Statement class
		super(From, self).__init__()
	
	def _getStatement(self):
		if self.alias:
			return 'FROM {0} AS {1}'.format(self.table.FullName, self.alias)
		return 'FROM {0}'.format(self.table.FullName)
	
	def _validate(self):
		return None


class Join(Statement):
	""" Join statement object. """
	
	def __init__(self, childTable, parentTable, childAlias=None, parentAlias=None, ON=None, joinType=enums.JoinType.inner.value):
		# Table class object for table to be joined
	    self.childTable = db.Table(childTable)
	    # Table class object for table being joined on
	    self.parentTable = db.Table(parentTable)
	    self.childAlias = childAlias if childAlias else self.childTable.Alias
	    self.parentAlias = parentAlias if parentAlias else self.parentTable.Alias
	    self.ON = ON if ON else self._getONClause()
	    self.joinType = joinType
	    super(Join, self).__init__()
					
	def _getStatement(self):
		return '{0} {1} AS {2} ON {3}'.format(self._getJoinTypeString(), self.childTable.FullName, self.childAlias, self.ON)
	
	def _validate(self):
		# Make sure 'ON' clause is appropriate (not aliased wrong, columns exist, columns have FK constraint)
		# Make sure data is returned from _getColumnsToJoinOn...
		return None
		
	def _getJoinTypeString(self):
		return ' '.join([self.joinType, 'JOIN'])
	
	def _getONClause(self):
		childColumn, parentColumn = self._getOnColumns()
		return '{0}.[{1}] = {2}.[{3}]'.format(self.childAlias, childColumn, self.parentAlias, parentColumn)
		
	def _getOnColumns(self):
		# Query to get the fk relationship table between table 1 and 2
	    query = """SELECT rc.[name] AS [Child Column], pc.[name] AS [Parent Column]
                   FROM sys.foreign_keys AS fk
                   JOIN sys.tables AS pt ON pt.object_id = fk.parent_object_id
                   JOIN sys.tables AS rt ON rt.object_id = fk.referenced_object_id
                   JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id = fk.object_id
                   JOIN sys.columns pc ON pc.column_id = fkc.parent_column_id AND pc.object_id = fkc.parent_object_id
                   JOIN sys.columns rc ON rc.column_id = fkc.referenced_column_id AND rc.object_id = fkc.referenced_object_id
                   WHERE (pt.[name] = ? AND rt.[name] = ?) OR (pt.[name] = ? AND rt.[name] = ?)"""
	    args = [self.parentTable.Name, self.childTable.Name, self.childTable.Name, self.parentTable.Name] 
	    data = system.db.runPrepQuery(query, args)
	    return data[0]['Child Column'], data[0]['Parent Column']


class Where(Statement):
	""" Where statement object. """
	# Write method to convert dictionary to appropriate clauses
	
	def __init__(self, clauses=None, filters=None):
		# Dictionary of filters to construct where clauses on
		self.filters = filters
		# List of string clauses
		self.clauses = clauses if clauses else self._getClauses()
		super(Where, self).__init__()
		
	def _getStatement(self):
		return 'WHERE {0}'.format(self._getFiltersString())
	
	def _validate(self):
	    return None
	    
	def _getFiltersString(self):
		return ' AND '.join(self.clauses) if self.clauses else ''
	
	def _getClauses(self):
		return [("[{0}] = '{1}'".format(key, value) if value else '[{0}] IS NULL'.format(key)) 
				for key, value in self.filters.items()]


class OrderBy(Statement):
	""" Order by statement object. """
	
	def __init__(self, columns, DESC=False):
		self.columns = columns
		self.DESC = DESC
		super(OrderBy, self).__init__()
		
	def _getStatement(self):
		if self.DESC:
			return 'ORDER BY {0} DESC'.format(self._getFieldsString())
		return 'ORDER BY {0}'.format(self._getFieldsString())
		
	def _getFieldsString(self):
		return ', '.join(self.columns)
		
class GroupBy(Statement):
	""" Group by statement object. """
	
	def __init__(self, columns):
		self.columns = columns
		super(GroupBy, self).__init__()
		
	def _getStatement(self):
		return 'GROUP BY {0}'.format(self._getFieldsString())
		
	def _getFieldsString(self):
		return ', '.join(self.columns)
	pass


class Offset(Statement):
	""" Offset statement object. """
	
	def __init__(self, num):
		self.num = num
		super(Offset, self).__init__()
		
	def _getStatement(self):
		return 'OFFSET {0} ROWS'.format(self.num)
		
	def _validate(self):
		return None


class Fetch(Statement):
	""" Fetch statement object. """
	
	def __init__(self, num):
		self.num = num
		super(Fetch, self).__init__()
		
	def _getStatement(self):
		return 'FETCH NEXT {0} ROWS ONLY'.format(self.num)
		
	def _validate(self):
		return None


class Union(object):
	""" Union statement object. """
	# TODO!
	# Option to union two Query objs?
	# Rules: 1) Each select statement unioned together must have same number of columns.
	#		 2) Columns must have the same data type.
	#		 3) Columns must be in the same order. 
	
	def __init__(self, queries=None, ALL=False):
		self.queries = queries if queries else []
		self.ALL = ALL
		
	def _getStatement(self):
		pass
		
	def _validate(self):
		pass


class Query(object):
	""" Query master class object. """
	
	def __init__(self):
		# Statement objects (ordered)
		self._statementObjs = []
		# Query validation 
		self._error = None
		
	@property
	def Query(self):
		self._error = self._validate()
		if isinstance(self._error, Error):
			return self._error
		return ' '.join(obj.Statement for obj in self._statementObjs)
		
	@property
	def BaseStatement(self):
		return self._statementObjs[0]
		
	def _validate(self):
		# Check 1: Make sure objects didn't return an error (assign query object child object's error)
		for obj in self._statementObjs:
			if isinstance(obj._error, Error):
				return obj._error
		
		# Check 2: Union statement returns same number of columns as parent clause.
		return None
	
	def Delete(self, table):
		self._statementObjs.append(Delete(table))
		return self
	
	def Insert(self, table, values, output=None): 
		self._statementObjs.append(Insert(table, values, output))
		return self
	
	def Update(self, table):
		self._statementObjs.append(Update(table))
		return self
		
	def Set(self, values):
		self._statementObjs.append(Set(values))
		return self
		
	def Select(self, columns=[], distinct=False, top=''):
		self._statementObjs.append(Select(columns, distinct, top))
		return self
		
	def From(self, table, alias=''):
		self._statementObjs.append(From(table, alias))
		return self
	
	# Move parameters around to make more intuitive? 
	def Join(self, childTable, parentTable=None, childAlias=None, parentAlias=None, ON=None, joinType=enums.JoinType.inner.value):
		if parentTable is None:
			parentTable = next(obj.table.Name for obj in self._statementObjs
							   if isinstance(obj, From))
		self._statementObjs.append(Join(childTable, parentTable, childAlias, parentAlias, ON, joinType))
		return self
		
	def Where(self, clauses=None, filters=None):
		self._statementObjs.append(Where(clauses, filters))
		return self
		
	def Union(self, query):
		# TODO! What is the best approach here?
		pass
		
	def OrderBy(self, columns, DESC=False):
		self._statementObjs.append(OrderBy(columns, DESC))
		return self
		
	def GroupBy(self, columns):
		self._statementObjs.append(GroupBy(columns))
		return self
		
	def Offset(self, num):
		self._statementObjs.append(Offset(num))
		return self
	
	def Fetch(self, num):
		self._statementObjs.append(Fetch(num))
		return self
	
	def paginate(self, orderBy, rowsPerPage, currentPage):
		self.OrderBy(orderBy)
		self.Offset((currentPage - 1)*rowsPerPage)
		self.Fetch(rowsPerPage)
		return self
	
	def execute(self, args=[], dataBase='PRT_DB', NamedQuery=False):
		# @@NEEDS_BUSINESS_LOGIC@@
		# NOT DONE
		# Validating after all the statement object methods have been 
		# ran on the query object.
		self._error = self._validate()
		if isinstance(self._error, Error):
			return self._error
		
		# Unhandled failure handling.	
		try:
			if NamedQuery:
				data = system.db.runNamedQuery('Util/Generic', {'Query': self.insertArgsIntoQuery(args),
																'database': dataBase})
				return system.dataset.toPyDataSet(data)
			# Using runPrepUpdate() for queries of type update, delete, and insert.
			if isinstance(self.BaseStatement, (Update, Delete, Insert)):
				# If insert statement has OUPUT INSERTED clause, use runPrepQuery
				if isinstance(self.BaseStatement, Insert):
					if self.BaseStatement.output:
						return system.db.runPrepQuery(self.Query, args, dataBase)
				# Returns the number of rows affected.
				return system.db.runPrepUpdate(self.Query, args, dataBase)
			else:
				return system.db.runPrepQuery(self.Query, args, dataBase)
		except:
			return Error(enums.Message.UNHANDLED_FAILURE.value, 
						 'Query "{0}" against {1} could not compile.'.format(self.insertArgsIntoQuery(args), dataBase))
	
	def insertArgsIntoQuery(self, args):
		# Artificial replacement of '?' with args value (does not change object Statements, 
		# merely returns a modified string)
		q = self.Query
		for arg in args:
			q = q.replace('?', "'{0}'".format(str(arg)), 1)
		return q
