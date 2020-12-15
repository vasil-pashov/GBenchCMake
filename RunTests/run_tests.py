import json
import argparse
import pathlib
import os
import subprocess
import sys
import re
import io
import logging
import typing

args = None


def setupArgparse():
	"""Define available command line arguments and parse them from the command line"""
	defaultListPath = os.path.join(
			pathlib.Path().absolute(), 'benchmark_targets_list.txt')
	parser = argparse.ArgumentParser()
	parser.add_argument('--format', help="Format of the output",
											choices=["json", "console"], default="json")
	parser.add_argument(
			'--out_path', help="File where all benchmarks will be added")
	parser.add_argument('--target_list', default=defaultListPath,
											help="Path to file which contains description of each benchmark to be run")
	parser.add_argument(
			"--filter", help="Global filter for benchmark names. First local filters are applied and then the""global filter is applied to the resulting benchmark names.")
	parser.add_argument(
			"--repetitions", help="How many times a benchmark should be repeated.""Overrides the number selected in the description file", type=int)
	parser.add_argument(
			"--min_time", help="Minimum amout of time in seconds which a given benchmark will be run", type=float)
	parser.add_argument("--log_level", help="Log level. 1 being the most verbose 5 being the least verbose",
											type=int, choices=[0, 1, 2, 3, 4, 5], default=3)
	return parser.parse_args()


def getTargetList(path: str) -> list:
	"""Read paths to files which contain descriptions for running benchmark executables

	The file located at path must contain paths to files where each path is on a new line.
	The files listed will contain information about how to run a benchmark i.e. command line
	arguments for the benchmark executable
	
	:param path: Path to a file containing list of files with descriptions for benchmarks
	:type path: str
	:returns: A list with file paths where each path points to a file with benchmark descriptions
	:rtype: list
	"""
	with open(path, "r") as mainListFile:
		targetList = [l.strip() for l in mainListFile.readlines()]
	return targetList


def executeAllDescriptions(descPath: str, outputFile: typing.TextIO) -> bool:
	"""Read all benchmark descriptions in file with path descPath and execute them

	The file descPath must contain benchmark descriptions in JSON format. There must be
	exactly one JSON on each line, no whitespaces are allowed.

	:param descPath: Path to a file containing benchmark run descriptions
	:type descPath: str
	:param outputFile: File where the result will be written
	:type outputFile: typing.Union[typing.TextIO, None]
	:returns: Whether at leas one benchmark has been executed
	:rtpye: bool
	"""
	didWriteTest = False
	with open(descPath, "r") as descListFile:
		descriptions = [json.loads(descStr) for descStr in descListFile.readlines()]
		numDescriptions = len(descriptions)
		currentDescription = 1
		for desc in descriptions:
			sys.stdout.flush()
			logging.info(
					"[subtarget {}/{}]".format(currentDescription, numDescriptions, desc))
			hasTests = executeDescription(desc, outputFile)
			didWriteTest = hasTests or didWriteTest
			if outputFile and args.format == "json" and currentDescription < numDescriptions and hasTests:
				outputFile.flush()
				outputFile.write(",")
			currentDescription += 1
	return didWriteTest


def applyGlobalFilter(executablePath: str, localFilter: str, globalFilter: str) -> typing.List[str]:
	"""Filter benchmarks from executablePath with global and localFilter

	First apply local filter to all benchmarks in executablePath then
	apply global filter to further filter the benchmarks from executablePath.
	:param executablePath: Path to benchmark executable
	:type executablePath: str
	:param localFilter: Regex with google benchmark synthax which will be applied to executablePath
	:type localFilter: str
	:param globalFilter: Regex with python synthax wich will be used to filter the results which were matched by localFilter
	:type globalFilter: str
	:returns: List with benchmark names wich matched both localFilter and globalFilter
	:rtype: typing.List[str]
	"""
	command = "%s --benchmark_list_tests=true --benchmark_filter=%s" % (
		executablePath, localFilter)
	proc = subprocess.Popen(command, stdout=subprocess.PIPE)
	regex = re.compile(globalFilter)
	return [benchName.strip() for benchName in io.TextIOWrapper(proc.stdout) if regex.match(benchName)]


