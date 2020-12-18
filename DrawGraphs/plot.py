from collections import OrderedDict
import typing
import json

def PlotColumnException(Exception):
  def __init__(self, message):
    self.message=message


def makePlotColumnDesc(id: str, label: str=None, type: str="string", role: typing.Union[str, None]=None):
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
    'label': label if label else id,
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

    self.columns[column['id']]=column

  def containsColumn(self, column):
    return column['id'] in self.columns

class PlotRowException(Exception):
  def __init__(self, message):
    self.message=message


class DataTable:
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
  def domainId(self):
    return self.__description.domainId  

  @property
  def columns(self):
    return self.__description.columns.keys()

  def __iter__(self):
    return iter(self.__rows)

  def __getitem__(self, rowId):
    if rowId < 0 or rowId >= len(self.__rows):
      raise PlotRowException(
        "Trying to access row with invalid id: {}".format(rowId))
    return self.__rows[rowId]

  def __setitem__(self, rowId, values):
    if self.__description.domainId not in values:
      raise PlotRowException("Row is missing domain value.")
    if rowId < 0 or rowId >= len(self.__rows):
      raise PlotRowException(
        "Trying to access row with invalid id: {}".format(rowId))
    self.__rows[rowId]=values

  def _toJsonStrValue(self, colId: str, value) -> str:
    """Return string representation of value which could be accepted by JSON.parse
  
    :param colId: Name of the column
    :type colId: str
    :param value: The value which will be reformated as acceptable string value
    """

    type=self.__description.columns[colId]['type']
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
    elif type == "string":
      strVal = "\"%s\"" % (str(value))
    else:
      strVal = str(value)
    return strVal

  def optionsJSON(self):
    return json.dumps(self._options)

  def addColumn(self, colDesc):
    if self.__description.containsColumn(colDesc) == False:
      self.__description.addColumn(colDesc)

  def addRow(self, rowData: dict) -> int:
    """Adds domain value and the values at other variables at this domain value

    :param rowData: Key/value store with the values of the domain and the other variables
    the keys must be the id-s of the columns (ordering here is not important). The domain
    variable must be in the rowData. Other variables are optional. ID-s which are not in
    the description are not allowed.
    :returns: Unique identifier for the added row
    """

    if self.__description.domainId not in rowData:
      raise PlotRowException("Row is missing domain value.")
    diff=rowData.keys() - self.columns
    if len(diff):
      raise PlotRowException("Adding row with unknown columns: {}".format(diff))
    idx=len(self.__rows)
    self.__rows.append(rowData)
    return idx

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
    createRow = lambda row: "[%s]" % (",".join([self._toJsonStrValue(col, row[col]) for col in self.columns]))
    rowsString=",".join([createRow(row) for row in self.__rows])
    return "\'[%s, %s]\'" % (json.dumps(cols), rowsString)


class Plot(DataTable):
  """Class to represent a function plot.

  The domain column represents the x-axis. All other columns represent
  different functions, all of which are going to be plotted on the same graph
  __xAxisIndex: Key-value store where the keys are values of the domain column
  and the values are indexes into __rows array.
  """

  def __init__(self, description):
    super().__init__(description)
    self.__xAxisIndex={}

  def addValue(self, domainValue, values):
    """Adds values for different graphs for the given domainValue

    :param domainValue: x-axis value
    :param values: Key-value store where keys are names of plots
    and values are value of the plots at the given domainValue
    """
    for col in values:
      if col not in self.columns:
        raise PlotRowException("Adding value to an unknown column: {}".format(col))
    idx=self.__xAxisIndex.get(domainValue, -1)
    if idx == -1:
      row={**values, self.domainId: domainValue}
      rowId=self.addRow(row)
      self.__xAxisIndex[domainValue]=rowId
    else:
      super().__getitem__(idx).update(values)

  def __setitem__(self, domainValue, values):
    idx=self.__xAxisIndex.get(domainValue, -1)
    if idx == -1:
      row={**values, self.domainId: domainValue}
      rowId=self.addRow(row)
      self.__xAxisIndex[domainValue]=rowId
    else:
      super().__setitem__(idx, values)

  def __getitem__(self, domainValue):
    idx=self.__xAxisIndex[domainValue]
    return super().__getitem__(idx)

  def __iter__(self):
    """Iterate over all domainValues.

    The values are not guaranteed to have a specific order
    """

    return iter(self.__xAxisIndex)