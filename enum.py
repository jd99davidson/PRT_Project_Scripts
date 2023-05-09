from enum import Enum

# These enum classes define globally static string values

class Message(Enum):
	SUCCESS = 'success_message'
	WARNING = 'warning_message'
	HANDLED_FAILURE = 'handled_failure_message'
	UNHANDLED_FAILURE = 'unhandled_failure_message'
	QUERY_FAILURE = 'Query compile failure.'


class DisplayMode(Enum):
	Edit = 'Edit'
	View = 'View'
	Minimized = 'Minimized'
	Maximized = 'Maximized'


class FormMode(Enum):
	Edit = 'Edit'
	View = 'View'
	New = 'New'


class cmd(Enum):
	Save = 'Save'
	Delete = 'Delete'


class Alert(Enum):
	NoResults = 'NoResults'
	SeeMore = 'SeeMore'
	ChangesSaved = 'ChangesSaved'
	EntryDeleted = 'EntryDeleted'
	Warning = 'Warning'
	Error = 'Error'


class ExtProps(Enum):
	IsAutoID = 'IsAutoID'
	IsPrimaryID = 'IsPrimaryID'
	IsOneToMany = 'IsOneToMany'


class JoinType(Enum):
	inner = 'INNER'
	left = 'LEFT'
	right = 'RIGHT'
	outer = 'OUTER'


class Direction(Enum):
	UP = 'up'
	DOWN = 'down'
	LEFT = 'left'
	RIGHT = 'right'


class OrderBy(Enum):
	ASC = 'ASC'
	DESC = 'DESC'
	NONE = ''


class DataType(Enum):
	VARCHAR = 'varchar'
	INT = 'int'
	TINYINT = 'tinyint'
	SMALLINT = 'smallint'
	DATETIME = 'datetime'
	BIT = 'bit'
	
class ButtonColor(Enum):
	LIGHT_GRAY = '#D5D5D5'
	DARK_GRAY = '#808080'
	BLUE = '#4747FF'
	GREEN = '#00AC00'
	RED = '#D90000'
	GOLD = '#FFD700'

class Cursors(Enum):
	POINTER = 'pointer'
	AUTO = 'auto'
