import os
import time

import log_utils
import string
import random
import subprocess

log = log_utils.get_logger(f"{os.path.basename(__file__)}")

class Ticker():
    def __init__(self, period=5):
        self.period = period
        self.last_time = None

    def restart(self):
        last = bool(self.last_time)
        self.last_time = None
        return last

    def tick(self):
        new_time = time.time()
        if self.last_time is None or (new_time - self.last_time) >= self.period:
            self.last_time = new_time
            return True
        return False

def create_tmp_file(baseFilename=None, mutate=False, maxRetries=2):
    if baseFilename == None:
        baseFilename = "/tmp/" + "".join(random.choice(string.ascii_lowercase) for i in range(15))
        mutate = True
    filenameSuffix = ""
    ex = None
    attemptNum = 1
    while maxRetries < 0 or attemptNum <= 1 + maxRetries:
        filename = baseFilename + filenameSuffix
        try:
            return open(filename, 'x')
        except Exception as e:
            log.debug("Exception while creating tmp file (attempt %d): %s", attemptNum, filename)
            ex = e
        attemptNum+=1
        if mutate:
            filenameSuffix = ".{}".format(attemptNum)
    raise ex

def run_subprocess(
    cmdArgs,
    shell=False,
    timeout=0,
    throwOnStdErr=True,
    expectedReturnCode=0,
    throwOnUnexpectedReturnCode=True,
    logAndReturnStdout=True,
    stdoutFilePath=None,
    stderrFilePath=None
):
    fullCmd = " ".join(cmdArgs)
    stdoutFile = None
    stderrFile = None
    try:
        if stdoutFilePath is not None:
            stdoutFile = open(stdoutFilePath, 'w')
        else:
            stdoutFile = create_tmp_file()
        if stderrFilePath is not None:
            stderrFile = open(stderrFilePath, 'w')
        else:
            stderrFile = create_tmp_file()
        log.debug(
            "command (stdoutFile=%s, stderrFile=%s, shell=%s): %s",
            stdoutFile.name,
            stderrFile.name,
            shell,
            fullCmd)
        # Do NOT use subprocess.run(). Some commands seem to hang, probably because of issues with directing
        # stdout/stderr to in-memory "pipes". subprocess.run() does not have the option to specify output files for
        # stdout and stderr.
        subp = subprocess.Popen(fullCmd if shell else cmdArgs, shell=shell, stdout=stdoutFile, stderr=stderrFile)
        subp.stdoutFilePath = stdoutFile.name
        subp.stderrFilePath = stderrFile.name
        if timeout==0:
            success=False
            while not success:
                try:
                    subp.communicate(timeout=60)
                    success=True
                except subprocess.TimeoutExpired as e:
                    log.debug(e)
        else:
            try:
                subp.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                subp.kill()
                subp.communicate()
                raise
        subp.stdout = None
        if logAndReturnStdout:
            with open(stdoutFile.name, 'r') as stdoutFile2:
                for line in stdoutFile2:
                    if subp.stdout == None:
                        log.debug("stdout (%s):", stdoutFile2.name)
                        subp.stdout = ""
                    log.debug("%s", line.rstrip('\n'))
                    # TODO Do something better/more efficient in case the file is very large
                    subp.stdout = subp.stdout + line
        subp.stderr = None
        with open(stderrFile.name, 'r') as stderrFile2:
            for line in stderrFile2:
                if subp.stderr == None:
                    log.debug("stderr (%s):", stderrFile2.name)
                    subp.stderr = ""
                log.debug("%s", line.rstrip('\n'))
                # TODO Do something better/more efficient in case the file is very large
                subp.stderr = subp.stderr + line
        if subp.stderr and len(subp.stderr) > 0:
            if throwOnStdErr:
                raise Exception("stderr output during command: {}: {}".format(fullCmd, subp.stderr[0:256]))
        # TODO After logging stdout/stderr, delete the files (only in success case?)
        if throwOnUnexpectedReturnCode and not subp.returncode == expectedReturnCode:
            raise Exception("Unexpected return code ({}, expected {}): {}".format(
                subp.returncode,
                expectedReturnCode,
                fullCmd))
        return subp
    finally:
        if stdoutFile is not None:
            stdoutFile.close()
        if stderrFile is not None:
            stderrFile.close()
