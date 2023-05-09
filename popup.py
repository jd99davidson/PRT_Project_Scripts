from qc import Query
from val import Error

class AssetTypePopup(object):
	""" Asset Type popup view object. """
	
	TABLE_NAME = 'Enum.AssetType'
	POPUP_ID = 'AssetTypePopup'
	
	def __init__(self, autoID, dataBase):
		self._autoID = autoID
		self.dataBase = util.getDatabaseObj(dataBase)
		# Cache
		self._values = None
		self._table = db.Table(self.TABLE_NAME, self.dataBase)
		self._row = db.Row(self._table, self._autoID)
		
	@property
	def AutoID(self):
		return self._autoID
		
	@property
	def Values(self):
		if self._values:
			return self._values
		self._values = self._getValues()
		return self._values
	
	def _getValues(self):
		return self._row.Values
		
	def saveChanges(self, values):
		# @@NEEDS_BUSINESS_LOGIC@@
		if self._row.Exists:
			result = self._row.update(values)
			# Currently does not execute because of isinstance() error...
			if isinstance(result, Error):
				payload = {'error': result.Value}
				system.perspective.sendMessage('{0}RaiseError'.format(self._table.Name), payload)
			else:
				# Send message that changes were made
				payload = {'AssetTypeAutoID': self._row.AutoID}
				system.perspective.sendMessage('{0}ChangesSaved'.format(self._table.Name), payload)
		else:
			# Expecting newAutoID but catches errors
			result = self._row.create(values)
			# Currently does not execute because of isinstance() error...
			if isinstance(result, Error):
				payload = {'error': result.Value}
				system.perspective.sendMessage('{0}RaiseError'.format(self._table.Name), payload)
			else:
				# Send message that changes were saved
				payload = {'AssetTypeAutoID': result}
				system.perspective.sendMessage('{0}ChangesSaved'.format(self._table.Name), payload)
		
	def close(self):
		system.perspective.closePopup(self.POPUP_ID)
