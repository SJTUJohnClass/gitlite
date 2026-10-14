import sys, re, shlex, difflib, time
from datetime import datetime
from subprocess import \
     check_output, PIPE, STDOUT, DEVNULL, CalledProcessError, TimeoutExpired
from os.path import abspath, basename, dirname, exists, isfile, join, splitext
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
       --progdir=DIR  Project/build directory containing the gitlite executable,
                      or the executable path itself.
       --timeout=SEC  Default number of seconds allowed to each execution
                      of gitlite.
       --src=SRC      Use SRC instead of "src" as the subdirectory containing
                      files referenced by + and =.
       --debug        Pause before each command.
       --tolerance=N  Set the maximum allowed edit distance between program
                      output and expected output to N (default 0).
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
   T N    Set the timeout for gitlite commands in the rest of this test to N
          seconds.
   P N    Pause the test for N seconds. This is useful when distinct commit
          timestamps are required.
   + NAME F
          Copy the contents of src/F into a file named NAME.
   N NAME F
          Copy src/F into NAME after removing one final newline byte. This is
          useful for testing end-of-file newline handling.
   - NAME
          Delete the file named NAME.
   > COMMAND OPERANDS
   LINE1
   LINE2
   ...
   <<<
          Run gitlite with COMMAND ARGUMENTS as its parameters. Compare
          its output with LINE1, LINE2, etc., reporting an error if there is
          "sufficient" discrepancy. The <<< delimiter may be followed by
          an asterisk (*), in which case, the preceding lines are treated as
          Python regular expressions and matched accordingly, or G, in which
          case they are expected commit IDs for a strictly checked global-log.
          The directory
          The executable is found from the project containing tester.py unless
          --progdir is provided.
   = NAME F
          Check that the file named NAME is identical to src/F, and report an
          error if not. CRLF and LF text line endings are treated alike.
   B NAME F
          Compare NAME with src/F byte-for-byte (for binary and line-ending
          preservation tests).
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
   A PREFIX_VAR ASSET_VAR ID ASSET [ID ASSET ...]
          Find the shortest prefix shared by at least two candidate IDs. Store
          that prefix and the asset paired with the lexicographically first
          match. An ID paired with !exclude participates only as an excluded
          object: the chosen prefix must not match it.

For each TEST.in, reports at most one error.  Without the --show option,
simply indicates tests passed and failed. If N is positive, also prints details
of the first N failing tests. With --show=all, shows details of all failing
tests.  With --keep, keeps the directories created for the tests (with names
TEST.dir).

