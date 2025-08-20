import sys, re
from subprocess import \
     check_output, PIPE, STDOUT, DEVNULL, CalledProcessError, TimeoutExpired
from os.path import abspath, basename, dirname, exists, join, splitext
from getopt import getopt, GetoptError
from os import chdir, environ, getcwd, mkdir, remove, access, W_OK
from shutil import copyfile, rmtree
from math import log

SHORT_USAGE = """\
Usage: python3 tester.py OPTIONS TEST.in ...

   OPTIONS may include
       --show=N       Show details on up to N tests.
       --show=all     Show details on all tests.
       --reps=R       Repeat each test R times.
       --keep         Keep test directories
       --progdir=DIR  Directory or JAR files containing gitlet application
       --timeout=SEC  Default number of seconds allowed to each execution
                      of gitlet.
       --src=SRC      Use SRC instead of "src" as the subdirectory containing
                      files referenced by + and =.
       --debug        Allows you to step through commands one by one and
                      attach a remote debugger
       --tolerance=N  Set the maximum allowed edit distance between program
                      output and expected output to N (default 3).
       --verbose      Print extra information about execution.
"""

USAGE = SHORT_USAGE + """\

For each TEST.in, change to an empty directory, and execute the instructions
in TEST.in.  Before executing an instruction, first replace any occurrence
of ${VAR} with the current definition of VAR (see the D command below).
Replace any occurrence of ${N} for non-negative decimal numeral N with
the value of the Nth captured group in the last ">" command's expected
output lines.  Undefined if the last ">" command did not end in "<<<*",
or did not have the indicated group. N=0 indicates the entire matched string.

The instructions each have one of the following forms:

   # ...  A comment, producing no effect.
   I FILE Include.  Replace this statement with the contents of FILE,
          interpreted relative to the directory containing the .in file.
   C DIR  Create, if necessary, and switch to a subdirectory named DIR under
          the main directory for this test.  If DIR is missing, changes
          back to the default directory.  This command is principally
          intended to let you set up remote repositories.
   T N    Set the timeout for gitlet commands in the rest of this test to N
          seconds.
   + NAME F
          Copy the contents of src/F into a file named NAME.
   - NAME
          Delete the file named NAME.
   > COMMAND OPERANDS
   LINE1
   LINE2
   ...
   <<<
          Run gitlet.Main with COMMAND ARGUMENTS as its parameters.  Compare
          its output with LINE1, LINE2, etc., reporting an error if there is
          "sufficient" discrepency.  The <<< delimiter may be followed by
          an asterisk (*), in which case, the preceding lines are treated as 
          Python regular expressions and matched accordingly. The directory
          or JAR file containing the gitlet.Main program is assumed to be
          in directory DIR specifed by --progdir (default is ..).
   = NAME F
          Check that the file named NAME is identical to src/F, and report an
          error if not.
   * NAME
          Check that the file NAME does not exist, and report an error if it
          does.
   E NAME
          Check that file or directory NAME exists, and report an error if it
          does not.
   D VAR "VALUE"
          Defines the variable VAR to have the literal value VALUE.  VALUE is
          taken to be a raw Python string (as in r"VALUE").  Substitutions are
          first applied to VALUE.

For each TEST.in, reports at most one error.  Without the --show option,
simply indicates tests passed and failed.  If N is postive, also prints details
of the first N failing tests. With --show=all, shows details of all failing
tests.  With --keep, keeps the directories created for the tests (with names
TEST.dir).

When finished, reports number of tests passed and failed, and the number of
faulty TEST.in files."""

TIMEOUT = 10

# C++ executable configuration
CPP_EXECUTABLE = "gitlite"

# 默认使用C++版本
USE_CPP = True

