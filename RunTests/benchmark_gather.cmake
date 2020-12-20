#! Enable generation of benchmarks
#
# Call this at the top level CMakeLists file. This will set some utility files and variables which are going to be used by other functions
# \param:ADD_TARGET If defined will create custom target RUN_PERF_TESTS which will execute all tests in BENCHMARK_TARGTES_LIST_FILE
# \param:TARGETS_DESCRIPTIONS_LIST_FILE Path to file where CMake will write paths to all benchmarks (with their properties) which will be run
# \param:PYTHON Path to python executable
# \param:PYTHON_EXECUTOR_PATH Must be provided in case ADD_TARGET is defined. Path to the python script (run_tests.py) which will read TARGETS_DESCRIPTIONS_LIST_FILE
# and execute all tests
# \param:FORMAT The format in which the result will be generated (json, console). By default is console
macro(enable_benchmarks)
	cmake_parse_arguments(
		BENCHMARK
		"ADD_TARGET"
		"TARGETS_DESCRIPTIONS_LIST_FILE;PYTHON;PYTHON_EXECUTOR_PATH;FORMAT"
		""
		${ARGN}
	)
	# BENCHMARK_TARGTES_LIST_FILE can be defined before calling enable_benchmarks in order to have the list file written in custom location
	if(NOT DEFINED BENCHMARK_TARGETS_DESCRIPTIONS_LIST_FILE)
		set(BENCHMARK_TARGETS_DESCRIPTIONS_LIST_FILE ${CMAKE_CURRENT_BINARY_DIR}/benchmark_targets_list.txt)
	endif()
	file(WRITE ${BENCHMARK_TARGETS_DESCRIPTIONS_LIST_FILE} "")
	define_property(
		GLOBAL PROPERTY __BENCHMARKS_REGISTERED
		BRIEF_DOCS "Global list of registered benchmarks."
		FULL_DOCS "Global list of registered benchmarks. Contains paths to files which represent targets and their cmd line options"
	)

	if(BENCHMARK_ADD_TARGET)
		if(NOT DEFINED BENCHMARK_PYTHON_EXECUTOR_PATH OR "PYTHON_EXECUTOR_PATH" IN_LIST BENCHMARK_KEYWORDS_MISSING_VALUES)
			message(FATAL_ERROR "Must provide PYTHON_EXECUTOR_PATH - path to python script run_test.py which will execute the tests")
		endif()
		if(NOT DEFINED BENCHMARK_PYTHON OR "BENCHMARK_PYTHON" IN_LIST BENCHMARK_KEYWORDS_MISSING_VALUES)
			message(WARNING "Path to python is not provided. Assume that python is added to the PATH variable")
			set(BENCHMARK_PYTHON "python")
		endif()
		set(BENCHMARK_SUPPORTED_FORMATS "json;console")
		if(DEFINED BENCHMARK_FORMAT AND NOT ${BENCHMARK_FORMAT} IN_LIST BENCHMARK_SUPPORTED_FORMATS)
			message(FATAL_ERROR "BENCHMARK_FORMAT not supported. Given ${BENCHMARK_FORMAT} supported formats: json, console")
		endif()
		if(NOT DEFINED BENCHMARK_FORMAT OR "BENCHMARK_FORMAT" IN_LIST BENCHMARK_KEYWORDS_MISSING_VALUES)
			set(BENCHMARK_FORMAT "console")
		endif()
		add_custom_target(
			RUN_PERF_TESTS
			COMMAND ${BENCHMARK_PYTHON} ${BENCHMARK_PYTHON_EXECUTOR_PATH} --target_list ${BENCHMARK_TARGETS_DESCRIPTIONS_LIST_FILE} --format ${BENCHMARK_FORMAT}
		)
	endif()
	set_property(GLOBAL PROPERTY __BENCHMARKS_REGISTERED "")
endmacro()

#! Add key/value string in JSON format ("key": "value" or "key": value) as a list entry.
# This utility function, for add_benchmark and it's not supposed to be used elsewhere.
# \arg:key Key of the JSON entry
# \arg:val Value of the JSON entry
# \arg:isString Boolean, whether val is string. If false val is assumed to be number
# \arg:list List where the key/value pair will be appended
macro(__appendJsonEntry key val isString list)
	if(${isString})
		set(__result "\"${key}\": \"${val}\"")
	else()
		set(__result "\"${key}\": ${val}")
	endif()
	list(APPEND ${list} ${__result})
	unset(__result)
