# GBenchCMake
Provides CMake functionality to register benchmars with google benchmark (similar to ctest and gtest). Provides python scripts to execute and visualize the results from the benchmarks.

## Dependencies
1. Google Benchmark 1.5.0
2. CMake 3.18
4. Python 3.8
5. Jinja2 python library - used for creating plots
6. Google charts forzen version 49 - used for creating plots

## How to use
This repo provides 3 components:
1. CMake `RunTests/benchmark_gather.cmake` used to register benchmarks programmatically via CMake.
2. Python `RunTests/run_tests.py` used to execute all registed benchmarks.
3. Python `DrawGraphs/main.py` used to create various plots for the generated benchmarks.

### CMake
Include `RunTests/benchmark_gather.cmake` in the **top level** `CMakeLists.txt` file of the project and call `enable_benchmarks`.
To see how to generate Visual Studio custom target to run all tests and other additional options see: [enable_benchmarks()](#enable_benchmarks)
When CMake project is generated `benchmark_targets_list.txt` will be created. This file will contain list of files (separated by newline), 
where each file in the list contains information needed to execute the benchmarks i.e. number of repetitions, min run time, filter for tests 
(most of the parameters correspond to command line arguments for google benchmark). In `benchmark_targets_list.txt` there is one file per google benchmark executable.

To register benchmarks use `add_benchmark()`. For additional options see: [add_benchmark()](#add_benchmark). When `add_benchmark()` is called for the first time, it creates a file which will hold all properties for the given target and registers that file in `benchmark_targets_list.txt`. Each next call only adds configurations to the already created config file.

### Python
#### Running tests
To execute all registered benchmarks run `RunTests/run_tests.py`. For information about command line arguments check: [run_tests.py](#run_testspy)

#### Ploting tests
To create plots using the result from `RunTests/run_tests.py` run `DrawGraphs/main.py`. For information about command line arguments check: *ADD LINK*

## Function documentation

### enable_benchmarks()
This must be called from the **top level** `CMakeLists.txt` file. It will set some utility files and variables which are going to be used by other functions. It can take the following parameters:
#### ADD_TARGET
If defined will create custom target `RUN_PERF_TESTS` which will execute all tests in [TARGETS_DESCRIPTIONS_LIST_FILE](#TARGETS_DESCRIPTIONS_LIST_FILE)
#### TARGETS_DESCRIPTIONS_LIST_FILE
Path to file where CMake will write paths to all files with benchmark descriptions which will be run. By default it will be in the top level build directory.
#### PYTHON
Path to python executable which `RUN_PERF_TESTS` will use to execute all benchmarks. By default it assumes that it's in the path environment variable and it's value is `python`
#### PYTHON_EXECUTOR_PATH
Must be provided in case [ADD_TARGET](#ADD_TARGET) is defined. Path to the python script (run_tests.py) which will read [TARGETS_DESCRIPTIONS_LIST_FILE](#TARGETS_DESCRIPTIONS_LIST_FILE)
and execute all tests
#### FORMAT
The format in which the result from `RUN_PERF_TESTS` will be generated (json, console). By default is console.

Example use:
```
enable_benchmarks(
  ADD_TARGET
  PYTHON_EXECUTOR_PATH ./run_tests.py
  FORMAT "json"
)
```

### add_benchmark()
Add functions from the a given google benchmark executable alongside with options to execute them. Calling add_benchmark() with the same target multiple times
is allowed, no checks are made wheter the same benchmark function will be run multiple times. Paramters:

#### BINARY_TARGET
**Mandatory**. CMake target (result from add_executable) which is going to be executed.
#### REPETITIONS
How many times to repeat the benchmark (corresponds to --benchmark_repetitions)
#### FILTER
Regex for benchmarks from the target. Only benchmarks matching the regex will be executed.
This must follow the google benchmark rules for regular expressions. This is not mandatory, by default all benchmarks will be executed.
(corresponds to --benchmark_filter)
#### MIN_TIME
Minimum number of seconds we should run benchmark before results are considered significant (corresponds to --benchmark_min_time)
#### UNIT
Overwrite the unit of the benchmarks. The executor script will change the unit to the given one. Allowed units are
* s - seconds
* ms - milliseconds
* us - microseconds
* ns - nanoseconds
Note: google benchmark does not provide seconds natively.

**Example use.**

Given the following `benchmark.cpp` file

```cpp
#include <benchmark/benchmark.h>

static void benchmark_heavy(benchmark::State& state) {
  for (auto _ : state)
    // Some code to be benchmarked
}
// Register the function as a benchmark
BENCHMARK(benchmark_heavy);

// Define another benchmark
static void benchmark(benchmark::State& state) {
  for (auto _ : state)
    // Some code to be benchmarked
}
BENCHMARK(benchmark);

BENCHMARK_MAIN();
```
The following `CMakeLists.txt` will generate one executable file and will register two benchmarks which will be ran from that executable. The executable will
be ran twice and only the mathcing tests will be executed with the given parametres.
1. All benchmarks with suffix `_heavy` will be executed. They will be repeated 20 times
(mean, median and standard deviation will be reported), the result will be given in json format and `run_tests.py` will convert `real_time` and `cpu_time` to seconds.
2. All benchmarks which **do not** end with `_heavy` will be executed. The result will be reported in json format, google benchmark will probe for at least 1 second
before deciding that the results are stable

```cmake
project(benchmark)
add_executable(${PROJECT_NAME} benchmark.cpp)
target_link_libraries(${PROJECT_NAME} CONAN_PKG::benchmark)

add_benchmark(
  BINARY_TARGET ${PROJECT_NAME}
  REPETITIONS 20
  OUTPUT_FORMAT "json"
  FILTER "_heavy$"
  UNIT "s"
)

add_benchmark(
  BINARY_TARGET ${PROJECT_NAME}
  OUTPUT_FORMAT "json"
  FILTER "-_heavy$"
  MIN_TIME 1
)
```

### run_tests.py
This is a python a python script whic takes `benchmark_targets_list.txt` goes trough all files in it and for each file executes all benchmark benchmarks with the
given descriptions. There are a number of command line arguments which could be given to `run_tests.py` in order to override the options with wich the benchmarks
will be executed. The options are as follow:

#### --target_list
Path to`benchmark_targets_list.txt`. By default search for `benchmark_targets_list.txt` in the folder from which the script is executed.

#### --out_path
Path to a file where the results are going to be stored. The results from all executed benchmakrs are stored in one single file. If nothing is passed the result will
be printed to the `stdout`.

#### --format
Format of the output one of `json, console`. Console corresponds to google benchmark console output. Default is `json`.

#### --filter
Global filter for benchmark names. First local filters (the ones specified by [FILTER parameter](#FILTER))
are applied and then the global filter is applied to the resulting benchmark names. Only the benchmarks which are matched by **both** regular expressions will
be executed. **Important** this must follow standard python (UNIX) syntax for regular expressions.

#### --repetitions
All benchmarks will be runned with this number of repetitions. Overrides [REPETITIONS parameter](#REPETITIONS) for all benchmarks.

#### --min_time
Minimum amout of time, in seconds, which all benchmark will be run. Overrides [MIN_TIME parameter](#MIN_TIME) for all benchmarks.

#### --log_level
Verbosity of the console output. 0 being the most verbose and 5 being the least verbose. Default is 3.

### DrawGraphs/main.py

This is a python script which is used to generate plots using the output from [run_tests.py](#run_testspy). It has two modes.
1. Scan a given folder and parse all `.json` files in the folder. Use the dates in the files to create plots for each benchmark. The x-axis will be the date
while the y-axis will be the `real_time` returned by google benchmakr. Benchmarks which are in the same fixture will be reported on the same plot.
2. Take a singe file as input and for each fixture create a bar plot (plotting the `real_time` returned by google benchmark).

#### src
First positional argument. This is mandatory. If `--type=plot` this must be a path to a folder from which a time plot will be created, if `--type=bar` it must be
a path to file (einther produced directly by google benchmark or one produced by [run_tests.py](#run_testspy))

#### dest_file
Second positional argumend. This is mandatory. File where to write the generated plots. The plots will be generated via google charts in `html` format.

#### --type
One of `plot, bar`. The type of charts which are going to be generated. Default is `plot`