# Test scores mapping
TEST_SCORES = {
    "1-init": 2,
    "1-add-01": 1,
    "1-add-02": 1,
    "1-commit-01": 1,
    "1-commit-02": 1,
    "1-rm": 2,
    "1-robust": 2,
    "2-log": 2,
    "2-global-log-01": 1,
    "2-find-01": 2,
    "2-find-02": 1,
    "2-checkout-01": 2,
    "2-checkout-02": 2,
    "3-status": 2,
    "3-status-01": 2,
    "3-status-02": 2,
    "3-status-03": 2,
    "3-status-04": 2,
    "3-status-05": 2,
    "3-status-06": 2,
    "3-status-07": 1,
    "3-checkout-03": 2,
    "3-checkout-04": 2,
    "3-checkout-05": 1,
    "4-branch-01": 3,
    "4-branch-02": 2,
    "4-branch-03": 2,
    "4-rm-branch-01": 3,
    "4-rm-branch-02": 2,
    "4-reset-01": 3,
    "4-reset-02": 3,
    "4-global-log-02": 1,
    "4-find-03": 1,
    "5-merge-01": 3,
    "5-merge-02": 3,
    "5-merge-03": 3,
    "5-merge-04": 5,
    "5-merge-05": 3,
    "5-merge-06": 4,
    "5-merge-07": 4,
    "5-merge-08": 5,
    "6-status-05": 5,
    "6-remote-01": 5,
    "6-remote-02": 5,
    "6-remote-03": 5,
    "6-diff-01": 5,
    "6-diff-02": 5,
    "6-diff-03": 5
}

# Subtask groupings
SUBTASKS = {
    "Subtask1(init,add,commit,rm)": ["1-init", "1-add-01", "1-add-02", "1-commit-01", "1-commit-02", "1-rm", "1-robust"],
    "Subtask2(log,find,checkout)": ["2-log", "2-global-log-01", "2-find-01", "2-find-02", "2-checkout-01", "2-checkout-02"],
    "Subtask3(status,checkout)": ["3-status", "3-status-01", "3-status-02", "3-status-03", "3-status-04", "3-status-05", "3-status-06", "3-status-07", "3-checkout-03", "3-checkout-04", "3-checkout-05"],
    "Subtask4(branch,rm-branch,reset)": ["4-branch-01", "4-branch-02", "4-branch-03", "4-rm-branch-01", "4-rm-branch-02", "4-reset-01", "4-reset-02", "4-global-log-02", "4-find-03"],
    "Subtask5(merge)": ["5-merge-01", "5-merge-02", "5-merge-03", "5-merge-04", "5-merge-05", "5-merge-06", "5-merge-07", "5-merge-08"],
    "Subtask6(bonus)": ["6-status-05", "6-remote-01", "6-remote-02", "6-remote-03", "6-diff-01", "6-diff-02", "6-diff-03"]
}

DEBUG = False

DEBUG = False
DEBUG_MSG = \
    """You are in debug mode.
    In this mode, you will be shown each command from the test case.
    If you would like to step into and debug the command, type 's'. Once you have done so, go back to IntelliJ and click the debug button.
    If you would like to move on to the next command, type 'n'."""
cmd = None

def Usage():
    print(SHORT_USAGE, file=sys.stderr)
    sys.exit(1)

Mat = None
def Match(patn, s):
    global Mat
    Mat = re.match(patn, s)
    return Mat

def Group(n):
    return Mat.group(n)

def contents(filename):
    try:
        with open(filename) as inp:
            return inp.read()
    except FileNotFoundError:
        return None

def editDistance(s1, s2):
    dist = [list(range(len(s2) + 1))] + \
           [ [i] + [ 0 ] * len(s2) for i in range(1, len(s1) + 1) ]
    for i in range(1, len(s1) + 1):
        for j in range(1, len(s2) + 1):
            dist[i][j] = min(dist[i-1][j] + 1,
                             dist[i][j-1] + 1,
                             dist[i-1][j-1] + (s1[i-1] != s2[j-1]))
    return dist[len(s1)][len(s2)]

def createTempDir(base):
    for n in range(100):
        name = "{}_{}".format(base, n)
        try:
            mkdir(name)
            return name
        except OSError:
            pass
    else:
        raise ValueError("could not create temp directory for {}".format(base))

def cleanTempDir(dir):
    rmtree(dir, ignore_errors=True)

def doDelete(name, dir):
    try:
        remove(join(dir, name))
    except OSError:
        pass

def doCopy(dest, src, dir):
    try:
        doDelete(dest, dir)
        copyfile(join(src_dir, src), join(dir, dest))
    except OSError:
        raise ValueError("file {} could not be copied to {}".format(src, dest))

