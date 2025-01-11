from tempfile import NamedTemporaryFile, TemporaryDirectory
import re
import subprocess

import config


def fetch_code(source: str) -> tuple[str, str]:
    """
    Fetches code and a language name from a source string.\n
    Language name is converted to lowercase.\n
    Very first line (containing language name) is removed from the result.\n
    Raises `ValueError` if source does not contain a codeblock.\n
    Returns a tuple of `(code, language)` on success.
    """
    if not re.search(r'```.+\n(.|\n)+```', source):
        raise ValueError('Missing proper codeblock')
    
    language = re.search(r'(?<=```).+(?=\n)', source).group()
    code = re.search(r'(?<=```)(.|\n)+(?=```)', source).group().replace(f'{language}\n', '', 1)

    return code, language.lower()


def decode_output(process: subprocess.CompletedProcess) -> tuple[str, str]:
    """
    Attempts to decode stdout and stderr of a process.\n
    Returns a tuple of `(stdout, stderr)`.
    """
    try:
        return process.stdout.decode(), process.stderr.decode()
    except UnicodeDecodeError:
        try:
            return process.stdout.decode('cp1251'), process.stderr.decode('cp1251')
        except UnicodeDecodeError:
            pass
    return '', 'Could not decode output of a process'


def run_interpreter(code: str, tmpdir: TemporaryDirectory, extension: str, options: tuple[str], timeout: float) -> tuple[int, str, str]:
    """
    Runs an interpreter (depends on the given options).\n
    Provided code is written into a temporary file, and the filename is added as the last option.\n
    Raises `subprocess.TimeoutExpired` if process didn't exit in time.\n
    Returns a tuple of `(exit_code, stdout, stderr)` on success.
    """
    with NamedTemporaryFile('w', encoding='utf-8', suffix=extension, dir=tmpdir, delete=False) as tmpfile:
        code_path = tmpfile.name
        tmpfile.write(code)

    process = subprocess.run(options + (code_path,), cwd=tmpdir, capture_output=True, timeout=timeout)
    stdout, stderr = decode_output(process)

    return process.returncode, stdout, stderr


def run_compiler(code: str, tmpdir: TemporaryDirectory, extension: str, options: tuple[str], timeout: float, executable: str) -> tuple[int, str, str]:
    """
    Runs a compiler (depends on the given options).\n
    Provided code is written into a temporary file, and the filename is added as the last option.\n
    On successful compilation, executes `executable`.\n
    Raises `subprocess.TimeoutExpired` if any process didn't exit in time.\n
    Returns a tuple of `(exit_code, stdout, stderr)` on success or on compilation failure.
    """
    with NamedTemporaryFile('w', encoding='utf-8', suffix=extension, dir=tmpdir, delete=False) as tmpfile:
        code_path = tmpfile.name
        tmpfile.write(code)

    compiler = subprocess.run(options + (code_path,), cwd=tmpdir, capture_output=True, timeout=timeout)
    stdout, stderr = decode_output(compiler)

    if compiler.returncode != 0:
        return compiler.returncode, stdout, stderr

    process = subprocess.run((fr'{tmpdir}\{executable}',), cwd=tmpdir, capture_output=True, timeout=timeout)
    stdout, stderr = decode_output(process)

    return process.returncode, stdout, stderr


def run(code: str, tmpdir: TemporaryDirectory, language: str) -> tuple[int, str, str]:
    """
    Executes code using the appropriate compiler or interpreter.\n
    Raises `subprocess.TimeoutExpired` if any process didn't exit in time.\n
    Raises `ValueError` if language is invalid.\n
    Returns a tuple of `(exit_code, stdout, stderr)` on success or on compilation failure.
    """
    if language in ('python', 'py'):
        return run_interpreter(code, tmpdir, '.py', ('python',), config.TIMEOUT)
    elif language in ('ruby', 'rb'):
        return run_interpreter(code, tmpdir, '.rb', ('ruby',), config.TIMEOUT)
    elif language in ('javascript', 'js'):
        return run_interpreter(code, tmpdir, '.js', ('node',), config.TIMEOUT)
    elif language in ('ccl',):
        return run_interpreter(code, tmpdir, '.ccl', ('python', config.CCL_PATH), config.TIMEOUT)
    elif language in ('wilc',):
        return run_interpreter(code, tmpdir, '.wilc', ('python', '-m', 'wilc-lang'), config.TIMEOUT)
    elif language in ('c',):
        return run_compiler(code, tmpdir, '.c', ('gcc', '-o', 'out.exe'), config.TIMEOUT, 'out.exe')
    elif language in ('cpp', 'c++'):
        return run_compiler(code, tmpdir, '.cpp', ('g++', '-o', 'out.exe'), config.TIMEOUT, 'out.exe')
    elif language in ('cs', 'c#', 'csharp'):
        return run_compiler(code, tmpdir, '.cs', ('csc', '/out:out.exe'), config.TIMEOUT, 'out.exe')
    elif language in ('rust', 'rs'):
        return run_compiler(code, tmpdir, '.rs', ('rustc', '-o', 'out.exe'), config.TIMEOUT, 'out.exe')
    elif language in ('haskell', 'hs'):
        return run_compiler(code, tmpdir, '.hs', (config.GHC_PATH, '-o', 'out.exe'), config.TIMEOUT, 'out.exe')
    else:
        raise ValueError(f'Language `{language}` is not recognised')
