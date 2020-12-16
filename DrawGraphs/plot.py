from collections import OrderedDict
import typing
import json

def PlotColumnException(Exception):
  def __init__(self, message):
    self.message=message


def makePlotColumnDesc(id: str, label: str=id, type: str="string", role: typing.Union[str, None]=None):
  """Create description for a column in DataTable
  :param id: Id of the column used to reference it internaly
  :type id: str
  :param label: Labe of the column, this will be shown to the user
  :type label: str
  :param type: Type of the data stored in the column
  :type type: str
  :param role: Role of the column (annotation, tooltip, etc.)
  :type role: str
  """
  allowedTypes=["string", "date", "datetime", "number", "boolean", "timeofday"]
  if type not in allowedTypes:
    raise PlotColumnException(
      "Type {} is not supported. supported types are: {}".format(type, allowedTypes))
  colDesc={
    'id': id,
    'label': label,
    'type': type
  }
  if role:
    colDesc['role'] = role
  return colDesc


class PlotDescriptionException(Exception):
  def __init__(self, message):
    self.message=message

class PlotDescription:
  """Container for all columns descriptions and the domain variable id
  domainId: id for the column which will be the domain value (x-axis) 
  columns: Dict which will hold the columns of the DataTable
  """
  def __init__(self, domainId: str, columnList: list):
    """Initialize the plot.

    The variables will be displayed in the same order as they are in the columnList
    Column description with id domainId must exist in the columnList
    :param domainId: id of the domain value (x-axis)
    :type domainId: str
    :param columnList: The columns of the DataTable in the order they will be used.
    The domain column must be the first in this list
    :type columnList: list
    """ 
    self.domainId=domainId
    self.columns=OrderedDict((col['id'], col) for col in columnList)
    if domainId not in self.columns:
      raise PlotDescriptionError(domainId, "Plot description must contain a domain column")

  def addColumn(self, column):
    """Add column to the column. Keeps ordering.
    :param column: The column which will be added
    """
    self.columns[column.id]=column

class PlotRowException(Exception):
  def __init__(self, domainId, message):
    self.message=message

def _toJsonStrValue(type: str, value) -> str:
  """Return string representation of value which could be accepted by JSON.parse
  :param type: Name of the type of value
  :type type: str
  :param value: The value which will be reformated as acceptable string value
  """
  if value is None:
    return "null"
  if type == "datetime":
    strVal="\"Date(%d, %d, %d, %d, %d, %d)\"" % (
      value.year,
      value.month - 1,
      value.day,
      value.hour,
      value.minute,
      value.second
    )
  elif type == "date":
    strVal="\"Date(%d, %d, %d)\"" % (
      value.year,
      value.month - 1,
      value.day
    )
  else:
    strVal=str(value)
  return strVal


class Plot:
  """Holds data for a plot in format from whic is easy to create google chart

  __description: Description of each variable which is going to be plotted
  __rows: Each element of this is a list which contains domain value, and the values
  of each other variable at this domain value
  _options: Key value pairs with additional options. Will be used as-is in the resulting
  html page with the charts. Can contain any valid google chart options
  """
  def __init__(self, description):
    self.__description=description
    self.__rows=[]
    self._options={}

  @property
  def options(self):
    return self._options
  
  @options.setter 
  def options(self, options: dict):
    self._options=options

  @property
  def rows(self):
    return iter(self.__rows)

  def optionsJSON(self):
    return json.dumps(self._options)

  def addRow(self, rowData: dict):
    """Adds domain value and the values at other variables at this domain value
    :param rowData: Key/value store with the values of the domain and the other variables
    the keys must be the id-s of the columns (ordering here is not important). The domain
    variable must be in the rowData. Other variables are optional. ID-s which are not in
    the description are not allowed.
    """
    if self.__description.domainId not in rowData:
      raise PlotRowException("Row is missing domain value.")
    diff=rowData.keys() - self.__description.columns.keys()
    if len(diff):
      raise PlotRowException("Adding row with unknown columns: {}".format(diff))
    self.__rows.append(rowData)

  def __getRowDescStr(self, row: dict) -> str:
    """Create string with the sythax of JavaScript array for a row of the plot

    Will use the same ordering as in the colums of the description.
    The domainId will be first and so on.
    :param row: The row which will be converted to string acceptable by JSON.parse
    """
    getVal=lambda item: _toJsonStrValue(item[1]['type'], row.get(item[0], None))
    return "[%s]" % (",".join(map(getVal, self.__description.columns.items())))

  def toGoogleChartArrayStr(self):
    """Create JSON representation for the plot

    The JSON representation is compatible with google charts and can be parsed
    with JSON.parse and the it can be passed to google.visualization.arrayToDataTable
    the format is as follows
    [
      [domainDescJSON, colum1DescJSON, colum2DescJSON, ...],
      [domainVal, col1Val, col2Val, ...]
    ]
    """
    cols=[colDesc for colDesc in self.__description.columns.values()]
    rowDescrptionString=",".join(map(self.__getRowDescStr, self.__rows))
    return "\'[%s, %s]\'" % (json.dumps(cols), rowDescrptionString)