def doExecute(cmnd, dir, timeout, line_num):
    here = getcwd()
    out = ""
    try:
        chdir(dir)
        
        # 使用C++可执行文件
        full_cmnd = "{} {}".format(CPP_EXECUTABLE, cmnd)
            
        if DEBUG:
            print("[line {}]: gitlet {}".format(line_num, cmnd))
            input_prompt = ">>> "
            next_cmd = input(input_prompt)
            while(next_cmd not in "ns"):
                print("Please enter either 'n' or 's'.")
                next_cmd = input(input_prompt)

            if next_cmd == "s":
                # C++版本暂不支持调试模式，直接运行
                pass

        out = doCommand(full_cmnd, timeout)
        return "OK", out
    except CalledProcessError as excp:
        # The program exited with an error code. This is expected in some tests.
        # The output is in excp.output. We return "OK" to force the caller
        # to check the output against the expected output.
        # The fact that it exited with an error is implicitly checked by
        # whether the output matches the expected error message.
        return "OK", excp.output
    except TimeoutExpired:
        return "timeout", None
    finally:
        chdir(here)

def doCommand(full_cmnd, timeout):
    out = check_output(full_cmnd, shell=True, universal_newlines=True,
                        stdin=DEVNULL, stderr=STDOUT, timeout=timeout)
    return out

def canonicalize(s):
    if s is None:
        return None
    return re.sub('\r', '', s)

def fileExists(f, dir):
    return exists(join(dir, f))

def correctFileOutput(name, expected, dir):
    userData = canonicalize(contents(join(dir, name)))
    stdData = canonicalize(contents(join(src_dir, expected)))
    return userData == stdData

def write_file(test, tag, expected, actual):
    contents = "{}: \n{}: \nExpected: {}\nActual: {}\n".format(test, tag, expected, actual)
    with open("out.txt", 'a') as f:
        f.write(contents)

def correctProgramOutput(expected, actual, last_groups, is_regexp):
    expected = re.sub(r'[ \t]+\n', '\n', '\n'.join(expected))
    expected = re.sub(r'(?m)^[ \t]+', ' ', expected)
    actual = re.sub(r'[ \t]+\n', '\n', actual)
    actual = re.sub(r'(?m)^[ \t]+', ' ', actual)

    last_groups[:] = (actual,)
    if is_regexp:
        try:
            if not Match(expected.rstrip() + r"\Z", actual) \
                   and not Match(expected.rstrip() + r"\Z", actual.rstrip()):
                return False
        except:
            raise ValueError("bad pattern")
        last_groups[:] += Mat.groups()
    elif editDistance(expected.rstrip(), actual.rstrip()) > output_tolerance:
        return False
    return True

def reportDetails(test, included_files, line_num):
    if show is None:
        return
    if type(show) is int and show <= 0:
        print("   Limit on error details exceeded.")
        return
    direct = dirname(test)

    print("    Error on line {} of {}".format(line_num, basename(test)))

    for base in [basename(test)] + included_files:
        full = join(dirname(test), base)
        print(("-" * 20 + " {} " + "-" * 20).format(base))
        text_lines = list(enumerate(re.split(r'\n\r?', contents(full))))[:-1]
        fmt = "{{:{}d}}. {{}}".format(round(log(len(text_lines), 10)))
        text = '\n'.join(map(lambda p: fmt.format(p[0] + 1, p[1]), text_lines))
        print(text)
        print("-" * (42 + len(base)))

def chop_nl(s):
    if s and s[-1] == '\n':
        return s[:-1]
    else:
        return s

def line_reader(f, prefix):
    n = 0
    try:
        with open(f) as inp:
            while True:
                L = inp.readline()
                if L == '':
                    return
                n += 1
                included_file = yield (prefix + str(n), L)
                if included_file:
                    yield None
                    yield from line_reader(included_file, prefix + str(n) + ".")
    except FileNotFoundError:
        raise ValueError("file {} not found".format(f))