endmacro()


#! Register benchmark executable to be run with the given options
# \param:BINARY_TARGET CMake target (result from add_executable) which is going to be executed. This is mandatory.
# \param:REPETITIONS How many times to repeat the benchmark (corresponds to --benchmark_repetitions)
# \param:FILTER Regex for benchmarks from the target. Only benchmarks matching the regex will be executed. (corresponds to --benchmark_filter)
# \param:MIN_TIME Minimum number of seconds we should run benchmark before results are considered significant (corresponds to --benchmark_min_time)
# \param:UNIT Overwrite the unit of the benchmarks. The executor script will change the unit to the given one.
function(add_benchmark)
	cmake_parse_arguments(
		REGISTER_BENCHMARK
		""
		"BINARY_TARGET;REPETITIONS;FILTER;MIN_TIME;UNIT"
		""
		${ARGN}
	)
	if(NOT DEFINED REGISTER_BENCHMARK_BINARY_TARGET OR "BINARY_TARGET" IN_LIST REGISTER_BENCHMARK_KEYWORDS_MISSING_VALUES)
		message(FATAL_ERROR "Must specify BINARY_TARGET value when adding benchmark.")
	endif()
	set(propList "")
	__appendJsonEntry("target_file" $<TARGET_FILE:${REGISTER_BENCHMARK_BINARY_TARGET}> TRUE propList)

	if(DEFINED REGISTER_BENCHMARK_FILTER)
		__appendJsonEntry("filter" ${REGISTER_BENCHMARK_FILTER} TRUE propList)
	endif()

	if(DEFINED REGISTER_BENCHMARK_UNIT)
		__appendJsonEntry("unit" ${REGISTER_BENCHMARK_UNIT} TRUE propList)
	endif()

	if(DEFINED REGISTER_BENCHMARK_REPETITIONS)
		__appendJsonEntry("repetitions" "${REGISTER_BENCHMARK_REPETITIONS}" FALSE propList)
	endif()

	if(DEFINED REGISTER_BENCHMARK_MIN_TIME)
		__appendJsonEntry("min_time" "${REGISTER_BENCHMARK_MIN_TIME}" FALSE propList)
	endif()

	list(JOIN propList "," joinedProps)
	set(jsonProps "{${joinedProps}}")

	# Path to a file which defines path to the current target executable
	set(BENCHMARK_TARGET_DESCRIPTION_PATH ${CMAKE_CURRENT_BINARY_DIR}/benchmark_descriptions.txt)

	# Writhe the description JSON. Each description JSON must be on a new line and be one line only (no matter how long will the line be) 
	add_custom_command(
		TARGET ${REGISTER_BENCHMARK_BINARY_TARGET} POST_BUILD
		COMMAND echo ${jsonProps} >> ${BENCHMARK_TARGET_DESCRIPTION_PATH}
	)

	get_property(registerdBenchmarksContent GLOBAL PROPERTY __BENCHMARKS_REGISTERED)
	# We want to clean the file which holds the descriptions of the all benchmarks for this target
	# But we need to do it only once. So check if the target is already registered if not add command to clean
	# Also add the path to the file which holds the descriptions for this target. IMORTANT we have to add it only once
	if(NOT ${BENCHMARK_TARGET_DESCRIPTION_PATH} IN_LIST registerdBenchmarksContent)
		add_custom_command(
			TARGET ${REGISTER_BENCHMARK_BINARY_TARGET} PRE_BUILD
			COMMAND ${CMAKE_COMMAND} -E rm -f ${BENCHMARK_TARGET_DESCRIPTION_PATH}
		)
		set_property(GLOBAL APPEND PROPERTY __BENCHMARKS_REGISTERED ${BENCHMARK_TARGET_DESCRIPTION_PATH})
		file(APPEND ${BENCHMARK_TARGETS_DESCRIPTIONS_LIST_FILE} "${BENCHMARK_TARGET_DESCRIPTION_PATH}${newline}\n")
	endif()
endfunction()