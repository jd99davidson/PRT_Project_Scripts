# Validation script
from copy import deepcopy


class Error(object):
	""" Error class object. """
	
	def __init__(self, type_, message):
		self.type_ = type_
		self.message = message
		
	def __str__(self):
		return str(self.Value)
		
	@property
	def Value(self):
		return {self.type_: self.message}


class Warning(object):
	"""" Warning class object. """
	
	def __init__(self, message):
		self.message = message
		
	def __str__(self):
		return str(self.Value)
		
	def __add__(self, obj):
		if isinstance(obj, WarningGroup):
			return WarningGroup(obj.warnings.append(obj))
		return Warning(self.message + obj.message)
		
	@property
	def Value(self):
		return {enums.Message.WARNING.value: self.message}


class WarningGroup(object):
	"""" Warning Group class object. """
	
	def __init__(self, warnings=None):
		self.warnings = warnings if warnings else []
		
	def __str__(self):
		return str(self.Value)
		
	def __len__(self):
		return len(self.warnings)
		
	def __add__(self, obj):
		# Distinct from addWarning in that it creates a new
		# WarningGroup
		if isinstance(obj, Warning):
			warningsCopy = deepcopy(self.warnings)
			warningsCopy.append(obj)
			return WarningGroup(warningsCopy)
		return WarningGroup(self.warnings + obj.warnings)
	
	@property
	def Values(self):
		return [warning.Value for warning in self.warnings]
		
	def addWarning(self, warningObj):
		self.warnings.append(warningObj)
		return self.warnings


class ValidationHandler(object):
	""" Validation handler object. """
	
	def __init__(self, values, table):
		self.values = values
		self.table = table
		self.dataBase = self.table.dataBase
		
	@property
	def Row(self):
		return db.Row(self.table, filters=self.values)
		
	def validateCreate(self):
		# Can return either val.Error types, val.WarningGroup, or None
		
		# Universal validation that applies to all tables
		result = self.validateUniversalFailures()
		if isinstance(result, val.Error):
			return result
			
		if self.table.FullName == '[Asset].[Asset]':
			return self._validateAssetCreate()
		
		return None
		
	def validateUpdate(self):
		# Can return either val.Error, val.WarningGroup, or None
		
		# Universal validation that applies to all tables
		result = self.validateUniversalFailures()
		if isinstance(result, val.Error):
			return result
		
		return None
		
	def validateDelete(self):
		return None
		
	def validateUniversalFailures(self):
		result = self._validateUniqueIndices()
		if isinstance(result, val.Error):
			return result
		result = self._validateNonNullFields()
		if isinstance(result, val.Error):
			return result
		
	def _validateUniqueIndices(self):
		# Need this validation for each table for both create and update
		# How to do this without comparing the UI index values in self.values 
		# to EVERY UI instance in the table?
		for index, columns in self.table.UniqueIndices.items():
			pass
		return None
		
	def _validateNonNullFields(self):
		# Need this validation for each table for both create and update
		# Check to make self.values isn't trying to push empty Non null fields to db
		emptyNonNullFields = [field for field in self.values 
		                      if (not self.values[field]
		                          and field in self.table.NonNullColumnHeaders
		                          and field not in [self.table.AutoIDColumnHeader,
		                          					'DateCreated',
		                          					'isBaseTable',
		                          					'isDisabled'])]
		if emptyNonNullFields:
			emptyFields = ', '.join(emptyNonNullFields)
			return val.Error(enums.Message.HANDLED_FAILURE.value, 
							 'Table {0} requires values for {1}'.format(self.table.FullName, 
							 											emptyFields))
		return None
	
	def _validateAssetCreate(self):
		# NEED TO CONSIDER IF VALUES DOESN'T CONTAIN ALL COLUMNS...
	
		wg = WarningGroup()
	
		# Warning Check 1: AssetType is a rack but RackNumber, DropName, DropNumber, or PLCAssetAutoID is NULL
		rackColumns = ['RackNumber', 'DropName', 'DropNumber', 'PLCAssetAutoID']
		wg += self._checkAssetTypeColumns('RACK', rackColumns)
					
		# Warning Check 2: AssetType is a card but SlotNumber or RackAssetID is NULL
		cardColumns = ['SlotNumber', 'RackAssetAutoID']
		wg += self._checkAssetTypeColumns('CARD', cardColumns)
		
		# Warning Check 3: RackNumber, DropName, or DropNumber already assigned to RACK with the same PLCAssetAutoID
		values = self.values
		q = (qc.Query().Select(['plc.AssetID', 'a.RackNumber', 'a.DropName', 'a.DropNumber'])
					   .From('Asset.Asset', 'a')
					   .Join('Asset.Asset', childAlias='plc', ON='plc.AssetAutoID = a.PLCAssetAutoID')
					   .Where(['a.PLCAssetAutoID = ?', '(a.RackNumber = ? OR a.DropName = ? OR a.DropNumber = ?)']))
		data = q.execute([values['PLCAssetAutoID'], values['RackNumber'], values['DropName'], values['DropNumber']], dataBase=self.dataBase.Name)
		for row in data:
			if row['RackNumber'] == values['RackNumber']:
				message = 'Rack {0} already taken for {1}. Continue anyway?'.format(values['RackNumber'], row['AssetID'])
				wg.addWarning(Warning(message))
			if row['DropName'] == values['DropName']:
				message = 'Drop name {0} already configured on {1}. Continue anyway?'.format(values['DropName'], row['AssetID'])
				wg.addWarning(Warning(message))
			if row['DropNumber'] == values['DropNumber']:
				message = 'Drop number {0} already taken on {1}. Continue anyway?'.format(values['DropNumber'], row['AssetID'])
				wg.addWarning(Warning(message))
			
		# Warning Check 4: Slotnumber is already assigned to another card in the same rack. 
		# (Not tested yet because no Racks are assinged to assets yet.)
		q = (qc.Query().Select(['a.AssetID AS [AssetID]', 'a.SlotNumber', 'rk.AssetID AS [RackAssetID]'])
					   .From('Asset.Asset', 'a')
					   .Join('Asset.Asset', childAlias='rk', ON='rk.AssetAutoID = a.RackAssetAutoID')
					   .Where(['a.RackAssetAutoID = ?', 'a.SlotNumber = ?']))
		data = q.execute([values['RackAssetAutoID'], values['SlotNumber']], dataBase=self.dataBase.Name)
		for row in data:
			message = 'Slot {0} is occupied on {1} by {2}. Continue anyway?'.format(values['SlotNumber'], row['RackAssetID'], row['AssetID'])
			wg.addWarning(Warning(message))
			
		return wg if len(wg) else None
		
	def _checkAssetTypeColumns(self, type_, columns):
		wg = WarningGroup()
		# Get AutoID for the Asset Type
		q = qc.Query().Select(['AssetTypeAutoID']).From('Enum.AssetType').Where(['AssetType = ?'])
		data = q.execute([type_], dataBase=self.dataBase.Name)
		# Check if values provided contain the Auto ID
		if data[0]['AssetTypeAutoID'] in self.values.values():
			# Add a warning to the group if the column value is NULL
			for col in columns:
				if util.isNullValue(self.values[col]):
					message = 'Create {0} without {1}?'.format(type_, col)
					wg.addWarning(Warning(message))
		return wg
	