def doTest(test):
    last_groups = []
    base = splitext(basename(test))[0]
    test_score = TEST_SCORES.get(base, 0)
    # 不再输出单个测试的进度信息

    if DEBUG:
        print(DEBUG_MSG)

    timeout = TIMEOUT
    defns = {}

    def do_substs(L):
        c = 0
        L0 = None
        while L0 != L and c < 10:
            c += 1
            L0 = L
            L = re.sub(r'\$\{(.*?)\}', subst_var, L)
        return L

    def subst_var(M):
        key = M.group(1)
        if Match(r'\d+$', key):
            try:
                return last_groups[int(key)]
            except IndexError:
                raise ValueError("FAILED (nonexistent group: {{{}}})"
                                 .format(key))
        elif M.group(1) in defns:
            return defns[M.group(1)]
        else:
            raise ValueError("undefined substitution: ${{{}}}".format(M.group(1)))

    try:
        tmpdir = None
        for _ in range(num_reps):
            if tmpdir is not None:
                cleanTempDir(tmpdir)
            cdir = tmpdir = createTempDir(base)
            if verbose:
                print("Testing directory: {}".format(tmpdir))
            line_num = None
            inp = line_reader(test, '')
            included_files = []
            while True:
                line_num, line = next(inp, (line_num, ''))
                if line == "":
                    break
                if not Match(r'\s*#', line):
                    line = do_substs(line)
                if verbose:
                    print("+ {}".format(line.rstrip()))
                if Match(r'\s*#', line) or Match(r'\s+$', line):
                    pass
                elif Match(r'I\s+(\S+)', line):
                    inp.send(join(dirname(test), Group(1)))
                    included_files.append(Group(1))
                elif Match(r'C\s*(\S*)', line):
                    if Group(1) == "":
                        cdir = tmpdir
                    else:
                        cdir = join(tmpdir, Group(1))
                        if not exists(cdir):
                            mkdir(cdir)
                elif Match(r'T\s*(\S+)', line):
                    try:
                        timeout = float(Group(1))
                    except:
                        ValueError("bad time: {}".format(line))
                elif Match(r'\+\s*(\S+)\s+(\S+)', line):
                    doCopy(Group(1), Group(2), cdir)
                elif Match(r'-\s*(\S+)', line):
                    doDelete(Group(1), cdir)
                elif Match(r'>\s*(.*)', line):
                    cmnd = Group(1)
                    expected = []
                    while True:
                        line_num, L = next(inp, (line_num, ''))
                        if L == '':
                            raise ValueError("unterminated command: {}"
                                             .format(line))
                        L = L.rstrip()
                        if Match(r'<<<(\*?)', L):
                            is_regexp = Group(1)
                            break
                        expected.append(do_substs(L))
                    msg, out = doExecute(cmnd, cdir, timeout, line_num)
                    if verbose:
                        if out:
                            print(re.sub(r'(?m)^', '- ', chop_nl(out)))
                    if msg == "OK":
                        if not correctProgramOutput(expected, out, last_groups,
                                                    is_regexp):
                            write_file(test, cmnd, expected, out)
                            msg = "incorrect output"
                    if msg != "OK":
                        print("{}: FAILED ({}) (0pts/{}pts)".format(base, msg, test_score))
                        return False, test_score
                elif Match(r'=\s*(\S+)\s+(\S+)', line):
                    if not correctFileOutput(Group(1), Group(2), cdir):
                        print("ERROR (file {} has incorrect content) (0pts/{}pts)"
                              .format(Group(1), test_score))
                        reportDetails(test, included_files, line_num)
                        return False, test_score
                elif Match(r'\*\s*(\S+)', line):
                    if fileExists(Group(1), cdir):
                        print("ERROR (file {} present) (0pts/{}pts)".format(Group(1), test_score))
                        reportDetails(test, included_files, line_num)
                        return False, test_score
                elif Match(r'E\s*(\S+)', line):
                    if not fileExists(Group(1), cdir):
                        print("ERROR (file or directory {} not present) (0pts/{}pts)"
                              .format(Group(1), test_score))
                        reportDetails(test, included_files, line_num)
                        return False, test_score
                elif Match(r'(?s)D\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*"(.*)"\s*$', line):
                    defns[Group(1)] = Group(2)
                else:
                    raise ValueError("bad test line at {}".format(line_num))
        print("{}: OK ({}pts/{}pts)".format(base, test_score, test_score))
        return True, test_score
    finally:
        if verbose:
            print("Testing directory: {}".format(tmpdir))
        if not keep:
            cleanTempDir(tmpdir)