When finished, reports number of tests passed and failed, and the number of
faulty TEST.in files."""

TIMEOUT = 10

# C++ executable configuration
CPP_EXECUTABLE = "gitlite"

# Test scores mapping
TEST_SCORES = {
    "1-init": 1,
    "1-add-01": 1,
    "1-add-02": 1,
    "1-add-03": 1,
    "1-commit-01": 1,
    "1-commit-02": 1,
    "1-rm": 1,
    "1-robust": 2,
    "1-ignore-add": 1,
    "2-log": 2,
    "2-global-log": 2,
    "2-tag-01": 2,
    "2-tag-02": 2,
    "2-robust": 2,
    "3-status-01": 1,
    "3-status-02": 1,
    "3-status-03": 1,
    "3-status-04": 1,
    "3-status-05": 1,
    "3-status-06": 1,
    "3-status-07": 1,
    "3-status-08": 1,
    "3-status-09": 1,
    "3-branch-01": 1,
    "3-branch-02": 1,
    "3-rm-branch": 1,
    "3-robust": 1,
    "3-status-10": 1,
    "3-status-11": 1,
    "4-checkout-01": 1,
    "4-checkout-02": 1,
    "4-checkout-03": 1,
    "4-checkout-04": 1,
    "4-checkout-05": 1,
    "4-checkout-06": 1,
    "4-checkout-07": 1,
    "4-checkout-08": 1,
    "4-checkout-09": 1,
    "4-checkout-10": 1,
    "4-checkout-11": 1,
    "4-reset-01": 1,
    "4-reset-02": 1,
    "4-reset-03": 1,
    "4-robust": 1,
    "5-merge-01": 1,
    "5-merge-02": 2,
    "5-merge-03": 2,
    "5-merge-04": 1,
    "5-merge-05": 2,
    "5-merge-06": 1,
    "5-merge-07": 2,
    "5-merge-08": 1,
    "5-merge-09": 1,
    "5-merge-10": 1,
    "5-robust": 1,
    "Comp-init": 1,
    "Comp-add-01": 1,
    "Comp-add-02": 1,
    "Comp-commit-01": 1,
    "Comp-commit-02": 1,
    "Comp-ignore-add": 1,
    "Comp-rm": 1,
    "Comp-global-log": 1,
    "Comp-log": 1,
    "Comp-robust": 1,
    "Bonus-remote-01": 3,
    "Bonus-remote-02": 4,
    "Bonus-remote-03": 4,
    "Bonus-remote-04": 2,
    "Bonus-remote-robust": 2,
    "Bonus-diff-01": 2,
    "Bonus-diff-02": 3,
    "Bonus-diff-03": 2,
    "Bonus-show-01": 2,
    "Bonus-show-02": 2,
    "Bonus-show-03": 2,
    "Bonus-diff-robust": 2
}

# Subtask groupings
SUBTASKS = {
    "Subtask1(init,add,commit,rm)": ["1-init", "1-add-01", "1-add-02", "1-commit-01", "1-commit-02", "1-rm", "1-add-03", "1-robust", "1-ignore-add"],
    "Subtask2(log,global-log,tag)": ["2-log", "2-global-log", "2-tag-01", "2-tag-02", "2-robust"],
    "Subtask3(status,branch,rm-branch)": ["3-status-01", "3-status-02", "3-status-03", "3-status-04", "3-status-05", "3-status-06", "3-status-07", "3-status-08", "3-status-09", "3-status-10", "3-status-11", "3-branch-01", "3-branch-02", "3-rm-branch", "3-robust"],
    "Subtask4(checkout,reset)": ["4-checkout-01", "4-checkout-02", "4-checkout-03", "4-checkout-04", "4-checkout-05", "4-checkout-06", "4-checkout-07", "4-checkout-08", "4-checkout-09", "4-checkout-10", "4-checkout-11", "4-reset-01", "4-reset-02", "4-reset-03", "4-robust"],
    "Subtask5(merge)": ["5-merge-01", "5-merge-02", "5-merge-03", "5-merge-04", "5-merge-05", "5-merge-06", "5-merge-07", "5-merge-08", "5-merge-09", "5-merge-10", "5-robust"],
    "Complement": ["Comp-init", "Comp-add-01", "Comp-add-02", "Comp-commit-01", "Comp-commit-02", "Comp-ignore-add", "Comp-rm", "Comp-log", "Comp-global-log", "Comp-robust"],
    "Bonus": ["Bonus-remote-01", "Bonus-remote-02", "Bonus-remote-03", "Bonus-remote-04", "Bonus-remote-robust", "Bonus-diff-01", "Bonus-diff-02", "Bonus-diff-03", "Bonus-show-01", "Bonus-show-02", "Bonus-show-03", "Bonus-diff-robust"]
}

# Bonus has two independent 15-point choices. Its final score is the larger
# category score; points from the two choices are never added together.
SUBTASK_CAPS = {"Bonus": 15}
BONUS_CATEGORIES = {
    "Remote": [name for name in SUBTASKS["Bonus"] if "-remote-" in name],
    "Diff+Show": [name for name in SUBTASKS["Bonus"]
                  if "-diff-" in name or "-show-" in name],
}

# Keep per-test result labels aligned within each subtask.  The colon is part
# of the padded name column; two spaces separate it from the status column.
TEST_TO_SUBTASK = {
    test_name: subtask_name
    for subtask_name, test_names in SUBTASKS.items()
    for test_name in test_names
}
SUBTASK_TEST_NAME_WIDTHS = {
    subtask_name: max(map(len, test_names))
    for subtask_name, test_names in SUBTASKS.items()
}


def format_test_status(test_name, status):
    subtask_name = TEST_TO_SUBTASK.get(test_name)
    name_width = SUBTASK_TEST_NAME_WIDTHS.get(subtask_name, len(test_name))
    return "{:<{}}  {}".format(test_name + ":", name_width + 1, status)

# Tests are isolated, so dependencies are grading prerequisites rather than
# shared setup.  The runner topologically orders them and skips a dependent
# test when any prerequisite fails or is skipped.
TEST_DEPENDENCIES = {
    "1-add-01": ["1-init"], "1-add-02": ["1-init"],
    "1-add-03": ["1-commit-02", "1-rm"],
    "1-ignore-add": ["1-commit-02"],
    "1-commit-01": ["1-init"], "1-commit-02": ["1-add-01"],
    "1-rm": ["1-commit-02"],
    "2-log": ["1-commit-02"], "2-global-log": ["2-log"],
    "2-tag-01": ["1-commit-02"],
    "2-tag-02": ["2-log", "2-tag-01"],
    "2-robust": ["2-log", "2-global-log", "2-tag-01"],
    "3-status-01": ["1-init"], "3-status-02": ["1-commit-02", "1-rm"],
    "3-status-03": ["1-add-01"], "3-status-04": ["1-commit-02", "1-rm"],
    "3-status-05": ["1-rm"], "3-status-06": ["1-commit-02", "1-rm"],
    "3-status-07": ["1-commit-02", "1-rm"],
    "3-status-09": ["1-add-01", "1-commit-02"],
    "3-branch-01": ["3-status-10"], "3-branch-02": ["3-branch-01"],
    "3-rm-branch": ["3-branch-01"],
    "3-robust": ["3-status-01", "3-branch-01", "3-rm-branch"],
    "3-status-10": ["1-commit-02", "1-rm", "3-status-01"],
    "3-status-11": ["1-ignore-add", "2-tag-01", "3-status-01", "3-status-10"],
    "4-checkout-01": ["1-commit-02"],
    "4-checkout-02": ["2-log", "4-checkout-01"],
    "4-checkout-03": ["2-log", "4-checkout-02"],
    "4-checkout-04": ["2-log", "3-status-10", "4-checkout-02"],
    "4-checkout-05": ["2-log", "3-status-01", "4-checkout-02"],
    "4-checkout-06": ["2-log", "2-tag-01", "3-branch-01", "3-status-10", "4-checkout-02"],
    "4-checkout-07": ["1-commit-02", "3-branch-01", "3-status-10"],
    "4-checkout-08": ["2-log", "4-checkout-07"],
    "4-checkout-09": ["3-rm-branch", "4-checkout-07"],
    "4-checkout-10": ["1-ignore-add", "1-rm", "3-status-11", "4-checkout-07"],
    "4-checkout-11": ["3-branch-02", "4-checkout-07"],
    "4-reset-01": ["1-rm", "2-log", "4-checkout-07"],
    "4-reset-02": ["3-status-11", "4-reset-01"],
    "4-reset-03": ["2-tag-01", "4-reset-01"],
    "4-robust": ["4-checkout-01", "4-reset-01"],
    "5-merge-01": ["1-rm", "2-log", "4-checkout-07"],
    "5-merge-02": ["5-merge-01"], "5-merge-03": ["5-merge-01"],
    "5-merge-04": ["3-status-11", "5-merge-01"], "5-merge-05": ["5-merge-01"],
    "5-merge-06": ["5-merge-01"], "5-merge-07": ["5-merge-02"],
    "5-merge-08": ["5-merge-01"], "5-merge-09": ["5-merge-01"],
    "5-merge-10": ["5-merge-01"],
    "5-robust": ["5-merge-01"],
    "Comp-init": ["1-init", "2-log", "3-status-01"],
    "Comp-add-01": ["1-add-01", "1-add-02", "1-commit-02", "1-rm", "3-status-01"],
    "Comp-add-02": ["1-add-03", "1-commit-02", "1-rm", "3-status-10"],
    "Comp-commit-01": ["1-commit-01", "2-log", "3-status-01"],
    "Comp-commit-02": ["1-commit-02", "3-status-01", "4-checkout-01"],
    "Comp-ignore-add": ["1-ignore-add", "3-status-01", "4-checkout-01"],
    "Comp-rm": ["1-rm", "3-status-04"],
    "Comp-log": ["2-log", "5-merge-01"],
    "Comp-global-log": ["2-global-log", "2-tag-01", "3-rm-branch", "4-checkout-02", "4-checkout-07", "4-reset-01", "5-merge-01"],
    "Comp-robust": ["1-robust", "1-rm", "2-robust", "3-status-01", "4-checkout-01"],
    "Bonus-remote-01": ["2-global-log", "4-reset-01"], "Bonus-remote-02": ["Bonus-remote-01", "5-merge-01"],
    "Bonus-remote-03": ["Bonus-remote-01"], "Bonus-remote-04": ["Bonus-remote-01"],
    "Bonus-remote-robust": ["Bonus-remote-01"],
    "Bonus-diff-01": ["1-commit-02", "3-status-10", "4-checkout-01"],
    "Bonus-diff-02": ["1-rm", "2-log", "2-tag-01", "Bonus-diff-01"],
    "Bonus-diff-03": ["2-log", "2-tag-01", "Bonus-diff-01"],
    "Bonus-show-01": ["2-log", "3-status-10", "Bonus-diff-01"],
    "Bonus-show-02": ["2-tag-02", "Bonus-show-01"],
    "Bonus-show-03": ["5-merge-01", "Bonus-show-01"],
    "Bonus-diff-robust": ["Bonus-diff-03", "Bonus-show-02"],
}

DEBUG = False
DEBUG_MSG = \
    """You are in debug mode.
    In this mode, you will be shown each command from the test case.
    Enter 's' to run the command, or 'n' to run it and continue."""
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

def doCopyWithoutFinalNewline(dest, src, dir):
    try:
        doDelete(dest, dir)
        with open(join(src_dir, src), 'rb') as inp:
            data = inp.read()
        if data.endswith(b'\n'):
            data = data[:-1]
        with open(join(dir, dest), 'wb') as out:
            out.write(data)
    except OSError:
        raise ValueError("file {} could not be copied to {}".format(src, dest))

def doExecute(cmnd, dir, timeout, line_num):
    here = getcwd()
    out = ""
    try:
        chdir(dir)
        
        full_cmnd = [CPP_EXECUTABLE] + shlex.split(cmnd)
            
        if DEBUG:
            print("[line {}]: gitlite {}".format(line_num, cmnd))
            input_prompt = ">>> "
            next_cmd = input(input_prompt)
            while next_cmd not in ("n", "s"):
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
    out = check_output(full_cmnd, shell=False, universal_newlines=True,
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

def correctFileBytes(name, expected, dir):
    try:
        with open(join(dir, name), 'rb') as actual_file:
            actual = actual_file.read()
        with open(join(src_dir, expected), 'rb') as expected_file:
            wanted = expected_file.read()
        return actual == wanted
    except OSError:
        return False

def write_file(test, tag, expected, actual):
    expected_text = '\n'.join(expected) if isinstance(expected, list) else str(expected)
    actual_text = '' if actual is None else str(actual)
    delta = ''.join(difflib.unified_diff(
        expected_text.splitlines(True), actual_text.splitlines(True),
        fromfile='expected', tofile='actual'))
    report = "{}:\ncommand/check: {}\nExpected:\n{}\nActual:\n{}\nDiff:\n{}\n".format(
        test, tag, expected_text, actual_text, delta or '(no textual diff)')
    with open("out.txt", 'a') as f:
        f.write(report)

def write_file_comparison(test, name, expected, directory, exact):
    actual_path, expected_path = join(directory, name), join(src_dir, expected)
    try:
        actual = open(actual_path, 'rb').read()
    except OSError:
        actual = b''
    try:
        wanted = open(expected_path, 'rb').read()
    except OSError:
        wanted = b''
    if not exact:
        actual = actual.replace(b'\r', b'')
        wanted = wanted.replace(b'\r', b'')
    try:
        write_file(test, "file " + name,
                   wanted.decode('utf-8').splitlines(), actual.decode('utf-8'))
    except UnicodeDecodeError:
        write_file(test, "binary file " + name,
                   [wanted.hex(' ')], actual.hex(' '))

def correctProgramOutput(expected, actual, last_groups, is_regexp):
    expected = '\n'.join(expected)
    actual = canonicalize(actual)
    # The DSL represents lines rather than the final line terminator. Accept
    # exactly one terminal newline difference, but no other whitespace changes.
    candidates = [actual]
    if actual.endswith('\n'):
        candidates.append(actual[:-1])

    if is_regexp:
        match = None
        try:
            for candidate in candidates:
                if Match(expected + r"\Z", candidate):
                    match = Mat
                    break
        except:
            raise ValueError("bad pattern")
        if match is None:
            return False
        last_groups[:] = (actual,) + match.groups()
    elif min(editDistance(expected, candidate) for candidate in candidates) > output_tolerance:
        return False
    else:
        last_groups[:] = (actual,)
    return True


def correctGlobalLogOutput(expected, actual, last_groups):
    """Check exact commit set, uniqueness, and required global-log ordering."""
    require_tie = "@require-timestamp-tie" in (line.strip() for line in expected)
    wanted = [line.strip() for line in expected
              if line.strip() and line.strip() != "@require-timestamp-tie"]
    if any(re.fullmatch(r'[0-9a-f]{40}', commit_id) is None for commit_id in wanted):
        raise ValueError("bad commit id in global-log expectation")
    if len(wanted) != len(set(wanted)):
        raise ValueError("duplicate commit id in global-log expectation")

    actual = canonicalize(actual)
    header = re.compile(r'(?m)^===\ncommit ([0-9a-f]{40})\n')
    starts = list(header.finditer(actual))
    if not starts or starts[0].start() != 0:
        return False

    entries = []
    date_pattern = re.compile(
        r'(?m)^Date: [A-Za-z]{3} [A-Za-z]{3} \d{2} '
        r'\d{2}:\d{2}:\d{2} \d{4} [+-]\d{4}$')
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(actual)
        block = actual[match.start():end]
        dates = date_pattern.findall(block)
        if len(dates) != 1:
            return False
        try:
            timestamp = datetime.strptime(
                dates[0][len("Date: "):], "%a %b %d %H:%M:%S %Y %z").timestamp()
        except ValueError:
            return False
        entries.append((match.group(1), timestamp))

    actual_ids = [commit_id for commit_id, _ in entries]
    if len(actual_ids) != len(set(actual_ids)) or set(actual_ids) != set(wanted):
        return False
    if require_tie and len({timestamp for _, timestamp in entries}) == len(entries):
        return False
    ordered = sorted(entries, key=lambda entry: (-entry[1], entry[0]))
    if entries != ordered:
        return False
    last_groups[:] = (actual,)
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
                elif Match(r'P\s*(\S+)', line):
                    try:
                        time.sleep(float(Group(1)))
                    except ValueError:
                        raise ValueError("bad pause: {}".format(line))
                elif Match(r'\+\s*(\S+)\s+(\S+)', line):
                    doCopy(Group(1), Group(2), cdir)
                elif Match(r'N\s+(\S+)\s+(\S+)', line):
                    doCopyWithoutFinalNewline(Group(1), Group(2), cdir)
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
                        if Match(r'<<<([*G]?)\Z', L):
                            comparison = Group(1)
                            break
                        expected.append(do_substs(L))
                    msg, out = doExecute(cmnd, cdir, timeout, line_num)
                    if verbose:
                        if out:
                            print(re.sub(r'(?m)^', '- ', chop_nl(out)))
                    if msg == "OK":
                        if comparison == 'G':
                            correct = correctGlobalLogOutput(expected, out, last_groups)
                        else:
                            correct = correctProgramOutput(expected, out, last_groups,
                                                           comparison == '*')
                        if not correct:
                            write_file(test, cmnd, expected, out)
                            reportDetails(test, included_files, line_num)
                            msg = "incorrect output"
                    if msg != "OK":
                        if msg != "incorrect output":
                            write_file(test, cmnd, ["command completed"], msg)
                        print(format_test_status(
                            base, "FAILED ({}) (0pts/{}pts)".format(msg, test_score)))
                        return False, test_score
                elif Match(r'=\s*(\S+)\s+(\S+)', line):
                    if not correctFileOutput(Group(1), Group(2), cdir):
                        write_file_comparison(test, Group(1), Group(2), cdir, False)
                        print(format_test_status(
                            base, "FAILED (file {} has incorrect content) (0pts/{}pts)"
                            .format(Group(1), test_score)))
                        reportDetails(test, included_files, line_num)
                        return False, test_score
                elif Match(r'B\s+(\S+)\s+(\S+)', line):
                    if not correctFileBytes(Group(1), Group(2), cdir):
                        write_file_comparison(test, Group(1), Group(2), cdir, True)
                        print(format_test_status(
                            base, "FAILED (file {} differs byte-for-byte) (0pts/{}pts)"
                            .format(Group(1), test_score)))
                        reportDetails(test, included_files, line_num)
                        return False, test_score
                elif Match(r'\*\s*(\S+)', line):
                    if fileExists(Group(1), cdir):
                        write_file(test, "absence of " + Group(1), ["file absent"], "file present")
                        print(format_test_status(
                            base, "FAILED (file {} present) (0pts/{}pts)"
                            .format(Group(1), test_score)))
                        reportDetails(test, included_files, line_num)
                        return False, test_score
                elif Match(r'E\s*(\S+)', line):
                    if not fileExists(Group(1), cdir):
                        write_file(test, "existence of " + Group(1), ["file present"], "file absent")
                        print(format_test_status(
                            base, "FAILED (file or directory {} not present) (0pts/{}pts)"
                            .format(Group(1), test_score)))
                        reportDetails(test, included_files, line_num)
                        return False, test_score
                elif Match(r'(?s)D\s*([a-zA-Z_][a-zA-Z_0-9]*)\s*"(.*)"\s*$', line):
                    defns[Group(1)] = Group(2)
                elif line.startswith('A '):
                    parts = shlex.split(line)
                    if len(parts) < 7 or (len(parts) - 3) % 2:
                        raise ValueError("bad ambiguous-prefix instruction")
                    prefix_var, asset_var = parts[1], parts[2]
                    pairs = list(zip(parts[3::2], parts[4::2]))
                    candidates = []
                    excluded = []
                    for commit_id, asset in pairs:
                        if not re.fullmatch(r'[0-9a-f]{40}', commit_id):
                            raise ValueError("bad commit id in A instruction")
                        (excluded if asset == '!exclude' else candidates).append(
                            (commit_id, asset))
                    choice = None
                    for prefix_length in range(1, 40):
                        buckets = {}
                        for commit_id, asset in candidates:
                            buckets.setdefault(commit_id[:prefix_length], []).append(
                                (commit_id, asset))
                        choices = sorted(
                            prefix for prefix, values in buckets.items()
                            if len(values) >= 2
                            and not any(commit_id.startswith(prefix)
                                        for commit_id, _ in excluded))
                        if choices:
                            prefix = choices[0]
                            choice = (prefix, min(buckets[prefix]))
                            break
                    if choice is None:
                        raise ValueError("A instruction has no ambiguous prefix")
                    prefix, (commit_id, asset) = choice
                    defns[prefix_var] = prefix
                    defns[asset_var] = asset
                else:
                    raise ValueError("bad test line at {}".format(line_num))
        print(format_test_status(
            base, "OK ({}pts/{}pts)".format(test_score, test_score)))
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
        
        project_root = dirname(dirname(abspath(__file__)))
        search_root = abspath(prog_dir) if prog_dir is not None else project_root
        possible_paths = [search_root] if isfile(search_root) else [
            join(search_root, 'build', 'gitlite'),
            join(search_root, 'gitlite'),
        ]
        cpp_executable_path = next((path for path in possible_paths
                                    if isfile(path)), None)
        if cpp_executable_path:
            CPP_EXECUTABLE = cpp_executable_path
        else:
            print("Could not find gitlite C++ executable.", file=sys.stderr)
            print("Looked for it at:", file=sys.stderr)
            for path in possible_paths:
                print("  {}".format(path), file=sys.stderr)
            print("Please compile gitlite first or specify --progdir.", file=sys.stderr)
            sys.exit(1)
    except GetoptError:
        Usage()
    if not files:
        print(USAGE)
        sys.exit(0)

    # Each run reports only failures from that run.
    if exists("out.txt"):
        remove("out.txt")

    requested_paths = {}
    for path in files:
        if exists(path):
            requested_paths[splitext(basename(path))[0]] = path

    # Include prerequisites even when the caller asks for a single advanced
    # test. Only explicitly requested tests contribute to the reported score.
    search_dirs = list(dict.fromkeys(dirname(path) for path in files))
    all_paths = dict(requested_paths)
    ordered_names = []
    visiting = set()
    visited = set()

    def locate_test(name):
        if name in all_paths:
            return all_paths[name]
        for directory in search_dirs:
            candidate = join(directory, name + '.in')
            if exists(candidate):
                all_paths[name] = candidate
                return candidate
        raise ValueError("missing prerequisite test {}".format(name))

    def visit_test(name):
        if name in visited:
            return
        if name in visiting:
            raise ValueError("cyclic test dependency involving {}".format(name))
        visiting.add(name)
        locate_test(name)
        for dependency in TEST_DEPENDENCIES.get(name, []):
            visit_test(dependency)
        visiting.remove(name)
        visited.add(name)
        ordered_names.append(name)

    try:
        grouped_request_order = [
            name
            for test_names in SUBTASKS.values()
            for name in test_names
            if name in requested_paths
        ]
        grouped_request_order.extend(
            name for name in requested_paths if name not in TEST_TO_SUBTASK)
        for name in grouped_request_order:
            visit_test(name)
    except ValueError as excp:
        print("FAILED ({})".format(excp), file=sys.stderr)
        sys.exit(1)

    num_tests = len(requested_paths)
    errs = 0
    fails = 0
    skips = 0
    total_score = 0
    earned_score = 0
    failed_tests = []
    skipped_tests = []
    outcomes = {}

    # Track subtask scores
    subtask_scores = {}
    for subtask_name, test_list in SUBTASKS.items():
        subtask_scores[subtask_name] = {'earned': 0, 'total': 0, 'tests': []}

    for test_name in requested_paths:
        test_points = TEST_SCORES.get(test_name, 0)
        total_score += test_points
        for subtask_name, test_list in SUBTASKS.items():
            if test_name in test_list:
                subtask_scores[subtask_name]['total'] += test_points
                break

    for test_name in ordered_names:
        test = all_paths[test_name]
        requested = test_name in requested_paths
        test_points = TEST_SCORES.get(test_name, 0)
        failed_dependency = next(
            (dependency for dependency in TEST_DEPENDENCIES.get(test_name, [])
             if outcomes.get(dependency) != 'passed'), None)
        if failed_dependency is not None:
            outcomes[test_name] = 'skipped'
            if requested:
                skips += 1
                skipped_tests.append(test_name)
                print(format_test_status(
                    test_name,
                    "SKIPPED (prerequisite {} did not pass) (0pts/{}pts)"
                    .format(failed_dependency, test_points)))
            continue
        try:
            result = doTest(test)
            success = result[0] if isinstance(result, tuple) else bool(result)
            outcomes[test_name] = 'passed' if success else 'failed'
            if not requested:
                continue
            current_subtask = next(
                (name for name, members in SUBTASKS.items() if test_name in members), None)
            if success:
                earned_score += test_points
                if current_subtask:
                    subtask_scores[current_subtask]['earned'] += test_points
                    subtask_scores[current_subtask]['tests'].append((test_name, True, test_points))
            else:
                errs += 1
                failed_tests.append(test_name)
                if current_subtask:
                    subtask_scores[current_subtask]['tests'].append((test_name, False, 0))
                if type(show) is int:
                    show -= 1
        except ValueError as excp:
            outcomes[test_name] = 'failed'
            if requested:
                print(format_test_status(
                    test_name, "FAILED ({})".format(excp.args[0])))
                fails += 1
                failed_tests.append(test_name)

    # Every non-Bonus raw point is one final point. Bonus credits whichever of
    # its two independent choices earned more; partial scores do not combine.
    bonus_results = {
        test_name: points
        for test_name, passed, points in subtask_scores["Bonus"]['tests']
        if passed
    }
    bonus_category_scores = {
        category: sum(bonus_results.get(test_name, 0) for test_name in tests)
        for category, tests in BONUS_CATEGORIES.items()
    }
    bonus_credited = max(bonus_category_scores.values(), default=0)
    earned_score = sum(
        score['earned'] for name, score in subtask_scores.items() if name != "Bonus"
    ) + bonus_credited

    print()
    print("Ran {} tests.".format(num_tests))
    print("Bonus category scores: {}; credited {} pts (higher category).".format(
        ", ".join("{} {} pts".format(name, score)
                  for name, score in bonus_category_scores.items()),
        bonus_credited))
    print("Total Score: {:g} pts".format(earned_score))
    
    if errs == fails == skips == 0:
        print("All tests passed!")
    else:
        passed_tests = num_tests - errs - fails - skips
        print("{} tests passed, {} tests failed, {} tests skipped."
              .format(passed_tests, errs + fails, skips))
        if failed_tests:
            print("Failed tests: {}".format(", ".join(failed_tests)))
        if skipped_tests:
            print("Skipped tests: {}".format(", ".join(skipped_tests)))
        sys.exit(1)
