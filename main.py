from collections import OrderedDict
import json
import os
import argparse
import glob
import datetime
import jinja2
import pathlib

class PlotColumnDescription:
	def __init__(self, id, label=id, type="string", role=None):
		self.id=id
		self.label=label
		self.type=type
		if role:
			self.role=role

class PlotDescriptionError(Exception):
	def __init__(self, domainId, message):
		self.domainId=domainId
		self.message=message

class PlotDescription:
	def __init__(self, domainDescription):
		self.domainId=domainDescription.domain
		self.columns[self.domainId]=domainDescription

	def __init__(self, domainId, columnList):
		self.domainId=domainId
		self.columns=OrderedDict()
		hasDomain=False
		for col in columnList:
			if col.id == domainId:
				hasDomain=True
			self.columns[col.id]=col
		if not hasDomain:
			raise PlotDescriptionError(domainId, "Plot description must contain a domain column")

	def addColumn(self, column):
		self.columns[column.id]=column

class PlotRowException(Exception):
	def __init__(self, domainId, message):
		self.domainId=domainId
		self.message=message

class Plot:
	def __init__(self, description):
		self.description=description
		self.rows=[]
		self._options={}

	@property
	def options(self):
		return self._options
	
	@options.setter	
	def options(self, options):
		self._options=options

	def optionsJSON(self):
		return json.dumps(self._options)

	def addRow(self, rowData):
		if self.description.domainId not in rowData:
			raise PlotRowException(self.domainId, "Row is missing domain value.")

		for id in rowData.keys():
			if id not in self.description.columns:
				raise PlotRowException(self.description.domainId, "Adding row with unknown column id:{}".format(id))

		self.rows.append(rowData)

	def __toJsonStrValue(self, type, value):
		if type == "datetime":
			strVal="\"Date(%d, %d, %d, %d, %d, %d)\"" % (
				value.year,
				value.month,
				value.day,
				value.hour,
				value.minute,
				value.second
			)
		else:
			strVal=str(value)
		return strVal

	def __getRowDescStr(self, row, columns):
		rowStr="["
		processedColumns=1
		for (colId, col) in columns.items():
			if colId in row:
				rowStr+=self.__toJsonStrValue(col.type, row[colId])
			else:
				rowStr+=","
			if processedColumns < len(columns):
				rowStr+=","
			processedColumns+=1
		rowStr+="]"
		return rowStr

	def __getRowDescriptionListStr(self):
		rowListStr=""
		columns=self.description.columns
		processedRows=1
		for row in self.rows:
			rowListStr+=self.__getRowDescStr(row, columns)		
			if processedRows < len(self.rows):
				rowListStr+=","
			processedRows+=1
		return rowListStr


	def toGoogleChartArrayStr(self):
		cols=[colDesc.__dict__ for colDesc in self.description.columns.values()]
		rowDescrptionString=self.__getRowDescriptionListStr()
		return "\'[%s, %s]\'" % (json.dumps(cols), rowDescrptionString)
	

# Used in argparse to check if given argument is valid folder path
def dirPath(string):
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)

# Set arguments which can be received from the command line and parse them
# Returns key/value map with the parsed arguments
def setupArgparse():
	parser=argparse.ArgumentParser()
	parser.add_argument('src_dir', type=dirPath, help='Directory containing perfs to be ploted.')
	parser.add_argument('dest_file', help='Destination where to put the plots from src_dir')
	return parser.parse_args()

def makeOptions(title):
	options={}
	options['title']=title
	options['legend']={'position': 'top'}
	options['curveType']='function'
	hAxis={
		'format': 'yyyy-M-dd',
		'gridlines': {'count': 0},
		'slantedText': True,
		'slantedTextAngle':-80
	}
	options['hAxis']=hAxis
	return options


def gatherPlotData(dir):
	descList=[
		PlotColumnDescription("date", label="Date", type="datetime"),
		PlotColumnDescription("cpu_time", label="CPU Time", type="number"),
		PlotColumnDescription("real_time", label="Real Time", type="number")
	]	
	plotDesc=PlotDescription("date", descList)
	allPlots={}
	pattern=os.path.join(dir, "*.json")
	fileNameList=glob.glob(pattern)
	for fileName in fileNameList:
		with open(fileName, "r") as file:
			jsonData=json.load(file)
			for executable in jsonData:
				exeName=executable['context']['executable']
				date=datetime.datetime.strptime(executable['context']['date'], '%m/%d/%y %H:%M:%S')
				benchmarks=executable['benchmarks']
				for benchmark in benchmarks:
					name=benchmark['name']
					cpuTime=benchmark['cpu_time']
					realTime=benchmark['real_time']
					unit=benchmark['time_unit']
					row={
						'date': date,
						'cpu_time': cpuTime,
						'real_time': realTime
					}
					if name not in  allPlots:
						plot=Plot(plotDesc)
						plot.addRow(row)
						allPlots[name]=plot
						plot.options=makeOptions(name)
					else:
						plot=allPlots[name]
						plot.addRow(row)
	return allPlots

def drawPlots(plots, dest):
	templateLoader=jinja2.FileSystemLoader(
		os.path.join(
			pathlib.Path(__file__).parent.absolute(),
			"./templates"
		)
	)
	environment=jinja2.Environment(loader=templateLoader)
	template=environment.get_template("plot.html")
	renderResult=template.render(plots=plots)
	with open(dest, "w") as destFile:
		destFile.write(renderResult)

def main():
	args=setupArgparse()
	plots=gatherPlotData(args.src_dir)
	drawPlots(plots, args.dest_file)


if __name__ == '__main__':
	main()