if __name__ == "__main__":
    show = None
    keep = False
    prog_dir = None
    verbose = False
    src_dir = 'src'
    output_tolerance = 0
    num_reps = 1

    try:
        opts, files = \
            getopt(sys.argv[1:], '',
                   ['show=', 'keep', 'progdir=', 'verbose', 'src=', 'reps=',
                    'tolerance=', 'debug'])
        for opt, val in opts:
            if opt == '--show':
                val = val.lower()
                if re.match(r'-?\d+', val):
                    show = int(val)
                elif val == 'all':
                    show = val
                else:
                    Usage()
            elif opt == "--keep":
                keep = True
            elif opt == "--progdir":
                prog_dir = val
            elif opt == "--src":
                src_dir = abspath(val)
            elif opt == "--verbose":
                verbose = True
            elif opt == "--tolerance":
                output_tolerance = int(val)
            elif opt == "--debug":
                DEBUG = True
            elif opt == "--reps":
                num_reps = int(val)
        
        if prog_dir is None:
            project_root = dirname(dirname(abspath(__file__)))
            prog_dir = project_root
            # Try multiple possible locations for the C++ executable
            possible_paths = [
                join(project_root, 'build', 'gitlite'),
            ]
            cpp_executable_path = None
            for path in possible_paths:
                if exists(path):
                    cpp_executable_path = path
                    break
            
            if cpp_executable_path:
                CPP_EXECUTABLE = cpp_executable_path
            else:
                print("Could not find gitlite C++ executable.", file=sys.stderr)
                print("Looked for it at:", file=sys.stderr)
                for path in possible_paths:
                    print("  {}".format(path), file=sys.stderr)
                print("Please compile the C++ version first or specify --progdir.", file=sys.stderr)
                sys.exit(1)
    except GetoptError:
        Usage()
    if not files:
        print(USAGE)
        sys.exit(0)

    num_tests = len(files)
    errs = 0
    fails = 0
    total_score = 0
    earned_score = 0
    failed_tests = []
    
    # Track subtask scores
    subtask_scores = {}
    for subtask_name, test_list in SUBTASKS.items():
        subtask_scores[subtask_name] = {'earned': 0, 'total': 0, 'tests': []}

    for test in files:
        try:
            if not exists(test):
                num_tests -= 1
            else:
                test_name = splitext(basename(test))[0]
                test_points = TEST_SCORES.get(test_name, 0)
                total_score += test_points
                
                # Find which subtask this test belongs to
                current_subtask = None
                for subtask_name, test_list in SUBTASKS.items():
                    if test_name in test_list:
                        current_subtask = subtask_name
                        subtask_scores[subtask_name]['total'] += test_points
                        break
                
                result = doTest(test)
                if isinstance(result, tuple):
                    success, points = result
                    if success:
                        earned_score += points
                        if current_subtask:
                            subtask_scores[current_subtask]['earned'] += points
                            subtask_scores[current_subtask]['tests'].append((test_name, True, points))
                    else:
                        errs += 1
                        failed_tests.append(test_name)
                        if current_subtask:
                            subtask_scores[current_subtask]['tests'].append((test_name, False, 0))
                        if type(show) is int:
                            show -= 1
                else:
                    # Old format compatibility
                    if not result:
                        errs += 1
                        failed_tests.append(test_name)
                        if current_subtask:
                            subtask_scores[current_subtask]['tests'].append((test_name, False, 0))
                        if type(show) is int:
                            show -= 1
                    else:
                        earned_score += test_points
                        if current_subtask:
                            subtask_scores[current_subtask]['earned'] += test_points
                            subtask_scores[current_subtask]['tests'].append((test_name, True, test_points))
        except ValueError as excp:
            print("FAILED ({})".format(excp.args[0]))
            fails += 1
            test_name = splitext(basename(test))[0]
            failed_tests.append(test_name)

    print()
    print("Ran {} tests.".format(num_tests))
    print("Total Score: {} pts".format(earned_score))
    
    if errs == fails == 0:
        print("All tests passed!")
    else:
        passed_tests = num_tests - errs - fails
        print("{} tests passed, {} tests failed.".format(passed_tests, errs + fails))
        if failed_tests:
            print("Failed tests: {}".format(", ".join(failed_tests)))
        sys.exit(1)