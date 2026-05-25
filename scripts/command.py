import enum
import inspect
import logging
import sys
from log_utils import formatter as logFormatter
from log_utils import logger as log
from log_utils import stderrHandler as logStdErrHandler
from log_utils import MaxLogLevelFilter
from utils import Ticker

class Verbosity(enum.IntEnum):
    LOGQUIET = -2,
    APPQUIET = -1,
    NORMAL = 0,
    APPVERBOSE = 1,
    LOGVERBOSE = 2

class Command:
    def __init__(self, args):
        self.mArgs = args
        self.mVerbosity = Verbosity.NORMAL

    def create_arg_parser(self):
        self.unimplemented_function(self.create_arg_parser.__name__, self.__class__)

    def run(self):
        parser = self.create_arg_parser()
        parser.add_argument(
            "--verbose", "-v",
            action='count',
            default=Verbosity.NORMAL,
            help="Increase the verbosity")
        parser.add_argument(
            "--quiet", "-q",
            action='count',
            default=Verbosity.NORMAL,
            help="Decrease the verbosity")
        self.parse_args(parser)
        try:
            return self.run_command()
        except Exception as e:
            log.error(e)
            raise
        return 1

    def parse_args(self, parser):
        self.parsed_args = parser.parse_args(self.mArgs[1:])
        self.parsed_args.verbosity = self.parsed_args.verbose - self.parsed_args.quiet
        self.set_log_levels(self.parsed_args.verbosity)

    # Implementations can override this function to change logging behavior. Overriding with a no-op function will
    # remove any verbosity-based modifications of the log level and will use default behavior from log_utils.py. As of
    # this writing, that behavior is that ERROR and CRITICAL logs go to stderr, nothing goes to stdout, and all logs go
    # to a rotating log file.
    def set_log_levels(self, verbosity):
        # Quiet mode
        if verbosity < Verbosity.LOGQUIET:
            log.removeHandler(logStdErrHandler)
        if verbosity == Verbosity.LOGQUIET:
            logStdErrHandler.setLevel(logging.CRITICAL)

        # Verbosity level -1 is reserved for the command implementations to have a "quiet" mode without hiding error
        # output.
        if verbosity == Verbosity.NORMAL:
            logStdErrHandler.setLevel(logging.ERROR)

        # Verbosity level 1 is reserved for the command implementations to have a "verbose" mode without increasing the
        # log level.
        minimumVerbosityForIncreasingLogVerbosity = Verbosity.LOGVERBOSE

        # Verbose mode
        if verbosity >= minimumVerbosityForIncreasingLogVerbosity:
            stdoutHandler = logging.StreamHandler(stream=sys.stdout)
            stdoutHandler.setFormatter(logFormatter)
            # Convert verbosity level to log level numeric value (10 = Debug, 20 = INFO, 30 = WARNING); note that
            # numerical values for log levels are inversely related to verbosity levels.
            # Only supports log levels WARNING, INFO, and DEBUG. ERROR/CRITICAL will be logged to stderr by default.
            stdoutHandler.setLevel(
                max(logging.DEBUG, (logging.WARNING - (10 * (verbosity - minimumVerbosityForIncreasingLogVerbosity)))))
            # Hide log ERROR and CRITICAL logs, since they'll go to stderr.
            stdoutHandler.addFilter(MaxLogLevelFilter(logging.WARNING))
            log.addHandler(stdoutHandler)

    def run_command(self):
        self.unimplemented_function(self.run_command.__name__, self.__class__)

    def unimplemented_function(self, functionName, cls):
        raise Exception("Unimplemented function! Implement {}.{} ({}).".format(
            cls.__name__,
            functionName,
            inspect.getfile(cls)))

    def print(self, verbosity, msg, end="\n", flush=False):
        log.debug("%s", msg)
        if self.parsed_args.verbosity >= verbosity:
            print(msg, end=end, flush=flush)
            return True
        return False

    def print_n(self, msg, end="\n", flush=False):
        return self.print(Verbosity.NORMAL, msg, end=end, flush=flush)

    def print_v(self, msg, end="\n", flush=False):
        return self.print(Verbosity.APPVERBOSE, msg, end=end, flush=flush)

class Progresser():
    def __init__(self, cmd: Command, period=5):
        self.cmd = cmd
        self.period = period
        self.ticker = Ticker(period)

    def tick(self):
        if (self.cmd.parsed_args.verbosity == Verbosity.NORMAL) and self.ticker.tick():
            print(".", end="", flush=True)
            return True
        return False
    
    def done(self):
        if self.cmd.parsed_args.verbosity == Verbosity.NORMAL:
            print("done", flush=True)
            self.restart()
            return True
        self.restart()
        return False

    def restart(self):
        return self.ticker.restart()

def run_command(command):
    log.info("{}".format(" ".join(command.mArgs)), stacklevel=2)
    errorCode=command.run()
    if errorCode != 0:
        log.error("{} command gave non-zero return code: {}".format(inspect.getfile(command.__class__), errorCode), stacklevel=2)
    return errorCode