def runBenchmarkCommand(command: str, outputFile: typing.TextIO) -> None:
	"""Execute run command as a process. If outputFile is not none write the result there
	:param command: Command line which will be executed
	:type command: str
	:param outputFile: File where to write the result from command
	:type outputFile: typing.TextIO
	"""
	outputFile.flush()
	subprocess.run(command, stdout=outputFile)


def createCommand(desc: dict, benchmarkName: typing.Union[str, None]) -> str:
	"""Read various properties from desc and create google benchmark command form them
	:param desc: Collection which holds properties for google benchmark	
	:type desc: dict
	:param benchmarkName: If not none will override all filters and the command will execute this specific benchmark
	:type benchmarkName: str	
	:returns: Command which can be executed by the command line
	:rtype: str
	"""
	numReps = args.repetitions if args.repetitions else desc.get(
		'repetitions', 1)
	benchFilter = benchmarkName if benchmarkName else desc.get("filter", None)
	command = "%s --benchmark_format=%s --benchmark_repetitions=%d" \
		" --benchmark_report_aggregates_only=true" % (
				desc['target_file'], args.format, numReps)
	if benchFilter:
		command += " --benchmark_filter=%s" % (benchFilter)
	if "min_time" in desc:
		command += " --benchmark_min_time%d" % (desc['min_time'])
	return command


def executeDescription(desc: dict, outputFile: typing.TextIO) -> bool:
	"""Create command from description, run it and save it in a file
	:param desc: Description of the benchmark which will be run
	:type desc: dict
	:param outputFile: File where to write the result from the benchmark
	:type outputFile: typing.TextIO
	:returns: If at least one benchmark has been executed
	:rtype: bool
	"""
	if args.filter is not None:
		filteredBenches = applyGlobalFilter(desc['target_file'], desc.get("filter", "."), args.filter)
		numBenches = len(filteredBenches)
		if numBenches == 0:
			return False
		currentBench = 1
		for benchName in filteredBenches:
			logging.info(
					"[filter_item {}/{}]".format(currentBench, numBenches))
			command = createCommand(desc, benchName)
			runBenchmarkCommand(command, outputFile)
			if args.format == "json" and currentBench < numBenches:
				outputFile.write(",")
			currentBench += 1
	else:
		command = createCommand(desc, None)
		runBenchmarkCommand(command, outputFile)
	return True


def iterateMainList(outputFile: typing.TextIO):
	"""Entry point for executing all listed benchmarks.

	Read the file that contains all files which contain benchmark descriptions and
	execute all descriptions. If format is JSON the output will be a list containing
	objects from all calls to google benchmark.

	:param outputFile: File where the result will be writed
	:type outputFile: typing.TextIO
	"""
	targetList = getTargetList(args.target_list)
	numTargets = len(targetList)
	currentTarget = 1
	if args.format == "json":
		outputFile.write("[")
	for target in targetList:
		sys.stdout.flush()
		logging.info(
				"[target {}/{}] {}".format(currentTarget, numTargets, target))
		hasTests = executeAllDescriptions(target, outputFile)
		if args.format == "json" and currentTarget < numTargets and hasTests:
			outputFile.write(",")
		currentTarget += 1
	if args.format == "json":
		outputFile.write("]")
	sys.stdout.flush()
	logging.info("All benchmarks completed")


def main():
	global args
	args = setupArgparse()
	logging.basicConfig(
			format='[%(asctime)s] %(levelname)s: %(message)s',
			level=args.log_level * 10,
			datefmt='%Y/%m/%d %H:%M:%S')
	outputFile = open(args.out_path, "w") if args.out_path else sys.stdout
	iterateMainList(outputFile)
	if outputFile and outputFile != sys.stdout:
		outputFile.close()


if __name__ == '__main__':
	main()
